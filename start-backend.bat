@echo off
REM Windows 批处理启动脚本
echo 正在启动 Source Code Audit System...
set CONFIG_PATH=./config/config.yaml
python -m backend.app.main
pause