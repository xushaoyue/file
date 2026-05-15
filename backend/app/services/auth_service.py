import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.session import Session as SessionModel

logger = logging.getLogger("audit.auth_service")


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.security.bcrypt_cost_factor
)

TOKEN_BLACKLIST: set = set()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配。

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    # bcrypt 最大支持72字节密码，过长的密码需要截断
    return pwd_context.verify(plain_password[:72], hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希处理。

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码字符串
    """
    # bcrypt 最大支持72字节密码，过长的密码需要截断
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌（Access Token）。

    Args:
        data: 要编码到 token 中的数据字典
        expires_delta: 令牌过期时间增量，如果为 None 则使用配置中的默认值

    Returns:
        str: 编码后的 JWT token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.secret_key,
        algorithm=settings.security.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    创建刷新令牌（Refresh Token）。

    Args:
        data: 要编码到 token 中的数据字典

    Returns:
        str: 编码后的 JWT refresh token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.security.refresh_token_expire_days
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.secret_key,
        algorithm=settings.security.algorithm
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    验证并解码 JWT token。

    Args:
        token: JWT token 字符串
        token_type: token 类型，"access" 或 "refresh"

    Returns:
        Optional[Dict[str, Any]]: 解码后的 payload 字典，验证失败返回 None
    """
    logger.info(f"开始验证 token，类型: {token_type}")
    
    if is_token_blacklisted(token):
        logger.warning("Token 在黑名单中")
        return None

    try:
        logger.info(f"使用 secret key 验证 token: {settings.security.secret_key[:20]}...")
        logger.info(f"使用算法: {settings.security.algorithm}")
        
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm]
        )
        
        logger.info(f"解码成功，payload: {payload}")

        if payload.get("type") != token_type:
            logger.warning(f"Token 类型不匹配: 期望 {token_type}, 实际 {payload.get('type')}")
            return None

        return payload
    except JWTError as e:
        logger.error(f"JWT 验证失败: {str(e)}")
        return None


def blacklist_token(token: str) -> None:
    """
    将 token 加入黑名单。

    Args:
        token: 要加入黑名单的 token 字符串
    """
    TOKEN_BLACKLIST.add(token)


def is_token_blacklisted(token: str) -> bool:
    """
    检查 token 是否在黑名单中。

    Args:
        token: 要检查的 token 字符串

    Returns:
        bool: token 是否在黑名单中
    """
    return token in TOKEN_BLACKLIST


def remove_from_blacklist(token: str) -> None:
    """
    从黑名单中移除 token。

    Args:
        token: 要移除的 token 字符串
    """
    TOKEN_BLACKLIST.discard(token)


def create_session(db: Session, user_id: int, session_id: str,
                   client_ip: Optional[str] = None,
                   user_agent: Optional[str] = None) -> SessionModel:
    """
    创建用户会话记录。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        session_id: 会话 ID
        client_ip: 客户端 IP 地址
        user_agent: 用户代理字符串

    Returns:
        SessionModel: 创建的会话对象
    """
    from backend.app.models.session import Session as SessionModel

    session = SessionModel(
        session_id=session_id,
        user_id=user_id,
        ip_address=client_ip,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        ),
        is_active=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session_activity(db: Session, session_id: str) -> Optional[SessionModel]:
    """
    更新会话的最后活动时间。

    Args:
        db: 数据库会话
        session_id: 会话 ID

    Returns:
        Optional[SessionModel]: 更新的会话对象，如果不存在返回 None
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if session:
        session.last_activity = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    return session


def revoke_session(db: Session, session_id: str) -> bool:
    """
    撤销指定会话。

    Args:
        db: 数据库会话
        session_id: 要撤销的会话 ID

    Returns:
        bool: 是否成功撤销
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if session:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True

    return False


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    """
    撤销用户的所有会话。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        int: 被撤销的会话数量
    """
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.is_active == True
    ).all()

    count = len(sessions)
    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)

    db.commit()
    return count
