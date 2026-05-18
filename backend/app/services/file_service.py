import os
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from starlette.responses import StreamingResponse

from backend.app.config import settings
from backend.app.models.user import User
from backend.app.services.permission_service import check_permission


def normalize_path(path: Union[str, Path],
                   base_path: Optional[Union[str, Path]] = None) -> Path:
    """
    规范化并验证文件路径，防止路径遍历攻击。

    Args:
        path: 要规范化的路径
        base_path: 基础路径，如果提供则确保返回的路径在基础路径内

    Returns:
        Path: 规范化后的绝对路径

    Raises:
        ValueError: 如果路径无效或试图遍历基础路径
    """
    if base_path is None:
        base_path = _get_base_path()

    if isinstance(path, str):
        path = Path(path)

    path_str = str(path)
    # Windows: Path("/") 或 Path("/xxx") 会解析为盘符根目录（如 D:\）
    # 映射为基础目录或基础目录下的相对路径
    if path_str in ("/", "\\"):
        path = Path(str(base_path))
    elif os.name == 'nt' and len(path_str) > 1 and path_str[0] in ('/', '\\'):
        rel_part = path_str.lstrip('/\\')
        path = Path(str(base_path)) / rel_part if rel_part else Path(str(base_path))

    abs_path = path.expanduser().resolve()

    if base_path:
        if isinstance(base_path, str):
            base_path = Path(base_path)
        base_path = base_path.expanduser().resolve()

        try:
            abs_path.relative_to(base_path)
        except ValueError:
            raise ValueError(f"路径 '{path}' 不在允许的目录 '{base_path}' 内")

    for part in abs_path.parts:
        if part == ".." or part.startswith("~"):
            raise ValueError(f"无效的路径: {path}")

    return abs_path


def _get_base_path() -> Path:
    base = settings.file_access.base_path
    if base:
        return Path(base).expanduser().resolve()
    return Path.cwd()


def check_file_permission(user: User, path: Union[str, Path],
                          operation: str) -> bool:
    """
    检查用户对文件的操作权限。

    Args:
        user: 用户对象
        path: 文件路径
        operation: 操作类型 ("read", "write", "delete", "download")

    Returns:
        bool: 是否具有权限
    """
    path_str = str(normalize_path(path))
    return check_permission(user, path_str, operation)


