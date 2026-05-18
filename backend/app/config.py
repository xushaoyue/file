"""
配置管理模块

本模块负责加载和管理系统的所有配置项，支持从 YAML 配置文件
和环境变量中读取配置，使用 Pydantic 进行配置验证和类型安全。

配置项包括：
- 应用基本配置（名称、端口、调试模式等）
- 数据库配置（类型、路径、连接池等）
- 安全配置（密钥、令牌过期时间、密码加密等）
- 文件监控配置（监控路径、排除规则等）
- 限流配置
- 日志配置
- 审计配置
- 文件访问配置
- 管理员默认账户配置
"""

import os
from typing import List, Optional
from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path


class AppConfig(BaseModel):
    """
    应用基本配置
    
    属性:
        name: 应用名称
        version: 应用版本号
        host: 服务监听地址
        port: 服务监听端口
        debug: 是否开启调试模式
        cors_origins: 允许的 CORS 源地址列表
        timezone: 系统时区
    """
    name: str = "Source Code Audit System"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000"]
    timezone: str = "Asia/Shanghai"


class DatabaseConfig(BaseModel):
    """
    数据库配置
    
    属性:
        type: 数据库类型（"sqlite" 或 "postgresql"）
        path: 数据库路径或连接字符串
        echo: 是否输出 SQL 语句日志
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数
    
    计算属性:
        url: 完整的数据库连接 URL
    """
    type: str = "sqlite"
    path: str = "./data/audit.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def url(self) -> str:
        """
        生成数据库连接 URL
        
        根据数据库类型返回对应的连接字符串。
        SQLite 使用文件路径，PostgreSQL 使用完整连接字符串。
        
        返回:
            数据库连接 URL 字符串
        """
        if self.type == "sqlite":
            return f"sqlite:///{self.path}"
        elif self.type == "postgresql":
            return f"postgresql://{self.path}"
        return self.path


class SecurityConfig(BaseModel):
    """
    安全配置
    
    属性:
        secret_key: JWT 签名密钥（生产环境必须修改！）
        algorithm: JWT 签名算法
        access_token_expire_minutes: 访问令牌有效期（分钟）
        refresh_token_expire_days: 刷新令牌有效期（天）
        bcrypt_cost_factor: bcrypt 密码哈希成本因子
        max_login_attempts: 最大登录失败次数
        lockout_duration_minutes: 登录失败锁定时长（分钟）
    """
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    bcrypt_cost_factor: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


class MonitorConfig(BaseModel):
    """
    文件系统监控配置
    
    属性:
        enabled: 是否启用文件监控
        watch_paths: 要监控的目录路径列表
        exclude_paths: 要排除的路径模式列表
        exclude_extensions: 要排除的文件扩展名列表
        mode: 监控模式（"recursive" 递归或 "non-recursive" 非递归）
        capture_diff: 是否捕获文件变更差异
        diff_context_lines: 差异比较时的上下文行数
        batch_size: 批量处理事件的大小
        batch_timeout_seconds: 批量处理的超时时间（秒）
    """
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
    """
    API 限流配置
    
    属性:
        enabled: 是否启用限流
        per_minute: 每分钟最大请求数
    """
    enabled: bool = True
    per_minute: int = 60


class LogConfig(BaseModel):
    """
    日志配置
    
    属性:
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        dir: 日志文件存储目录
        retention_days: 日志保留天数
        format: 日志格式（"json" 或 "text"）
        app_log_file: 应用日志文件名
        audit_log_prefix: 审计日志文件名前缀
    """
    level: str = "INFO"
    dir: str = "./logs/audit"
    retention_days: int = 365
    format: str = "json"
    app_log_file: str = "app.log"
    audit_log_prefix: str = "audit"


class AuditConfig(BaseModel):
    """
    审计日志配置
    
    属性:
        log_level: 审计日志级别（"minimal", "standard", "verbose"）
        batch_operation_threshold: 批量操作阈值
        log_list_operations: 是否记录文件列表操作
        log_read_operations: 是否记录文件读取操作
        enable_batch_logging: 是否启用批量日志记录
    """
    log_level: str = "standard"  # minimal, standard, verbose
    batch_operation_threshold: int = 10
    log_list_operations: bool = False
    log_read_operations: bool = False
    enable_batch_logging: bool = True


class FileAccessConfig(BaseModel):
    """
    文件访问配置
    
    属性:
        base_path: 文件访问的基础路径（限制用户只能访问此路径下的文件）
        max_file_size_mb: 最大文件大小（MB）
        allowed_encodings: 允许的文件编码列表
        preview_lines: 文件预览时显示的最大行数
    """
    base_path: str = ""
    max_file_size_mb: int = 100
    allowed_encodings: List[str] = ["utf-8", "gbk", "gb2312"]
    preview_lines: int = 1000


class AdminConfig(BaseModel):
    """
    管理员默认账户配置
    
    属性:
        default_username: 默认管理员用户名
        default_password: 默认管理员密码（首次登录后建议修改）
        must_change_password: 是否要求首次登录时修改密码
    """
    default_username: str = "admin"
    default_password: str = "Admin@123456"
    must_change_password: bool = True


class Settings(BaseSettings):
    """
    全局配置聚合类
    
    将所有配置模块聚合为一个统一的配置对象，便于访问。
    """
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    monitor: MonitorConfig = MonitorConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    log: LogConfig = LogConfig()
    audit: AuditConfig = AuditConfig()
    file_access: FileAccessConfig = FileAccessConfig()
    admin: AdminConfig = AdminConfig()

    class Config:
        env_file = ".env"
        extra = "allow"


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    加载配置文件
    
    优先从指定的配置文件加载，如果文件不存在则使用默认配置。
    配置文件路径可通过 CONFIG_PATH 环境变量指定。
    
    参数:
        config_path: 配置文件路径（可选）
    
    返回:
        加载后的 Settings 配置对象
    """
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
    """
    获取全局配置单例
    
    使用 LRU 缓存确保配置只加载一次，提高性能。
    
    返回:
        全局 Settings 配置对象
    """
    return load_config()


# 全局配置实例
settings = get_settings()
