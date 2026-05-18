import os
from typing import List, Optional
from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path


class AppConfig(BaseModel):
    name: str = "Source Code Audit System"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000"]


class DatabaseConfig(BaseModel):
    type: str = "sqlite"
    path: str = "./data/audit.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def url(self) -> str:
        if self.type == "sqlite":
            return f"sqlite:///{self.path}"
        elif self.type == "postgresql":
            return f"postgresql://{self.path}"
        return self.path


class SecurityConfig(BaseModel):
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    bcrypt_cost_factor: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


class MonitorConfig(BaseModel):
    enabled: bool = True
    watch_paths: List[str] = []
    exclude_paths: List[str] = []
    exclude_extensions: List[str] = []
    mode: str = "recursive"
    capture_diff: bool = True
    diff_context_lines: int = 3
    batch_size: int = 100
    batch_timeout_seconds: int = 5


class RateLimitConfig(BaseModel):
    enabled: bool = True
    per_minute: int = 60


class LogConfig(BaseModel):
    level: str = "INFO"
    dir: str = "./logs/audit"
    retention_days: int = 365
    format: str = "json"
    app_log_file: str = "app.log"
    audit_log_prefix: str = "audit"


class FileAccessConfig(BaseModel):
    base_path: str = ""
    max_file_size_mb: int = 100
    allowed_encodings: List[str] = ["utf-8", "gbk", "gb2312"]
    preview_lines: int = 1000


class AdminConfig(BaseModel):
    default_username: str = "admin"
    default_password: str = "Admin@123456"
    must_change_password: bool = True


class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    monitor: MonitorConfig = MonitorConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    log: LogConfig = LogConfig()
    file_access: FileAccessConfig = FileAccessConfig()
    admin: AdminConfig = AdminConfig()

    class Config:
        env_file = ".env"
        extra = "allow"


def load_config(config_path: Optional[str] = None) -> Settings:
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH", "/workspace/config/config.yaml")
    
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            return Settings(**config_data)
    
    return Settings()


@lru_cache()
def get_settings() -> Settings:
    return load_config()


settings = get_settings()
