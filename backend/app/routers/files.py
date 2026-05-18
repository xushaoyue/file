import os
import shutil
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user
from backend.app.schemas.file import (
    FileListResponse,
    FileItem,
    FileReadResponse,
    FileWriteRequest,
    FileDeleteResponse
)
from backend.app.schemas.common import ResponseModel
from backend.app.services import file_service
from backend.app.services.audit_service import log_event
from backend.app.models.user import User

router = APIRouter(prefix="/api/v1/files", tags=["文件管理"])


def get_client_info(request: Request) -> tuple:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent


@router.get("/list", response_model=FileListResponse)
async def list_files(
    request: Request,
    path: str = Query(default="/", description="要列出的目录路径"),
    recursive: bool = Query(default=False, description="是否递归列出子目录"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=1000, description="每页条目数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    列出目录中的文件。

    Args:
        request: HTTP 请求对象
        path: 要列出的目录路径
        recursive: 是否递归列出子目录
        page: 页码（从 1 开始）
        page_size: 每页条目数
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        FileListResponse: 文件列表响应
    """
    client_ip, user_agent = get_client_info(request)

    result = file_service.list_files(
        path=path,
        recursive=recursive,
        page=page,
        page_size=page_size,
        user=current_user,
        operation="read"
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    items = [
        FileItem(
            name=item["name"],
            path=item["path"],
            type="directory" if item["is_dir"] else "file",
            size=item.get("size", 0),
            modified_at=item.get("modified")
        )
        for item in result["files"]
    ]

    log_event(
        db,
        event_data={
            "event_type": "file_operation",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "list",
            "file_path": path,
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return FileListResponse(
        path=path,
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get("/read", response_model=FileReadResponse)
async def read_file(
    request: Request,
    path: str = Query(..., description="要读取的文件路径"),
    encoding: str = Query(default="utf-8", description="文件编码"),
    max_lines: Optional[int] = Query(default=None, description="最大读取行数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    读取文件内容。

    Args:
        request: HTTP 请求对象
        path: 要读取的文件路径
        encoding: 文件编码，默认为 utf-8
        max_lines: 最大读取行数（用于预览）
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        FileReadResponse: 文件内容响应
    """
    client_ip, user_agent = get_client_info(request)

    result = file_service.read_file(
        path=path,
        encoding=encoding,
        user=current_user,
        max_lines=max_lines
    )

    if "error" in result:
        log_event(
            db,
            event_data={
                "event_type": "file_operation",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "read",
                "file_path": path,
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": result["error"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    log_event(
        db,
        event_data={
            "event_type": "file_operation",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "read",
            "file_path": path,
            "file_size_after": result.get("size"),
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return FileReadResponse(
        path=result["path"],
        content=result["content"],
        encoding=result["encoding"],
        size=result["size"],
        modified_at=result.get("modified")
    )


@router.put("/write", response_model=ResponseModel)
async def write_file(
    request: Request,
    file_data: FileWriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    写入文件内容。

    Args:
        request: HTTP 请求对象
        file_data: 文件写入数据
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 写入结果响应
    """
    client_ip, user_agent = get_client_info(request)

    result = file_service.write_file(
        path=file_data.path,
        content=file_data.content,
        encoding=file_data.encoding,
        create_if_not_exists=file_data.create_if_not_exists,
        user=current_user
    )

    if "error" in result:
        log_event(
            db,
            event_data={
                "event_type": "file_operation",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "write",
                "file_path": file_data.path,
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": result["error"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    log_event(
        db,
        event_data={
            "event_type": "file_operation",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "write",
            "file_path": file_data.path,
            "file_size_before": result.get("size_before"),
            "file_size_after": result.get("size"),
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"文件写入成功: {file_data.path}",
        data={
            "path": result["path"],
            "size": result["size"],
            "size_before": result.get("size_before"),
            "encoding": result["encoding"]
        }
    )


@router.delete("/delete", response_model=ResponseModel)
async def delete_file(
    request: Request,
    path: str = Query(..., description="要删除的文件或目录路径"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除文件或目录。

    Args:
        request: HTTP 请求对象
        path: 要删除的文件或目录路径
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        ResponseModel: 删除结果响应
    """
    client_ip, user_agent = get_client_info(request)

    result = file_service.delete_file(
        path=path,
        user=current_user
    )

    if "error" in result:
        log_event(
            db,
            event_data={
                "event_type": "file_operation",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "delete",
                "file_path": path,
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": result["error"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    log_event(
        db,
        event_data={
            "event_type": "file_operation",
            "user_id": current_user.id,
            "username": current_user.username,
            "user_role": current_user.role,
            "operation": "delete",
            "file_path": path,
            "file_size_before": result.get("deleted_size"),
            "status": "success",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )

    return ResponseModel(
        success=True,
        message=f"文件删除成功: {path}",
        data={
            "path": result["path"],
            "deleted_size": result.get("deleted_size"),
            "was_directory": result.get("was_directory")
        }
    )


@router.get("/download")
async def download_file(
    request: Request,
    path: str = Query(..., description="要下载的文件路径"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载文件。

    Args:
        request: HTTP 请求对象
        path: 要下载的文件路径
        current_user: 当前用户对象
        db: 数据库会话

    Returns:
        StreamingResponse: 文件流响应
    """
    client_ip, user_agent = get_client_info(request)

    try:
        response = file_service.download_file(
            path=path,
            user=current_user
        )

        log_event(
            db,
            event_data={
                "event_type": "file_operation",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "download",
                "file_path": path,
                "status": "success",
                "client_ip": client_ip,
                "user_agent": user_agent
            }
        )

        return response

    except ValueError as e:
        log_event(
            db,
            event_data={
                "event_type": "file_operation",
                "user_id": current_user.id,
                "username": current_user.username,
                "user_role": current_user.role,
                "operation": "download",
                "file_path": path,
                "status": "failure",
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/directory", response_model=ResponseModel)
async def create_directory(
    request: Request,
    path: str = Query(..., description="父目录路径"),
    name: str = Query(..., description="目录名称"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip, user_agent = get_client_info(request)
    target_path = os.path.join(path, name) if path != "/" else f"/{name}"

    result = file_service.create_directory(path=target_path, user=current_user)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    log_event(db, event_data={
        "event_type": "file_operation",
        "user_id": current_user.id,
        "username": current_user.username,
        "user_role": current_user.role,
        "operation": "create_directory",
        "file_path": target_path,
        "status": "success",
        "client_ip": client_ip,
        "user_agent": user_agent
    })

    return ResponseModel(success=True, message=f"目录创建成功: {name}")


@router.post("/upload", response_model=ResponseModel)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    path: str = Form(default="/"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip, user_agent = get_client_info(request)
    target_dir = file_service.normalize_path(path)

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标目录不存在")

    target_path = target_dir / file.filename

    try:
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传失败: {str(e)}")

    log_event(db, event_data={
        "event_type": "file_operation",
        "user_id": current_user.id,
        "username": current_user.username,
        "user_role": current_user.role,
        "operation": "upload",
        "file_path": str(target_path),
        "file_size_after": len(content),
        "status": "success",
        "client_ip": client_ip,
        "user_agent": user_agent
    })

    return ResponseModel(success=True, message=f"文件上传成功: {file.filename}")


@router.put("/rename", response_model=ResponseModel)
async def rename_file(
    request: Request,
    old_path: str = Query(..., description="原文件路径"),
    new_path: str = Query(..., description="新文件路径"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip, user_agent = get_client_info(request)
    src = file_service.normalize_path(old_path)
    dst = file_service.normalize_path(new_path)

    if not src.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件不存在")

    try:
        os.rename(src, dst)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"重命名失败: {str(e)}")

    log_event(db, event_data={
        "event_type": "file_operation",
        "user_id": current_user.id,
        "username": current_user.username,
        "user_role": current_user.role,
        "operation": "rename",
        "file_path": str(src),
        "dest_path": str(dst),
        "status": "success",
        "client_ip": client_ip,
        "user_agent": user_agent
    })

    return ResponseModel(success=True, message="重命名成功")


@router.put("/move", response_model=ResponseModel)
async def move_file(
    request: Request,
    source_path: str = Query(..., description="源文件路径"),
    target_path: str = Query(..., description="目标路径"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip, user_agent = get_client_info(request)
    src = file_service.normalize_path(source_path)
    dst = file_service.normalize_path(target_path)

    if not src.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="源文件不存在")

    try:
        if dst.is_dir():
            dst = dst / src.name
        shutil.move(str(src), str(dst))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"移动失败: {str(e)}")

    log_event(db, event_data={
        "event_type": "file_operation",
        "user_id": current_user.id,
        "username": current_user.username,
        "user_role": current_user.role,
        "operation": "move",
        "file_path": str(src),
        "dest_path": str(dst),
        "status": "success",
        "client_ip": client_ip,
        "user_agent": user_agent
    })

    return ResponseModel(success=True, message="移动成功")


@router.post("/copy", response_model=ResponseModel)
async def copy_file_route(
    request: Request,
    source_path: str = Query(..., description="源文件路径"),
    target_path: str = Query(..., description="目标路径"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip, user_agent = get_client_info(request)

    result = file_service.copy_file(src=source_path, dst=target_path, user=current_user)

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    log_event(db, event_data={
        "event_type": "file_operation",
        "user_id": current_user.id,
        "username": current_user.username,
        "user_role": current_user.role,
        "operation": "copy",
        "file_path": source_path,
        "dest_path": target_path,
        "status": "success",
        "client_ip": client_ip,
        "user_agent": user_agent
    })

    return ResponseModel(success=True, message="复制成功")
