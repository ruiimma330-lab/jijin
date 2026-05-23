"""新手引导页面 — 零基础入门，三步学会基金投资。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

STEPS = [
    {
        "icon": "📖",
        "title": "第一步：搞懂基本概念",
        "desc": "先弄明白投资是什么，为什么要投基金。",
    },
    {
        "icon": "🏦",
        "title": "第二步：准备好账户",
        "desc": "选一个平台开户，绑定银行卡。",
    },
    {
        "icon": "💰",
        "title": "第三步：完成第一笔交易",
        "desc": "搜索基金、输入金额、确认买入。",
    },
]


def _render_step_one():
    st.subheader("📖 投资是什么？为什么要投基金？")

    st.info(
        "💡 **一句话总结**：投资就是用今天的钱，为将来的自己赚钱。\n\n"
        "你把钱交给专业的基金经理，他帮你买一堆股票/债券，"
        "就像请了个专业厨师帮你做菜，比你自己瞎炒强多了。"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏠 基金是什么？")
        st.markdown(
            """
        **基金 = 把钱交给专业人士打理**

        打个比方：你想开餐馆但不会做菜，怎么办？
        - 方案A：自己瞎做 → 大概率难吃（自己炒股）
        - 方案B：请个厨师 → 你出钱，他出力（买基金）

        基金经理就是这个"厨师"，他帮你挑选哪些股票/债券值得买。

        基金的优势：
        - ✅ 门槛低：10元就能买
        - ✅ 分散投资：一只基金持有一篮子资产，不怕单只暴雷
        - ✅ 专业管理：基金经理全职研究市场
        - ✅ 流动性好：随时可赎回（不像买房要挂几个月）
        """
        )
    with col2:
        st.markdown("#### ⏳ 复利：时间是最好的朋友")
        st.markdown(
            """
        **复利 = 利滚利，利息再生利息**

        举个小例子（年化 8% 假设）：
        - 每月投 1000 元
        - 投 10 年：本金 12 万 → 约 18 万
        - 投 20 年：本金 24 万 → 约 59 万
        - 投 30 年：本金 36 万 → 约 150 万

        📈 越早开始，复利效果越明显！

        > 彼得·林奇说："你不需要预测市场，只需要时间。"
        """
        )

    st.divider()
    st.markdown("#### 🤔 常见疑问")
    with st.expander("我只有几百块钱，能投吗？", expanded=False):
        st.markdown(
            "当然可以！大部分基金起投金额只有 **10 元**。"
            "定投的话每月几百块就够，重要的是养成习惯，而不是金额大小。"
        )
    with st.expander("基金会亏钱吗？", expanded=False):
        st.markdown(
            "会。基金的净值每天都会波动，有涨有跌是正常的。\n\n"
            "- 股票型基金：波动较大，年化波动率通常在 15-25%\n"
            "- 债券型基金：波动较小，年化波动率通常在 2-5%\n"
            "- 货币基金：几乎不亏，但收益率也最低\n\n"
            "📌 关键不是会不会亏，而是你能承受多少波动。记住：**用闲钱投资，长期持有**。"
        )


def _render_step_two():
    st.subheader("🏦 选一个平台，开个账户")

    st.info("💡 开户只需要 5-10 分钟。准备好：身份证 + 银行卡 + 手机号。")

    st.markdown("#### 📱 三个主流选择")
    cols = st.columns(3)
    with cols[0]:
        with st.container(border=True):
            st.markdown("#### 🐜 支付宝")
            st.markdown(
                """
            **适合**：大多数人

            **优点**：
            - 已经有了，不用另外下载
            - 操作最简单
            - 费率一折优惠

            **不足**：
            - 基金选择不如券商全
            - 没有投顾服务

            **费率**：申购费 1 折
            """
            )
            st.success("⭐ 推荐新手使用")
    with cols[1]:
        with st.container(border=True):
            st.markdown("#### 🏢 天天基金")
            st.markdown(
                """
            **适合**：想深入了解的用户

            **优点**：
            - 基金信息最全
            - 社区讨论活跃
            - 费率一折

            **不足**：
            - 需要单独下载 App
            - 界面功能较多，新手可能觉得复杂

            **费率**：申购费 1 折
            """
            )
    with cols[2]:
        with st.container(border=True):
            st.markdown("#### 🏛️ 券商")
            st.markdown(
                """
            **适合**：还想买股票的用户

            **优点**：
            - 可以买卖股票+基金+ETF
            - 有投顾和研报服务

            **不足**：
            - 需要视频认证
            - 场外基金费率一般不打折

            **费率**：申购费通常不打折
            """
            )

    st.divider()
    st.markdown("#### 📋 开户步骤（以支付宝为例）")
    steps_md = """
    | 步骤 | 操作 | 说明 |
    |------|------|------|
    | 1️⃣ | 打开支付宝 → 底部「理财」 | 进入理财频道 |
    | 2️⃣ | 点击「基金」 | 进入基金专区 |
    | 3️⃣ | 完成风险测评 | 系统会问几个问题了解你的风险承受能力（约2分钟） |
    | 4️⃣ | 绑定银行卡 | 选择一张储蓄卡用于购买和赎回（已绑定的跳过） |
    | 5️⃣ | 完成！ | 开户成功，可以开始买基金了 |
    """
    st.markdown(steps_md)
    st.caption(
        "⚠️ 风险测评要认真填写，它会决定你能买哪些类型的基金。保守型投资者不能购买高风险基金。"
    )


def _render_step_three():
    st.subheader("💰 完成第一笔交易")

    st.info(
        "💡 第一次买基金不用多，**10 元就够了**。\n\n"
        "重点是走一遍流程，熟悉操作。以后定投可以随时调整金额。"
    )

    st.markdown("#### 🛒 交易四步走")
    transaction_steps = [
        (
            "🔍",
            "搜索基金",
            "在搜索框输入基金名称或代码，比如「沪深300」或「110020」",
        ),
        (
            "📊",
            "看一眼基本信息",
            "基金类型、历史收益、费率、基金经理。不用深入研究，确认是你要的类型就行。",
        ),
        (
            "✏️",
            "输入金额 → 确认",
            "输入买入金额（如 10 元），系统会自动计算能买到多少份额。点击「确认买入」。",
        ),
        (
            "📋",
            "查看持仓",
            '买入后 T+1 日（下一个交易日）确认份额，在"我的持仓"里可以看到。',
        ),
    ]
    for icon, title, desc in transaction_steps:
        with st.container(border=True):
            cols = st.columns([1, 12])
            with cols[0]:
                st.markdown(f"## {icon}")
            with cols[1]:
                st.markdown(f"**{title}**")
                st.caption(desc)

    st.divider()
    st.markdown("#### ⚠️ 第一次买要注意的事")
    tips = [
        "先买**债券型基金**或**指数基金**，别一上来就买股票型（波动大，新手容易慌）。",
        "买入时间：**交易日 15:00 前**买入按当天净值确认，15:00 后按下个交易日。周末和节假日不交易。",
        "不要一次 all in：第一次只投一小笔试试水，以后慢慢加。",
        "持有至少 7 天以上再考虑赎回，否则可能有较高的赎回费（惩罚性费率）。",
    ]
    for tip in tips:
        st.markdown(f"- {tip}")


def _render_completion():
    st.balloons()
    st.success(
        "## 🎉 恭喜！你已经准备好开始投资了！\n\n"
        "你已经了解了：\n"
        "- ✅ 基金是什么、复利有多重要\n"
        "- ✅ 怎么开户、选哪个平台\n"
        "- ✅ 如何完成第一笔交易\n\n"
        "接下来，试试用平台的工具帮自己做决策吧 👇"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 筛选基金", use_container_width=True, type="primary"):
            st.session_state["active_view"] = "scanner"
            st.session_state["active_function"] = "scanner"
            st.rerun()
    with col2:
        if st.button("📊 查看市场信号", use_container_width=True):
            st.session_state["active_view"] = "signals"
            st.session_state["active_function"] = "signals"
            st.rerun()
    with col3:
        if st.button("💼 上传我的持仓", use_container_width=True):
            st.session_state["active_view"] = "portfolio_upload"
            st.session_state["active_function"] = "portfolio_upload"
            st.rerun()

    st.divider()
    st.caption(
        "💡 **小提示**：先别急着买太多！用「筛选器」找到合适的基金，"
        "再用「策略回测」看看定投效果，等心里有底了再动手。\n\n"
        "⚠️ 记住：投资有风险，用闲钱投资，坚持长期。"
    )


# ── 主渲染函数 ────────────────────────────────────────────


def render():
    st.title("🎓 新手引导")
    st.markdown("零基础入门，从开户到第一笔交易，三步搞定。")

    # 进度追踪
    if "guide_step" not in st.session_state:
        st.session_state["guide_step"] = 0

    step = st.session_state["guide_step"]
    total = len(STEPS)

    # 进度条
    if step < total:
        st.progress(step / total, text=f"进度 {step}/{total}")
    else:
        st.progress(1.0, text="🎉 全部完成！")

    st.divider()

    # 已完成步骤回顾
    if step == total:
        _render_completion()
    else:
        step_info = STEPS[step]
        st.markdown(f"### {step_info['icon']} {step_info['title']}")
        st.caption(step_info["desc"])
        st.divider()

        if step == 0:
            _render_step_one()
        elif step == 1:
            _render_step_two()
        elif step == 2:
            _render_step_three()

        # 下一步按钮
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            label = "✨ 完成！" if step == total - 1 else "下一步 →"
            if st.button(label, use_container_width=True, type="primary"):
                st.session_state["guide_step"] = step + 1
                st.rerun()

        # 可选的返回上一步
        if step > 0:
            with col1:
                if st.button("← 上一步", use_container_width=True):
                    st.session_state["guide_step"] = step - 1
                    st.rerun()

    # 底部重置
    if step > 0:
        st.divider()
        if st.button("🔄 重新开始", use_container_width=False):
            st.session_state["guide_step"] = 0
            st.rerun()
