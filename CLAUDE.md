# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基金/A股投资学习与分析平台，面向投资新手。知识库文档 + Jupyter Notebook 教程 + Streamlit Web 界面。

## 常用命令

```bash
# 环境 (Python 3.12+, uv 管理)
uv sync                        # 基础依赖
uv sync --extra all            # 全部可选依赖 (pandas-ta, scikit-learn, backtrader)
uv sync --dev                  # 含测试工具 (pytest, ruff)

# Web 界面 (主要入口)
uv run streamlit run app/app.py

# Jupyter 教程
uv run jupyter notebook notebooks/

# 测试
uv run pytest tests/ -v                    # 全部测试
uv run pytest tests/test_indicators.py -v  # 单个测试文件
uv run pytest tests/ -v -k "test_rsi"      # 按关键字筛选
uv run pytest tests/ -v --cov=scripts --cov-report=term-missing  # 含覆盖率

# 代码检查
uv run ruff check .
uv run ruff format --check .               # 格式检查

# CLI 脚本 (可独立运行，也通过 Web 界面调用)
uv run python scripts/data/fetch_fund.py                     # 基金排行
uv run python scripts/data/fetch_fund.py --code 000001       # 单只基金净值
uv run python scripts/data/fetch_index.py                    # 指数估值一览
uv run python scripts/data/fetch_stock.py --market           # A股市场总览
uv run python scripts/analysis/risk.py --code 110020         # 风险评估
uv run python scripts/analysis/correlation.py --codes 110020,001632  # 相关性矩阵
uv run python scripts/analysis/performance.py --code 110020  # CAPM 业绩归因
uv run python scripts/strategy/backtest.py --code 110020     # 定投/一次性/网格回测
uv run python scripts/strategy/signals.py --code 110020      # 市场择时信号
uv run python scripts/strategy/portfolio.py --codes 110020,001632  # 组合优化
```

## 架构

```
app/                        # Streamlit Web 界面 (单页仪表盘)
├── app.py                  # 入口: 市场状态条 + 功能卡片(3x3) + 动态内容区 + sidebar AI 面板
├── pages/
│   ├── 01_fund_scanner.py  # 基金筛选 → render()
│   ├── 02_market_signals.py
│   ├── 03_portfolio_optimizer.py
│   ├── 04_performance.py
│   ├── 05_risk_report.py
│   ├── 06_backtest.py
│   ├── 07_my_portfolio.py  # CSV 持仓导入 + 健康度诊断
│   └── 08_ai_chat.py       # 独立 AI 对话页 (app.py 中 sidebar 已含 AI 面板，此页备用)
├── utils/
│   ├── ai_advisor.py       # OpenAI 兼容接口封装 → "小财" AI 投资顾问
│   └── csv_parser.py       # 支付宝/微信/天天基金 CSV 持仓解析 (模糊列名匹配)
└── assets/style.css        # 仪表盘样式 (卡片悬停、badge、metric 字号)

scripts/                    # 后端逻辑 (被 Web 层和 CLI 共用)
├── data/client.py          # 核心: akshare 统一封装层，所有数据入口
│   ├── fetch_fund.py       # 基金排行/净值/列表
│   ├── fetch_index.py      # 指数行情/估值 (INDEX_MAP + PE_HISTORY)
│   └── fetch_stock.py      # 个股行情/财务数据/行业板块
├── analysis/
│   ├── correlation.py      # 相关性矩阵 + 热力图
│   ├── performance.py      # CAPM alpha/beta, IR, 牛熊捕获率, 滚动归因
│   ├── risk.py             # VaR/CVaR, 最大回撤, 偏度/峰度
│   └── fund_scanner.py     # 多维度基金筛选
├── strategy/
│   ├── backtest.py         # DCA/一次性/网格回测 (BacktestResult 不可变 dataclass)
│   ├── portfolio.py        # 组合优化 (最大夏普/最小方差/风险平价)
│   └── signals.py          # 择时信号 (PE分位 + 均线 + RSI)
└── utils/
    ├── indicators.py       # MA, EMA, MACD, RSI, 布林带, KDJ (纯函数，返回新对象)
    └── viz.py              # matplotlib 图表 (净值走势/收益分布/回撤/风险收益散点)

knowledge/                  # 知识库 (Markdown 文档，AI RAG 数据源)
├── 00-导读-新手必读.md
├── 01-基金基础/            # 基金分类、运作原理
├── 02-投资入门/            # 复利、定投
├── 03-A股市场/             # A股概述、购买实战
├── 04-分析方法/            # 指标解读、综合评估
├── 05-投资策略/            # 定投、网格、资产配置
└── 06-风险管理/            # 风险认知、仓位管理

notebooks/                  # Jupyter 交互教程
├── 00-白话入门.ipynb
├── 01-你的第一笔基金数据.ipynb
├── 02-基金对比与筛选.ipynb
├── 03-定投策略回测.ipynb
├── 04-构建投资组合.ipynb
└── 05-市场估值分析.ipynb

data/
├── cache/                  # 数据缓存 (gitignored)
└── output/                 # 输出结果 (gitignored)

tests/
├── test_indicators.py      # 技术指标: SMA/EMA/MACD/RSI/布林带/KDJ/波动率/夏普/回撤
├── test_correlation.py     # 相关性矩阵 + 解读逻辑边界
├── test_portfolio.py       # 组合优化 (最大夏普/最小方差/风险平价/有效前沿)
├── test_backtest.py        # DCA/一次性/网格回测
├── test_signals.py         # 均线信号 + RSI信号
└── test_risk.py            # 最大回撤/VaR/CVaR/滚动波动率
```

