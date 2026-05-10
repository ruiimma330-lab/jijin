"""市场信号页面 — PE估值、均线、RSI 综合择时信号。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import plotly.graph_objects as go
from scripts.strategy.signals import composite_signal


SIGNAL_STYLE = {
    "BUY": {"icon": "🟢", "label": "买入信号", "color": "green"},
    "SELL": {"icon": "🔴", "label": "卖出信号", "color": "red"},
    "HOLD": {"icon": "🟡", "label": "持有/观望", "color": "orange"},
    "WAIT": {"icon": "⚪", "label": "等待", "color": "gray"},
    "N/A": {"icon": "⬜", "label": "无信号", "color": "gray"},
}


def _signal_badge(signal: str) -> str:
    s = SIGNAL_STYLE.get(signal, SIGNAL_STYLE["N/A"])
    return f"{s['icon']} **{signal}** — {s['label']}"


def render():
    st.title("📊 市场择时信号")
    st.markdown("综合 PE 估值、均线交叉、RSI 三大信号，判断当前是否适合买入。")

    col1, col2 = st.columns(2)
    with col1:
        fund_code = st.text_input("基金代码 (可选，用于均线/RSI)", value="110020",
                                   max_chars=6, placeholder="如 110020")
    with col2:
        index_code = st.selectbox(
            "基准指数 (PE估值)",
            ["000300", "000905", "399006", "000688", "000016"],
            format_func=lambda x: {
                "000300": "沪深300", "000905": "中证500", "399006": "创业板指",
                "000688": "科创50", "000016": "上证50",
            }.get(x, x),
        )

    if st.button("📡 获取信号", type="primary"):
        with st.spinner("正在计算市场信号..."):
            try:
                result = composite_signal(
                    fund_code=fund_code if fund_code else None,
                    index_code=index_code,
                )
                st.session_state["signals_result"] = result
            except Exception as e:
                st.error(f"信号获取失败: {e}")
                return

    result = st.session_state.get("signals_result")
    if result is None:
        st.info("👆 选择指数和基金，点击「获取信号」查看当前市场状态。")
        return

    # 综合信号大卡片
    overall = result["overall_signal"]
    style = SIGNAL_STYLE.get(overall, SIGNAL_STYLE["N/A"])
    st.markdown(f"""
    <div style="padding:20px;border-radius:10px;background:{style['color']}15;
                border:2px solid {style['color']};text-align:center;margin:10px 0;">
        <h2>{style['icon']} 综合信号: {overall}</h2>
        <p style="font-size:1.2em;">{result['suggestion']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 分项信号
    st.subheader("📋 信号明细")
    signals = result.get("signals", {})

    for name, s in signals.items():
        sig = s.get("signal", "N/A")
        style_s = SIGNAL_STYLE.get(sig, SIGNAL_STYLE["N/A"])

        with st.expander(f"{style_s['icon']} **{name}**: {sig}", expanded=True):
            if name == "PE估值":
                pe = s.get("current_pe")
                pct = s.get("percentile")
                median = s.get("median_pe")
                if pe is not None:
                    st.metric("当前 PE", f"{pe}", f"分位 {pct}%")
                    st.metric("历史中位数 PE", f"{median}")

                    # PE 仪表盘
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=pct if pct else 0,
                        title={"text": "PE 估值分位"},
                        delta={"reference": 50},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 30], "color": "lightgreen"},
                                {"range": [30, 70], "color": "lightyellow"},
                                {"range": [70, 100], "color": "lightcoral"},
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 2},
                                "thickness": 0.8, "value": pct if pct else 50,
                            },
                        },
                    ))
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

                st.caption(s.get("action", ""))

            elif name == "均线":
                cols = st.columns(4)
                cols[0].metric("当前净值", f"{s.get('current_nav', '?'):.4f}")
                cols[1].metric("MA20", f"{s.get('ma20', '?'):.4f}")
                cols[2].metric("MA60", f"{s.get('ma60', '?'):.4f}")
                cols[3].metric("间距", f"{s.get('gap_pct', '?')}%")
                st.caption(s.get("detail", ""))

            elif name == "RSI":
                rsi_val = s.get("rsi", 50)
                if rsi_val is not None:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=float(rsi_val),
                        title={"text": "RSI (14)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 30], "color": "lightgreen"},
                                {"range": [30, 70], "color": "lightyellow"},
                                {"range": [70, 100], "color": "lightcoral"},
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 2},
                                "thickness": 0.8, "value": 70,
                            },
                        },
                    ))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
                st.caption(s.get("action", ""))

    # 免责声明
    st.warning(
        "⚠️ 择时信号基于历史统计规律，**不保证未来准确性**。"
        "新手建议忽略短期信号，坚持长期定投。"
    )

    # AI 解读
    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        if st.button("🔮 让 AI 解释这些信号", key="ai_signals"):
            try:
                from app.utils.ai_advisor import get_advisor
                advisor = get_advisor()
                interpretation = advisor.interpret("signals", result)
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