def list_files(path: Union[str, Path],
               recursive: bool = False,
               page: int = 1,
               page_size: int = 100,
               user: Optional[User] = None,
               operation: str = "read") -> Dict[str, Any]:
    """
    列出目录中的文件。

    Args:
        path: 目录路径
        recursive: 是否递归列出子目录
        page: 页码（从 1 开始）
        page_size: 每页条目数
        user: 用户对象（用于权限检查）
        operation: 需要的操作权限

    Returns:
        Dict[str, Any]: 包含 files 列表、总数、分页信息的结果字典
    """
    abs_path = normalize_path(path)
    base = _get_base_path()

    if not abs_path.exists():
        return {"error": "路径不存在", "files": [], "total": 0}
    if not abs_path.is_dir():
        return {"error": "路径不是目录", "files": [], "total": 0}

    if user and not check_file_permission(user, abs_path, operation):
        return {"error": "没有权限访问该目录", "files": [], "total": 0}

    all_items = []

    if recursive:
        for root, dirs, files in os.walk(abs_path):
            for name in files + dirs:
                item_path = Path(root) / name
                all_items.append(_get_file_info(item_path, base))
    else:
        for item in abs_path.iterdir():
            all_items.append(_get_file_info(item, base))

    total = len(all_items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = all_items[start:end]

    return {
        "files": paginated_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }


def _get_file_info(path: Path, base_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    获取文件或目录的信息。

    Args:
        path: 文件路径
        base_path: 基础路径，如果提供则返回相对于基础路径的路径

    Returns:
        Dict[str, Any]: 文件信息字典
    """
    stat = path.stat()
    display_path = str(path)
    if base_path:
        try:
            display_path = "/" + path.relative_to(base_path).as_posix()
        except ValueError:
            pass
    return {
        "name": path.name,
        "path": display_path,
        "is_dir": path.is_dir(),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }


def read_file(path: Union[str, Path],
              encoding: str = "utf-8",
              user: Optional[User] = None,
              max_lines: Optional[int] = None) -> Dict[str, Any]:
    """
    读取文件内容。

    Args:
        path: 文件路径
        encoding: 文件编码，默认为 utf-8
        user: 用户对象（用于权限检查）
        max_lines: 最大读取行数（用于预览）

    Returns:
        Dict[str, Any]: 包含 content、lines、size 等信息的结果字典
    """
    abs_path = normalize_path(path)

    if not abs_path.exists():
        return {"error": "文件不存在"}
    if not abs_path.is_file():
        return {"error": "路径不是文件"}

    if user and not check_file_permission(user, abs_path, "read"):
        return {"error": "没有读取权限"}

    if encoding not in settings.file_access.allowed_encodings:
        return {"error": f"不支持的编码: {encoding}"}

    file_size = abs_path.stat().st_size
    if file_size > settings.file_access.max_file_size_mb * 1024 * 1024:
        return {"error": f"文件超过大小限制 ({settings.file_access.max_file_size_mb}MB)"}

    try:
        with open(abs_path, "r", encoding=encoding) as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
                truncated = any(f.readline() for _ in range(1))
            else:
                content = f.read()
                lines = content.splitlines()
                truncated = False

        return {
            "content": content,
            "lines": len(lines),
            "size": file_size,
            "encoding": encoding,
            "truncated": truncated,
            "path": str(abs_path),
            "modified": datetime.fromtimestamp(abs_path.stat().st_mtime).isoformat()
        }
    except UnicodeDecodeError:
        return {"error": f"无法使用 {encoding} 编码读取文件"}
    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}


def write_file(path: Union[str, Path],
               content: str,
               encoding: str = "utf-8",
               create_if_not_exists: bool = True,
               user: Optional[User] = None) -> Dict[str, Any]:
    """
    写入文件内容。

    Args:
        path: 文件路径
        content: 要写入的内容
        encoding: 文件编码，默认为 utf-8
        create_if_not_exists: 如果文件不存在是否创建
        user: 用户对象（用于权限检查）

    Returns:
        Dict[str, Any]: 包含 success、path、size 等信息的结果字典
    """
    abs_path = normalize_path(path)

    if user and not check_file_permission(user, abs_path, "write"):
        return {"error": "没有写入权限"}

    if not abs_path.parent.exists():
        if not create_if_not_exists:
            return {"error": "父目录不存在"}
        abs_path.parent.mkdir(parents=True, exist_ok=True)

    if abs_path.exists() and not abs_path.is_file():
        return {"error": "路径已存在且不是文件"}

    if encoding not in settings.file_access.allowed_encodings:
        return {"error": f"不支持的编码: {encoding}"}

    try:
        size_before = abs_path.stat().st_size if abs_path.exists() else 0

        with open(abs_path, "w", encoding=encoding) as f:
            f.write(content)

        size_after = abs_path.stat().st_size

        return {
            "success": True,
            "path": str(abs_path),
            "size": size_after,
            "size_before": size_before,
            "encoding": encoding,
            "modified": datetime.fromtimestamp(abs_path.stat().st_mtime).isoformat()
        }
    except Exception as e:
        return {"error": f"写入文件失败: {str(e)}"}


def delete_file(path: Union[str, Path],
                user: Optional[User] = None) -> Dict[str, Any]:
    """
    删除文件或目录。

    Args:
        path: 文件路径
        user: 用户对象（用于权限检查）

    Returns:
        Dict[str, Any]: 包含 success、path 等信息的结果字典
    """
    abs_path = normalize_path(path)

    if not abs_path.exists():
        return {"error": "文件不存在"}

    if user and not check_file_permission(user, abs_path, "delete"):
        return {"error": "没有删除权限"}

    try:
        size = abs_path.stat().st_size if abs_path.is_file() else 0
        is_dir = abs_path.is_dir()

        if is_dir:
            import shutil
            shutil.rmtree(abs_path)
        else:
            abs_path.unlink()

        return {
            "success": True,
            "path": str(abs_path),
            "deleted_size": size,
            "was_directory": is_dir
        }
    except Exception as e:
        return {"error": f"删除文件失败: {str(e)}"}


def download_file(path: Union[str, Path],
                  user: Optional[User] = None) -> StreamingResponse:
    """
    生成文件下载响应。

    Args:
        path: 文件路径
        user: 用户对象（用于权限检查）

    Returns:
        StreamingResponse: 文件流响应

    Raises:
        ValueError: 如果文件不存在或用户没有下载权限
    """
    abs_path = normalize_path(path)

    if not abs_path.exists():
        raise ValueError("文件不存在")

    if not abs_path.is_file():
        raise ValueError("路径不是文件")

    if user and not check_file_permission(user, abs_path, "download"):
        raise ValueError("没有下载权限")

    def file_iterator():
        chunk_size = 8192
        with open(abs_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk

    filename = abs_path.name
    content_type_map = {
        ".txt": "text/plain",
        ".json": "application/json",
        ".xml": "application/xml",
        ".py": "text/x-python",
        ".js": "application/javascript",
        ".html": "text/html",
        ".css": "text/css",
    }
    content_type = content_type_map.get(abs_path.suffix.lower(), "application/octet-stream")

    return StreamingResponse(
        file_iterator(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(abs_path.stat().st_size)
        }
    )


def get_file_hash(path: Union[str, Path], algorithm: str = "sha256") -> Optional[str]:
    """
    计算文件的哈希值。

    Args:
        path: 文件路径
        algorithm: 哈希算法 ("md5", "sha1", "sha256")

    Returns:
        Optional[str]: 文件哈希值，计算失败返回 None
    """
    abs_path = normalize_path(path)

    if not abs_path.exists() or not abs_path.is_file():
        return None

    try:
        hash_func = getattr(hashlib, algorithm)()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return None


def create_directory(path: Union[str, Path],
                     user: Optional[User] = None) -> Dict[str, Any]:
    """
    创建目录。

    Args:
        path: 目录路径
        user: 用户对象（用于权限检查）

    Returns:
        Dict[str, Any]: 包含 success、path 等信息的结果字典
    """
    abs_path = normalize_path(path)

    if abs_path.exists():
        if abs_path.is_dir():
            return {"error": "目录已存在"}
        return {"error": "路径已存在且不是目录"}

    if user and not check_file_permission(user, abs_path.parent, "write"):
        return {"error": "没有创建目录的权限"}

    try:
        abs_path.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "path": str(abs_path),
            "created": datetime.fromtimestamp(abs_path.stat().st_ctime).isoformat()
        }
    except Exception as e:
        return {"error": f"创建目录失败: {str(e)}"}


def copy_file(src: Union[str, Path],
              dst: Union[str, Path],
              user: Optional[User] = None) -> Dict[str, Any]:
    """
    复制文件。

    Args:
        src: 源文件路径
        dst: 目标文件路径
        user: 用户对象（用于权限检查）

    Returns:
        Dict[str, Any]: 包含 success、src、dst 等信息的结果字典
    """
    src_path = normalize_path(src)
    dst_path = normalize_path(dst)

    if not src_path.exists():
        return {"error": "源文件不存在"}
    if not src_path.is_file():
        return {"error": "源路径不是文件"}

    if user:
        if not check_file_permission(user, src_path, "read"):
            return {"error": "没有读取源文件的权限"}
        if not check_file_permission(user, dst_path, "write"):
            return {"error": "没有写入目标文件的权限"}

    try:
        import shutil
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name

        shutil.copy2(src_path, dst_path)

        return {
            "success": True,
            "src": str(src_path),
            "dst": str(dst_path),
            "size": dst_path.stat().st_size
        }
    except Exception as e:
        return {"error": f"复制文件失败: {str(e)}"}
