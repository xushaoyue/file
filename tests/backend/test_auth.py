"""
认证功能测试
测试用户登录、注册、登出、Token 刷新等功能
"""

import pytest


class TestAuthentication:
    """认证功能测试套件"""

    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "TestPassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"

    def test_login_invalid_password(self, client, test_user):
        """测试密码错误登录失败"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "WrongPassword123"}
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录失败"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "Password123"}
        )
        assert response.status_code == 401

    def test_register_success(self, client):
        """测试成功注册新用户"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "NewUser123",
                "confirm_password": "NewUser123",
                "email": "newuser@example.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "newuser"
        assert "access_token" in data

    def test_register_password_mismatch(self, client):
        """测试两次密码不一致注册失败"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "Password123",
                "confirm_password": "DifferentPassword123",
                "email": "newuser@example.com"
            }
        )
        assert response.status_code == 400
        assert "密码不匹配" in response.json()["detail"]

    def test_register_duplicate_username(self, client, test_user):
        """测试重复用户名注册失败"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "password": "Password123",
                "confirm_password": "Password123",
                "email": "another@example.com"
            }
        )
        assert response.status_code == 400

    def test_refresh_token_success(self, client, test_user):
        """测试成功刷新 Token"""
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "TestPassword123"}
        )
        refresh_token = login_response.json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_token_invalid(self, client):
        """测试无效的刷新 Token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401

    def test_logout_success(self, client, user_token):
        """测试成功登出"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_logout_without_token(self, client):
        """测试无 Token 登出失败"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_get_current_user(self, client, user_token, test_user):
        """测试获取当前用户信息"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data


class TestAuthenticationSecurity:
    """认证安全测试"""

    def test_inactive_user_cannot_login(self, client, db_session):
        """测试停用用户无法登录"""
        from backend.app.models.user import User
        from backend.app.services.auth_service import get_password_hash

        inactive_user = User(
            username="inactiveuser",
            password_hash=get_password_hash("Password123"),
            is_active=False
        )
        db_session.add(inactive_user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inactiveuser", "password": "Password123"}
        )
        assert response.status_code == 401

    def test_multiple_failed_logins_tracking(self, client, test_user):
        """测试多次登录失败追踪"""
        for _ in range(3):
            client.post(
                "/api/v1/auth/login",
                data={"username": "testuser", "password": "WrongPassword"}
            )

        from backend.app.models.user import User
        from backend.app.database import SessionLocal

        db = SessionLocal()
        user = db.query(User).filter(User.username == "testuser").first()
        assert user.failed_attempts >= 3
        db.close()
