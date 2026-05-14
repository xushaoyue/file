#!/bin/bash

# 测试运行脚本
# 用于运行所有自动化测试

set -e

echo "========================================="
echo "源码安全审计系统 - 自动化测试"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查依赖
check_dependencies() {
    echo "检查测试依赖..."
    echo ""

    # 检查 Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}错误: Python 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python 已安装: $(python --version)${NC}"

    # 检查 pip
    if ! command -v pip &> /dev/null; then
        echo -e "${RED}错误: pip 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ pip 已安装${NC}"
    echo ""
}

# 安装后端测试依赖
install_backend_deps() {
    echo "安装后端测试依赖..."
    pip install -q -r tests/requirements-test.txt
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
    echo ""
}

# 运行后端测试
run_backend_tests() {
    echo "========================================="
    echo "运行后端 API 测试"
    echo "========================================="
    echo ""

    cd /workspace

    # 运行所有后端测试
    pytest tests/backend/ -v --tb=short

    echo ""
    echo -e "${GREEN}✓ 后端测试完成${NC}"
    echo ""
}

# 生成测试覆盖率报告
generate_coverage_report() {
    echo "========================================="
    echo "生成测试覆盖率报告"
    echo "========================================="
    echo ""

    pytest tests/backend/ --cov=backend --cov-report=html --cov-report=term

    echo ""
    echo -e "${GREEN}✓ 覆盖率报告已生成: htmlcov/index.html${NC}"
    echo ""
}

# 运行快速测试（不生成覆盖率）
run_quick_tests() {
    echo "运行快速测试..."
    pytest tests/backend/ -v --tb=short -x

    echo ""
    echo -e "${GREEN}✓ 快速测试完成${NC}"
    echo ""
}

# 主菜单
show_menu() {
    echo "请选择测试选项："
    echo "1) 运行所有测试（包括覆盖率）"
    echo "2) 运行快速测试（不生成覆盖率）"
    echo "3) 仅安装依赖"
    echo "4) 仅运行后端测试"
    echo "5) 退出"
    echo ""
}

# 交互式菜单
interactive_menu() {
    show_menu
    read -p "请输入选项 [1-5]: " choice

    case $choice in
        1)
            check_dependencies
            install_backend_deps
            run_backend_tests
            generate_coverage_report
            echo -e "${GREEN}========================================="
            echo "所有测试完成！"
            echo "=========================================${NC}"
            ;;
        2)
            check_dependencies
            install_backend_deps
            run_quick_tests
            ;;
        3)
            check_dependencies
            install_backend_deps
            echo -e "${GREEN}依赖安装完成${NC}"
            ;;
        4)
            check_dependencies
            install_backend_deps
            run_backend_tests
            ;;
        5)
            echo "退出"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项${NC}"
            exit 1
            ;;
    esac
}

# 非交互模式（CI/CD 使用）
non_interactive() {
    check_dependencies
    install_backend_deps
    run_backend_tests

    if [ "$1" == "--with-coverage" ]; then
        generate_coverage_report
    fi

    echo -e "${GREEN}测试完成！${NC}"
}

# 主入口
main() {
    if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  -h, --help           显示帮助信息"
        echo "  -q, --quick          快速测试（不生成覆盖率）"
        echo "  -c, --with-coverage  运行测试并生成覆盖率报告"
        echo "  (无参数)             显示交互式菜单"
        exit 0
    elif [ "$1" == "-q" ] || [ "$1" == "--quick" ]; then
        check_dependencies
        install_backend_deps
        run_quick_tests
    elif [ "$1" == "-c" ] || [ "$1" == "--with-coverage" ]; then
        non_interactive "--with-coverage"
    elif [ -t 0 ]; then
        # 检测是否为交互式终端
        interactive_menu
    else
        # 非交互式模式
        non_interactive
    fi
}

main "$@"
