# 源码安全审计系统启动教程

## 项目架构

| 组件 | 技术栈                           | 端口   |
| -- | ----------------------------- | ---- |
| 前端 | Vue 3 + Vite + Element Plus   | 3000 |
| 后端 | FastAPI + SQLAlchemy + SQLite | 8000 |

***

## 前置要求

- **Node.js** >= 20.x
- **Python** >= 3.9
- **npm** 或 **pnpm**

***

## 启动完整流程

### 1. 首次设置（只需要做一次）

```
# 进入项目目录
cd e:\工作\tools\codeSafe

# 创建虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 在激活的虚拟环境中安装依赖
pip install -r backend/requirements.txt
```

### 2. 每次启动项目（每次都需要）

```PowerShell
# 进入项目目录
cd e:\工作\tools\codeSafe

# 激活虚拟环境（关键步骤）
venv\Scripts\activate

# 设置环境变量并启动程序
.\start_all.ps1
```

### 3. 退出虚拟环境（可选）

```
deactivate
```

## 注意事项

1. 激活虚拟环境后 ，命令行提示符会显示 (venv) 前缀，表示已进入虚拟环境
2. 每次打开新终端启动程序时 ，都需要重新激活虚拟环境
3. 如果忘记激活虚拟环境直接运行程序，可能会找不到依赖包

下次启动时只需双击这个脚本即可。
