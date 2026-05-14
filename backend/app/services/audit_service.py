import os
import csv
import json
import io
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from backend.app.models.audit_log import AuditLog
from backend.app.config import settings


def log_event(db: Session, event_data: Dict[str, Any]) -> AuditLog:
    """
    记录审计事件到数据库。

    Args:
        db: 数据库会话
        event_data: 事件数据字典，包含以下字段：
            - event_type: 事件类型
            - user_id: 用户 ID（可选）
            - username: 用户名
            - user_role: 用户角色
            - operation: 操作类型
            - file_path: 文件路径
            - file_size_before: 操作前文件大小（可选）
            - file_size_after: 操作后文件大小（可选）
            - status: 状态 ("success", "failure", "error")
            - client_ip: 客户端 IP（可选）
            - user_agent: 用户代理（可选）
            - session_id: 会话 ID（可选）
            - diff_content: 差异内容（可选）
            - error_message: 错误信息（可选）
            - event_metadata: 额外元数据（可选）

    Returns:
        AuditLog: 创建的审计日志对象
    """
    log = AuditLog(
        event_type=event_data.get("event_type", "general"),
        user_id=event_data.get("user_id"),
        username=event_data.get("username"),
        user_role=event_data.get("user_role"),
        operation=event_data.get("operation"),
        file_path=event_data.get("file_path", ""),
        file_size_before=event_data.get("file_size_before"),
        file_size_after=event_data.get("file_size_after"),
        status=event_data.get("status", "success"),
        client_ip=event_data.get("client_ip"),
        user_agent=event_data.get("user_agent"),
        session_id=event_data.get("session_id"),
        diff_content=event_data.get("diff_content"),
        error_message=event_data.get("error_message"),
        event_metadata=event_data.get("event_metadata"),
        timestamp=datetime.utcnow()
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def write_to_file(log: AuditLog) -> bool:
    """
    将审计日志写入文件系统。

    Args:
        log: 审计日志对象

    Returns:
        bool: 是否成功写入
    """
    os.makedirs(settings.log.dir, exist_ok=True)

    date_str = log.timestamp.strftime("%Y-%m-%d")
    filename = f"{settings.log.audit_log_prefix}_{date_str}.log"
    filepath = os.path.join(settings.log.dir, filename)

    log_entry = {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "event_type": log.event_type,
        "user_id": log.user_id,
        "username": log.username,
        "user_role": log.user_role,
        "operation": log.operation,
        "file_path": log.file_path,
        "status": log.status,
        "client_ip": log.client_ip
    }

    try:
        if settings.log.format == "json":
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        else:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(
                    f"[{log_entry['timestamp']}] {log_entry['event_type']} | "
                    f"User: {log_entry['username']} | Op: {log_entry['operation']} | "
                    f"Path: {log_entry['file_path']} | Status: {log_entry['status']}\n"
                )
        return True
    except Exception:
        return False


def query_logs(db: Session,
               filters: Optional[Dict[str, Any]] = None,
               page: int = 1,
               page_size: int = 50,
               sort_by: str = "timestamp",
               sort_order: str = "desc") -> Dict[str, Any]:
    """
    查询审计日志。

    Args:
        db: 数据库会话
        filters: 筛选条件字典，可包含：
            - user_id: 用户 ID
            - username: 用户名
            - operation: 操作类型
            - file_path: 文件路径（支持模糊匹配）
            - event_type: 事件类型
            - status: 状态
            - start_date: 开始日期
            - end_date: 结束日期
        page: 页码（从 1 开始）
        page_size: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向 ("asc" 或 "desc")

    Returns:
        Dict[str, Any]: 包含 logs 列表、总数、分页信息的字典
    """
    if filters is None:
        filters = {}

    query = db.query(AuditLog)

    if "user_id" in filters and filters["user_id"] is not None:
        query = query.filter(AuditLog.user_id == filters["user_id"])

    if "username" in filters and filters["username"]:
        query = query.filter(AuditLog.username == filters["username"])

    if "operation" in filters and filters["operation"]:
        query = query.filter(AuditLog.operation == filters["operation"])

    if "event_type" in filters and filters["event_type"]:
        query = query.filter(AuditLog.event_type == filters["event_type"])

    if "file_path" in filters and filters["file_path"]:
        query = query.filter(AuditLog.file_path.contains(filters["file_path"]))

    if "status" in filters and filters["status"]:
        query = query.filter(AuditLog.status == filters["status"])

    if "start_date" in filters and filters["start_date"]:
        if isinstance(filters["start_date"], str):
            start_date = datetime.fromisoformat(filters["start_date"])
        else:
            start_date = filters["start_date"]
        query = query.filter(AuditLog.timestamp >= start_date)

    if "end_date" in filters and filters["end_date"]:
        if isinstance(filters["end_date"], str):
            end_date = datetime.fromisoformat(filters["end_date"])
        else:
            end_date = filters["end_date"]
        query = query.filter(AuditLog.timestamp <= end_date)

    total = query.count()

    sort_column = getattr(AuditLog, sort_by, AuditLog.timestamp)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    start = (page - 1) * page_size
    logs = query.offset(start).limit(page_size).all()

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }


