from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class GitRepositoryCreate(BaseModel):
    name: str = Field(..., max_length=100, description="仓库名称")
    remote_url: str = Field(..., max_length=500, description="远程仓库 URL")
    local_path: Optional[str] = Field(None, max_length=500, description="本地存放路径")
    branch: str = Field("main", max_length=100, description="默认分支")
    auth_type: str = Field("none", pattern="^(none|ssh|token|password)$", description="认证类型")
    auth_credential: Optional[str] = Field(None, max_length=500, description="认证凭据（加密存储）")


class GitRepositoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="仓库名称")
    remote_url: Optional[str] = Field(None, max_length=500, description="远程仓库 URL")
    branch: Optional[str] = Field(None, max_length=100, description="默认分支")
    auth_type: Optional[str] = Field(None, pattern="^(none|ssh|token|password)$", description="认证类型")
    auth_credential: Optional[str] = Field(None, max_length=500, description="认证凭据")


class GitRepositoryResponse(BaseModel):
    id: int
    name: str
    remote_url: str
    local_path: str
    branch: str
    auth_type: str
    status: str
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    current_branch: Optional[str] = None
    is_dirty: Optional[bool] = None

    class Config:
        from_attributes = True


class GitRepositoryListResponse(BaseModel):
    repositories: List[GitRepositoryResponse]
    total: int


class GitSyncResponse(BaseModel):
    success: bool
    message: str
    commit_before: Optional[str] = None
    commit_after: Optional[str] = None


class GitOperationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class GitCommitResponse(BaseModel):
    id: int
    repository_id: int
    commit_hash: str
    author_name: Optional[str]
    author_email: Optional[str]
    committer_name: Optional[str]
    committer_email: Optional[str]
    message: Optional[str]
    committed_at: Optional[datetime]
    branch: Optional[str]
    parents: Optional[str]
    files_changed: Optional[int]
    insertions: Optional[int]
    deletions: Optional[int]

    class Config:
        from_attributes = True


class GitCommitDetailResponse(BaseModel):
    commit_hash: str
    short_hash: str
    author_name: Optional[str]
    author_email: Optional[str]
    committer_name: Optional[str]
    committer_email: Optional[str]
    message: Optional[str]
    committed_at: Optional[str]
    parents: List[str]
    files_changed: int
    insertions: int
    deletions: int
    diffs: List[Dict[str, Any]]


class GitCommitHistoryResponse(BaseModel):
    commits: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class GitDiffEntry(BaseModel):
    filename: str
    change_type: str
    old_filename: Optional[str]
    new_filename: Optional[str]
    lines_added: int
    lines_deleted: int
    content: Optional[str]


class GitDiffResponse(BaseModel):
    success: bool
    commit_a: str
    commit_b: Optional[str]
    diffs: List[GitDiffEntry]
    total_files_changed: int
    total_insertions: int
    total_deletions: int


class GitBlameLine(BaseModel):
    line_number: int
    commit_hash: str
    short_hash: str
    author_name: Optional[str]
    author_email: Optional[str]
    committed_at: Optional[str]
    line_content: str


class GitBlameResponse(BaseModel):
    success: bool
    blame: List[GitBlameLine]
    file_path: str


class GitBranchResponse(BaseModel):
    name: str
    is_active: bool
    commit_hash: str
    commit_message: str


class GitRemoteBranchResponse(BaseModel):
    name: str
    remote: str
    commit_hash: Optional[str]


class GitBranchListResponse(BaseModel):
    success: bool
    local_branches: List[GitBranchResponse]
    remote_branches: List[GitRemoteBranchResponse]


class GitTagResponse(BaseModel):
    name: str
    commit_hash: Optional[str]
    message: Optional[str]
    tagger: Optional[str]
    tagged_at: Optional[str]


class GitTagListResponse(BaseModel):
    success: bool
    tags: List[GitTagResponse]


class GitFileAtCommitResponse(BaseModel):
    success: bool
    commit_hash: str
    file_path: str
    content: str
    size: int
    committed_at: Optional[str]


class GitWebhookConfigRequest(BaseModel):
    webhook_secret: Optional[str] = Field(None, description="Webhook 签名密钥")
    provider: Optional[str] = Field(None, pattern="^(github|gitlab|gitea|bitbucket)$", description="Git 服务提供商")
    enabled: Optional[bool] = Field(None, description="是否启用 Webhook")
    auto_pull: Optional[bool] = Field(None, description="是否自动拉取")


class GitWebhookConfigResponse(BaseModel):
    id: int
    repository_id: int
    provider: Optional[str]
    enabled: bool
    auto_pull: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class GitWebhookResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    pull_error: Optional[str] = None


class GitWebhookEventData(BaseModel):
    event_type: Optional[str]
    branch: Optional[str]
    commit_hash: Optional[str]
    commits: List[Dict[str, Any]]
    pusher: Optional[str]
    repository_name: Optional[str]