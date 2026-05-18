"""
数据库连接和初始化模块

本模块负责数据库连接的管理、会话创建和数据库表初始化。
使用 SQLAlchemy 作为 ORM 框架，支持 SQLite 和 PostgreSQL 数据库。

主要功能:
- 创建数据库引擎
- 定义数据库会话工厂
- 提供依赖注入用的数据库会话获取函数
- 初始化数据库表结构
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from typing import Generator
from backend.app.config import settings
import os

# SQLAlchemy 基类，所有数据模型都继承自此类
Base = declarative_base()

# 创建数据库引擎
# SQLite 使用 NullPool 避免线程安全问题，生产环境使用连接池
engine = create_engine(
    settings.database.url,
    connect_args={"check_same_thread": False} if settings.database.type == "sqlite" else {},
    poolclass=NullPool if settings.database.type == "sqlite" else None,
    echo=settings.database.echo
)

# 数据库会话工厂
# autocommit=False: 禁止自动提交，需要手动调用 commit()
# autoflush=False: 禁止自动刷新到数据库
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    获取数据库会话的依赖注入函数
    
    用于 FastAPI 的 Depends 依赖注入，自动管理会话的生命周期。
    请求结束后自动关闭会话。
    
    生成:
        SQLAlchemy Session 对象
    
    使用示例:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    
    执行以下操作:
    1. 导入所有数据模型（确保 SQLAlchemy 知道所有表结构）
    2. 创建数据库文件所在目录（如果不存在）
    3. 创建日志存储目录（如果不存在）
    4. 创建所有数据库表（如果不存在）
    
    注意:
        - 此函数是幂等的，重复调用不会产生问题
        - 不会修改已存在的表结构（如需迁移使用 Alembic）
        - 应在应用启动时调用一次
    """
    # 导入所有模型，确保 SQLAlchemy 能识别它们
    from backend.app.models import user, ssh_key, permission, audit_log, session
    from backend.app.models import git_repository, git_commit, git_webhook
    
    # 创建数据库文件目录
    db_path = settings.database.path.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 创建日志目录
    os.makedirs(settings.log.dir, exist_ok=True)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
