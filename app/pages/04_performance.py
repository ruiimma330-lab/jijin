"""业绩归因页面 — CAPM Alpha/Beta、信息比率、牛熊市表现。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import plotly.graph_objects as go
from scripts.analysis.performance import performance_report


def render():
    st.title("📈 业绩归因分析")
    st.markdown("拆解基金收益来源：哪些来自市场（Beta），哪些来自基金经理能力（Alpha）。")

    col1, col2 = st.columns(2)
    with col1:
        fund_code = st.text_input("基金代码", value="110020", max_chars=6,
                                   placeholder="如 110020")
    with col2:
        benchmark = st.selectbox(
            "基准指数",
            ["000300", "000905", "399006", "000688", "000016"],
            format_func=lambda x: {
                "000300": "沪深300", "000905": "中证500", "399006": "创业板指",
                "000688": "科创50", "000016": "上证50",
            }.get(x, x),
        )

    if st.button("📈 生成归因报告", type="primary"):
        if not fund_code:
            st.warning("请输入基金代码")
            return

        with st.spinner(f"正在分析基金 {fund_code} 的业绩归因..."):
            try:
                report = performance_report(fund_code, benchmark)
                st.session_state["performance_report"] = report
            except Exception as e:
                st.error(f"分析失败: {e}")
                return

    report = st.session_state.get("performance_report")
    if report is None:
        st.info("👆 输入基金代码和基准指数，点击「生成归因报告」查看业绩拆解。")
        return

    bm_name = report["benchmark_name"]

    # CAPM 卡片
    st.subheader(f"🔬 CAPM 归因 (基准: {bm_name})")

    if report.get("beta") is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            alpha = report["alpha_annual"]
            st.metric("Alpha (年化)", f"{alpha}%",
                       "超额收益" if alpha > 0 else "跑输基准")
        with col2:
            beta = report["beta"]
            label = "激进" if beta > 1.1 else ("保守" if beta < 0.9 else "同步")
            st.metric("Beta", f"{beta}", label)
        with col3:
            r2 = report["r_squared"]
            st.metric("R²", f"{r2}", "高拟合" if r2 > 0.7 else "拟合低")
        with col4:
            st.metric("p 值", f"{report['p_value']}",
                       "显著" if report["p_value"] < 0.05 else "不显著")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("基金年化收益", f"{report['fund_return']}%")
        with col2:
            st.metric(f"{bm_name}年化收益", f"{report['bench_return']}%")
        with col3:
            st.metric("CAPM 预期收益", f"{report['expected_return']}%")

        # Alpha/Beta 可视化
        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=alpha,
            title={"text": "Alpha (年化 %)"},
            gauge={
                "axis": {"range": [-20, 20]},
                "bar": {"color": "green" if alpha > 0 else "red"},
                "steps": [
                    {"range": [-20, 0], "color": "lightcoral"},
                    {"range": [0, 20], "color": "lightgreen"},
                ],
                "threshold": {"line": {"color": "black", "width": 2}, "value": 0},
            },
        ))
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(report.get("error", "CAPM 计算失败，数据不足"))

    # 主动管理能力
    st.subheader("🎯 主动管理能力")
    col1, col2 = st.columns(2)
    with col1:
        ir = report["information_ratio"]
        st.metric("信息比率", f"{ir}",
                   "优秀" if ir > 0.5 else ("良好" if ir > 0 else "跑输"))
    with col2:
        te = report["tracking_error"]
        st.metric("跟踪误差", f"{te}%",
                   "积极管理" if te > 8 else ("接近指数" if te < 3 else "适度偏离"))

    # 牛熊市表现
    bb = report.get("bull_bear", {})
    if bb.get("upside_capture") is not None:
        st.subheader("🐂🐻 牛熊市表现")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 上涨捕获率", f"{bb['upside_capture']}%",
                       "涨时跟得上" if bb["upside_capture"] > 90 else "涨时跑输")
            st.caption(f"上涨市: 基金 {bb['bull_fund_return']}% / 基准 {bb['bull_bench_return']}%")
        with col2:
            st.metric("📉 下跌捕获率", f"{bb['downside_capture']}%",
                       "跌时跌得少" if bb["downside_capture"] < 100 else "跌时跌得多")
            st.caption(f"下跌市: 基金 {bb['bear_fund_return']}% / 基准 {bb['bear_bench_return']}%")

    # 滚动分析
    rolling = report.get("rolling")
    if rolling is not None and not rolling.empty:
        st.subheader("🔄 滚动 Alpha/Beta (60天窗口)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["alpha_annual"],
            name="Alpha (年化%)", line=dict(color="green"),
        ))
        fig.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["beta"],
            name="Beta", yaxis="y2", line=dict(color="orange"),
        ))
        fig.update_layout(
            xaxis_title="日期",
            yaxis=dict(title="Alpha (%)"),
            yaxis2=dict(title="Beta", overlaying="y", side="right"),
            height=400,
            legend=dict(x=0.01, y=0.99),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "💡 **解读指南**: Alpha>0 → 经理有选股能力；Beta<1 → 防御型基金；"
        "IR>0.5 → 主动管理优秀；上涨捕获率>100 且下跌捕获率<100 → 理想基金。"
    )

    # AI 解读
    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        if st.button("🔮 让 AI 解释业绩归因结果", key="ai_perf"):
            try:
                from app.utils.ai_advisor import get_advisor
                advisor = get_advisor()

                # 精简传给 AI 的数据
                ai_data = {
                    "fund_code": fund_code,
                    "benchmark": f"{bm_name} ({benchmark})",
                    "alpha_annual": report.get("alpha_annual"),
                    "beta": report.get("beta"),
                    "r_squared": report.get("r_squared"),
                    "p_value": report.get("p_value"),
                    "fund_return": report.get("fund_return"),
                    "bench_return": report.get("bench_return"),
                    "information_ratio": report.get("information_ratio"),
                    "tracking_error": report.get("tracking_error"),
                }
                if bb:
                    ai_data["bull_bear"] = bb

                interpretation = advisor.interpret("performance", ai_data)
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
