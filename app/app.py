"""jijin — 基金投资学习与分析平台

单页仪表盘：市场状态条 + 功能卡片 + 动态内容区 + AI 常驻面板。
"""

import sys
import os
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

# ── 页面配置 ──────────────────────────────────────────

st.set_page_config(
    page_title="jijin · 基金投资助手",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Session 初始化 ───────────────────────────────────

FUNCTIONS = {
    "scanner":  {"icon": "🔍", "label": "基金筛选",   "desc": "从几千只基金中按条件筛选"},
    "signals":  {"icon": "📊", "label": "市场信号",   "desc": "PE估值 + 均线 + RSI 综合判断"},
    "portfolio":{"icon": "🎯", "label": "组合优化",   "desc": "最优资产配置方案"},
    "performance":{"icon":"📈","label": "业绩归因",   "desc": "收益来源拆解 Alpha/Beta"},
    "risk":     {"icon": "⚠️", "label": "风险评估",   "desc": "VaR + 最大回撤 + 波动率"},
    "backtest": {"icon": "⏳", "label": "策略回测",   "desc": "定投 vs 一次性 vs 网格"},
    "portfolio_upload": {"icon": "💼", "label": "我的持仓", "desc": "上传CSV，诊断持仓健康度"},
}

VIEWS = {
    "home": "仪表盘",
    **{k: v["label"] for k, v in FUNCTIONS.items()},
}

TEMPLATE_PARAMS = {
    "scanner": {"view_name": "scanner", "import_mod": "01_fund_scanner"},
    "signals": {"view_name": "signals", "import_mod": "02_market_signals"},
    "portfolio": {"view_name": "portfolio", "import_mod": "03_portfolio_optimizer"},
    "performance": {"view_name": "performance", "import_mod": "04_performance"},
    "risk": {"view_name": "risk", "import_mod": "05_risk_report"},
    "backtest": {"view_name": "backtest", "import_mod": "06_backtest"},
    "portfolio_upload": {"view_name": "portfolio_upload", "import_mod": "07_my_portfolio"},
}


def init_session():
    defaults = {
        "active_view": "home",
        "active_function": None,
        "ai_chat_history": [],
        "portfolio_holdings": None,
        "portfolio_df": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── 市场状态条 ───────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_market_bar() -> pd.DataFrame:
    """获取主要指数实时行情（缓存5分钟）。"""
    try:
        import akshare as ak
        indices = [
            ("sh000001", "上证指数"), ("sz399001", "深证成指"),
            ("sh000300", "沪深300"), ("sz399006", "创业板指"),
        ]
        rows = []
        for symbol, name in indices:
            try:
                df = ak.stock_zh_index_daily_em(symbol=symbol)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    close = float(latest["close"])
                    open_p = float(latest["open"])
                    chg = (close - open_p) / open_p * 100
                    rows.append({"指数": name, "收盘": close, "涨跌": chg})
            except Exception:
                rows.append({"指数": name, "收盘": None, "涨跌": None})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def render_market_bar():
    df = get_market_bar()
    if df.empty:
        st.caption("⏳ 市场数据加载中...")
        return

    cols = st.columns(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i]:
            chg = row["涨跌"]
            if chg is not None:
                color = "#16a34a" if chg >= 0 else "#dc2626"
                arrow = "▲" if chg >= 0 else "▼"
                st.markdown(
                    f"<div style='text-align:center;padding:8px 0;'>"
                    f"<span style='color:#666;font-size:0.75rem;'>{row['指数']}</span><br>"
                    f"<span style='font-size:1.1rem;font-weight:700;'>{row['收盘']:.0f}</span><br>"
                    f"<span style='color:{color};font-size:0.85rem;'>{arrow} {abs(chg):.2f}%</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='text-align:center;padding:8px 0;'>"
                    f"<span style='color:#666;font-size:0.75rem;'>{row['指数']}</span><br>"
                    f"<span style='color:#999;'>--</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ── 功能卡片 ─────────────────────────────────────────

def render_function_cards():
    """3列功能卡片网格。"""
    items = list(FUNCTIONS.items())
    cols = st.columns(3)

    for i, (key, info) in enumerate(items):
        with cols[i % 3]:
            # 卡片容器
            with st.container(border=True):
                st.markdown(f"### {info['icon']} {info['label']}")
                st.caption(info["desc"])

                if st.button("进入", key=f"card_{key}", use_container_width=True):
                    st.session_state["active_view"] = key
                    st.session_state["active_function"] = key
                    st.rerun()


# ── AI 面板 (右侧 sidebar) ────────────────────────────

def render_ai_panel():
    """常驻 AI 顾问面板。"""
    with st.sidebar:
        st.markdown("### 🤖 小财 · AI 顾问")

        # 快捷指令
        with st.expander("📌 快捷指令", expanded=False):
            quick_actions = [
                ("帮我筛选低风险的债券基金", "scanner"),
                ("当前市场适合定投吗？", "signals"),
                ("我的持仓结构健康吗？", "portfolio_upload"),
                ("什么叫最大回撤？", "chat"),
            ]
            for label, target in quick_actions:
                if st.button(label, key=f"quick_{label[:8]}", use_container_width=True):
                    if target == "chat":
                        st.session_state["ai_quick_prompt"] = label
                    else:
                        st.session_state["active_view"] = target
                        st.session_state["active_function"] = target
                        st.rerun()

        st.divider()

        # 聊天历史
        for msg in st.session_state.get("ai_chat_history", [])[-6:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 输入框
        prompt = st.chat_input("问小财任何投资问题...")

        # 处理快捷指令
        if "ai_quick_prompt" in st.session_state and st.session_state["ai_quick_prompt"]:
            prompt = st.session_state.pop("ai_quick_prompt")

        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state["ai_chat_history"].append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("小财思考中..."):
                    try:
                        from app.utils.ai_advisor import get_advisor
                        advisor = get_advisor()
                        history = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state["ai_chat_history"][-8:-1]
                        ]
                        reply = advisor.chat(history, prompt)
                        st.markdown(reply)
                        st.session_state["ai_chat_history"].append(
                            {"role": "assistant", "content": reply}
                        )
                    except Exception as e:
                        st.error(f"AI 出错了: {e}")

        # 底部
        st.divider()
        st.caption("⚠️ 所有分析仅供学习，不构成投资建议")

        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state["ai_chat_history"] = []
            st.rerun()


# ── 内容区路由 ────────────────────────────────────────

def render_content():
    """根据 active_view 渲染对应内容。"""
    view = st.session_state.get("active_view", "home")

    if view == "home":
        render_dashboard()
        return

    # 功能视图
    info = FUNCTIONS.get(view)
    if info is None:
        render_dashboard()
        return

    # 返回按钮
    if st.button("← 返回首页", key="back_home"):
        st.session_state["active_view"] = "home"
        st.session_state["active_function"] = None
        st.rerun()

    st.title(f"{info['icon']} {info['label']}")
    st.caption(info["desc"])
    st.divider()

    # 动态加载对应页面模块
    tmpl = TEMPLATE_PARAMS.get(view)
    if tmpl:
        try:
            mod = __import__(f"app.pages.{tmpl['import_mod']}", fromlist=["render"])
            mod.render()
        except ImportError as e:
            st.error(f"页面加载失败: {e}")
        except Exception as e:
            st.error(f"运行出错: {e}")


def render_dashboard():
    """仪表盘首页。"""
    st.title("📈 jijin · 基金投资助手")
    st.caption(f"你的私人投资学习平台 — {date.today()}")

    # 市场状态
    st.subheader("📡 市场概览")
    render_market_bar()

    st.divider()

    # 功能卡片
    st.subheader("🔧 分析工具")
    render_function_cards()

    # 持仓概览
    holdings = st.session_state.get("portfolio_holdings")
    if holdings:
        st.divider()
        st.subheader("💼 我的持仓")
        total = sum(h.holding_amount for h in holdings)
        daily = sum(h.daily_return for h in holdings if h.daily_return)
        col1, col2, col3 = st.columns(3)
        col1.metric("持仓总市值", f"{total:,.0f} 元")
        col2.metric("持有基金", f"{len(holdings)} 只")
        col3.metric("昨日收益", f"{daily:+,.2f} 元" if daily else "?")


# ── 主入口 ────────────────────────────────────────────

def main():
    load_css()
    init_session()
    render_ai_panel()
    render_content()


if __name__ == "__main__":
    main()
