# 源代码审计系统启动教程

## 项目架构

| 组件 | 技术栈                           | 端口   |
| -- | ----------------------------- | ---- |
| 前端 | Vue 3 + Vite + Element Plus   | 3000 |
| 后端 | FastAPI + SQLAlchemy + SQLite | 8000 |

***

## 前置要求

- **Node.js** >= 18.x
- **Python** >= 3.9
- **npm** 或 **pnpm**

***

## 1. 启动后端服务

```bash
# 进入后端目录
cd e:\工作\tools\codeSafe\backend

# 安装 Python 依赖
pip install -r requirements.txt

# 启动后端服务
cd e:\工作\tools\codeSafe
$env:CONFIG_PATH="./config/config.yaml"
python -m backend.app.main
```

后端启动成功后会：

- 自动初始化 SQLite 数据库 (`./data/audit.db`)
- 创建默认管理员账户

***

## 2. 启动前端服务

```bash
# 新开一个终端，进入前端目录
cd e:\工作\tools\codeSafe\frontend

# 安装前端依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器地址：`http://localhost:3000`

***

## 3. 登录系统

- **默认管理员账号**: `admin`
- **默认密码**: `Admin@123456`
- **首次登录后需要修改密码**

***

## 配置文件说明

主配置文件位于 `e:\工作\tools\codeSafe\config\config.yaml`：

```yaml
app:
  port: 8000          # 后端端口
database:
  path: "./data/audit.db"   # 数据库路径
admin:
  default_username: "admin"
  default_password: "Admin@123456"
monitor:
  enabled: true
  watch_paths:        # 监控的代码目录
    - "/source"
    - "D:/Projects/SourceCode"
```

***

## 常用命令

```bash
# 前端构建生产版本
npm run build

# 前端预览生产版本
npm run preview
```

