from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user
from backend.app.schemas.ssh_key import SSHKeyCreate, SSHKeyResponse
from backend.app.schemas.common import ResponseModel
from backend.app.services.ssh_key_service import (
    add_ssh_key,
    list_ssh_keys,
    delete_ssh_key
)
from backend.app.services.audit_service import log_event
from backend.app.models.user import User

router = APIRouter(prefix="/api/v1/keys", tags=["SSH 密钥管理"])


def get_client_info(request: Request) -> tuple:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent


def extract_key_type(public_key: str) -> str:
    """
    从公钥字符串中提取密钥类型。

    Args:
        public_key: SSH 公钥字符串

    Returns:
        str: 密钥类型（如 rsa, ed25519）
    """
    if not public_key:
        return "unknown"

    parts = public_key.strip().split()
    if len(parts) >= 1:
        key_type = parts[0]
        if "rsa" in key_type.lower():
            return "rsa"
        elif "ed25519" in key_type.lower():
            return "ed25519"
        elif "ecdsa" in key_type.lower():
            return "ecdsa"
        elif "ssh-rsa" in key_type.lower():
            return "rsa"
        elif "ssh-ed25519" in key_type.lower():
            return "ed25519"
        return key_type

    return "unknown"


@router.get("", response_model=dict)
async def list_user_ssh_keys(
    request: Request,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    列出当前用户的 SSH 密钥。

    Args:
        request: HTTP 请求对象
        is_active: 是否只返回激活的密钥
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        dict: 包含 SSH 密钥列表
    """
    client_ip, user_agent = get_client_info(request)

    ssh_keys = list_ssh_keys(db, current_user.id, is_active=is_active)

    log_event(
        db,
        event_data={
            "event_type": "ssh_key",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "list_keys",
            "file_path": "/keys",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return {
        "keys": [
            SSHKeyResponse(
                id=ssh_key.id,
                key_name=ssh_key.key_name,
                key_type=ssh_key.key_type,
                fingerprint=ssh_key.fingerprint,
                created_at=ssh_key.created_at,
                last_used=ssh_key.last_used,
                is_active=ssh_key.is_active
            )
            for ssh_key in ssh_keys
        ],
        "total": len(ssh_keys)
    }


@router.post("", response_model=SSHKeyResponse)
async def add_user_ssh_key(
    request: Request,
    key_data: SSHKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加新的 SSH 公钥。

    Args:
        request: HTTP 请求对象
        key_data: SSH 密钥数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        SSHKeyResponse: 创建的 SSH 密钥信息
    """
    client_ip, user_agent = get_client_info(request)

    key_type = extract_key_type(key_data.public_key)

    fingerprint = None
    try:
        import hashlib
        import base64
        parts = key_data.public_key.strip().split()
        if len(parts) >= 2:
            key_data_bytes = base64.b64decode(parts[1])
            hash_obj = hashlib.sha256(key_data_bytes)
            fingerprint = base64.b64encode(hash_obj.digest()).decode('utf-8')
    except Exception:
        pass

    ssh_key = add_ssh_key(
        db,
        user_id=current_user.id,
        key_name=key_data.key_name,
        public_key=key_data.public_key,
        key_type=key_type,
        fingerprint=fingerprint
    )

    log_event(
        db,
        event_data={
            "event_type": "ssh_key",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "add_key",
            "file_path": "/keys",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return SSHKeyResponse(
        id=ssh_key.id,
        key_name=ssh_key.key_name,
        key_type=ssh_key.key_type,
        fingerprint=ssh_key.fingerprint,
        created_at=ssh_key.created_at,
        last_used=ssh_key.last_used,
        is_active=ssh_key.is_active
    )


@router.delete("/{key_id}", response_model=ResponseModel)
async def delete_user_ssh_key(
    request: Request,
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除 SSH 密钥。

    Args:
        request: HTTP 请求对象
        key_id: 要删除的密钥 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 删除结果响应
    """
    client_ip, user_agent = get_client_info(request)

    success = delete_ssh_key(db, key_id, current_user.id)

    if not success:
        log_event(
            db,
            event_data={
                "event_type": "ssh_key",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "delete_key",
                "file_path": f"/keys/{key_id}",
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": "SSH 密钥不存在或不属于当前用户"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSH 密钥不存在或不属于当前用户"
        )

    log_event(
        db,
        event_data={
            "event_type": "ssh_key",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "delete_key",
            "file_path": f"/keys/{key_id}",
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"SSH 密钥 {key_id} 已成功删除",
        data={"key_id": key_id}
    )
