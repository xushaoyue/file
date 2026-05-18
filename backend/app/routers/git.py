from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user
from backend.app.schemas.git import (
    GitRepositoryCreate,
    GitRepositoryUpdate,
    GitRepositoryResponse,
    GitRepositoryListResponse,
    GitSyncResponse,
    GitOperationResponse,
    GitCommitHistoryResponse,
    GitCommitDetailResponse,
    GitDiffResponse,
    GitBlameResponse,
    GitBranchListResponse,
    GitTagListResponse,
    GitFileAtCommitResponse,
    GitWebhookConfigRequest,
    GitWebhookConfigResponse,
    GitWebhookResponse
)
from backend.app.models.user import User
from backend.app.git_integration.git_service import GitService
from backend.app.git_integration.webhook_handler import WebhookHandler

router = APIRouter(prefix="/api/v1/git", tags=["Git 仓库管理"])


@router.post("/repositories", response_model=GitOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    request: Request,
    repo_data: GitRepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建并克隆 Git 仓库。

    Args:
        request: HTTP 请求对象
        repo_data: 仓库创建数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitOperationResponse: 操作结果
    """
    git_service = GitService(db)
    result = git_service.clone_repository(
        name=repo_data.name,
        remote_url=repo_data.remote_url,
        local_path=repo_data.local_path,
        branch=repo_data.branch,
        auth_type=repo_data.auth_type,
        auth_credential=repo_data.auth_credential
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "创建仓库失败")
        )

    return GitOperationResponse(
        success=True,
        message="仓库克隆成功",
        data={
            "id": result["repository"].id,
            "name": result["repository"].name,
            "remote_url": result["repository"].remote_url,
            "local_path": result["repository"].local_path,
            "branch": result["repository"].branch
        }
    )


@router.get("/repositories", response_model=GitRepositoryListResponse)
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取所有 Git 仓库列表。

    Args:
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitRepositoryListResponse: 仓库列表响应
    """
    git_service = GitService(db)
    repos = git_service.list_repositories()
    return GitRepositoryListResponse(
        repositories=repos,
        total=len(repos)
    )


@router.get("/repositories/{repo_id}", response_model=GitRepositoryResponse)
async def get_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取单个仓库详情。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitRepositoryResponse: 仓库详情
    """
    git_service = GitService(db)
    repo = git_service.get_repository_by_id(repo_id)

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="仓库不存在"
        )

    repo_dict = {
        "id": repo.id,
        "name": repo.name,
        "remote_url": repo.remote_url,
        "local_path": repo.local_path,
        "branch": repo.branch,
        "auth_type": repo.auth_type,
        "status": repo.status,
        "last_synced_at": repo.last_synced_at,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at
    }

    return GitRepositoryResponse(**repo_dict)


@router.put("/repositories/{repo_id}", response_model=GitOperationResponse)
async def update_repository(
    repo_id: int,
    repo_data: GitRepositoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新仓库信息。

    Args:
        repo_id: 仓库 ID
        repo_data: 更新数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitOperationResponse: 操作结果
    """
    git_service = GitService(db)
    repo = git_service.get_repository_by_id(repo_id)

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="仓库不存在"
        )

    if repo_data.name is not None:
        repo.name = repo_data.name
    if repo_data.remote_url is not None:
        repo.remote_url = repo_data.remote_url
    if repo_data.branch is not None:
        repo.branch = repo_data.branch
    if repo_data.auth_type is not None:
        repo.auth_type = repo_data.auth_type
    if repo_data.auth_credential is not None:
        repo.auth_credential = repo_data.auth_credential

    db.commit()
    db.refresh(repo)

    return GitOperationResponse(
        success=True,
        message="仓库信息更新成功",
        data={
            "id": repo.id,
            "name": repo.name,
            "remote_url": repo.remote_url,
            "branch": repo.branch
        }
    )


