"""
Pytest 配置和 Fixtures
提供测试所需的共享资源
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ['CONFIG_PATH'] = './config/config.yaml'
os.environ['PYTEST_RUNNING'] = '1'

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.services.auth_service import get_password_hash, TOKEN_BLACKLIST


TEST_DATABASE_URL = "sqlite:///./test_data/test_audit.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖，提供测试数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def clear_token_blacklist():
    """在每个测试前清空token黑名单"""
    TOKEN_BLACKLIST.clear()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话，每个测试函数都会重新创建"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建 FastAPI 测试客户端"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(
        username="testuser",
        password_hash=get_password_hash("TestPassword123"),
        email="test@example.com",
        role="user",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """创建测试管理员用户"""
    admin = User(
        username="testadmin",
        password_hash=get_password_hash("AdminPassword123"),
        email="admin@example.com",
        role="admin",
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def user_token(client, test_user):
    """获取普通用户的访问令牌"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "TestPassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_token(client, test_admin):
    """获取管理员的访问令牌"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "AdminPassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(user_token):
    """普通用户认证头"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(admin_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_token}"}
