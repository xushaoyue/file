from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user, require_admin
from backend.app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserPermission
)
from backend.app.schemas.common import ResponseModel
from backend.app.services import user_service
from backend.app.services.audit_service import log_event
from backend.app.models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


def get_client_info(request: Request) -> tuple:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent


@router.get("", response_model=dict)
async def list_users(
    request: Request,
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回的最大记录数"),
    role: Optional[str] = Query(default=None, description="按角色筛选"),
    is_active: Optional[bool] = Query(default=None, description="按激活状态筛选"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    列出所有用户（管理员专用）。

    Args:
        request: HTTP 请求对象
        skip: 跳过的记录数
        limit: 返回的最大记录数
        role: 按角色筛选
        is_active: 按激活状态筛选
        current_user: 当前管理员用户对象
        db: 数据库会话

    Returns:
        dict: 包含用户列表和总数
    """
    client_ip, user_agent = get_client_info(request)

    users = user_service.list_users(
        db,
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active
    )

    total = user_service.count_users(
        db,
        role=role,
        is_active=is_active
    )

    user_responses = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            must_change_password=user.must_change_password
        )
        for user in users
    ]

    log_event(
        db,
        event_data={
            "event_type": "user_management",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "list_users",
            "file_path": "/users",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return {
        "users": user_responses,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=UserResponse)
async def create_user_endpoint(
    request: Request,
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    创建新用户（管理员专用）。

    Args:
        request: HTTP 请求对象
        user_data: 用户创建数据
        current_user: 当前管理员用户对象
        db: 数据库会话

    Returns:
        UserResponse: 创建的用户信息
    """
    client_ip, user_agent = get_client_info(request)

    try:
        user = user_service.create_user(
            db,
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            role=user_data.role
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    log_event(
        db,
        event_data={
            "event_type": "user_management",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "create_user",
            "file_path": f"/users/{user.id}",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        must_change_password=user.must_change_password
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户详情。

    Args:
        user_id: 用户 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        UserResponse: 用户信息
    """
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看此用户信息"
        )

    user = user_service.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        must_change_password=user.must_change_password
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户信息。

    Args:
        request: HTTP 请求对象
        user_id: 用户 ID
        user_data: 用户更新数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        UserResponse: 更新后的用户信息
    """
    client_ip, user_agent = get_client_info(request)

    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此用户信息"
        )

    if current_user.role != "admin":
        if user_data.role is not None or user_data.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="普通用户不能修改角色或激活状态"
            )

    update_dict = user_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有要更新的字段"
        )

    user = user_service.update_user(db, user_id, update_dict)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    log_event(
        db,
        event_data={
            "event_type": "user_management",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "update_user",
            "file_path": f"/users/{user_id}",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        must_change_password=user.must_change_password
    )


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    删除用户（管理员专用）。

    Args:
        request: HTTP 请求对象
        user_id: 用户 ID
        current_user: 当前管理员用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 删除结果响应
    """
    client_ip, user_agent = get_client_info(request)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )

    success = user_service.delete_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    log_event(
        db,
        event_data={
            "event_type": "user_management",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "delete_user",
            "file_path": f"/users/{user_id}",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"用户 {user_id} 已成功删除",
        data={"user_id": user_id}
    )


@router.put("/{user_id}/permissions", response_model=ResponseModel)
async def set_user_permissions(
    request: Request,
    user_id: int,
    permission_data: UserPermission,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    设置用户权限（管理员专用）。

    Args:
        request: HTTP 请求对象
        user_id: 用户 ID
        permission_data: 权限数据
        current_user: 当前管理员用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 设置结果响应
    """
    client_ip, user_agent = get_client_info(request)

    user = user_service.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    from backend.app.services.permission_service import set_user_permissions

    success = set_user_permissions(
        db,
        user_id=user_id,
        permissions=[
            {
                "allowed_path": perm.allowed_path,
                "can_read": perm.can_read,
                "can_write": perm.can_write,
                "can_delete": perm.can_delete,
                "can_download": perm.can_download
            }
            for perm in permission_data.permissions
        ]
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置权限失败"
        )

    log_event(
        db,
        event_data={
            "event_type": "user_management",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "set_permissions",
            "file_path": f"/users/{user_id}/permissions",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"用户 {user_id} 的权限已成功更新",
        data={"user_id": user_id, "permissions_count": len(permission_data.permissions)}
    )
