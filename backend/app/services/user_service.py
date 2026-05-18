from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.services.auth_service import get_password_hash, verify_password
from backend.app.config import settings


def create_user(db: Session, username: str, password: str,
                email: Optional[str] = None, full_name: Optional[str] = None,
                role: str = "user", **extra_fields) -> User:
    """
    创建新用户。

    Args:
        db: 数据库会话
        username: 用户名（唯一）
        password: 明文密码，将自动哈希
        email: 邮箱地址（可选，唯一）
        full_name: 用户全名（可选）
        role: 用户角色，默认为 "user"
        **extra_fields: 其他可选字段

    Returns:
        User: 创建的用户对象

    Raises:
        ValueError: 如果用户名或邮箱已存在
    """
    existing_user = db.query(User).filter(
        (User.username == username) | (email and User.email == email)
    ).first()

    if existing_user:
        if existing_user.username == username:
            raise ValueError("用户名已存在")
        raise ValueError("邮箱已被使用")

    user = User(
        username=username,
        password_hash=get_password_hash(password),
        email=email,
        full_name=full_name,
        role=role,
        is_active=True,
        must_change_password=settings.admin.must_change_password if role == "admin" else False,
        failed_attempts=0,
        locked_until=None,
        **extra_fields
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    根据用户 ID 获取用户。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        Optional[User]: 找到的用户对象，不存在返回 None
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    根据用户名获取用户。

    Args:
        db: 数据库会话
        username: 用户名

    Returns:
        Optional[User]: 找到的用户对象，不存在返回 None
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    根据邮箱获取用户。

    Args:
        db: 数据库会话
        email: 邮箱地址

    Returns:
        Optional[User]: 找到的用户对象，不存在返回 None
    """
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session, skip: int = 0, limit: int = 100,
               role: Optional[str] = None,
               is_active: Optional[bool] = None) -> List[User]:
    """
    列出用户，支持分页和筛选。

    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数
        role: 按角色筛选
        is_active: 按激活状态筛选

    Returns:
        List[User]: 符合条件的用户列表
    """
    query = db.query(User)

    if role is not None:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


def count_users(db: Session, role: Optional[str] = None,
                is_active: Optional[bool] = None) -> int:
    """
    统计用户数量。

    Args:
        db: 数据库会话
        role: 按角色筛选
        is_active: 按激活状态筛选

    Returns:
        int: 符合条件的用户总数
    """
    query = db.query(User)

    if role is not None:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.count()


def update_user(db: Session, user_id: int,
                data: Dict[str, Any]) -> Optional[User]:
    """
    更新用户信息。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        data: 要更新的字段字典

    Returns:
        Optional[User]: 更新后的用户对象，不存在返回 None
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    update_fields = {}
    for key, value in data.items():
        if key == "password":
            update_fields["password_hash"] = get_password_hash(value)
        elif key in ["username", "email", "full_name", "role", "is_active",
                     "must_change_password", "last_login"]:
            update_fields[key] = value

    if update_fields:
        for key, value in update_fields.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(user)

    return user


def delete_user(db: Session, user_id: int) -> bool:
    """
    删除用户。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        bool: 是否成功删除
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True


def check_login_attempts(user: User) -> bool:
    """
    检查用户登录尝试是否被锁定。

    Args:
        user: 用户对象

    Returns:
        bool: True 表示未锁定可以登录，False 表示被锁定
    """
    if user.locked_until is None:
        return True

    if datetime.now(timezone.utc).replace(tzinfo=None) > user.locked_until:
        return True

    return False


def increment_failed_attempts(db: Session, user: User) -> User:
    """
    增加用户失败登录尝试次数。

    Args:
        db: 数据库会话
        user: 用户对象

    Returns:
        User: 更新后的用户对象
    """
    user.failed_attempts += 1

    if user.failed_attempts >= settings.security.max_login_attempts:
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=settings.security.lockout_duration_minutes
        )

    db.commit()
    db.refresh(user)

    return user


def reset_failed_attempts(db: Session, user: User) -> User:
    """
    重置用户失败登录尝试次数。

    Args:
        db: 数据库会话
        user: 用户对象

    Returns:
        User: 更新后的用户对象
    """
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, username: str, password: str) -> tuple[Optional[User], Optional[str]]:
    """
    验证用户凭据。

    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        tuple[Optional[User], Optional[str]]: (用户对象, 错误信息)
        - 验证成功返回 (user, None)
        - 验证失败返回 (None, 错误信息)
    """
    user = get_user_by_username(db, username)

    if not user:
        return None, "用户名或密码错误"

    if not user.is_active:
        return None, "用户已被停用，请联系管理员"

    if not check_login_attempts(user):
        # 计算剩余锁定时间
        remaining = user.locked_until - datetime.now(timezone.utc).replace(tzinfo=None)
        remaining_minutes = max(1, int(remaining.total_seconds() / 60))
        return None, f"账号已被锁定，请 {remaining_minutes} 分钟后重试"

    if verify_password(password, user.password_hash):
        reset_failed_attempts(db, user)
        user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        return user, None

    increment_failed_attempts(db, user)
    
    # 检查是否因为这次失败尝试导致锁定
    if not check_login_attempts(user):
        remaining = user.locked_until - datetime.now(timezone.utc).replace(tzinfo=None)
        remaining_minutes = max(1, int(remaining.total_seconds() / 60))
        return None, f"密码错误次数过多，账号已被锁定，请 {remaining_minutes} 分钟后重试"
    
    return None, "用户名或密码错误"


def change_user_password(db: Session, user_id: int, old_password: str,
                         new_password: str) -> bool:
    """
    修改用户密码。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        old_password: 旧密码
        new_password: 新密码

    Returns:
        bool: 是否成功修改
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    if not verify_password(old_password, user.password_hash):
        return False

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return True


def force_change_password(db: Session, user_id: int, new_password: str) -> bool:
    """
    强制修改用户密码（管理员操作）。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        new_password: 新密码

    Returns:
        bool: 是否成功修改
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return True


def activate_user(db: Session, user_id: int) -> Optional[User]:
    """
    激活用户账户。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        Optional[User]: 激活后的用户对象
    """
    return update_user(db, user_id, {"is_active": True})


def deactivate_user(db: Session, user_id: int) -> Optional[User]:
    """
    停用用户账户。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        Optional[User]: 停用后的用户对象
    """
    return update_user(db, user_id, {"is_active": False})


def unlock_user(db: Session, user_id: int) -> Optional[User]:
    """
    解除用户账户锁定。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        Optional[User]: 更新后的用户对象
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    user.locked_until = None
    user.failed_attempts = 0
    db.commit()
    db.refresh(user)

    return user
