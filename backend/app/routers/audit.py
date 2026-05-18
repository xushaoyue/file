from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user, require_admin
from backend.app.schemas.audit import (
    AuditLogResponse,
    AuditLogQuery,
    AuditLogList,
    AuditStats
)
from backend.app.schemas.common import ResponseModel
from backend.app.services import audit_service
from backend.app.models.user import User
from backend.app.utils import get_timezone_offset


def _local_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """将前端传来的本地时间（naive）转为 UTC（naive）用于数据库查询"""
    if dt is None:
        return None
    offset = get_timezone_offset(dt)
    return dt - offset

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])


@router.get("/logs", response_model=AuditLogList)
async def query_audit_logs(
    request: Request,
    start_date: Optional[datetime] = Query(default=None, description="开始日期"),
    end_date: Optional[datetime] = Query(default=None, description="结束日期"),
    user_id: Optional[int] = Query(default=None, description="用户 ID"),
    username: Optional[str] = Query(default=None, description="用户名"),
    operation: Optional[str] = Query(default=None, description="操作类型"),
    file_path: Optional[str] = Query(default=None, description="文件路径"),
    status: Optional[str] = Query(default=None, description="状态"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条目数"),
    sort_by: str = Query(default="timestamp", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询审计日志，支持分页和筛选。

    Args:
        request: HTTP 请求对象
        start_date: 开始日期
        end_date: 结束日期
        user_id: 用户 ID
        username: 用户名
        operation: 操作类型
        file_path: 文件路径（支持模糊匹配）
        status: 状态
        page: 页码（从 1 开始）
        page_size: 每页条目数
        sort_by: 排序字段
        sort_order: 排序方向
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        AuditLogList: 审计日志列表响应
    """
    filters = {}

    if start_date:
        filters["start_date"] = _local_to_utc(start_date)
    if end_date:
        filters["end_date"] = _local_to_utc(end_date)
    if user_id:
        filters["user_id"] = user_id
    if username:
        filters["username"] = username
    if operation:
        filters["operation"] = operation
    if file_path:
        filters["file_path"] = file_path
    if status:
        filters["status"] = status

    if current_user.role != "admin":
        filters["user_id"] = current_user.id

    result = audit_service.query_logs(
        db,
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    logs = [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp,
            event_type=log.event_type,
            user_id=log.user_id,
            username=log.username,
            user_role=log.user_role,
            operation=log.operation,
            file_path=log.file_path,
            file_size_before=log.file_size_before,
            file_size_after=log.file_size_after,
            status=log.status,
            client_ip=log.client_ip,
            user_agent=log.user_agent,
            diff_content=log.diff_content,
            error_message=log.error_message,
            extra_data=log.extra_data
        )
        for log in result["logs"]
    ]

    return AuditLogList(
        logs=logs,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取单个审计日志详情。

    Args:
        log_id: 审计日志 ID
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        AuditLogResponse: 审计日志详情
    """
    log = audit_service.get_log_by_id(db, log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审计日志不存在"
        )

    if current_user.role != "admin" and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看此日志"
        )

    return AuditLogResponse(
        id=log.id,
        timestamp=log.timestamp,
        event_type=log.event_type,
        user_id=log.user_id,
        username=log.username,
        user_role=log.user_role,
        operation=log.operation,
        file_path=log.file_path,
        file_size_before=log.file_size_before,
        file_size_after=log.file_size_after,
        status=log.status,
        client_ip=log.client_ip,
        user_agent=log.user_agent,
        diff_content=log.diff_content,
        error_message=log.error_message,
        extra_data=log.extra_data
    )


@router.get("/export")
async def export_audit_logs(
    request: Request,
    format: str = Query(default="csv", regex="^(csv|json)$", description="导出格式"),
    start_date: Optional[datetime] = Query(default=None, description="开始日期"),
    end_date: Optional[datetime] = Query(default=None, description="结束日期"),
    user_id: Optional[int] = Query(default=None, description="用户 ID"),
    username: Optional[str] = Query(default=None, description="用户名"),
    operation: Optional[str] = Query(default=None, description="操作类型"),
    status: Optional[str] = Query(default=None, description="状态"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    导出审计日志为 CSV 或 JSON 格式。

    Args:
        request: HTTP 请求对象
        format: 导出格式 ("csv" 或 "json")
        start_date: 开始日期
        end_date: 结束日期
        user_id: 用户 ID
        username: 用户名
        operation: 操作类型
        status: 状态
        current_user: 当前管理员用户对象
        db: 数据库会话

    Returns:
        StreamingResponse: 导出的文件流
    """
    filters = {}

    if start_date:
        filters["start_date"] = _local_to_utc(start_date)
    if end_date:
        filters["end_date"] = _local_to_utc(end_date)
    if user_id:
        filters["user_id"] = user_id
    if username:
        filters["username"] = username
    if operation:
        filters["operation"] = operation
    if status:
        filters["status"] = status

    try:
        content = audit_service.export_logs(db, filters=filters, format=format)

        if format == "csv":
            media_type = "text/csv"
            filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            media_type = "application/json"
            filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/stats", response_model=AuditStats)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(default=None, description="开始日期"),
    end_date: Optional[datetime] = Query(default=None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取审计日志统计信息。

    Args:
        start_date: 统计开始日期
        end_date: 统计结束日期
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        AuditStats: 审计统计信息
    """
    total_result = audit_service.get_statistics(
        db,
        start_date=_local_to_utc(start_date),
        end_date=_local_to_utc(end_date),
        group_by="day"
    )

    daily_trend_data = total_result.get("statistics", [])
    total_operations = sum(item.get("count", 0) for item in daily_trend_data)

    operation_result = audit_service.get_statistics(
        db,
        start_date=_local_to_utc(start_date),
        end_date=_local_to_utc(end_date),
        group_by="operation"
    )

    user_result = audit_service.get_statistics(
        db,
        start_date=_local_to_utc(start_date),
        end_date=_local_to_utc(end_date),
        group_by="user"
    )

    return AuditStats(
        total_operations=total_operations,
        daily_trend=daily_trend_data,
        operations_by_type={
            item["operation"]: item["count"]
            for item in operation_result.get("statistics", [])
        },
        top_users=user_result.get("statistics", [])[:10],
        top_files=[]
    )
