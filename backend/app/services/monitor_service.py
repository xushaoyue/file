import os
import time
import fnmatch
import threading
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from datetime import datetime, timedelta, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from backend.app.config import settings
from backend.app.services.audit_service import log_event, write_to_file, get_current_time
from backend.app.database import SessionLocal


class AuditEventHandler(FileSystemEventHandler):
    """
    文件系统事件处理器，用于监听和记录文件变更。

    Attributes:
        db_session_factory: 数据库会话工厂函数
        watch_paths: 监控的路径列表
        exclude_paths: 排除的路径列表
        exclude_extensions: 排除的文件扩展名列表
        capture_diff: 是否捕获文件差异
        pending_events: 待处理的事件队列
        batch_size: 批处理大小
        batch_timeout: 批处理超时时间（秒）
        audit_config: 审计配置
    """

    def __init__(self,
                 db_session_factory,
                 watch_paths: Optional[List[str]] = None,
                 exclude_paths: Optional[List[str]] = None,
                 exclude_extensions: Optional[List[str]] = None,
                 capture_diff: bool = True,
                 diff_context_lines: int = 3,
                 batch_size: int = 100,
                 batch_timeout: float = 5.0):
        """
        初始化事件处理器。

        Args:
            db_session_factory: 数据库会话工厂函数
            watch_paths: 监控的路径列表
            exclude_paths: 排除的路径列表
            exclude_extensions: 排除的文件扩展名列表
            capture_diff: 是否捕获文件差异
            diff_context_lines: 差异上下文行数
            batch_size: 批处理大小
            batch_timeout: 批处理超时时间
        """
        super().__init__()
        self.db_session_factory = db_session_factory
        self.watch_paths = watch_paths or settings.monitor.watch_paths
        self.exclude_paths = exclude_paths or settings.monitor.exclude_paths
        self.exclude_extensions = exclude_extensions or settings.monitor.exclude_extensions
        self.capture_diff = capture_diff and settings.audit.log_level == "verbose"
        self.diff_context_lines = diff_context_lines
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.audit_config = settings.audit

        self._pending_events: List[Dict[str, Any]] = []
        self._last_flush = time.time()
        self._lock = threading.Lock()

    def _should_exclude(self, path: str) -> bool:
        """
        检查路径是否应该被排除。

        Args:
            path: 文件路径

        Returns:
            bool: 是否应该排除
        """
        for exclude_path in self.exclude_paths:
            if fnmatch.fnmatch(path.replace("\\", "/"), exclude_path.replace("\\", "/")):
                return True

        for exclude_ext in self.exclude_extensions:
            if path.endswith(exclude_ext):
                return True

        return False

    def _get_file_diff(self, path: str, max_lines: int = 10) -> Optional[str]:
        """
        获取文件的变更差异。

        Args:
            path: 文件路径
            max_lines: 最大行数

        Returns:
            Optional[str]: 文件差异内容
        """
        if not self.capture_diff:
            return None

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[:max_lines]
                return "".join(lines)
        except Exception:
            return None

    def _get_file_size(self, path: str) -> Optional[int]:
        """
        获取文件大小。

        Args:
            path: 文件路径

        Returns:
            Optional[int]: 文件大小（字节）
        """
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    def _to_relative_path(self, path: str) -> str:
        """
        将绝对路径转换为相对于监控路径的路径。

        Args:
            path: 原始绝对路径

        Returns:
            str: 相对路径（以 / 开头），如果不在监控路径下则返回原路径
        """
        path_obj = Path(path)
        for watch_path in self.watch_paths:
            try:
                watch_obj = Path(os.path.abspath(watch_path))
                relative = path_obj.relative_to(watch_obj)
                return "/" + relative.as_posix()
            except (ValueError, OSError):
                continue
        return path

    def _create_event_data(self, event: FileSystemEvent) -> Dict[str, Any]:
        """
        创建事件数据字典。

        Args:
            event: 文件系统事件对象

        Returns:
            Dict[str, Any]: 事件数据字典
        """
        event_type_map = {
            "created": "file_created",
            "deleted": "file_deleted",
            "modified": "file_modified",
            "moved": "file_moved",
            "closed": "file_closed"
        }

        operation_map = {
            "created": "create",
            "deleted": "delete",
            "modified": "modify",
            "moved": "move",
            "closed": "close"
        }

        dest_path = getattr(event, "dest_path", None)

        return {
            "event_type": event_type_map.get(event.event_type, event.event_type),
            "operation": operation_map.get(event.event_type, "unknown"),
            "file_path": self._to_relative_path(event.src_path),
            "dest_path": self._to_relative_path(dest_path) if dest_path else None,
            "is_directory": event.is_directory,
            "timestamp": get_current_time(),
            "status": "success",
            "username": "system"
        }

    def _flush_events(self):
        """
        将待处理的事件批量写入数据库。
        """
        with self._lock:
            if not self._pending_events:
                return

            events_to_write = self._pending_events[:]
            self._pending_events.clear()
            self._last_flush = time.time()

        db = self.db_session_factory()
        try:
            for event_data in events_to_write:
                try:
                    audit_log = log_event(db, event_data)
                    write_to_file(audit_log)
                except Exception:
                    pass
        finally:
            db.close()

    def on_any_event(self, event: FileSystemEvent):
        """
        处理任何文件系统事件。

        Args:
            event: 文件系统事件对象
        """
        # 过滤掉目录修改事件（通常是无意义的系统行为，如访问时间更新）
        if event.event_type == "modified" and event.is_directory:
            return
            
        # 过滤掉 close 事件（大多数情况下不需要记录）
        if event.event_type == "closed":
            return

        if self._should_exclude(event.src_path):
            return

        if hasattr(event, "dest_path") and event.dest_path:
            if self._should_exclude(event.dest_path):
                return

        event_data = self._create_event_data(event)

        if event.event_type == "modified" and not event.is_directory:
            event_data["file_size_before"] = self._get_file_size(event.src_path)
            event_data["diff_content"] = self._get_file_diff(
                event.src_path,
                self.diff_context_lines
            )
        elif event.event_type == "created" and not event.is_directory:
            event_data["file_size_after"] = self._get_file_size(event.src_path)
        elif event.event_type == "deleted":
            event_data["file_size_before"] = self._get_file_size(event.src_path)

        with self._lock:
            self._pending_events.append(event_data)

            should_flush = (
                len(self._pending_events) >= self.batch_size or
                time.time() - self._last_flush >= self.batch_timeout
            )

        if should_flush:
            self._flush_events()

    def on_created(self, event):
        """
        文件或目录创建时调用。

        Args:
            event: 创建事件对象
        """
        pass

    def on_deleted(self, event):
        """
        文件或目录删除时调用。

        Args:
            event: 删除事件对象
        """
        pass

    def on_modified(self, event):
        """
        文件或目录修改时调用。

        Args:
            event: 修改事件对象
        """
        pass

    def on_moved(self, event):
        """
        文件或目录移动时调用。

        Args:
            event: 移动事件对象
        """
        pass

    def shutdown(self):
        """
        关闭处理器，刷新所有待处理的事件。
        """
        self._flush_events()


