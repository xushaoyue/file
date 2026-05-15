# 自动化测试框架

本目录包含源码安全审计系统的自动化测试。

## 目录结构

```
tests/
├── backend/
│   ├── __init__.py
│   ├── conftest.py              # pytest 配置和 fixtures
│   ├── test_auth.py             # 认证相关测试
│   ├── test_users.py            # 用户管理测试
│   ├── test_files.py            # 文件操作测试
│   ├── test_audit.py            # 审计日志测试
│   └── utils.py                 # 测试辅助函数
├── frontend/
│   ├── __init__.js
│   ├── components/              # 组件测试
│   ├── views/                   # 页面测试
│   └── e2e/                    # 端到端测试
├── pytest.ini                   # pytest 配置
├── requirements-test.txt        # 测试依赖
└── README.md                    # 测试文档
```

## 快速开始

### 1. 安装测试依赖

```bash
pip install -r requirements-test.txt
```

### 2. 运行所有测试

```bash
pytest tests/ -v
```

### 3. 运行特定模块测试

```bash
# 测试认证功能
pytest tests/backend/test_auth.py -v

# 测试用户管理
pytest tests/backend/test_users.py -v

# 测试文件操作
pytest tests/backend/test_files.py -v

# 测试审计日志
pytest tests/backend/test_audit.py -v
```

### 4. 生成测试覆盖率报告

```bash
pytest tests/ --cov=backend --cov-report=html
```

## 测试配置

环境变量配置：

```bash
# .env.test
CONFIG_PATH="./config/config.yaml"
TEST_DATABASE_URL="sqlite:///./test_data/test_audit.db"
```

## 持续集成

测试可以在 CI/CD 管道中自动运行：

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: pytest tests/ -v --cov=backend
```
