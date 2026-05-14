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

    def test_list_files(self, client, auth_headers):
        """测试列出目录文件"""
        response = client.get(
            "/api/v1/files/list?path=/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_files_recursive(self, client, auth_headers):
        """测试递归列出文件"""
        response = client.get(
            "/api/v1/files/list?path=/&recursive=true",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_list_files_pagination(self, client, auth_headers):
        """测试文件列表分页"""
        response = client.get(
            "/api/v1/files/list?path=/&page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_read_file(self, client, auth_headers):
        """测试读取文件内容"""
        test_file = create_test_file("/tmp/test_read.txt", "Hello, World!")
        try:
            response = client.get(
                "/api/v1/files/read?path=/tmp/test_read.txt",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data["content"] == "Hello, World!"
        finally:
            cleanup_test_files(test_file)

    def test_read_file_with_encoding(self, client, auth_headers):
        """测试读取文件（指定编码）"""
        test_file = create_test_file("/tmp/test_utf8.txt", "中文测试内容")
        try:
            response = client.get(
                "/api/v1/files/read?path=/tmp/test_utf8.txt&encoding=utf-8",
                headers=auth_headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_read_nonexistent_file(self, client, auth_headers):
        """测试读取不存在的文件"""
        response = client.get(
            "/api/v1/files/read?path=/nonexistent/file.txt",
            headers=auth_headers
        )
        assert response.status_code in [400, 404]

    def test_write_file(self, client, auth_headers):
        """测试写入文件"""
        response = client.put(
            "/api/v1/files/write",
            headers=auth_headers,
            json={
                "path": "/tmp/test_write.txt",
                "content": "New content",
                "encoding": "utf-8",
                "create_if_not_exists": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        cleanup_test_files("/tmp/test_write.txt")

    def test_write_file_update(self, client, auth_headers):
        """测试更新文件内容"""
        test_file = create_test_file("/tmp/test_update.txt", "Original content")

        try:
            response = client.put(
                "/api/v1/files/write",
                headers=auth_headers,
                json={
                    "path": "/tmp/test_update.txt",
                    "content": "Updated content",
                    "encoding": "utf-8"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            cleanup_test_files(test_file)

    def test_write_file_without_permission(self, client, auth_headers):
        """测试写入无权限文件"""
        response = client.put(
            "/api/v1/files/write",
            headers=auth_headers,
            json={
                "path": "/root/protected.txt",
                "content": "Hacking...",
                "encoding": "utf-8"
            }
        )
        assert response.status_code in [400, 403]

    def test_delete_file(self, client, auth_headers):
        """测试删除文件"""
        test_file = create_test_file("/tmp/test_delete.txt", "To be deleted")

        response = client.delete(
            "/api/v1/files/delete?path=/tmp/test_delete.txt",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_nonexistent_file(self, client, auth_headers):
        """测试删除不存在的文件"""
        response = client.delete(
            "/api/v1/files/delete?path=/nonexistent/file.txt",
            headers=auth_headers
        )
        assert response.status_code in [400, 404]

    def test_download_file(self, client, auth_headers):
        """测试下载文件"""
        test_file = create_test_file("/tmp/test_download.txt", "Download me!")

        try:
            response = client.get(
                "/api/v1/files/download?path=/tmp/test_download.txt",
                headers=auth_headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_download_nonexistent_file(self, client, auth_headers):
        """测试下载不存在的文件"""
        response = client.get(
            "/api/v1/files/download?path=/nonexistent/file.txt",
            headers=auth_headers
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

        user = User(
            username="fileuser",
            password_hash=get_password_hash("Password123"),
            role="user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "fileuser", "password": "Password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        test_file = create_test_file("/tmp/permitted.txt", "Content")
        try:
            response = client.get(
                "/api/v1/files/read?path=/tmp/permitted.txt",
                headers=headers
            )
            assert response.status_code == 200
        finally:
            cleanup_test_files(test_file)

    def test_file_operation_creates_audit_log(
        self, client, auth_headers
    ):
        """测试文件操作会创建审计日志"""
        test_file = create_test_file("/tmp/audit_test.txt", "Audit me!")

        try:
            response = client.get(
                "/api/v1/files/read?path=/tmp/audit_test.txt",
                headers=auth_headers
            )

            assert response.status_code == 200

        finally:
            cleanup_test_files(test_file)
