from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.permission import Permission
from backend.app.models.user import User


def check_permission(user: User, path: str, operation: str) -> bool:
    """
    检查用户对指定路径是否具有指定操作的权限。

    Args:
        user: 用户对象
        path: 文件路径
        operation: 操作类型 ("read", "write", "delete", "download")

    Returns:
        bool: 是否具有权限
    """
    if user.role == "admin":
        return True

    operation_map = {
        "read": "can_read",
        "write": "can_write",
        "delete": "can_delete",
        "download": "can_download"
    }

    permission_field = operation_map.get(operation)
    if not permission_field:
        return False

    for permission in user.permissions:
        if _path_matches(path, permission.allowed_path):
            return getattr(permission, permission_field, False)

    return False


def _path_matches(file_path: str, allowed_path: str) -> bool:
    """
    检查文件路径是否匹配允许的路径模式。

    支持通配符匹配：
    - "*" 匹配任意字符
    - "**" 匹配路径中的任意层级

    Args:
        file_path: 文件路径
        allowed_path: 允许的路径模式

    Returns:
        bool: 是否匹配
    """
    import re
    from pathlib import Path

    file_path = Path(file_path).as_posix()
    allowed_path = Path(allowed_path).as_posix()
    file_path = re.sub(r'^[A-Za-z]:', '', file_path)

    if allowed_path.endswith("*"):
        pattern = "^" + re.escape(allowed_path.rstrip("*"))
        if allowed_path.endswith("**"):
            pattern = "^" + re.escape(allowed_path.rstrip("**")) + ".*"
        return bool(re.match(pattern, file_path))
    elif "**" in allowed_path:
        pattern = allowed_path.replace("**", ".*")
        return bool(re.match(f"^{pattern}$", file_path))
    else:
        return file_path == allowed_path or file_path.startswith(allowed_path + "/")


def get_user_permissions(db: Session, user_id: int) -> List[Permission]:
    """
    获取用户的所有权限记录。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        List[Permission]: 权限对象列表
    """
    return db.query(Permission).filter(Permission.user_id == user_id).all()


def get_permission_by_id(db: Session, permission_id: int) -> Optional[Permission]:
    """
    根据权限 ID 获取权限记录。

    Args:
        db: 数据库会话
        permission_id: 权限 ID

    Returns:
        Optional[Permission]: 权限对象，不存在返回 None
    """
    return db.query(Permission).filter(Permission.id == permission_id).first()


def get_permission_by_path(db: Session, user_id: int, path: str) -> Optional[Permission]:
    """
    获取用户对指定路径的权限记录。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        path: 文件路径

    Returns:
        Optional[Permission]: 权限对象，不存在返回 None
    """
    permissions = db.query(Permission).filter(
        Permission.user_id == user_id
    ).all()

    for permission in permissions:
        if _path_matches(path, permission.allowed_path):
            return permission

    return None


def set_user_permissions(db: Session, user_id: int,
                         permissions: List[Dict[str, Any]]) -> List[Permission]:
    """
    批量设置用户的权限。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        permissions: 权限配置列表，每项包含 path 和权限字段

    Returns:
        List[Permission]: 设置后的权限对象列表
    """
    existing = db.query(Permission).filter(Permission.user_id == user_id).all()
    for perm in existing:
        db.delete(perm)

    db.commit()

    new_permissions = []
    for perm_data in permissions:
        permission = Permission(
            user_id=user_id,
            allowed_path=perm_data.get("path", perm_data.get("allowed_path")),
            can_read=perm_data.get("can_read", False),
            can_write=perm_data.get("can_write", False),
            can_delete=perm_data.get("can_delete", False),
            can_download=perm_data.get("can_download", False)
        )
        db.add(permission)
        new_permissions.append(permission)

    db.commit()
    for perm in new_permissions:
        db.refresh(perm)

    return new_permissions