**Web 界面路由机制**: 
- 单页应用，`st.session_state.active_view` 控制当前视图
- `FUNCTIONS` dict 定义功能卡片列表（icon/label/desc），仪表盘渲染为 3 列网格
- `TEMPLATE_PARAMS` dict 映射卡片 key → `view_name` + `import_mod`（对应 pages/ 下的模块）
- 功能页: `render_content()` 通过 `__import__(f"app.pages.{mod}", fromlist=["render"])` 动态加载并调用 `mod.render()`
- AI 面板: `render_ai_panel()` 常驻 sidebar，含聊天+快捷指令
- 数据获取用 `@st.cache_data(ttl=300)` 缓存市场数据，避免每次交互重新请求

**数据流**: `client.py` (akshare) → `analysis/` / `strategy/` → `utils/viz.py` (可选) → 输出

**关键约定**:
- 所有数据通过 `scripts/data/client.py` 获取，统一入口便于切换数据源
- `client.get_fund_nav()` 是最核心函数，几乎所有分析工具都依赖它
- `scripts/` 模块通过 `sys.path.insert(0, ...)` 被 CLI 脚本、测试和 Web 层导入（跨层导入的标准方式）
- 所有指标/分析函数返回新对象，不修改入参（不可变数据模式，使用 `@dataclass(frozen=True)`）
- 中文注释和终端输出，英文代码标识符

## AI 配置

使用 DeepSeek V4 Pro，通过 OpenAI 兼容 SDK 调用。在 `.env` 中配置：

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-pro
```

`AIAdvisor` 类 (`app/utils/ai_advisor.py`)：
- 单例 `get_advisor()` 全局复用
- `interpret(analysis_type, data)` — 解读分析结果（注入知识库 RAG）
- `chat(history, question)` — 自由对话（关键词匹配知识库）
- `_safety_check()` — 禁止模式检测（不推荐具体基金、不预测收益）
- 无 API 时自动 fallback 到 `_rule_based_interpret()` 模板化解读

## 数据源

| 源 | 用途 | 配置 |
|----|------|------|
| akshare | 主力数据源，免费无需 API Key | 默认 |
| tushare | 可选，需 token | 填 `.env` 中 `TUSHARE_TOKEN` |

`.env.example` 中有完整的环境变量模板。`data/cache/` 和 `data/output/` 被 gitignore。

## 会话管理

- **上下文超过 60% 时主动执行 `/compact` 命令**，释放上下文空间后再继续
- 执行 compact 前，将当前进度和关键状态保存到对话中

## 测试

- 框架: pytest, 覆盖率: pytest-cov
- 测试按类组织（`pytest` class），fixture 在模块顶部定义
- 所有测试通过 `sys.path.insert(0, ...)` 导入 `scripts/` 中的源码模块（和 `app/app.py` 相同模式）
- 典型写法: `class TestMovingAverage:` 内含 `def test_sma_basic(self, simple_series):`
