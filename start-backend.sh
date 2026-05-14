#!/bin/bash
# Linux/macOS 启动脚本
echo "正在启动 Source Code Audit System..."
export CONFIG_PATH="./config/config.yaml"
python -m backend.app.main