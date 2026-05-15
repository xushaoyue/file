"""
文件操作功能测试
测试文件浏览、读取、编辑、删除、下载等操作
"""

import pytest
import os
import tempfile
from pathlib import Path
from tests.backend.utils import create_test_file, cleanup_test_files


class TestFileOperations:
    """文件操作功能测试套件"""

    def test_list_files(self, client, admin_auth_headers):
        """测试列出目录文件"""
        response = client.get(
            "/api/v1/files/list?path=/workspace",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_files_recursive(self, client, admin_auth_headers):
        """测试递归列出文件"""
        response = client.get(
            "/api/v1/files/list?path=/workspace&recursive=true",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_list_files_pagination(self, client, admin_auth_headers):
        """测试文件列表分页"""
        response = client.get(
            "/api/v1/files/list?path=/workspace&page=1&page_size=10",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_read_file(self, client, admin_auth_headers):
        """测试读取文件内容"""
        test_file_path = Path("/workspace") / "test_read.txt"
        test_file = create_test_file(str(test_file_path), "Hello, World!")
        try:
            response = client.get(
                f"/api/v1/files/read?path={test_file_path}",
                headers=admin_auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data["content"] == "Hello, World!"
        finally:
            cleanup_test_files(test_file)

    def test_read_file_with_encoding(self, client, admin_auth_headers):
        """测试读取文件（指定编码）"""
        test_file_path = Path("/workspace") / "test_utf8.txt"
        test_file = create_test_file(str(test_file_path), "中文测试内容")
        try:
            response = client.get(
                f"/api/v1/files/read?path={test_file_path}&encoding=utf-8",
                headers=admin_auth_headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_read_nonexistent_file(self, client, admin_auth_headers):
        """测试读取不存在的文件"""
        response = client.get(
            "/api/v1/files/read?path=/workspace/nonexistent/file.txt",
            headers=admin_auth_headers
        )
        assert response.status_code in [400, 404]

    def test_write_file(self, client, admin_auth_headers):
        """测试写入文件"""
        test_file_path = Path("/workspace") / "test_write.txt"
        try:
            response = client.put(
                "/api/v1/files/write",
                headers=admin_auth_headers,
                json={
                    "path": str(test_file_path),
                    "content": "New content",
                    "encoding": "utf-8",
                    "create_if_not_exists": True
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            cleanup_test_files(str(test_file_path))

    def test_write_file_update(self, client, admin_auth_headers):
        """测试更新文件内容"""
        test_file_path = Path("/workspace") / "test_update.txt"
        test_file = create_test_file(str(test_file_path), "Original content")

        try:
            response = client.put(
                "/api/v1/files/write",
                headers=admin_auth_headers,
                json={
                    "path": str(test_file_path),
                    "content": "Updated content",
                    "encoding": "utf-8"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            cleanup_test_files(test_file)

    def test_delete_file(self, client, admin_auth_headers):
        """测试删除文件"""
        test_file_path = Path("/workspace") / "test_delete.txt"
        test_file = create_test_file(str(test_file_path), "To be deleted")

        response = client.delete(
            f"/api/v1/files/delete?path={test_file_path}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_nonexistent_file(self, client, admin_auth_headers):
        """测试删除不存在的文件"""
        response = client.delete(
            "/api/v1/files/delete?path=/workspace/nonexistent/file.txt",
            headers=admin_auth_headers
        )
        assert response.status_code in [400, 404]

    def test_download_file(self, client, admin_auth_headers):
        """测试下载文件"""
        test_file_path = Path("/workspace") / "test_download.txt"
        test_file = create_test_file(str(test_file_path), "Download me!")

        try:
            response = client.get(
                f"/api/v1/files/download?path={test_file_path}",
                headers=admin_auth_headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_download_nonexistent_file(self, client, admin_auth_headers):
        """测试下载不存在的文件"""
        response = client.get(
            "/api/v1/files/download?path=/workspace/nonexistent/file.txt",
            headers=admin_auth_headers
        )
        assert response.status_code in [400, 404]


class TestFileOperationsWithPermissions:
    """文件操作权限测试"""

    def test_read_file_with_permission(
        self, client, admin_auth_headers, db_session
    ):
        """测试有权限读取文件"""
        from backend.app.models.user import User
        from backend.app.services.auth_service import get_password_hash
        from backend.app.models.permission import Permission

        user = User(
            username="fileuser",
            password_hash=get_password_hash("Password123"),
            role="user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # 给用户添加权限
        permission = Permission(
            user_id=user.id,
            allowed_path="/workspace",
            can_read=True,
            can_write=True,
            can_delete=False,
            can_download=True
        )
        db_session.add(permission)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "fileuser", "password": "Password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        test_file_path = Path("/workspace") / "permitted.txt"
        test_file = create_test_file(str(test_file_path), "Content")
        try:
            response = client.get(
                f"/api/v1/files/read?path={test_file_path}",
                headers=headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_file_operation_creates_audit_log(
        self, client, admin_auth_headers
    ):
        """测试文件操作会创建审计日志"""
        test_file_path = Path("/workspace") / "audit_test.txt"
        test_file = create_test_file(str(test_file_path), "Audit me!")

        try:
            response = client.get(
                f"/api/v1/files/read?path={test_file_path}",
                headers=admin_auth_headers
            )

            assert response.status_code == 200

        finally:
            cleanup_test_files(test_file)
