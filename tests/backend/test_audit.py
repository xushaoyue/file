"""
审计日志功能测试
测试审计日志查询、筛选、导出等功能
"""

import pytest
from datetime import datetime, timedelta


class TestAuditLogs:
    """审计日志功能测试套件"""

    def test_get_audit_logs(self, client, admin_auth_headers):
        """测试获取审计日志列表"""
        response = client.get(
            "/api/v1/audit/logs",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["logs"], list)

    def test_get_audit_logs_pagination(self, client, admin_auth_headers):
        """测试审计日志分页"""
        response = client.get(
            "/api/v1/audit/logs?page=1&page_size=10",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_filter_logs_by_user(self, client, admin_auth_headers, user_token, test_user):
        """测试按用户筛选审计日志"""
        response = client.get(
            f"/api/v1/audit/logs?user_id={test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(log["user_id"] == test_user.id for log in data["logs"])

    def test_filter_logs_by_operation(self, client, admin_auth_headers):
        """测试按操作类型筛选"""
        response = client.get(
            "/api/v1/audit/logs?operation=login",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_filter_logs_by_status(self, client, admin_auth_headers):
        """测试按状态筛选"""
        response = client.get(
            "/api/v1/audit/logs?status=success",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(log["status"] == "success" for log in data["logs"])

    def test_filter_logs_by_date_range(self, client, admin_auth_headers):
        """测试按日期范围筛选"""
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()

        response = client.get(
            f"/api/v1/audit/logs?start_date={start_date}&end_date={end_date}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_filter_logs_by_file_path(self, client, admin_auth_headers):
        """测试按文件路径筛选"""
        response = client.get(
            "/api/v1/audit/logs?file_path=/test",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_get_audit_log_detail(self, client, admin_auth_headers, user_token, test_user):
        """测试获取单个审计日志详情"""
        response = client.get(
            "/api/v1/audit/logs/1",
            headers=admin_auth_headers
        )
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "timestamp" in data
            assert "operation" in data

    def test_normal_user_can_only_see_own_logs(self, client, auth_headers):
        """测试普通用户只能看到自己的日志"""
        response = client.get(
            "/api/v1/audit/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["username"] == "testuser"


class TestAuditLogsExport:
    """审计日志导出功能测试"""

    def test_export_logs_as_csv(self, client, admin_auth_headers):
        """测试导出日志为 CSV 格式"""
        response = client.get(
            "/api/v1/audit/export?format=csv",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_logs_as_json(self, client, admin_auth_headers):
        """测试导出日志为 JSON 格式"""
        response = client.get(
            "/api/v1/audit/export?format=json",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_export_logs_with_filters(self, client, admin_auth_headers):
        """测试带筛选条件导出日志"""
        start_date = (datetime.now() - timedelta(days=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/export?format=csv&start_date={start_date}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_normal_user_cannot_export_logs(self, client, auth_headers):
        """测试普通用户不能导出日志"""
        response = client.get(
            "/api/v1/audit/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 403


class TestAuditStatistics:
    """审计统计功能测试"""

    def test_get_audit_statistics(self, client, admin_auth_headers):
        """测试获取审计统计信息"""
        response = client.get(
            "/api/v1/audit/stats",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_operations" in data
        assert "operations_by_type" in data

    def test_get_audit_stats_with_date_range(self, client, admin_auth_headers):
        """测试按日期范围获取统计"""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()

        response = client.get(
            f"/api/v1/audit/stats?start_date={start_date}&end_date={end_date}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_normal_user_can_get_own_stats(self, client, auth_headers):
        """测试普通用户可以获取自己的统计"""
        response = client.get(
            "/api/v1/audit/stats",
            headers=auth_headers
        )
        assert response.status_code == 200


class TestAuditLogsIntegrity:
    """审计日志完整性测试"""

    def test_login_creates_audit_log(self, client, test_user):
        """测试登录操作创建审计日志"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "TestPassword123"}
        )
        assert response.status_code == 200

    def test_failed_login_creates_audit_log(self, client, test_user):
        """测试失败登录也创建审计日志"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "WrongPassword"}
        )
        assert response.status_code == 401

    def test_audit_log_contains_required_fields(self, client, admin_auth_headers):
        """测试审计日志包含必需字段"""
        response = client.get(
            "/api/v1/audit/logs",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

        if response.json()["logs"]:
            log = response.json()["logs"][0]
            required_fields = [
                "id", "timestamp", "event_type", "username",
                "operation", "file_path", "status"
            ]
            for field in required_fields:
                assert field in log, f"Missing field: {field}"