@router.delete("/repositories/{repo_id}", response_model=GitOperationResponse)
async def delete_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除仓库。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitOperationResponse: 操作结果
    """
    git_service = GitService(db)
    result = git_service.remove_repository(repo_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "删除仓库失败")
        )

    return GitOperationResponse(
        success=True,
        message="仓库删除成功"
    )


@router.post("/repositories/{repo_id}/sync", response_model=GitSyncResponse)
async def sync_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    同步拉取仓库更新。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitSyncResponse: 同步结果
    """
    git_service = GitService(db)
    result = git_service.sync_repository(repo_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "同步仓库失败")
        )

    return GitSyncResponse(
        success=True,
        message=result.get("message", "同步成功"),
        commit_before=result.get("commit_before"),
        commit_after=result.get("commit_after")
    )


@router.get("/repositories/{repo_id}/commits", response_model=GitCommitHistoryResponse)
async def get_commit_history(
    repo_id: int,
    branch: Optional[str] = Query(None, description="分支名称"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取提交历史。

    Args:
        repo_id: 仓库 ID
        branch: 分支名称（可选，默认使用仓库默认分支）
        page: 页码
        page_size: 每页数量
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitCommitHistoryResponse: 提交历史响应
    """
    git_service = GitService(db)
    result = git_service.get_commit_history(repo_id, branch, page, page_size)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取提交历史失败")
        )

    return GitCommitHistoryResponse(
        commits=result["commits"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"]
    )


@router.get("/repositories/{repo_id}/commits/{commit_hash}", response_model=GitCommitDetailResponse)
async def get_commit_detail(
    repo_id: int,
    commit_hash: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取提交详情。

    Args:
        repo_id: 仓库 ID
        commit_hash: 提交哈希
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitCommitDetailResponse: 提交详情响应
    """
    git_service = GitService(db)
    result = git_service.get_commit_detail(repo_id, commit_hash)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取提交详情失败")
        )

    return result["commit"]


@router.get("/repositories/{repo_id}/diff", response_model=GitDiffResponse)
async def get_diff(
    repo_id: int,
    commit_a: str = Query(..., description="提交 A 的哈希"),
    commit_b: Optional[str] = Query(None, description="提交 B 的哈希（可选，默认与父提交对比）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取两个提交之间的差异。

    Args:
        repo_id: 仓库 ID
        commit_a: 提交 A 的哈希
        commit_b: 提交 B 的哈希（可选）
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitDiffResponse: 差异响应
    """
    git_service = GitService(db)
    result = git_service.get_diff(repo_id, commit_a, commit_b)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取差异失败")
        )

    return GitDiffResponse(
        success=True,
        commit_a=result["commit_a"],
        commit_b=result["commit_b"],
        diffs=result["diffs"],
        total_files_changed=result["total_files_changed"],
        total_insertions=result["total_insertions"],
        total_deletions=result["total_deletions"]
    )


@router.get("/repositories/{repo_id}/blame", response_model=GitBlameResponse)
async def get_blame(
    repo_id: int,
    file_path: str = Query(..., description="文件路径"),
    line_start: Optional[int] = Query(None, ge=1, description="起始行号"),
    line_end: Optional[int] = Query(None, ge=1, description="结束行号"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取文件的 blame 信息（逐行作者追溯）。

    Args:
        repo_id: 仓库 ID
        file_path: 文件路径
        line_start: 起始行号（可选）
        line_end: 结束行号（可选）
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitBlameResponse: Blame 响应
    """
    git_service = GitService(db)
    result = git_service.get_blame(repo_id, file_path, line_start, line_end)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取 blame 信息失败")
        )

    return GitBlameResponse(
        success=True,
        blame=result["blame"],
        file_path=result["file_path"]
    )


@router.get("/repositories/{repo_id}/branches", response_model=GitBranchListResponse)
async def list_branches(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取分支列表。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitBranchListResponse: 分支列表响应
    """
    git_service = GitService(db)
    result = git_service.list_branches(repo_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取分支列表失败")
        )

    return GitBranchListResponse(
        success=True,
        local_branches=result["local_branches"],
        remote_branches=result["remote_branches"]
    )


@router.get("/repositories/{repo_id}/tags", response_model=GitTagListResponse)
async def list_tags(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取标签列表。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitTagListResponse: 标签列表响应
    """
    git_service = GitService(db)
    result = git_service.list_tags(repo_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取标签列表失败")
        )

    return GitTagListResponse(
        success=True,
        tags=result["tags"]
    )


@router.get("/repositories/{repo_id}/files/{file_path}/at/{commit_hash}", response_model=GitFileAtCommitResponse)
async def get_file_at_commit(
    repo_id: int,
    file_path: str,
    commit_hash: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取特定提交中的文件内容。

    Args:
        repo_id: 仓库 ID
        file_path: 文件路径
        commit_hash: 提交哈希
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitFileAtCommitResponse: 文件内容响应
    """
    git_service = GitService(db)
    result = git_service.get_file_at_commit(repo_id, commit_hash, file_path)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "获取文件内容失败")
        )

    return GitFileAtCommitResponse(
        success=True,
        commit_hash=result["commit_hash"],
        file_path=result["file_path"],
        content=result["content"],
        size=result["size"],
        committed_at=result["committed_at"]
    )


@router.get("/repositories/{repo_id}/webhook/config", response_model=GitWebhookConfigResponse)
async def get_webhook_config(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取仓库的 Webhook 配置。

    Args:
        repo_id: 仓库 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitWebhookConfigResponse: Webhook 配置响应
    """
    webhook_handler = WebhookHandler(db)
    result = webhook_handler.get_webhook_config(repo_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Webhook 配置不存在")
        )

    return GitWebhookConfigResponse(
        id=result["config"]["id"],
        repository_id=result["config"]["repository_id"],
        provider=result["config"]["provider"],
        enabled=result["config"]["enabled"],
        auto_pull=result["config"]["auto_pull"],
        created_at=result["config"]["created_at"]
    )


@router.put("/repositories/{repo_id}/webhook/config", response_model=GitOperationResponse)
async def update_webhook_config(
    repo_id: int,
    config_data: GitWebhookConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新仓库的 Webhook 配置。

    Args:
        repo_id: 仓库 ID
        config_data: Webhook 配置数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        GitOperationResponse: 操作结果
    """
    webhook_handler = WebhookHandler(db)
    result = webhook_handler.update_webhook_config(
        repo_id=repo_id,
        webhook_secret=config_data.webhook_secret,
        provider=config_data.provider,
        enabled=config_data.enabled,
        auto_pull=config_data.auto_pull
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "更新 Webhook 配置失败")
        )

    return GitOperationResponse(
        success=True,
        message=result["message"],
        data=result["config"]
    )


@router.post("/repositories/{repo_id}/webhook/receive", response_model=GitWebhookResponse)
async def receive_webhook(
    repo_id: int,
    request: Request,
    provider: Optional[str] = Query(None, description="Git 服务提供商"),
    db: Session = Depends(get_db)
):
    """
    接收 Git Webhook 事件（无需认证，通过签名验证）。

    Args:
        repo_id: 仓库 ID
        request: HTTP 请求对象
        provider: Git 服务提供商（可选）
        db: 数据库会话

    Returns:
        GitWebhookResponse: Webhook 处理结果
    """
    payload = await request.body()

    signature = request.headers.get("X-Hub-Signature-256") or \
                request.headers.get("X-Gitlab-Token") or \
                request.headers.get("X-Gitea-Signature")

    webhook_handler = WebhookHandler(db)
    result = webhook_handler.handle_webhook(repo_id, payload, signature, provider)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Webhook 处理失败")
        )

    return GitWebhookResponse(
        success=True,
        message=result["message"],
        data=result.get("data"),
        pull_error=result.get("pull_error")
    )