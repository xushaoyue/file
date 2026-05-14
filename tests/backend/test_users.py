"""
用户管理功能测试
测试用户 CRUD 操作和权限管理
"""

import pytest


class TestUserManagement:
    """用户管理功能测试套件"""

    def test_list_users_as_admin(self, client, admin_auth_headers, test_user):
        """测试管理员查看用户列表"""
        response = client.get(
            "/api/v1/users",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_users_as_normal_user(self, client, auth_headers):
        """测试普通用户无法查看用户列表"""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_create_user(self, client, admin_auth_headers):
        """测试创建新用户"""
        response = client.post(
            "/api/v1/users",
            headers=admin_auth_headers,
            json={
                "username": "newuser",
                "password": "NewUser123",
                "email": "newuser@example.com",
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "user"
        assert data["is_active"] is True

    def test_create_admin_user(self, client, admin_auth_headers):
        """测试创建管理员用户"""
        response = client.post(
            "/api/v1/users",
            headers=admin_auth_headers,
            json={
                "username": "newadmin",
                "password": "Admin123",
                "role": "admin"
            }
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_create_duplicate_user(self, client, admin_auth_headers, test_user):
        """测试创建重复用户名失败"""
        response = client.post(
            "/api/v1/users",
            headers=admin_auth_headers,
            json={
                "username": "testuser",
                "password": "Password123",
                "role": "user"
            }
        )
        assert response.status_code == 400

    def test_get_user_by_id(self, client, admin_auth_headers, test_user):
        """测试根据 ID 获取用户信息"""
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

    def test_update_user(self, client, admin_auth_headers, test_user):
        """测试更新用户信息"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers,
            json={"email": "updated@example.com"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_user_password(self, client, admin_auth_headers, test_user):
        """测试更新用户密码"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers,
            json={"password": "NewPassword456"}
        )
        assert response.status_code == 200

    def test_update_own_info_as_normal_user(self, client, auth_headers, test_user):
        """测试普通用户更新自己的信息"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={"email": "mynewemail@example.com"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "mynewemail@example.com"

    def test_cannot_update_other_user_as_normal_user(
        self, client, db_session, auth_headers, admin_auth_headers
    ):
        """测试普通用户不能更新其他用户信息"""
        from backend.app.models.user import User
        from backend.app.services.auth_service import get_password_hash

        another_user = User(
            username="another",
            password_hash=get_password_hash("Password123"),
            role="user"
        )
        db_session.add(another_user)
        db_session.commit()
        db_session.refresh(another_user)

        response = client.put(
            f"/api/v1/users/{another_user.id}",
            headers=auth_headers,
            json={"email": "hacked@example.com"}
        )
        assert response.status_code == 403

    def test_delete_user(self, client, admin_auth_headers, db_session):
        """测试删除用户"""
        from backend.app.models.user import User
        from backend.app.services.auth_service import get_password_hash

        user_to_delete = User(
            username="todelete",
            password_hash=get_password_hash("Password123")
        )
        db_session.add(user_to_delete)
        db_session.commit()
        db_session.refresh(user_to_delete)
        user_id = user_to_delete.id

        response = client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_cannot_delete_self(self, client, admin_auth_headers, test_admin):
        """测试不能删除自己"""
        response = client.delete(
            f"/api/v1/users/{test_admin.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 400
        assert "不能删除自己" in response.json()["detail"]

    def test_filter_users_by_role(self, client, admin_auth_headers, test_user, test_admin):
        """测试按角色筛选用户"""
        response = client.get(
            "/api/v1/users?role=admin",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        users = response.json()["users"]
        assert all(u["role"] == "admin" for u in users)

    def test_filter_users_by_status(self, client, admin_auth_headers, test_user):
        """测试按状态筛选用户"""
        response = client.get(
            "/api/v1/users?is_active=true",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        users = response.json()["users"]
        assert all(u["is_active"] is True for u in users)

    def test_pagination(self, client, admin_auth_headers, db_session):
        """测试分页功能"""
        from backend.app.models.user import User
        from backend.app.services.auth_service import get_password_hash

        for i in range(15):
            user = User(
                username=f"pageuser{i}",
                password_hash=get_password_hash("Password123")
            )
            db_session.add(user)
        db_session.commit()

        response = client.get(
            "/api/v1/users?skip=0&limit=10",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 10
        assert data["total"] >= 15


class TestUserPermissions:
    """用户权限测试"""

    def test_set_user_permissions(self, client, admin_auth_headers, test_user):
        """测试设置用户权限"""
        response = client.put(
            f"/api/v1/users/{test_user.id}/permissions",
            headers=admin_auth_headers,
            json={
                "permissions": [
                    {
                        "allowed_path": "/source/project1",
                        "can_read": True,
                        "can_write": True,
                        "can_delete": False,
                        "can_download": True
                    }
                ]
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_admin_required_for_user_management(self, client, auth_headers):
        """测试用户管理需要管理员权限"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "username": "hacker",
                "password": "Password123",
                "role": "admin"
            }
        )
        assert response.status_code == 403
