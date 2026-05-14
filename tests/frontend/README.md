# 前端测试方案

## 概述

前端测试采用多层次测试策略：
- **单元测试**：使用 Vitest 测试组件和工具函数
- **组件测试**：使用 Vue Test Utils 测试 Vue 组件
- **端到端测试**：使用 Playwright 进行完整的用户流程测试

## 目录结构

```
tests/
└── frontend/
    ├── __init__.js
    ├── unit/                 # 单元测试
    │   ├── utils.test.js
    │   └── validators.test.js
    ├── components/           # 组件测试
    │   ├── LoginForm.test.js
    │   ├── UserTable.test.js
    │   └── AuditLogList.test.js
    ├── views/               # 页面测试
    │   ├── Login.test.js
    │   ├── Dashboard.test.js
    │   └── UserManagement.test.js
    └── e2e/                # 端到端测试
        ├── login.spec.js
        ├── file_browser.spec.js
        └── audit_logs.spec.js
```

## 快速开始

### 1. 安装测试依赖

```bash
cd frontend
npm install --save-dev vitest @vue/test-utils happy-dom playwright
```

### 2. 配置 Vitest

在 `vite.config.js` 中添加：

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
})
```

### 3. 在 package.json 中添加测试脚本

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

### 4. 运行测试

```bash
# 运行所有测试
npm test

# 运行单元测试
npm test -- tests/unit

# 运行组件测试
npm test -- tests/components

# 运行端到端测试
npm run test:e2e

# 生成覆盖率报告
npm run test:coverage
```

## 测试示例

### 单元测试示例

```javascript
// tests/unit/utils.test.js
import { describe, it, expect } from 'vitest'

describe('工具函数测试', () => {
  it('日期格式化函数', () => {
    expect(formatDate('2024-01-01')).toBe('2024-01-01')
  })

  it('权限检查函数', () => {
    expect(hasPermission('read', ['read', 'write'])).toBe(true)
    expect(hasPermission('delete', ['read', 'write'])).toBe(false)
  })
})
```

### 组件测试示例

```javascript
// tests/components/LoginForm.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginForm from '@/views/Login.vue'

describe('LoginForm 组件测试', () => {
  it('渲染登录表单', () => {
    const wrapper = mount(LoginForm)
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('表单验证', async () => {
    const wrapper = mount(LoginForm)
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('.el-form-item__error').exists()).toBe(true)
  })

  it('提交表单', async () => {
    const wrapper = mount(LoginForm, {
      data() {
        return {
          form: {
            username: 'admin',
            password: 'password123'
          }
        }
      }
    })

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('submit')).toBeTruthy()
  })
})
```

### 端到端测试示例

```javascript
// tests/e2e/login.spec.js
import { test, expect } from '@playwright/test'

test.describe('登录功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('成功登录', async ({ page }) => {
    await page.fill('input[placeholder="请输入用户名"]', 'admin')
    await page.fill('input[placeholder="请输入密码"]', 'Admin@123456')
    await page.click('button:has-text("登录")')

    await expect(page).toHaveURL('/')
    await expect(page.locator('.el-menu')).toBeVisible()
  })

  test('登录失败', async ({ page }) => {
    await page.fill('input[placeholder="请输入用户名"]', 'admin')
    await page.fill('input[placeholder="请输入密码"]', 'wrongpassword')
    await page.click('button:has-text("登录")')

    await expect(page.locator('.el-message--error')).toBeVisible()
  })

  test('未登录访问受保护页面', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL('/login')
  })
})
```

### API Mock 测试

```javascript
// tests/mocks/handlers.js
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.post('/api/v1/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock_token',
      refresh_token: 'mock_refresh_token',
      user: {
        id: 1,
        username: 'testuser',
        role: 'user'
      }
    })
  }),

  http.get('/api/v1/users', () => {
    return HttpResponse.json({
      users: [
        { id: 1, username: 'admin', role: 'admin' },
        { id: 2, username: 'user1', role: 'user' }
      ],
      total: 2
    })
  })
]
```

## 测试覆盖率目标

- **单元测试覆盖率**: 80%+
- **组件测试覆盖率**: 70%+
- **关键业务流程**: 100%

## 持续集成

在 CI 中运行测试：

```yaml
# .github/workflows/frontend-test.yml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run unit tests
        run: npm test
      - name: Run e2e tests
        run: npm run test:e2e
```

## 测试最佳实践

1. **AAA 模式**：Arrange（准备）→ Act（执行）→ Assert（断言）
2. **单一职责**：每个测试只验证一个功能点
3. **独立测试**：测试之间不应有依赖关系
4. **清晰的命名**：测试名称应清晰表达测试内容
5. **Mock 外部依赖**：API 调用等外部依赖应使用 Mock
6. **定期运行**：每次提交代码前运行所有测试
