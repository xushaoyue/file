from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ResponseModel(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: str = ""
    timestamp: datetime = datetime.now()


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: datetime = datetime.now()
