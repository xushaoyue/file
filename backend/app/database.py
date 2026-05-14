from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from typing import Generator
from backend.app.config import settings
import os

Base = declarative_base()

engine = create_engine(
    settings.database.url,
    connect_args={"check_same_thread": False} if settings.database.type == "sqlite" else {},
    poolclass=StaticPool if settings.database.type == "sqlite" else None,
    echo=settings.database.echo
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.app.models import user, ssh_key, permission, audit_log, session
    os.makedirs(os.path.dirname(settings.database.path.replace("sqlite:///", "")), exist_ok=True)
    os.makedirs(settings.log.dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
