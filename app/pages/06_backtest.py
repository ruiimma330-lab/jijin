"""策略回测页面 — 定投 vs 一次性 vs 网格交易，对比分析。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
from scripts.strategy.backtest import backtest_dca, backtest_lump, backtest_grid
from scripts.data.client import get_fund_nav, DataSourceError


def render():
    st.title("⏳ 策略回测")
    st.markdown("用历史数据模拟不同投资策略，看看定投和一次性投资差距有多大。")

    fund_code = st.text_input("基金代码", value="110020", max_chars=6,
                               placeholder="输入 6 位基金代码")

    col1, col2, col3 = st.columns(3)
    with col1:
        lump_amount = st.number_input("一次性投资金额", value=10000, step=1000, min_value=1000)
    with col2:
        monthly_amount = st.number_input("每月定投金额", value=1000, step=100, min_value=100)
    with col3:
        grid_pct = st.slider("网格间距 (%)", 3.0, 15.0, 5.0, 1.0)

    if st.button("⏳ 开始回测", type="primary"):
        if not fund_code:
            st.warning("请输入基金代码")
            return

        with st.spinner(f"正在获取基金 {fund_code} 的历史净值并进行回测..."):
            try:
                nav_df = get_fund_nav(fund_code)
                if nav_df.empty:
                    st.error("无数据")
                    return

                date_range = f"{nav_df['date'].min().date()} ~ {nav_df['date'].max().date()}"
                st.caption(f"数据范围: {date_range}")

                r1 = backtest_lump(nav_df, lump_amount)
                r2 = backtest_dca(nav_df, monthly_amount, "monthly")
                r3 = backtest_dca(nav_df, monthly_amount / 4, "weekly")

                results = [
                    {"策略": r1.strategy, "总投入": r1.total_invested,
                     "最终资产": round(r1.final_value), "总收益率": f"{r1.total_return:.1f}%",
                     "年化": f"{r1.annual_return:.1f}%", "最大回撤": f"{r1.max_drawdown:.1f}%",
                     "夏普": f"{r1.sharpe_ratio:.2f}"},
                    {"策略": r2.strategy, "总投入": r2.total_invested,
                     "最终资产": round(r2.final_value), "总收益率": f"{r2.total_return:.1f}%",
                     "年化": f"{r2.annual_return:.1f}%", "最大回撤": f"{r2.max_drawdown:.1f}%",
                     "夏普": f"{r2.sharpe_ratio:.2f}"},
                    {"策略": r3.strategy, "总投入": r3.total_invested,
                     "最终资产": round(r3.final_value), "总收益率": f"{r3.total_return:.1f}%",
                     "年化": f"{r3.annual_return:.1f}%", "最大回撤": f"{r3.max_drawdown:.1f}%",
                     "夏普": f"{r3.sharpe_ratio:.2f}"},
                ]

                # 网格交易（如果数据足够长）
                try:
                    r4 = backtest_grid(nav_df, lump_amount, grid_pct)
                    results.append({
                        "策略": r4.strategy, "总投入": r4.total_invested,
                        "最终资产": round(r4.final_value), "总收益率": f"{r4.total_return:.1f}%",
                        "年化": f"{r4.annual_return:.1f}%", "最大回撤": f"{r4.max_drawdown:.1f}%",
                        "夏普": f"{r4.sharpe_ratio:.2f}",
                    })
                except Exception:
                    pass

                st.session_state["backtest_results"] = results
                st.session_state["backtest_nav"] = nav_df
                st.session_state["backtest_code"] = fund_code

            except DataSourceError as e:
                st.error(f"数据获取失败: {e}")
                return

    results = st.session_state.get("backtest_results")
    if results is None:
        st.info("👆 输入基金代码，点击「开始回测」对比不同策略。")
        return

    # 对比表格
    st.subheader("📊 策略对比")
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 柱状图对比
    st.subheader("📈 收益对比")
    chart_data = pd.DataFrame({
        "策略": [r["策略"] for r in results],
        "总收益率": [float(r["总收益率"].replace("%", "")) for r in results],
        "最大回撤": [float(r["最大回撤"].replace("%", "")) for r in results],
    }).set_index("策略")

    st.bar_chart(chart_data)

    # 解读
    best = max(results, key=lambda r: float(r["总收益率"].replace("%", "")))
    best_sharpe = max(results, key=lambda r: float(r["夏普"]))

    col1, col2 = st.columns(2)
    with col1:
        st.success(f"🏆 **收益最高**: {best['策略']}（{best['总收益率']}）")
    with col2:
        st.info(f"🛡️ **风险调整最佳**: {best_sharpe['策略']}（夏普 {best_sharpe['夏普']}）")

    st.divider()
    with st.expander("🤖 AI 解读 (点击展开)", expanded=False):
        if st.button("🔮 让 AI 帮我分析回测结果", key="ai_backtest"):
            try:
                from app.utils.ai_advisor import get_advisor
                advisor = get_advisor()
                interpretation = advisor.interpret("backtest", {
                    "fund_code": st.session_state.get("backtest_code"),
                    "results": results,
                })
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化，请先完成 Phase 3。")
            except Exception as e:
                st.warning(f"AI 解读暂时不可用: {e}")
