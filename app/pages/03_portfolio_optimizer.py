"""组合优化页面 — 最大夏普、最小方差、风险平价三种策略。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scripts.strategy.portfolio import optimize_portfolio, efficient_frontier


def render():
    st.title("🎯 投资组合优化")
    st.markdown("科学分配资金到多只基金，找到收益和风险的最佳平衡点。")

    codes_input = st.text_input(
        "基金代码 (逗号分隔)",
        value="110020,001632,050027",
        placeholder="如 110020,001632,050027",
        help="输入 2-6 只基金代码，用逗号分隔",
    )

    if st.button("🎯 开始优化", type="primary"):
        fund_codes = [c.strip() for c in codes_input.split(",") if c.strip()]
        if len(fund_codes) < 2:
            st.warning("至少需要 2 只基金才能优化组合")
            return

        with st.spinner("正在获取基金数据并优化组合..."):
            try:
                result = optimize_portfolio(fund_codes)
                # 计算有效前沿
                ef = efficient_frontier(result["mean_returns"], result["cov_matrix"])
                st.session_state["portfolio_result"] = result
                st.session_state["portfolio_ef"] = ef
                st.session_state["portfolio_codes"] = fund_codes
            except ValueError as e:
                st.error(str(e))
                return
            except Exception as e:
                st.error(f"优化失败: {e}")
                return

    result = st.session_state.get("portfolio_result")
    ef = st.session_state.get("portfolio_ef")
    fund_codes = st.session_state.get("portfolio_codes")

    if result is None:
        st.info("👆 输入基金代码，点击「开始优化」查看最优组合方案。")
        return

    # 三种策略对比
    st.subheader("📊 三种策略对比")

    desc = {
        "最大夏普": "收益风险比最佳 — 适合追求效率",
        "最小方差": "最稳组合 — 适合保守型投资者",
        "风险平价": "各资产风险贡献相等 — 适合分散配置",
    }

    cols = st.columns(3)
    for col, (strategy, data) in zip(cols, result["results"].items()):
        with col:
            with st.container(border=True):
                st.markdown(f"**{strategy}**")
                st.caption(desc.get(strategy, ""))
                st.metric("年化收益", f"{data['return'] * 100:.1f}%")
                st.metric("年化波动", f"{data['volatility'] * 100:.1f}%")
                st.metric("夏普比率", f"{data['sharpe']:.2f}")

                # 小饼图
                weights = data["weights"]
                fig = go.Figure(
                    go.Pie(
                        labels=fund_codes,
                        values=[max(w, 0.001) for w in weights],
                        hole=0.5,
                        textinfo="label+percent",
                        showlegend=False,
                    )
                )
                fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(
                    fig, use_container_width=True, config={"displayModeBar": False}
                )

    # 权重详情表
    st.subheader("📋 各策略权重")
    weight_data = {"基金代码": fund_codes}
    for strategy, data in result["results"].items():
        weight_data[strategy] = [f"{w * 100:.0f}%" for w in data["weights"]]
    st.dataframe(pd.DataFrame(weight_data), use_container_width=True, hide_index=True)

    # 有效前沿图
    if ef is not None and not ef.empty:
        st.subheader("📈 有效前沿")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=ef["volatility"],
                y=ef["return"],
                mode="lines",
                name="有效前沿",
                line=dict(color="blue", width=2),
                hovertemplate="波动: %{x:.1f}%<br>收益: %{y:.1f}%<extra></extra>",
            )
        )

        # 三种策略点位
        colors = {"最大夏普": "red", "最小方差": "green", "风险平价": "orange"}
        for strategy, data in result["results"].items():
            fig.add_trace(
                go.Scatter(
                    x=[data["volatility"] * 100],
                    y=[data["return"] * 100],
                    mode="markers+text",
                    name=strategy,
                    text=[strategy],
                    textposition="top center",
                    marker=dict(
                        size=14, color=colors.get(strategy, "gray"), symbol="diamond"
                    ),
                )
            )

        fig.update_layout(
            title="有效前沿 — 三种策略位置",
            xaxis_title="年化波动率 (%)",
            yaxis_title="年化收益率 (%)",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    # 提示
    st.info(
        "💡 **新手建议**：推荐「风险平价」策略 — 各资产风险贡献均等，"
        "不依赖收益预测，更稳健。每半年再平衡一次即可。"
    )

    st.caption(
        "⚠️ 优化结果基于历史数据（最近一年），未来可能偏离。加入债券基金可大幅降低组合波动。"
    )

    # AI 解读
    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        if st.button("🔮 让 AI 帮我理解优化结果", key="ai_portfolio"):
            try:
                from app.utils.ai_advisor import get_advisor

                advisor = get_advisor()
                interpretation = advisor.interpret(
                    "portfolio",
                    {
                        "fund_codes": fund_codes,
                        "results": {
                            k: {
                                "return": f"{v['return'] * 100:.1f}%",
                                "volatility": f"{v['volatility'] * 100:.1f}%",
                                "sharpe": f"{v['sharpe']:.2f}",
                                "weights": {
                                    c: f"{w * 100:.0f}%"
                                    for c, w in zip(fund_codes, v["weights"])
                                },
                            }
                            for k, v in result["results"].items()
                        },
                    },
                )
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