class MonitorService:
    """
    文件系统监控服务。

    Attributes:
        observers: 观察者字典
        event_handler: 事件处理器
        is_running: 服务是否正在运行
    """

    def __init__(self, db_session_factory = None):
        """
        初始化监控服务。

        Args:
            db_session_factory: 数据库会话工厂函数
        """
        self.db_session_factory = db_session_factory or SessionLocal
        self.observers: Dict[str, Observer] = {}
        self.event_handler: Optional[AuditEventHandler] = None
        self._is_running = False
        self._lock = threading.Lock()

    def start(self, watch_paths: Optional[List[str]] = None) -> bool:
        """
        启动文件系统监控服务。

        Args:
            watch_paths: 要监控的路径列表，如果为 None 则使用配置中的路径

        Returns:
            bool: 是否成功启动
        """
        if self._is_running:
            return True

        if watch_paths is None:
            watch_paths = settings.monitor.watch_paths

        if not watch_paths:
            return False

        with self._lock:
            self.event_handler = AuditEventHandler(
                db_session_factory=self.db_session_factory,
                capture_diff=settings.monitor.capture_diff,
                diff_context_lines=settings.monitor.diff_context_lines,
                batch_size=settings.monitor.batch_size,
                batch_timeout=settings.monitor.batch_timeout_seconds
            )

            for path in watch_paths:
                if not os.path.exists(path):
                    continue

                observer = Observer()
                mode = settings.monitor.mode

                observer.schedule(
                    self.event_handler,
                    path,
                    recursive=(mode == "recursive")
                )
                observer.start()
                self.observers[path] = observer

            self._is_running = True

        return True

    def stop(self):
        """
        停止文件系统监控服务。
        """
        if not self._is_running:
            return

        with self._lock:
            for path, observer in list(self.observers.items()):
                observer.stop()
                observer.join(timeout=5)
                self.observers.pop(path, None)

            if self.event_handler:
                self.event_handler.shutdown()
                self.event_handler = None

            self._is_running = False

    def restart(self, watch_paths: Optional[List[str]] = None):
        """
        重启监控服务。

        Args:
            watch_paths: 要监控的路径列表

        Returns:
            bool: 是否成功重启
        """
        self.stop()
        return self.start(watch_paths)

    @property
    def is_running(self) -> bool:
        """
        检查服务是否正在运行。

        Returns:
            bool: 服务是否正在运行
        """
        return self._is_running

    def get_status(self) -> Dict[str, Any]:
        """
        获取监控服务状态。

        Returns:
            Dict[str, Any]: 状态信息字典
        """
        return {
            "is_running": self._is_running,
            "watch_paths": list(self.observers.keys()),
            "observer_count": len(self.observers),
            "pending_events": (
                len(self.event_handler._pending_events)
                if self.event_handler else 0
            )
        }

    def add_watch_path(self, path: str, recursive: bool = True) -> bool:
        """
        添加新的监控路径。

        Args:
            path: 要监控的路径
            recursive: 是否递归监控子目录

        Returns:
            bool: 是否成功添加
        """
        if not self._is_running:
            return False

        if not os.path.exists(path):
            return False

        if path in self.observers:
            return True

        with self._lock:
            observer = Observer()
            observer.schedule(self.event_handler, path, recursive=recursive)
            observer.start()
            self.observers[path] = observer

        return True

    def remove_watch_path(self, path: str) -> bool:
        """
        移除监控路径。

        Args:
            path: 要移除的路径

        Returns:
            bool: 是否成功移除
        """
        if path not in self.observers:
            return False

        with self._lock:
            observer = self.observers.pop(path)
            observer.stop()
            observer.join(timeout=5)

        return True

    def flush(self):
        """
        刷新所有待处理的事件到数据库。
        """
        if self.event_handler:
            self.event_handler._flush_events()


_monitor_service: Optional[MonitorService] = None
_service_lock = threading.Lock()


def get_monitor_service() -> MonitorService:
    """
    获取全局监控服务实例（单例模式）。

    Returns:
        MonitorService: 监控服务实例
    """
    global _monitor_service

    with _service_lock:
        if _monitor_service is None:
            _monitor_service = MonitorService()
        return _monitor_service


def start_monitoring(watch_paths: Optional[List[str]] = None) -> bool:
    """
    启动全局监控服务。

    Args:
        watch_paths: 要监控的路径列表

    Returns:
        bool: 是否成功启动
    """
    service = get_monitor_service()
    return service.start(watch_paths)


def stop_monitoring():
    """
    停止全局监控服务。
    """
    service = get_monitor_service()
    service.stop()


def get_monitoring_status() -> Dict[str, Any]:
    """
    获取全局监控服务状态。

    Returns:
        Dict[str, Any]: 状态信息字典
    """
    service = get_monitor_service()
    return service.get_status()
