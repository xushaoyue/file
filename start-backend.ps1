# Windows PowerShell 启动脚本
$ErrorActionPreference = "Stop"
Write-Host "正在启动 Source Code Audit System..." -ForegroundColor Green
$env:CONFIG_PATH = "./config/config.yaml"
python -m backend.app.main