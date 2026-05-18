import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from sqlalchemy.orm import Session

import git
from git import Repo, GitCommandError

from backend.app.models.git_repository import GitRepository
from backend.app.models.audit_log import AuditLog
from backend.app.config import settings
from backend.app.services.audit_service import log_event, log_batch_operation, get_current_time

logger = logging.getLogger("audit.git_service")


class GitService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def clone_repository(self, name: str, remote_url: str, local_path: Optional[str] = None,
                         branch: str = "main", auth_type: str = "none",
                         auth_credential: Optional[str] = None) -> Dict[str, Any]:
        if local_path is None:
            local_path = os.path.join(settings.file_access.base_path, name)

        abs_local_path = Path(local_path).resolve()
        os.makedirs(abs_local_path.parent, exist_ok=True)

        existing_repo = self.db.query(GitRepository).filter(
            GitRepository.name == name
        ).first()
        if existing_repo:
            return {"success": False, "error": f"仓库 '{name}' 已存在"}

        existing_by_path = self.db.query(GitRepository).filter(
            GitRepository.local_path == str(abs_local_path)
        ).first()
        if existing_by_path:
            return {"success": False, "error": f"本地路径 '{local_path}' 已被其他仓库使用"}

        if os.path.exists(abs_local_path) and len(os.listdir(abs_local_path)) > 0:
            return {"success": False, "error": f"目标目录 '{local_path}' 不为空"}

        try:
            # 设置 Git 超时和禁止交互式提示
            old_timeout = os.environ.get('GIT_HTTP_TIMEOUT')
            old_low_speed_limit = os.environ.get('GIT_HTTP_LOW_SPEED_LIMIT')
            old_low_speed_time = os.environ.get('GIT_HTTP_LOW_SPEED_TIME')
            os.environ['GIT_HTTP_TIMEOUT'] = '30'
            os.environ['GIT_HTTP_LOW_SPEED_LIMIT'] = '1000'
            os.environ['GIT_HTTP_LOW_SPEED_TIME'] = '30'
            os.environ['GIT_TERMINAL_PROMPT'] = '0'

            try:
                repo = Repo.clone_from(remote_url, str(abs_local_path), branch=branch)
            finally:
                # 恢复环境变量
                if old_timeout is not None:
                    os.environ['GIT_HTTP_TIMEOUT'] = old_timeout
                else:
                    os.environ.pop('GIT_HTTP_TIMEOUT', None)
                if old_low_speed_limit is not None:
                    os.environ['GIT_HTTP_LOW_SPEED_LIMIT'] = old_low_speed_limit
                else:
                    os.environ.pop('GIT_HTTP_LOW_SPEED_LIMIT', None)
                if old_low_speed_time is not None:
                    os.environ['GIT_HTTP_LOW_SPEED_TIME'] = old_low_speed_time
                else:
                    os.environ.pop('GIT_HTTP_LOW_SPEED_TIME', None)
                os.environ.pop('GIT_TERMINAL_PROMPT', None)

            repo_record = GitRepository(
                name=name,
                remote_url=remote_url,
                local_path=str(abs_local_path),
                branch=branch,
                auth_type=auth_type,
                auth_credential=auth_credential,
                status="cloned",
                last_synced_at=datetime.now(timezone.utc)
            )
            self.db.add(repo_record)
            self.db.commit()

            cloned_files = []
            for root, dirs, files in os.walk(abs_local_path):
                for file in files:
                    cloned_files.append(os.path.join(root, file))

            self._log_git_operation(None, name, "clone", {
                "repository_name": name,
                "remote_url": remote_url,
                "local_path": str(abs_local_path),
                "branch": branch,
                "total_files": len(cloned_files)
            })

            if len(cloned_files) > settings.audit.batch_operation_threshold:
                log_batch_operation(
                    self.db,
                    event_type="git_clone",
                    operation="clone",
                    file_paths=cloned_files,
                    username="system",
                    user_role="system",
                    status="success",
                    extra_data={
                        "repository_name": name,
                        "remote_url": remote_url,
                        "branch": branch
                    }
                )

            logger.info(f"仓库 '{name}' 克隆成功: {remote_url} -> {abs_local_path} ({len(cloned_files)} files)")
            return {"success": True, "message": "仓库克隆成功", "repository": repo_record, "files_count": len(cloned_files)}

        except GitCommandError as e:
            error_msg = f"克隆仓库失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"克隆仓库时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def list_repositories(self) -> List[Dict[str, Any]]:
        repos = self.db.query(GitRepository).all()
        result = []
        for repo in repos:
            repo_dict = {
                "id": repo.id,
                "name": repo.name,
                "remote_url": repo.remote_url,
                "local_path": repo.local_path,
                "branch": repo.branch,
                "auth_type": repo.auth_type,
                "status": repo.status,
                "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            }
            try:
                if os.path.exists(repo.local_path):
                    git_repo = Repo(repo.local_path)
                    repo_dict["current_branch"] = git_repo.active_branch.name if git_repo.active_branch else None
                    repo_dict["is_dirty"] = git_repo.is_dirty()
            except Exception as e:
                logger.warning(f"获取仓库 '{repo.name}' 状态失败: {str(e)}")

            result.append(repo_dict)
        return result

    def sync_repository(self, repo_id: int) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)
            origin = git_repo.remote(name="origin")

            before_hash = git_repo.head.commit.hexsha if git_repo.head.is_valid() else None

            origin.pull(repo_record.branch)

            after_hash = git_repo.head.commit.hexsha if git_repo.head.is_valid() else None

            repo_record.last_synced_at = datetime.now(timezone.utc)
            repo_record.status = "cloned"
            self.db.commit()

            synced_files = []
            for root, dirs, files in os.walk(repo_record.local_path):
                for file in files:
                    synced_files.append(os.path.join(root, file))

            self._log_git_operation(None, repo_record.name, "pull", {
                "repository_name": repo_record.name,
                "branch": repo_record.branch,
                "commit_before": before_hash,
                "commit_after": after_hash,
                "total_files": len(synced_files)
            })

            if len(synced_files) > settings.audit.batch_operation_threshold:
                log_batch_operation(
                    self.db,
                    event_type="git_pull",
                    operation="sync",
                    file_paths=synced_files,
                    username="system",
                    user_role="system",
                    status="success",
                    extra_data={
                        "repository_name": repo_record.name,
                        "branch": repo_record.branch,
                        "commit_before": before_hash,
                        "commit_after": after_hash
                    }
                )

            logger.info(f"仓库 '{repo_record.name}' 同步成功 ({len(synced_files)} files)")
            return {"success": True, "message": "仓库同步成功", "commit_before": before_hash, "commit_after": after_hash, "files_count": len(synced_files)}

        except GitCommandError as e:
            error_msg = f"同步仓库失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"同步仓库时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def remove_repository(self, repo_id: int) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        import shutil
        local_path = repo_record.local_path
        repo_name = repo_record.name

        try:
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
                logger.info(f"删除本地仓库目录: {local_path}")

            self._log_git_operation(None, repo_name, "delete", {
                "repository_name": repo_name,
                "local_path": local_path
            })

            self.db.delete(repo_record)
            self.db.commit()

            logger.info(f"仓库 '{repo_name}' 删除成功")
            return {"success": True, "message": "仓库删除成功"}

        except Exception as e:
            error_msg = f"删除仓库失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _log_git_operation(self, user_id: Optional[int], repo_name: str, operation: str, details: Dict[str, Any]):
        event_data = {
            "event_type": f"git_{operation}",
            "user_id": user_id,
            "username": "system",
            "user_role": "system",
            "operation": operation,
            "file_path": f"/git/{repo_name}",
            "status": "success",
            "extra_data": details,
            "timestamp": get_current_time()
        }
        try:
            log_event(self.db, event_data)
        except Exception as e:
            logger.warning(f"记录 Git 操作审计日志失败: {str(e)}")

    def get_repository_by_id(self, repo_id: int) -> Optional[GitRepository]:
        return self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()

    def get_repository_by_name(self, name: str) -> Optional[GitRepository]:
        return self.db.query(GitRepository).filter(GitRepository.name == name).first()

    def get_commit_history(self, repo_id: int, branch: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)
            target_branch = branch or repo_record.branch

            commits = []
            start = (page - 1) * page_size
            end = start + page_size

            for commit in git_repo.iter_commits(target_branch):
                commit_dict = {
                    "commit_hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "author_name": commit.author.name,
                    "author_email": commit.author.email,
                    "committer_name": commit.committer.name,
                    "committer_email": commit.committer.email,
                    "message": commit.message.strip(),
                    "committed_at": datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat(),
                    "parents": [p.hexsha for p in commit.parents],
                    "files_changed": len(commit.stats.files) if commit.stats else 0,
                    "insertions": commit.stats.total.get("insertions", 0) if commit.stats else 0,
                    "deletions": commit.stats.total.get("deletions", 0) if commit.stats else 0,
                    "branch": target_branch
                }
                commits.append(commit_dict)

            total = len(commits)
            paginated_commits = commits[start:end]

            return {
                "success": True,
                "commits": paginated_commits,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
            }

        except Exception as e:
            error_msg = f"获取提交历史失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_commit_detail(self, repo_id: int, commit_hash: str) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)

            try:
                commit = git_repo.commit(commit_hash)
            except git.BadName:
                return {"success": False, "error": "提交不存在"}

            diffs = []
            if commit.parents:
                parent_commit = commit.parents[0]
                for diff in parent_commit.diff(commit):
                    diff_dict = {
                        "filename": diff.a_path if diff.a_path else diff.b_path,
                        "change_type": diff.change_type,
                        "old_filename": diff.a_path,
                        "new_filename": diff.b_path,
                        "lines_added": diff.stats["insertions"] if diff.stats else 0,
                        "lines_deleted": diff.stats["deletions"] if diff.stats else 0,
                        "content": diff.diff.decode('utf-8', errors='replace') if diff.diff else None
                    }
                    diffs.append(diff_dict)

            commit_dict = {
                "commit_hash": commit.hexsha,
                "short_hash": commit.hexsha[:7],
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "committer_name": commit.committer.name,
                "committer_email": commit.committer.email,
                "message": commit.message.strip(),
                "committed_at": datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat(),
                "parents": [p.hexsha for p in commit.parents],
                "files_changed": len(commit.stats.files) if commit.stats else 0,
                "insertions": commit.stats.total.get("insertions", 0) if commit.stats else 0,
                "deletions": commit.stats.total.get("deletions", 0) if commit.stats else 0,
                "diffs": diffs
            }

            return {"success": True, "commit": commit_dict}

        except Exception as e:
            error_msg = f"获取提交详情失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_blame(self, repo_id: int, file_path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)
            abs_file_path = os.path.join(repo_record.local_path, file_path.lstrip('/'))

            if not os.path.exists(abs_file_path):
                return {"success": False, "error": "文件不存在"}

            blame_data = git_repo.blame('HEAD', abs_file_path)

            lines = []
            for commit, commit_lines in blame_data:
                for line_num, line in commit_lines:
                    line_info = {
                        "line_number": line_num,
                        "commit_hash": commit.hexsha,
                        "short_hash": commit.hexsha[:7],
                        "author_name": commit.author.name,
                        "author_email": commit.author.email,
                        "committed_at": datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat(),
                        "line_content": line.decode('utf-8', errors='replace')
                    }
                    lines.append(line_info)

            if line_start is not None:
                lines = [l for l in lines if l["line_number"] >= line_start]
            if line_end is not None:
                lines = [l for l in lines if l["line_number"] <= line_end]

            return {"success": True, "blame": lines, "file_path": file_path}

        except Exception as e:
            error_msg = f"获取 blame 信息失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_diff(self, repo_id: int, commit_hash_a: str, commit_hash_b: Optional[str] = None) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)

            try:
                commit_a = git_repo.commit(commit_hash_a)
            except git.BadName:
                return {"success": False, "error": f"提交 {commit_hash_a} 不存在"}

            if commit_hash_b:
                try:
                    commit_b = git_repo.commit(commit_hash_b)
                except git.BadName:
                    return {"success": False, "error": f"提交 {commit_hash_b} 不存在"}
            else:
                commit_b = commit_a.parents[0] if commit_a.parents else None

            if commit_b is None:
                return {"success": False, "error": "无法获取对比的提交"}

            diffs = []
            for diff in commit_b.diff(commit_a):
                diff_dict = {
                    "filename": diff.a_path if diff.a_path else diff.b_path,
                    "change_type": diff.change_type,
                    "old_filename": diff.a_path,
                    "new_filename": diff.b_path,
                    "lines_added": diff.stats["insertions"] if diff.stats else 0,
                    "lines_deleted": diff.stats["deletions"] if diff.stats else 0,
                    "content": diff.diff.decode('utf-8', errors='replace') if diff.diff else None
                }
                diffs.append(diff_dict)

            return {
                "success": True,
                "commit_a": commit_hash_a,
                "commit_b": commit_hash_b,
                "diffs": diffs,
                "total_files_changed": len(diffs),
                "total_insertions": sum(d["lines_added"] for d in diffs),
                "total_deletions": sum(d["lines_deleted"] for d in diffs)
            }

        except Exception as e:
            error_msg = f"获取差异失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_file_at_commit(self, repo_id: int, commit_hash: str, file_path: str) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)

            try:
                commit = git_repo.commit(commit_hash)
            except git.BadName:
                return {"success": False, "error": "提交不存在"}

            try:
                blob = commit.tree / file_path.lstrip('/')
                content = blob.data_stream.read().decode('utf-8', errors='replace')
            except KeyError:
                return {"success": False, "error": "文件不存在于该提交中"}

            return {
                "success": True,
                "commit_hash": commit_hash,
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "committed_at": datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat()
            }

        except Exception as e:
            error_msg = f"获取文件内容失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def list_branches(self, repo_id: int) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)

            branches = []
            for branch in git_repo.branches:
                branches.append({
                    "name": branch.name,
                    "is_active": branch.name == (git_repo.active_branch.name if git_repo.active_branch else None),
                    "commit_hash": branch.commit.hexsha,
                    "commit_message": branch.commit.message.strip()[:100]
                })

            remote_branches = []
            for remote in git_repo.remotes:
                for ref in remote.refs:
                    remote_branches.append({
                        "name": ref.name,
                        "remote": remote.name,
                        "commit_hash": ref.commit.hexsha if ref.commit else None
                    })

            return {
                "success": True,
                "local_branches": branches,
                "remote_branches": remote_branches
            }

        except Exception as e:
            error_msg = f"获取分支列表失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def list_tags(self, repo_id: int) -> Dict[str, Any]:
        repo_record = self.db.query(GitRepository).filter(GitRepository.id == repo_id).first()
        if not repo_record:
            return {"success": False, "error": "仓库不存在"}

        if not os.path.exists(repo_record.local_path):
            return {"success": False, "error": "本地仓库不存在"}

        try:
            git_repo = Repo(repo_record.local_path)

            tags = []
            for tag in git_repo.tags:
                tags.append({
                    "name": tag.name,
                    "commit_hash": tag.commit.hexsha if tag.commit else None,
                    "message": tag.message.strip() if tag.message else None,
                    "tagger": tag.tagger.name if tag.tagger else None,
                    "tagged_at": datetime.fromtimestamp(tag.tagged_date, timezone.utc).isoformat() if tag.tagged_date else None
                })

            return {"success": True, "tags": tags}

        except Exception as e:
            error_msg = f"获取标签列表失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}