def get_log_by_id(db: Session, log_id: int) -> Optional[AuditLog]:
    """
    根据 ID 获取审计日志。

    Args:
        db: 数据库会话
        log_id: 日志 ID

    Returns:
        Optional[AuditLog]: 审计日志对象，不存在返回 None
    """
    return db.query(AuditLog).filter(AuditLog.id == log_id).first()


def export_logs(db: Session,
               filters: Optional[Dict[str, Any]] = None,
               format: str = "csv") -> bytes:
    """
    导出审计日志为指定格式。

    Args:
        db: 数据库会话
        filters: 筛选条件（与 query_logs 相同）
        format: 导出格式 ("csv", "json")

    Returns:
        bytes: 导出的文件内容
    """
    result = query_logs(db, filters, page=1, page_size=100000, sort_order="asc")
    logs = result["logs"]

    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "timestamp", "event_type", "username", "user_role",
            "operation", "file_path", "status", "client_ip", "error_message"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for log in logs:
            writer.writerow({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "username": log.username or "",
                "user_role": log.user_role or "",
                "operation": log.operation,
                "file_path": log.file_path,
                "status": log.status,
                "client_ip": log.client_ip or "",
                "error_message": log.error_message or ""
            })

        return output.getvalue().encode("utf-8")

    elif format.lower() == "json":
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.username,
                "user_role": log.user_role,
                "operation": log.operation,
                "file_path": log.file_path,
                "file_size_before": log.file_size_before,
                "file_size_after": log.file_size_after,
                "status": log.status,
                "client_ip": log.client_ip,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "error_message": log.error_message,
                "event_metadata": log.event_metadata
            })

        return json.dumps(logs_data, ensure_ascii=False, indent=2).encode("utf-8")

    else:
        raise ValueError(f"不支持的导出格式: {format}")


def get_statistics(db: Session,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   group_by: str = "day") -> Dict[str, Any]:
    """
    获取审计日志统计信息。

    Args:
        db: 数据库会话
        start_date: 统计开始日期
        end_date: 统计结束日期
        group_by: 分组方式 ("day", "hour", "operation", "user", "status")

    Returns:
        Dict[str, Any]: 统计信息字典
    """
    query = db.query(AuditLog)

    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    if group_by == "day":
        date_trunc = func.date(AuditLog.timestamp)
        results = db.query(
            date_trunc.label("group_key"),
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.timestamp >= (start_date or datetime.min),
            AuditLog.timestamp <= (end_date or datetime.max)
        ).group_by(date_trunc).all()

        return {
            "statistics": [
                {"date": str(r.group_key), "count": r.count}
                for r in results
            ],
            "group_by": "day"
        }

    elif group_by == "operation":
        results = db.query(
            AuditLog.operation,
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.timestamp >= (start_date or datetime.min),
            AuditLog.timestamp <= (end_date or datetime.max)
        ).group_by(AuditLog.operation).all()

        return {
            "statistics": [
                {"operation": r.operation, "count": r.count}
                for r in results
            ],
            "group_by": "operation"
        }

    elif group_by == "user":
        results = db.query(
            AuditLog.username,
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.timestamp >= (start_date or datetime.min),
            AuditLog.timestamp <= (end_date or datetime.max),
            AuditLog.username.isnot(None)
        ).group_by(AuditLog.username).order_by(desc("count")).limit(50).all()

        return {
            "statistics": [
                {"username": r.username, "count": r.count}
                for r in results
            ],
            "group_by": "user"
        }

    elif group_by == "status":
        results = db.query(
            AuditLog.status,
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.timestamp >= (start_date or datetime.min),
            AuditLog.timestamp <= (end_date or datetime.max)
        ).group_by(AuditLog.status).all()

        return {
            "statistics": [
                {"status": r.status, "count": r.count}
                for r in results
            ],
            "group_by": "status"
        }

    else:
        total = query.count()
        success_count = query.filter(AuditLog.status == "success").count()
        failure_count = query.filter(AuditLog.status == "failure").count()
        error_count = query.filter(AuditLog.status == "error").count()

        return {
            "total": total,
            "success": success_count,
            "failure": failure_count,
            "error": error_count,
            "group_by": group_by
        }


def cleanup_old_logs(db: Session, days: int = None) -> int:
    """
    清理过期的审计日志。

    Args:
        db: 数据库会话
        days: 保留天数，如果为 None 则使用配置中的 retention_days

    Returns:
        int: 删除的日志数量
    """
    if days is None:
        days = settings.log.retention_days

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    count = db.query(AuditLog).filter(
        AuditLog.timestamp < cutoff_date
    ).delete()

    db.commit()

    return count


def get_recent_logs(db: Session,
                    user_id: Optional[int] = None,
                    limit: int = 20) -> List[AuditLog]:
    """
    获取最近的审计日志。

    Args:
        db: 数据库会话
        user_id: 用户 ID（可选），只获取该用户的日志
        limit: 返回的最大记录数

    Returns:
        List[AuditLog]: 审计日志列表
    """
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()


def get_failed_operations(db: Session,
                           hours: int = 24,
                           limit: int = 100) -> List[AuditLog]:
    """
    获取最近的失败操作记录。

    Args:
        db: 数据库会话
        hours: 时间范围（小时）
        limit: 返回的最大记录数

    Returns:
        List[AuditLog]: 失败的审计日志列表
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    return db.query(AuditLog).filter(
        AuditLog.timestamp >= cutoff_time,
        AuditLog.status.in_(["failure", "error"])
    ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
