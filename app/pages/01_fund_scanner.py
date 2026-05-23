"""基金筛选页面 — 多维度筛选，AI 解读。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import plotly.graph_objects as go
from scripts.analysis.fund_scanner import scan_funds


def render():
    st.title("🔍 基金筛选器")
    st.markdown("从几千只公募基金中按条件筛选，找到表现优秀的基金。")

    # -- 侧边栏参数 --
    st.sidebar.subheader("筛选条件")
    fund_type = st.sidebar.selectbox(
        "基金类型",
        ["all", "stock", "bond", "mix", "index", "qdii"],
        format_func=lambda x: {
            "all": "全部",
            "stock": "股票型",
            "bond": "债券型",
            "mix": "混合型",
            "index": "指数型",
            "qdii": "QDII",
        }.get(x, x),
        index=2,
    )
    min_return = st.sidebar.slider("最低年化收益 (%)", 0.0, 30.0, 5.0, 1.0)
    max_drawdown = st.sidebar.slider("最大可接受回撤 (%)", 5.0, 50.0, 20.0, 1.0)
    min_sharpe = st.sidebar.slider("最低夏普比率", 0.0, 3.0, 0.5, 0.1)
    top_n = st.sidebar.slider("显示数量", 5, 30, 15, 5)

    if st.sidebar.button("🔍 开始筛选", use_container_width=True, type="primary"):
        with st.spinner("正在扫描基金数据 (akshare)，约需 1-2 分钟..."):
            try:
                result = scan_funds(
                    fund_type=fund_type,
                    min_return=min_return,
                    max_drawdown=max_drawdown,
                    min_sharpe=min_sharpe,
                    top_n=top_n,
                )
                st.session_state["scanner_result"] = result
                st.session_state["scanner_params"] = {
                    "fund_type": fund_type,
                    "min_return": min_return,
                    "max_drawdown": max_drawdown,
                    "min_sharpe": min_sharpe,
                }
            except Exception as e:
                st.error(f"数据获取失败: {e}")
                st.info("请检查网络连接，akshare 可能需要稳定的网络。")
                return

    # -- 展示结果 --
    result = st.session_state.get("scanner_result")
    if result is None or result.empty:
        st.info("👆 在左侧设置筛选条件，点击「开始筛选」查看结果。")
        return

    st.success(f"找到 {len(result)} 只符合条件的基金")

    # 指标卡片
    cols = st.columns(6)
    metrics = [
        ("平均年化收益", f"{result['annual_return'].mean():.1f}%"),
        ("平均波动率", f"{result['annual_volatility'].mean():.1f}%"),
        ("平均回撤", f"{result['max_drawdown'].mean():.1f}%"),
        ("平均夏普", f"{result['sharpe_ratio'].mean():.2f}"),
        ("平均胜率", f"{result['win_rate'].mean():.0f}%"),
        ("最高分基金", str(result.iloc[0]["name"])),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    # 数据表格
    display_cols = [
        c
        for c in [
            "code",
            "name",
            "annual_return",
            "annual_volatility",
            "max_drawdown",
            "sharpe_ratio",
            "win_rate",
            "win_loss_ratio",
        ]
        if c in result.columns
    ]
    st.dataframe(
        result[display_cols].style.format(
            {
                "annual_return": "{:.1f}%",
                "annual_volatility": "{:.1f}%",
                "max_drawdown": "{:.1f}%",
                "sharpe_ratio": "{:.2f}",
                "win_rate": "{:.0f}%",
                "win_loss_ratio": "{:.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # 风险-收益散点图
    if "annual_return" in result.columns and "annual_volatility" in result.columns:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=result["annual_volatility"],
                y=result["annual_return"],
                mode="markers+text",
                text=result["name"].str[:6],
                textposition="top center",
                marker=dict(
                    size=12,
                    color=result["sharpe_ratio"]
                    if "sharpe_ratio" in result.columns
                    else None,
                    colorscale="RdYlGn",
                    showscale=True,
                    colorbar=dict(title="夏普"),
                ),
                hovertemplate="%{text}<br>收益: %{y:.1f}%<br>波动: %{x:.1f}%<extra></extra>",
            )
        )
        fig.update_layout(
            title="风险-收益散点图",
            xaxis_title="年化波动率 (%)",
            yaxis_title="年化收益率 (%)",
            height=500,
        )
        fig.add_hline(
            y=min_return,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"最低收益线 ({min_return}%)",
        )
        fig.add_vline(
            x=max_drawdown,
            line_dash="dash",
            line_color="red",
            annotation_text=f"最大回撤线 ({max_drawdown}%)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # AI 解读入口
    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        st.markdown("让 AI 用大白话帮你解释这份筛选结果的含义。")
        if st.button("🔮 让 AI 帮我解读", key="ai_scanner"):
            try:
                from app.utils.ai_advisor import get_advisor

                advisor = get_advisor()
                params = st.session_state.get("scanner_params", {})
                interpretation = advisor.interpret(
                    "scanner",
                    {
                        "result_df": result,
                        "fund_type": params.get("fund_type", "all"),
                        "min_return": params.get("min_return", 0),
                        "max_drawdown": params.get("max_drawdown", 100),
                        "min_sharpe": params.get("min_sharpe", 0),
                    },
                )
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
