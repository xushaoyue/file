import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from backend.app.models.git_webhook import GitWebhookConfig
from backend.app.models.git_repository import GitRepository
from backend.app.git_integration.git_service import GitService
from backend.app.services.audit_service import log_event, get_current_time

logger = logging.getLogger("audit.webhook_handler")


class WebhookHandler:
    SUPPORTED_PROVIDERS = ["github", "gitlab", "gitea", "bitbucket"]

    def __init__(self, db_session):
        self.db = db_session

    def _verify_signature(self, provider: str, secret: str, payload: bytes, signature: str) -> bool:
        if not secret or not signature:
            return False

        try:
            if provider == "github":
                digest = hmac.new(
                    secret.encode("utf-8"),
                    msg=payload,
                    digestmod=hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(f"sha256={digest}", signature)
            elif provider == "gitlab":
                digest = hmac.new(
                    secret.encode("utf-8"),
                    msg=payload,
                    digestmod=hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(digest, signature.replace("sha256=", ""))
            elif provider == "gitea":
                digest = hmac.new(
                    secret.encode("utf-8"),
                    msg=payload,
                    digestmod=hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(f"sha256={digest}", signature)
            else:
                return True
        except Exception as e:
            logger.error(f"签名验证失败: {str(e)}")
            return False

    def _parse_payload(self, provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "event_type": None,
            "branch": None,
            "commit_hash": None,
            "commits": [],
            "pusher": None,
            "repository_name": None
        }

        try:
            if provider == "github":
                result["event_type"] = "push"
                result["branch"] = payload.get("ref", "").replace("refs/heads/", "")
                result["commit_hash"] = payload.get("after")
                result["commits"] = payload.get("commits", [])
                result["pusher"] = payload.get("pusher", {}).get("name")
                result["repository_name"] = payload.get("repository", {}).get("name")

            elif provider == "gitlab":
                result["event_type"] = payload.get("object_kind")
                result["branch"] = payload.get("ref", "").replace("refs/heads/", "")
                result["commit_hash"] = payload.get("after")
                result["commits"] = payload.get("commits", [])
                result["pusher"] = payload.get("user_name")
                result["repository_name"] = payload.get("project", {}).get("name")

            elif provider == "gitea":
                result["event_type"] = payload.get("ref_type")
                result["branch"] = payload.get("ref", "").replace("refs/heads/", "")
                result["commit_hash"] = payload.get("after")
                result["commits"] = payload.get("commits", [])
                result["pusher"] = payload.get("pusher", {}).get("login") or payload.get("sender", {}).get("login")
                result["repository_name"] = payload.get("repository", {}).get("name")

            elif provider == "bitbucket":
                result["event_type"] = "push"
                changes = payload.get("push", {}).get("changes", [])
                if changes:
                    result["branch"] = changes[0].get("new", {}).get("name")
                    result["commit_hash"] = changes[0].get("new", {}).get("target", {}).get("hash")
                result["pusher"] = payload.get("actor", {}).get("display_name")
                result["repository_name"] = payload.get("repository", {}).get("name")

        except Exception as e:
            logger.error(f"解析 payload 失败: {str(e)}")

        return result

    def handle_webhook(self, repo_id: int, payload: bytes, signature: Optional[str] = None,
                       provider: Optional[str] = None) -> Dict[str, Any]:
        webhook_config = self.db.query(GitWebhookConfig).filter(
            GitWebhookConfig.repository_id == repo_id
        ).first()

        if not webhook_config:
            return {"success": False, "error": "Webhook 配置不存在"}

        if not webhook_config.enabled:
            return {"success": False, "error": "Webhook 已禁用"}

        if provider:
            webhook_config.provider = provider
            self.db.commit()

        actual_provider = webhook_config.provider or provider or "github"

        if webhook_config.webhook_secret and signature:
            if not self._verify_signature(actual_provider, webhook_config.webhook_secret, payload, signature):
                return {"success": False, "error": "签名验证失败"}

        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError:
            return {"success": False, "error": "无效的 JSON 格式"}

        parsed_data = self._parse_payload(actual_provider, payload_dict)

        self._log_webhook_event(repo_id, parsed_data)

        if parsed_data["event_type"] in ["push", "branch"] and webhook_config.auto_pull:
            result = self._auto_pull(repo_id, parsed_data)
            if result["success"]:
                return {"success": True, "message": "自动拉取成功", "data": parsed_data}
            else:
                return {"success": True, "message": "Webhook 已接收，但自动拉取失败", "data": parsed_data, "pull_error": result["error"]}

        return {"success": True, "message": "Webhook 已接收", "data": parsed_data}

    def _auto_pull(self, repo_id: int, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        git_service = GitService(self.db)
        result = git_service.sync_repository(repo_id)
        return result

    def _log_webhook_event(self, repo_id: int, parsed_data: Dict[str, Any]):
        repo = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        repo_name = repo.name if repo else str(repo_id)

        event_data = {
            "event_type": "git_webhook",
            "user_id": None,
            "username": parsed_data.get("pusher") or "webhook",
            "user_role": "external",
            "operation": parsed_data.get("event_type") or "unknown",
            "file_path": f"/git/{repo_name}",
            "status": "success",
            "extra_data": {
                "repository_id": repo_id,
                "repository_name": repo_name,
                "branch": parsed_data.get("branch"),
                "commit_hash": parsed_data.get("commit_hash"),
                "commit_count": len(parsed_data.get("commits", [])),
                "pusher": parsed_data.get("pusher")
            },
            "timestamp": get_current_time()
        }

        try:
            log_event(self.db, event_data)
        except Exception as e:
            logger.warning(f"记录 Webhook 审计日志失败: {str(e)}")

    def update_webhook_config(self, repo_id: int, webhook_secret: Optional[str] = None,
                              provider: Optional[str] = None, enabled: Optional[bool] = None,
                              auto_pull: Optional[bool] = None) -> Dict[str, Any]:
        webhook_config = self.db.query(GitWebhookConfig).filter(
            GitWebhookConfig.repository_id == repo_id
        ).first()

        if not webhook_config:
            repo = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
            if not repo:
                return {"success": False, "error": "仓库不存在"}

            webhook_config = GitWebhookConfig(
                repository_id=repo_id,
                webhook_secret=webhook_secret,
                provider=provider,
                enabled=enabled if enabled is not None else True,
                auto_pull=auto_pull if auto_pull is not None else True
            )
            self.db.add(webhook_config)
        else:
            if webhook_secret is not None:
                webhook_config.webhook_secret = webhook_secret
            if provider is not None:
                webhook_config.provider = provider
            if enabled is not None:
                webhook_config.enabled = enabled
            if auto_pull is not None:
                webhook_config.auto_pull = auto_pull

        self.db.commit()
        self.db.refresh(webhook_config)

        return {
            "success": True,
            "message": "Webhook 配置更新成功",
            "config": {
                "id": webhook_config.id,
                "repository_id": webhook_config.repository_id,
                "provider": webhook_config.provider,
                "enabled": webhook_config.enabled,
                "auto_pull": webhook_config.auto_pull
            }
        }

    def get_webhook_config(self, repo_id: int) -> Dict[str, Any]:
        webhook_config = self.db.query(GitWebhookConfig).filter(
            GitWebhookConfig.repository_id == repo_id
        ).first()

        if not webhook_config:
            return {"success": False, "error": "Webhook 配置不存在"}

        return {
            "success": True,
            "config": {
                "id": webhook_config.id,
                "repository_id": webhook_config.repository_id,
                "provider": webhook_config.provider,
                "enabled": webhook_config.enabled,
                "auto_pull": webhook_config.auto_pull,
                "created_at": webhook_config.created_at.isoformat() if webhook_config.created_at else None
            }
        }