from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from .user import PermissionItem


class FileItem(BaseModel):
    name: str
    path: str
    type: str = Field(..., pattern="^(file|directory)$")
    size: int = 0
    modified_at: Optional[datetime] = None
    permissions: Optional[PermissionItem] = None


class FileListResponse(BaseModel):
    path: str
    items: List[FileItem]
    total: int
    page: int
    page_size: int


class FileReadResponse(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    size: int
    modified_at: Optional[datetime] = None


class FileWriteRequest(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    create_if_not_exists: bool = True


class FileDeleteResponse(BaseModel):
    path: str
    deleted_at: datetime
