from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_serializer

from backend.app.utils import get_timezone_offset


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    operation: str
    file_path: str
    file_size_before: Optional[int] = None
    file_size_after: Optional[int] = None
    status: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    diff_content: Optional[str] = None
    error_message: Optional[str] = None
    extra_data: Optional[dict] = None

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime) -> str:
        offset = get_timezone_offset(dt)
        aware_dt = dt.replace(tzinfo=timezone.utc).astimezone(timezone(offset))
        return aware_dt.isoformat()

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="timestamp")
    sort_order: str = Field(default="desc")


class AuditLogList(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditStats(BaseModel):
    total_operations: int
    operations_by_type: Dict[str, int]
    daily_trend: List[Dict[str, Any]] = Field(default_factory=list, description="每日操作趋势")
    top_users: List[Dict[str, Any]]
    top_files: List[Dict[str, Any]]
