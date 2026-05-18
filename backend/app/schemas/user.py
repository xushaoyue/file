from datetime import datetime, timezone
from typing import Optional, List, Union

from pydantic import BaseModel, EmailStr, Field, field_serializer

from backend.app.utils import get_timezone_offset


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
    full_name: Optional[str] = None
    role: str = Field(default="user")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    must_change_password: bool = True

    @field_serializer('created_at', 'updated_at', 'last_login')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        offset = get_timezone_offset(dt)
        aware_dt = dt.replace(tzinfo=timezone.utc).astimezone(timezone(offset))
        return aware_dt.isoformat()

    class Config:
        from_attributes = True


class UserPermission(BaseModel):
    user_id: Optional[int] = None
    permissions: List[Union[PermissionItem, str]] = []


class ChangePassword(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, description="新密码")
