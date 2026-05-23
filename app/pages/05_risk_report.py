"""风险评估页面 — VaR、最大回撤、波动率分析报告。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from scripts.analysis.risk import risk_report
from scripts.data.client import get_fund_nav
from scripts.utils.viz import plot_drawdown


def render():
    st.title("⚠️ 风险评估报告")
    st.markdown("了解一只基金的风险有多大，帮你判断自己能不能承受。")

    fund_code = st.text_input(
        "基金代码",
        value="110020",
        max_chars=6,
        placeholder="输入 6 位基金代码，如 110020",
    )

    if st.button("📊 生成报告", type="primary"):
        if not fund_code:
            st.warning("请输入基金代码")
            return

        with st.spinner(f"正在分析基金 {fund_code} 的风险指标..."):
            try:
                report = risk_report(fund_code)
                nav_df = get_fund_nav(fund_code)
                st.session_state["risk_report"] = report
                st.session_state["risk_nav_df"] = nav_df
                st.session_state["risk_code"] = fund_code
            except Exception as e:
                st.error(f"数据获取失败: {e}")
                return

    report = st.session_state.get("risk_report")
    nav_df = st.session_state.get("risk_nav_df")
    if report is None:
        st.info("👆 输入基金代码，点击「生成报告」查看风险分析。")
        return

    if "error" in report:
        st.error(report["error"])
        return

    # 关键风险指标卡片
    st.subheader("📊 风险指标总览")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        vol = report["annual_volatility"]
        level = "🟢 低" if vol < 10 else ("🟡 中" if vol < 20 else "🔴 高")
        st.metric("年化波动率", f"{vol}%", level)
    with col2:
        dd = abs(report["max_drawdown"])
        level = "🟢 可控" if dd < 10 else ("🟡 注意" if dd < 20 else "🔴 较大")
        st.metric("最大回撤", f"{report['max_drawdown']}%", level)
    with col3:
        var95 = report["VaR_95"]
        st.metric("VaR (95%)", f"{var95}%", "单日亏损上限")
    with col4:
        st.metric("回撤次数", str(report["drawdown_count"]))

    col1, col2, col3 = st.columns(3)
    with col1:
        skew = report["skewness"]
        hint = " ⚠️ 左偏=暴跌风险" if skew < -0.5 else ""
        st.metric("偏度", f"{skew}", hint)
    with col2:
        kurt = report["kurtosis"]
        hint = " ⚠️ 尖峰=极端风险" if kurt > 2 else ""
        st.metric("峰度", f"{kurt}", hint)
    with col3:
        st.metric("CVaR (95%)", f"{report['CVaR_95']}%", "极端情况均值")

    # 回撤详细信息
    st.subheader("📉 回撤详情")
    st.markdown(f"""
    | 项目 | 数值 |
    |------|------|
    | 最大回撤区间 | {report["max_dd_start"]} ~ {report["max_dd_end"]} |
    | 恢复天数 | {report["recovery_days"]} 天 |
    | 平均回撤 | {report["avg_drawdown"]}% |
    """)

    # 回撤图表
    if nav_df is not None and not nav_df.empty:
        try:
            fig = plot_drawdown(nav_df)
            st.pyplot(fig)
        except Exception:
            st.warning("回撤图表暂时无法渲染，请稍后重试。")

    # VaR 解释
    st.subheader("🎲 风险价值 (VaR) 解读")
    var_95_abs = abs(float(report["VaR_95"]))
    st.markdown(f"""
    - **VaR(95%) = {report["VaR_95"]}%** — 95% 的把握，单日亏损不超过 **{var_95_abs}%**
    - 换句话说：每 100 个交易日中，约有 5 天亏损超过 {var_95_abs}%
    - **CVaR(95%) = {report["CVaR_95"]}%** — 如果真的遇到那 5% 的倒霉日子，平均会亏这么多

    💡 投资 {10000:,} 元，日常单日亏损大概率不超过 {var_95_abs * 100:.0f} 元。
    """)

    # AI 解读入口
    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        if st.button("🔮 让 AI 帮我解释这些风险数字", key="ai_risk"):
            try:
                from app.utils.ai_advisor import get_advisor

                advisor = get_advisor()
                interpretation = advisor.interpret("risk", report)
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
