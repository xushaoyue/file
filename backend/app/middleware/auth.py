import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.auth_service import verify_token
from backend.app.services.user_service import get_user_by_id

logger = logging.getLogger("audit.auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户。

    Args:
        token: OAuth2 Bearer token
        db: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 如果 token 无效或用户不存在
    """
    logger.info(f"收到 token: {token[:50]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, "access")
    logger.info(f"验证后的 payload: {payload}")
    
    if payload is None:
        logger.warning("Token 验证失败")
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        logger.warning("Payload 中没有 sub")
        raise credentials_exception
    
    try:
        user_id: int = int(user_id_str)
    except ValueError:
        logger.warning(f"无效的 user_id: {user_id_str}")
        raise credentials_exception

    user = get_user_by_id(db, user_id)
    if user is None:
        logger.warning(f"用户 {user_id} 不存在")
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被停用"
        )

    logger.info(f"成功获取用户: {user.username}")
    return user


def get_current_active_user(current_user = Depends(get_current_user)):
    """
    获取当前活跃用户。

    Args:
        current_user: 当前用户对象

    Returns:
        User: 当前活跃用户对象
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被停用"
        )
    return current_user


def require_admin(current_user = Depends(get_current_user)):
    """
    要求用户具有管理员权限。

    Args:
        current_user: 当前用户对象

    Returns:
        User: 管理员用户对象

    Raises:
        HTTPException: 如果用户不是管理员
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
