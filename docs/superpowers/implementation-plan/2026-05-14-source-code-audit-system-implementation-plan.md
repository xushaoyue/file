# 源码安全审计系统 - 实现计划

**项目名称**: Source Code Security Audit System (SCSAS)  
**版本**: v1.0.0  
**编写日期**: 2026-05-14  
**状态**: 待实施

---

## 1. 项目结构

根据设计文档，创建以下目录结构：

```
/workspace/
├── backend/                          # 后端代码
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 应用入口
│   │   ├── config.py                # 配置管理
│   │   ├── database.py              # 数据库连接
│   │   ├── models/                  # 数据模型
│   │   ├── schemas/                 # Pydantic 模型
│   │   ├── routers/                 # API 路由
│   │   ├── services/                # 业务逻辑
│   │   ├── middleware/              # 中间件
│   │   └── utils/                   # 工具函数
│   ├── requirements.txt
│   └── run.py
├── frontend/                        # 前端代码
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── cli/                             # CLI 工具
├── config/                          # 配置文件
├── docker/                          # Docker 部署
├── tests/                           # 测试代码
└── docs/                            # 文档
```

---

## 2. 后端实现计划

### 2.1 依赖安装

创建 `backend/requirements.txt`：

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.13.0
watchdog==3.0.0
pyyaml==6.0.1
click==8.1.7
python-json-logger==2.0.7
aiosqlite==0.19.0
```

### 2.2 配置管理

创建 `backend/app/config.py`：

```python
from pydantic_settings import BaseSettings
from typing import List, Optional
import yaml
from pathlib import Path

class Settings(BaseSettings):
    app_name: str = "Source Code Audit System"
    app_version: str = "1.0.0"
    
    # 数据库配置
    database_url: str = "sqlite:///./data/audit.db"
    
    # 安全配置
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # 文件监控配置
    watch_paths: List[str] = []
    exclude_paths: List[str] = [".git/*", "node_modules/*"]
    exclude_extensions: List[str] = [".pyc", ".class"]
    
    # 限流配置
    rate_limit_per_minute: int = 60
    
    # 日志配置
    log_dir: str = "./logs/audit"
    
    class Config:
        env_file = ".env"
        extra = "allow"
```

### 2.3 数据模型

#### 2.3.1 用户模型 (`backend/app/models/user.py`)

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    ssh_keys = relationship("SSHKey", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
```

#### 2.3.2 SSH 密钥模型

```python
class SSHKey(Base):
    __tablename__ = "ssh_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    key_name = Column(String(100))
    public_key = Column(Text, nullable=False)
    key_type = Column(String(20))  # rsa, ed25519, ecdsa
    fingerprint = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="ssh_keys")
```

#### 2.3.3 权限模型

```python
class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    allowed_path = Column(String(500), nullable=False)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_download = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="permissions")
```

#### 2.3.4 审计日志模型

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    event_type = Column(String(30), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50))
    user_role = Column(String(20))
    operation = Column(String(20), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False, index=True)
    file_size_before = Column(BigInteger, nullable=True)
    file_size_after = Column(BigInteger, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    client_ip = Column(String(50))
    user_agent = Column(Text)
    session_id = Column(String(100))
    diff_content = Column(Text)
    error_message = Column(Text)
    metadata = Column(JSON)
    
    user = relationship("User", back_populates="audit_logs")
```

#### 2.3.5 会话模型

```python
class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), unique=True, index=True)
    refresh_token_hash = Column(String(255))
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    user = relationship("User", back_populates="sessions")
```

### 2.4 服务层实现

#### 2.4.1 认证服务 (`backend/app/services/auth_service.py`)

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.settings.secret_key, algorithm=self.settings.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.settings.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.settings.secret_key, algorithm=self.settings.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> dict:
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=[self.settings.algorithm])
            if payload.get("type") != token_type:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            return payload
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

#### 2.4.2 文件服务 (`backend/app/services/file_service.py`)

```python
import os
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status

