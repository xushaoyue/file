#!/usr/bin/env python3
import sys
import os

os.environ['CONFIG_PATH'] = './config/config.yaml'
os.environ['PYTEST_RUNNING'] = '1'

sys.path.insert(0, '/workspace')

from backend.app.main import app

print("=== 已注册的路由 ===")
for route in app.routes:
    print(f"Path: {route.path}, Methods: {route.methods}, Name: {route.name}")

print("\n=== 测试登录路由 ===")
found_login = any(route.path == "/api/v1/auth/login" for route in app.routes)
print(f"登录路由找到: {found_login}")

print("\n=== 完整路由列表 ===")
for route in app.routes:
    print(f"{route.methods} {route.path}")
