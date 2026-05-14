import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import init_db, SessionLocal
from backend.app.middleware.logging import LoggingMiddleware
from backend.app.middleware.rate_limit import RateLimiter
from backend.app.services.user_service import get_user_by_username, create_user
from backend.app.services.monitor_service import start_monitoring, stop_monitoring, get_monitor_service
from backend.app.services.auth_service import get_password_hash

logging.basicConfig(
    level=getattr(logging, settings.log.level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audit.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("正在初始化数据库...")
    init_db()

    logger.info("检查默认管理员用户...")
    db = SessionLocal()
    try:
        admin_user = get_user_by_username(db, settings.admin.default_username)
        if not admin_user:
            logger.info("创建默认管理员用户: %s", settings.admin.default_username)
            create_user(
                db=db,
                username=settings.admin.default_username,
                password=settings.admin.default_password,
                role="admin",
                must_change_password=settings.admin.must_change_password
            )
            logger.info("默认管理员用户创建成功")
        else:
            logger.info("默认管理员用户已存在")
    finally:
        db.close()

    if settings.monitor.enabled and settings.monitor.watch_paths:
        logger.info("正在启动文件监控服务...")
        start_monitoring()
        logger.info("文件监控服务已启动")

    logger.info("应用程序启动完成")

    yield

    logger.info("正在关闭应用程序...")

    monitor_service = get_monitor_service()
    if monitor_service.is_running:
        logger.info("正在停止监控服务...")
        stop_monitoring()
        logger.info("监控服务已停止")

    logger.info("应用程序已关闭")


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    debug=settings.app.debug,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimiter)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "请求验证失败",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error("未处理的异常: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误"}
    )


@app.get("/health")
async def health_check():
    monitor_service = get_monitor_service()
    return {
        "status": "healthy",
        "service": settings.app.name,
        "version": settings.app.version,
        "monitor": {
            "enabled": settings.monitor.enabled,
            "running": monitor_service.is_running
        }
    }


try:
    from backend.app.routers import auth, files, audit, users, keys
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["文件"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
    app.include_router(keys.router, prefix="/api/v1/keys", tags=["密钥"])
except ImportError as e:
    logger.warning("部分路由模块导入失败: %s", str(e))