class FileService:
    def __init__(self, settings):
        self.settings = settings
    
    def normalize_path(self, path: str, base_path: str) -> Path:
        base = Path(base_path).resolve()
        target = (base / path).resolve()
        if not str(target).startswith(str(base)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal detected")
        return target
    
    def list_files(self, path: str, recursive: bool = False) -> List[dict]:
        # 实现文件列表功能
        pass
    
    def read_file(self, path: str, encoding: str = "utf-8") -> dict:
        # 实现文件读取功能
        pass
    
    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        # 实现文件写入功能
        pass
    
    def delete_file(self, path: str) -> dict:
        # 实现文件删除功能
        pass
```

#### 2.4.3 审计服务 (`backend/app/services/audit_service.py`)

```python
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

class AuditService:
    def __init__(self, db: Session, settings):
        self.db = db
        self.settings = settings
    
    def log_event(self, event_data: dict) -> AuditLog:
        # 创建审计日志记录
        log = AuditLog(**event_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        # 同时写入文件
        self._write_to_file(log)
        return log
    
    def _write_to_file(self, log: AuditLog):
        log_dir = Path(self.settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = log_dir / f"audit-{date_str}.jsonl"
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.username,
                "operation": log.operation,
                "file_path": log.file_path,
                "status": log.status,
                "client_ip": log.client_ip
            }, ensure_ascii=False) + "\n")
    
    def query_logs(self, filters: dict, page: int = 1, page_size: int = 20) -> dict:
        query = self.db.query(AuditLog)
        
        if filters.get("start_date"):
            query = query.filter(AuditLog.timestamp >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(AuditLog.timestamp <= filters["end_date"])
        if filters.get("user_id"):
            query = query.filter(AuditLog.user_id == filters["user_id"])
        if filters.get("operation"):
            query = query.filter(AuditLog.operation == filters["operation"])
        if filters.get("file_path"):
            query = query.filter(AuditLog.file_path.like(f"%{filters['file_path']}%"))
        
        total = query.count()
        logs = query.order_by(desc(AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size).all()
        
        return {"logs": logs, "total": total, "page": page, "page_size": page_size}
```

### 2.5 API 路由

#### 2.5.1 认证路由 (`backend/app/routers/auth.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 验证用户凭证
    # 生成 JWT Token
    # 返回 access_token 和 refresh_token
    pass

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 创建用户
    # 返回待审批状态
    pass

@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    # 刷新 Token
    pass

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    # 将 Token 加入黑名单
    pass
```

#### 2.5.2 文件路由 (`backend/app/routers/files.py`)

```python
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/files", tags=["文件操作"])

@router.get("/list")
async def list_files(
    path: str = Query(...),
    recursive: bool = False,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user)
):
    # 列出文件
    pass

@router.get("/read")
async def read_file(
    path: str = Query(...),
    encoding: str = "utf-8",
    current_user: User = Depends(get_current_user)
):
    # 读取文件
    pass

@router.put("/write")
async def write_file(
    request: WriteFileRequest,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # 写入文件并记录审计日志
    pass

@router.delete("/delete")
async def delete_file(
    path: str = Query(...),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # 删除文件并记录审计日志
    pass

@router.get("/download")
async def download_file(
    path: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    # 下载文件并记录审计日志
    pass
```

### 2.6 文件监控服务 (`backend/app/services/monitor_service.py`)

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List
import time

class AuditEventHandler(FileSystemEventHandler):
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
    
    def on_created(self, event):
        self._log_event("FILE_CREATED" if not event.is_directory else "DIRECTORY_CREATED", event)
    
    def on_modified(self, event):
        if not event.is_directory:
            self._log_event("FILE_MODIFIED", event)
    
    def on_deleted(self, event):
        self._log_event("FILE_DELETED" if not event.is_directory else "DIRECTORY_DELETED", event)
    
    def on_moved(self, event):
        self._log_event("FILE_MOVED", event)
    
    def _log_event(self, event_type, event):
        self.audit_service.log_event({
            "event_type": event_type,
            "operation": "create" if "CREATED" in event_type else "modify" if "MODIFIED" in event_type else "delete" if "DELETED" in event_type else "move",
            "file_path": event.dest_path if hasattr(event, 'dest_path') else event.src_path,
            "status": "success"
        })

class MonitorService:
    def __init__(self, watch_paths: List[str], audit_service: AuditService):
        self.observer = Observer()
        self.handler = AuditEventHandler(audit_service)
        for path in watch_paths:
            self.observer.schedule(self.handler, path, recursive=True)
    
    def start(self):
        self.observer.start()
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
```

---

## 3. 前端实现计划

### 3.1 技术栈

- Vue.js 3 (Composition API)
- Vite
- Element Plus
- Pinia (状态管理)
- Vue Router
- Axios

### 3.2 项目初始化

```bash
cd frontend
npm create vite@latest . -- --template vue
npm install element-plus @element-plus/icons-vue vue-router@4 pinia axios
```

### 3.3 目录结构

```
frontend/src/
├── App.vue
├── main.js
├── router/
│   └── index.js
├── views/
│   ├── Login.vue
│   ├── Dashboard.vue
│   ├── FileBrowser.vue
│   ├── AuditLogs.vue
│   ├── UserManagement.vue
│   └── Settings.vue
├── components/
│   ├── Layout/
│   ├── FileTree.vue
│   ├── FileList.vue
│   ├── LogTable.vue
│   └── StatsChart.vue
├── stores/
│   ├── auth.js
│   └── audit.js
├── api/
│   ├── auth.js
│   ├── files.js
│   └── audit.js
└── utils/
    └── request.js
```

### 3.4 主要页面组件

#### 3.4.1 登录页面 (`views/Login.vue`)

- 用户名/密码输入框
- 记住登录状态复选框
- SSH 公钥登录选项（高级）
- 登录按钮和错误提示

#### 3.4.2 文件浏览器 (`views/FileBrowser.vue`)

- 左侧目录树组件
- 右侧文件列表组件
- 文件预览和操作按钮
- 权限信息显示

#### 3.4.3 审计日志页面 (`views/AuditLogs.vue`)

- 筛选栏（时间范围、用户、操作类型）
- 日志列表表格
- 分页组件
- 统计图表
- 导出按钮

---

## 4. CLI 工具实现计划

### 4.1 项目结构

```
cli/
├── audit_cli/
│   ├── __init__.py
│   ├── cli.py              # 主入口
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证命令
│   │   ├── files.py       # 文件命令
│   │   ├── logs.py        # 审计日志命令
│   │   └── users.py       # 用户管理命令
│   └── utils/
│       ├── __init__.py
│       └── api_client.py
├── setup.py
└── requirements.txt
```

### 4.2 命令实现

```python
# cli/audit_cli/cli.py
import click
from audit_cli.commands import auth, files, logs, users

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """源码安全审计系统 CLI 工具"""
    pass

cli.add_command(auth.login)
cli.add_command(auth.logout)
cli.add_command(auth.whoami)
cli.add_command(files.ls)
cli.add_command(files.cat)
cli.add_command(files.edit)
cli.add_command(files.download)
cli.add_command(files.rm)
cli.add_command(logs.logs)
cli.add_command(logs.export)
cli.add_command(users.list_users)
cli.add_command(users.add_user)
cli.add_command(users.del_user)
cli.add_command(users.set_permission)

if __name__ == "__main__":
    cli()
```

---

## 5. 测试计划

### 5.1 单元测试

```python
# tests/backend/test_auth_service.py
import pytest
from backend.app.services.auth_service import AuthService

def test_password_hashing():
    service = AuthService()
    hashed = service.get_password_hash("testpassword123")
    assert service.verify_password("testpassword123", hashed)
    assert not service.verify_password("wrongpassword", hashed)

def test_token_creation():
    service = AuthService()
    token = service.create_access_token({"sub": "testuser"})
    assert token is not None
    payload = service.verify_token(token)
    assert payload["sub"] == "testuser"
```

### 5.2 集成测试

```python
# tests/backend/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

def test_login_failure():
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
```

---

## 6. 部署计划

### 6.1 Docker 配置

```dockerfile
# docker/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 配置文件模板

```yaml
# config/config.yaml
app:
  name: "Source Code Audit System"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000
  debug: false

database:
  type: "sqlite"
  path: "./data/audit.db"

security:
  secret_key: "your-secret-key-change-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7
  bcrypt_cost_factor: 12

monitor:
  watch_paths:
    - "/source"
  exclude_paths:
    - "*/.git/*"
    - "*/node_modules/*"
  exclude_extensions:
    - ".pyc"
    - ".class"

rate_limit:
  per_minute: 60

log:
  level: "INFO"
  dir: "./logs/audit"
  retention_days: 365
```

---

## 7. 实施优先级

| 阶段 | 模块 | 优先级 | 预计工作量 |
|------|------|--------|-----------|
| 1 | 项目结构搭建、依赖安装 | P0 | 1 天 |
| 2 | 数据库模型和迁移 | P0 | 2 天 |
| 3 | 认证服务和 API | P0 | 3 天 |
| 4 | 文件服务和管理 API | P0 | 3 天 |
| 5 | 审计日志服务和 API | P0 | 2 天 |
| 6 | 文件监控服务 | P1 | 2 天 |
| 7 | 前端登录和仪表盘 | P1 | 2 天 |
| 8 | 前端文件浏览器 | P1 | 3 天 |
| 9 | 前端审计日志页面 | P1 | 2 天 |
| 10 | CLI 工具 | P2 | 2 天 |
| 11 | 单元测试和集成测试 | P1 | 2 天 |
| 12 | Docker 部署配置 | P2 | 1 天 |

---

**文档版本历史**:

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0.0 | 2026-05-14 | 初始实现计划 |
