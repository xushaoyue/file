from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SSHKeyCreate(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100)
    public_key: str = Field(..., min_length=1)


class SSHKeyResponse(BaseModel):
    id: int
    key_name: str
    key_type: Optional[str] = None
    fingerprint: Optional[str] = None
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
