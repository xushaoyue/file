from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.ssh_key import SSHKey


def add_ssh_key(db: Session, user_id: int, key_name: str, public_key: str,
                key_type: Optional[str] = None,
                fingerprint: Optional[str] = None) -> SSHKey:
    """
    添加用户的 SSH 公钥。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        key_name: SSH 密钥名称
        public_key: SSH 公钥内容
        key_type: 密钥类型（如 rsa, ed25519）
        fingerprint: 密钥指纹

    Returns:
        SSHKey: 创建的 SSH 密钥对象
    """
    ssh_key = SSHKey(
        user_id=user_id,
        key_name=key_name,
        public_key=public_key,
        key_type=key_type,
        fingerprint=fingerprint,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )

    db.add(ssh_key)
    db.commit()
    db.refresh(ssh_key)

    return ssh_key


def list_ssh_keys(db: Session, user_id: int, is_active: Optional[bool] = None) -> List[SSHKey]:
    """
    列出用户的 SSH 密钥。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        is_active: 是否只返回激活的密钥

    Returns:
        List[SSHKey]: SSH 密钥列表
    """
    query = db.query(SSHKey).filter(SSHKey.user_id == user_id)

    if is_active is not None:
        query = query.filter(SSHKey.is_active == is_active)

    return query.order_by(SSHKey.created_at.desc()).all()


def get_ssh_key_by_id(db: Session, key_id: int) -> Optional[SSHKey]:
    """
    根据 ID 获取 SSH 密钥。

    Args:
        db: 数据库会话
        key_id: 密钥 ID

    Returns:
        Optional[SSHKey]: 找到的 SSH 密钥对象，不存在返回 None
    """
    return db.query(SSHKey).filter(SSHKey.id == key_id).first()


def delete_ssh_key(db: Session, key_id: int, user_id: int) -> bool:
    """
    删除 SSH 密钥。

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        user_id: 用户 ID（用于验证所有权）

    Returns:
        bool: 是否成功删除
    """
    ssh_key = db.query(SSHKey).filter(
        SSHKey.id == key_id,
        SSHKey.user_id == user_id
    ).first()

    if not ssh_key:
        return False

    db.delete(ssh_key)
    db.commit()

    return True


def update_ssh_key_last_used(db: Session, key_id: int) -> Optional[SSHKey]:
    """
    更新 SSH 密钥的最后使用时间。

    Args:
        db: 数据库会话
        key_id: 密钥 ID

    Returns:
        Optional[SSHKey]: 更新的 SSH 密钥对象
    """
    ssh_key = get_ssh_key_by_id(db, key_id)

    if ssh_key:
        ssh_key.last_used = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ssh_key)

    return ssh_key


def deactivate_ssh_key(db: Session, key_id: int, user_id: int) -> Optional[SSHKey]:
    """
    停用 SSH 密钥。

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        user_id: 用户 ID（用于验证所有权）

    Returns:
        Optional[SSHKey]: 停用后的 SSH 密钥对象
    """
    ssh_key = db.query(SSHKey).filter(
        SSHKey.id == key_id,
        SSHKey.user_id == user_id
    ).first()

    if not ssh_key:
        return None

    ssh_key.is_active = False
    db.commit()
    db.refresh(ssh_key)

    return ssh_key


def count_ssh_keys(db: Session, user_id: int, is_active: Optional[bool] = None) -> int:
    """
    统计用户的 SSH 密钥数量。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        is_active: 是否只统计激活的密钥

    Returns:
        int: SSH 密钥数量
    """
    query = db.query(SSHKey).filter(SSHKey.user_id == user_id)

    if is_active is not None:
        query = query.filter(SSHKey.is_active == is_active)

    return query.count()
