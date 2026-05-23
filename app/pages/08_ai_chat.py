"""AI 投资顾问对话页 — 自由提问，小财用大白话解答投资问题。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st


def render():
    st.title("🤖 AI 投资顾问 · 小财")
    st.markdown("你的私人投资学习伙伴。随便问，用大白话给你讲懂。")

    # 初始化聊天记录
    if "ai_chat_history" not in st.session_state:
        st.session_state["ai_chat_history"] = []

    # 快捷提问（selectbox + 发送按钮，避免大量状态按钮）
    st.subheader("💡 试试这些问题")
    quick_questions = [
        "什么是基金净值？用简单的话解释",
        "定投和一次性买入有什么区别？",
        "夏普比率是什么？有什么用？",
        "最大回撤 20% 算大吗？",
        "什么时候应该开始定投？",
        "PE 估值分位是什么意思？",
        "基金组合应该买几只？",
    ]

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_question = st.selectbox(
            "选择一个预设问题",
            quick_questions,
            index=None,
            placeholder="点击选择一个问题...",
            label_visibility="collapsed",
        )
    with col2:
        if st.button(
            "📤 发送", use_container_width=True, disabled=(selected_question is None)
        ):
            st.session_state["pending_question"] = selected_question
            st.rerun()

    st.divider()

    # 聊天历史
    for msg in st.session_state["ai_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 输入框
    prompt = st.chat_input("向小财提问...")

    # 处理快捷提问
    if "pending_question" in st.session_state:
        prompt = st.session_state.pop("pending_question")

    if prompt:
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["ai_chat_history"].append({"role": "user", "content": prompt})

        # 获取 AI 回复
        with st.chat_message("assistant"):
            with st.spinner("小财正在思考..."):
                try:
                    from app.utils.ai_advisor import get_advisor

                    advisor = get_advisor()

                    # 构建历史消息
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["ai_chat_history"][-8:-1]
                    ]

                    reply = advisor.chat(history, prompt)
                    st.markdown(reply)
                    st.session_state["ai_chat_history"].append(
                        {"role": "assistant", "content": reply}
                    )
                except ImportError:
                    st.warning(
                        "AI 顾问模块加载失败，请确保 app/utils/ai_advisor.py 存在。"
                    )
                except Exception as e:
                    st.error(f"AI 顾问出错了: {e}")
                    st.info(
                        "请检查 .env 中的配置：\n"
                        "- OPENAI_API_KEY=你的密钥\n"
                        "- OPENAI_BASE_URL=https://api.deepseek.com/v1\n"
                        "- LLM_MODEL=deepseek-chat"
                    )

    # 侧边栏提示
    with st.sidebar:
        st.subheader("关于小财")
        st.markdown("""
        小财是一个友好的投资学习伙伴，能帮你：

        - 📖 解释金融概念和术语
        - 📊 解读分析工具的结果
        - 💡 提供学习方法建议

        **小财不会做的**：
        - ❌ 推荐具体基金
        - ❌ 预测市场走势
        - ❌ 给出买卖建议

        ⚠️ 所有内容仅供学习，不构成投资建议。
        """)

        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state["ai_chat_history"] = []
            st.rerun()
