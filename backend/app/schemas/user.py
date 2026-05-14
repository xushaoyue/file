from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class PermissionItem(BaseModel):
    allowed_path: str
    can_read: bool = False
    can_write: bool = False
    can_delete: bool = False
    can_download: bool = False


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None
    role: str = Field(default="user")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    must_change_password: bool = True

    class Config:
        from_attributes = True


class UserPermission(BaseModel):
    user_id: int
    permissions: List[PermissionItem] = []