def add_permission(db: Session, user_id: int, path: str,
                    can_read: bool = True, can_write: bool = False,
                    can_delete: bool = False, can_download: bool = True,
                    replace: bool = False) -> Optional[Permission]:
    """
    为用户添加权限。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        path: 允许的路径
        can_read: 是否允许读取
        can_write: 是否允许写入
        can_delete: 是否允许删除
        can_download: 是否允许下载
        replace: 是否替换已存在的同路径权限

    Returns:
        Optional[Permission]: 创建的权限对象
    """
    existing = get_permission_by_path(db, user_id, path)

    if existing:
        if replace:
            existing.can_read = can_read
            existing.can_write = can_write
            existing.can_delete = can_delete
            existing.can_download = can_download
            db.commit()
            db.refresh(existing)
            return existing
        return existing

    permission = Permission(
        user_id=user_id,
        allowed_path=path,
        can_read=can_read,
        can_write=can_write,
        can_delete=can_delete,
        can_download=can_download
    )

    db.add(permission)
    db.commit()
    db.refresh(permission)

    return permission


def update_permission(db: Session, permission_id: int,
                      can_read: Optional[bool] = None,
                      can_write: Optional[bool] = None,
                      can_delete: Optional[bool] = None,
                      can_download: Optional[bool] = None) -> Optional[Permission]:
    """
    更新权限记录。

    Args:
        db: 数据库会话
        permission_id: 权限 ID
        can_read: 是否允许读取
        can_write: 是否允许写入
        can_delete: 是否允许删除
        can_download: 是否允许下载

    Returns:
        Optional[Permission]: 更新后的权限对象
    """
    permission = get_permission_by_id(db, permission_id)
    if not permission:
        return None

    if can_read is not None:
        permission.can_read = can_read
    if can_write is not None:
        permission.can_write = can_write
    if can_delete is not None:
        permission.can_delete = can_delete
    if can_download is not None:
        permission.can_download = can_download

    db.commit()
    db.refresh(permission)

    return permission


def remove_permission(db: Session, permission_id: int) -> bool:
    """
    删除权限记录。

    Args:
        db: 数据库会话
        permission_id: 权限 ID

    Returns:
        bool: 是否成功删除
    """
    permission = get_permission_by_id(db, permission_id)
    if not permission:
        return False

    db.delete(permission)
    db.commit()

    return True


def remove_user_all_permissions(db: Session, user_id: int) -> int:
    """
    删除用户的所有权限记录。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        int: 删除的权限数量
    """
    count = db.query(Permission).filter(Permission.user_id == user_id).delete()
    db.commit()

    return count


def copy_permissions(db: Session, from_user_id: int,
                      to_user_id: int) -> List[Permission]:
    """
    复制用户的权限到另一个用户。

    Args:
        db: 数据库会话
        from_user_id: 源用户 ID
        to_user_id: 目标用户 ID

    Returns:
        List[Permission]: 复制后的权限列表
    """
    source_permissions = get_user_permissions(db, from_user_id)

    permissions_data = [
        {
            "path": perm.allowed_path,
            "can_read": perm.can_read,
            "can_write": perm.can_write,
            "can_delete": perm.can_delete,
            "can_download": perm.can_download
        }
        for perm in source_permissions
    ]

    return set_user_permissions(db, to_user_id, permissions_data)


def list_permissions(db: Session, skip: int = 0, limit: int = 100,
                     user_id: Optional[int] = None,
                     path_prefix: Optional[str] = None) -> List[Permission]:
    """
    列出权限记录，支持分页和筛选。

    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数
        user_id: 按用户 ID 筛选
        path_prefix: 按路径前缀筛选

    Returns:
        List[Permission]: 符合条件的权限列表
    """
    query = db.query(Permission)

    if user_id is not None:
        query = query.filter(Permission.user_id == user_id)

    if path_prefix:
        query = query.filter(Permission.allowed_path.startswith(path_prefix))

    return query.offset(skip).limit(limit).all()
