#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   基金/A股投资学习与分析平台${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

check_deps() {
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[错误] 未找到 uv，请先安装: pip install uv${NC}"
        exit 1
    fi
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}[提示] 虚拟环境不存在，正在创建...${NC}"
        uv sync
    fi
    echo -e "${GREEN}[OK] 环境检查通过${NC}"
}

show_menu() {
    echo ""
    echo -e "${YELLOW}请选择启动模式:${NC}"
    echo "  1) Streamlit Web 界面   (浏览器仪表盘)"
    echo "  2) Jupyter Notebook      (交互式学习教程)"
    echo "  3) 依赖安装 / 更新"
    echo "  4) 运行测试"
    echo "  5) 退出"
    echo ""
}

check_deps

while true; do
    show_menu
    read -rp "输入选项 [1-5]: " choice

    case "$choice" in
        1)
            echo -e "${GREEN}正在启动 Streamlit Web 界面...${NC}"
            echo -e "${CYAN}浏览器打开后访问本地地址即可${NC}"
            uv run streamlit run app/app.py
            ;;
        2)
            echo -e "${GREEN}正在启动 Jupyter Notebook...${NC}"
            uv run jupyter notebook notebooks/
            ;;
        3)
            echo -e "${GREEN}正在安装/更新依赖...${NC}"
            uv sync --extra all --dev
            echo -e "${GREEN}[完成] 依赖已更新${NC}"
            ;;
        4)
            echo -e "${GREEN}正在运行测试...${NC}"
            uv run pytest tests/ -v
            ;;
        5)
            echo -e "${CYAN}再见！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项，请输入 1-5${NC}"
            ;;
    esac

    echo ""
    read -rp "按 Enter 继续..."
done
