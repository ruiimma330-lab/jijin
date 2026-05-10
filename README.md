# 基金/A股投资学习与分析平台

面向**投资新手**的系统化学习工具，从零开始搞懂基金和A股投资。

## 项目结构

```
jijin/
├── knowledge/       # 📚 知识库 — 系统化投资学习文档
├── scripts/         # 🛠️ 工具脚本 — 数据获取、分析、策略回测
├── notebooks/       # 📊 交互教程 — Jupyter 手把手操作
├── data/            # 💾 数据缓存
└── tests/           # 🧪 测试
```

## 快速开始

```bash
# 1. 安装 Python 3.11+ 和 uv
pip install uv

# 2. 安装依赖
uv sync

# 3. 启动 Jupyter
jupyter notebook notebooks/
```

## 学习路线

1. 阅读 `knowledge/00-导读-新手必读.md` 了解学习路径
2. 打开 `notebooks/01-你的第一笔基金数据.ipynb` 动手获取数据
3. 按知识库目录顺序，每读完一章运行对应的 notebook

## 数据源

| 数据源 | 内容 | 费用 |
|--------|------|------|
| akshare | A股行情、基金净值、指数估值 | 免费 |
| tushare | 财务数据、港股通 | 免费层可用 |
| Wind/Choice | 机构级数据 | 按需付费 |

## ⚠️ 免责声明

本项目仅供学习参考，**不构成任何投资建议**。投资有风险，入市需谨慎。
