@echo off
REM Windows 批处理测试脚本

echo =========================================
echo 源码安全审计系统 - 自动化测试
echo =========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python 未安装
    exit /b 1
)
echo ✓ Python 已安装

REM 安装测试依赖
echo.
echo 安装测试依赖...
pip install -q -r tests\requirements-test.txt
echo ✓ 依赖安装完成

REM 运行测试
echo.
echo =========================================
echo 运行后端测试
echo =========================================
echo.

pytest tests\backend\ -v --tb=short

if errorlevel 1 (
    echo.
    echo ✗ 测试失败
    exit /b 1
)

echo.
echo =========================================
echo ✓ 所有测试完成
echo =========================================
pause
