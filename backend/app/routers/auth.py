from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user, oauth2_scheme
from backend.app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse
)
from backend.app.schemas.common import ResponseModel, ErrorResponse
from backend.app.services.auth_service import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    blacklist_token,
    create_session,
    revoke_all_user_sessions
)
from backend.app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_username
)
from backend.app.services.audit_service import log_event
from backend.app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


def get_client_info(request: Request) -> tuple:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录接口。

    Args:
        request: HTTP 请求对象
        form_data: OAuth2 密码表单数据
        db: 数据库会话

    Returns:
        TokenResponse: 包含访问令牌和刷新令牌的响应
    """
    client_ip, user_agent = get_client_info(request)

    user, error_message = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        log_event(
            db,
            event_data={
                "event_type": "login",
                "username": form_data.username,
                "operation": "login",
                "file_path": "/auth",
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": error_message or "用户名或密码错误"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )

    session_id = f"{user.id}_{datetime.now(timezone.utc).timestamp()}"
    create_session(db, user.id, session_id, client_ip, user_agent)

    log_event(
        db,
        event_data={
            "event_type": "login",
            "user_id": user.id,
            "username": user.username,
            "user_role": user.role,
            "operation": "login",
            "file_path": "/auth",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent,
            "session_id": session_id
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.security.access_token_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册接口。

    Args:
        request: HTTP 请求对象
        register_data: 注册数据
        db: 数据库会话

    Returns:
        TokenResponse: 包含访问令牌和刷新令牌的响应
    """
    client_ip, user_agent = get_client_info(request)

    if register_data.password != register_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不匹配"
        )

    try:
        user = create_user(
            db,
            username=register_data.username,
            password=register_data.password,
            email=register_data.email,
            role="user"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )

    session_id = f"{user.id}_{datetime.now(timezone.utc).timestamp()}"
    create_session(db, user.id, session_id, client_ip, user_agent)

    log_event(
        db,
        event_data={
            "event_type": "register",
            "user_id": user.id,
            "username": user.username,
            "user_role": user.role,
            "operation": "register",
            "file_path": "/auth",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent,
            "session_id": session_id
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.security.access_token_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌。

    Args:
        refresh_data: 刷新令牌数据
        db: 数据库会话

    Returns:
        TokenResponse: 新的访问令牌和刷新令牌
    """
    payload = verify_token(refresh_data.refresh_token, "refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    username = payload.get("username")

    from backend.app.services.user_service import get_user_by_id
    user = get_user_by_id(db, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被停用"
        )

    blacklist_token(refresh_data.refresh_token)

    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.id, "username": user.username}
    )

    log_event(
        db,
        event_data={
            "event_type": "refresh",
            "user_id": user.id,
            "username": user.username,
            "user_role": user.role,
            "operation": "refresh_token",
            "file_path": "/auth",
            "status": "success"
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.security.access_token_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/logout")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    用户登出接口。

    Args:
        request: HTTP 请求对象
        token: 当前访问令牌
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 登出成功响应
    """
    client_ip, user_agent = get_client_info(request)

    blacklist_token(token)

    revoked_count = revoke_all_user_sessions(db, current_user.id)

    log_event(
        db,
        event_data={
            "event_type": "logout",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "logout",
            "file_path": "/auth",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"成功登出，已撤销 {revoked_count} 个会话",
        data={"revoked_sessions": revoked_count}
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    获取当前用户信息。

    Args:
        current_user: 当前用户对象

    Returns:
        UserResponse: 当前用户信息
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )
