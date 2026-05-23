"""我的持仓页面 — CSV 上传、持仓总览、健康诊断。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import plotly.express as px


def render():
    st.title("💼 我的持仓")
    st.markdown("上传支付宝/微信导出的基金持仓 CSV，分析你的投资组合健康状况。")

    # ── 上传区 ──
    st.subheader("📤 导入持仓数据")
    st.caption("支持支付宝、微信理财通、天天基金等平台的基金持仓导出文件")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader(
            "拖放或点击上传 CSV 文件",
            type=["csv"],
            help="从支付宝 App「理财」→「基金」→「持仓」→ 导出功能获取",
        )
    with col2:
        with st.expander("📖 如何导出？", expanded=False):
            st.markdown("""
            **支付宝**：
            理财 → 基金 → 我的持仓 → 右上角 ··· → 导出

            **微信理财通**：
            我的 → 基金 → 持仓 → 导出

            **天天基金**：
            我的 → 持仓 → 导出
            """)

    if uploaded is not None:
        with st.spinner("正在解析文件..."):
            from app.utils.csv_parser import parse_csv, holdings_to_dataframe

            result = parse_csv(uploaded.read(), uploaded.name)

            if not result.success:
                st.error(result.error)
            else:
                if result.warnings:
                    for w in result.warnings:
                        st.warning(w)

                platform_name = {
                    "alipay": "支付宝",
                    "wechat": "微信理财通",
                    "tiantian": "天天基金",
                    "generic": "通用格式",
                }.get(result.platform, result.platform)

                st.success(
                    f"✅ 识别为 **{platform_name}** 格式，共 {len(result.holdings)} 笔持仓"
                )

                # 存入 session
                df = holdings_to_dataframe(result.holdings)
                st.session_state["portfolio_holdings"] = result.holdings
                st.session_state["portfolio_df"] = df

    # ── 持仓展示 ──
    holdings = st.session_state.get("portfolio_holdings")
    df = st.session_state.get("portfolio_df")

    if holdings is None or df is None or df.empty:
        st.info("👆 上传你的基金持仓 CSV 文件，查看分析和诊断。")
        return

    # 总览卡片
    total_amount = sum(h.holding_amount for h in holdings)
    total_daily = sum(h.daily_return for h in holdings if h.daily_return)
    total_total_return = sum(h.total_return for h in holdings if h.total_return)

    cols = st.columns(4)
    cols[0].metric("💰 持仓总市值", f"{total_amount:,.0f} 元")
    cols[1].metric("📊 持有基金数", f"{len(holdings)} 只")
    cols[2].metric("📈 昨日收益", f"{total_daily:+,.2f} 元" if total_daily else "?")
    cols[3].metric(
        "🗂️ 累计收益", f"{total_total_return:+,.2f} 元" if total_total_return else "?"
    )

    # 持仓表格
    st.subheader("📋 持仓明细")
    display_df = df.copy()
    # 隐藏数据来源列
    if "数据来源" in display_df.columns:
        display_df = display_df.drop(columns=["数据来源"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 饼图：金额分配
    st.subheader("🍩 持仓分布")
    pie_data = df[df["持仓金额(元)"] > 0].copy()
    if not pie_data.empty:
        labels = pie_data["基金名称"].fillna(pie_data["基金代码"])
        fig = px.pie(
            values=pie_data["持仓金额(元)"],
            names=labels,
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── 健康诊断 ──
    st.subheader("🩺 持仓健康诊断")
    st.caption("基于现有数据进行的快速分析")

    issues = []
    if len(holdings) == 1:
        issues.append(
            "⚠️ 只持有 1 只基金，风险过于集中。建议至少持有 3-5 只不同类型基金。"
        )
    elif len(holdings) > 10:
        issues.append("⚠️ 持有超过 10 只基金，可能过于分散。建议精简到 5-8 只。")

    # 检查是否有债券基金（从名称猜测）
    bond_keywords = ["债", "债券", "bond", "纯债", "固收"]
    has_bond = any(
        any(kw in (h.fund_name or "").lower() for kw in bond_keywords) for h in holdings
    )
    if not has_bond:
        issues.append("💡 未检测到债券类基金。加入债券基金可以有效降低组合波动。")

    # 集中度检查
    if total_amount > 0:
        max_single = max(h.holding_amount for h in holdings)
        concentration = max_single / total_amount * 100
        if concentration > 50:
            issues.append(
                f"⚠️ 单只基金占比 {concentration:.0f}%，过于集中。"
                f"建议单只不超过总仓位的 30%。"
            )

    if issues:
        for issue in issues:
            st.markdown(issue)
    else:
        st.success("✅ 持仓结构基本健康。保持定投，定期再平衡。")

    # ── 与市场联动 ──
    st.subheader("🔍 查看持仓基金表现")
    codes = [h.fund_code for h in holdings]
    selected = st.selectbox(
        "选择一只基金查看详情",
        codes,
        format_func=lambda c: (
            f"{c} — {next((h.fund_name for h in holdings if h.fund_code == c), '')}"
        ),
    )

    if selected and st.button("📊 查看风险评估"):
        st.info(f"→ 跳转到风险评估页面查看基金 {selected} 的详细分析")
        st.switch_page("pages/05_risk_report.py")

    # ── AI 持仓诊断 ──
    st.divider()
    with st.expander("🤖 AI 持仓诊断 (点击展开)", expanded=True):
        if st.button("🔮 让 AI 诊断我的持仓健康度", key="ai_holding", type="primary"):
            try:
                from app.utils.ai_advisor import get_advisor

                advisor = get_advisor()

                summary = {
                    "持仓数量": len(holdings),
                    "总市值": f"{total_amount:,.0f} 元",
                    "持仓基金": [
                        {
                            "代码": h.fund_code,
                            "名称": h.fund_name,
                            "金额": f"{h.holding_amount:,.0f}",
                            "收益率": f"{h.return_rate}%" if h.return_rate else "未知",
                        }
                        for h in holdings
                    ],
                    "昨日收益": f"{total_daily:+,.2f}" if total_daily else "未知",
                    "累计收益": f"{total_total_return:+,.2f}"
                    if total_total_return
                    else "未知",
                }

                interpretation = advisor.interpret("portfolio", summary)
                st.markdown(interpretation)
            except ImportError:
                st.info("AI 顾问模块尚未初始化。")
            except Exception as e:
                st.warning(f"AI 诊断暂时不可用: {e}")
