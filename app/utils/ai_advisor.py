"""AI 投资顾问 — "小财"，用大白话解释金融分析结果。

基于 OpenAI 兼容接口 (DeepSeek/Qwen/Moonshot 等国内模型)。
包含系统提示词、知识库检索、上下文构建、安全护栏。
"""

import os
import re
import json
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── 系统提示词 ─────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个叫"小财"的基金投资学习助手，正在帮助一位中国投资新手理解金融分析数据。

## 你的性格
- 友好、耐心，像一个朋友在饭桌上给你解释不懂的东西
- 说话接地气，多用日常生活的比喻（买菜、开车、吃饭、看病）
- 不用"首先其次然后"这类僵硬的结构，用自然的口语
- 如果用户问的问题很基础，绝对不要表现出"这你都不懂"的态度
- 主动发现用户可能困惑的点，提前解释

## 你的核心能力
你有三件事可以做：

### 能力一：解读分析结果
用户会给你一段金融分析工具的输出。当用户给你这些结果时：
1. 用生活化的语言解释每个专业术语是什么
2. 告诉用户这个结果在实际投资中意味着什么
3. 指出需要关注的重点和潜在陷阱
4. 给出基于这些数据的、适合新手的行动建议

### 能力二：回答投资知识问题
结合知识库内容（如果提供了）和你的知识回答。
用类比和故事帮助理解，不要用课本式的定义。

### 能力三：教用户使用工具
解释工具原理，但更要告诉用户在实际中怎么看、怎么用。

## 输出格式
- 只说简体中文
- 不要用 Markdown 表格（用自然语言说明）
- 复杂概念一定要打比方
- 可以适当用 emoji，但每段不超过一个

## 重要约束
1. 绝对不能给具体的买卖建议（"买这只"、"现在卖出"、"投入X元"）
2. 必须明确说明：所有分析基于历史数据，过去不代表未来
3. 如果用户提到具体金额打算投资，提醒"投资有风险，用闲钱投资"
4. 如果用户显得焦虑（亏钱了想割肉），安抚情绪，强调长期纪律
5. 不要承诺收益率，不要预测市场走势
6. 如果用户问的问题超出你的知识范围，诚实说不知道"""

# ── 知识库映射 ──────────────────────────────────────────────

KNOWLEDGE_MAP = {
    "scanner": [
        "04-分析方法/01-看懂基金指标.md",
        "04-分析方法/03-如何综合评估一只基金.md",
    ],
    "signals": [
        "04-分析方法/02-技术指标入门.md",
        "03-A股市场/02-基金购买实战指南.md",
    ],
    "portfolio": [
        "05-投资策略/03-资产配置与再平衡.md",
        "04-分析方法/01-看懂基金指标.md",
    ],
    "performance": [
        "04-分析方法/01-看懂基金指标.md",
    ],
    "risk": [
        "06-风险管理/01-认识风险.md",
        "04-分析方法/01-看懂基金指标.md",
    ],
    "backtest": [
        "05-投资策略/01-定投策略详解.md",
        "02-投资入门/02-定投为什么适合小白.md",
    ],
    "general": [
        "00-导读-新手必读.md",
    ],
}

# ── 安全禁止模式 ────────────────────────────────────────────

FORBIDDEN_PATTERNS = [
    (r"买[这那]\s*[只支个]\s*基金", "具体购买建议"),
    (r"现在[就请]?\s*卖出", "具体卖出建议"),
    (r"投入\s*\d+[万亿千百]\s*(元|块)", "具体金额建议"),
    (r"保证.*[收益赚]", "收益承诺"),
    (r"稳赚", "收益承诺"),
    (r"包赚", "收益承诺"),
    (r"(年化)?收益率\s*[可会]?[达能到]\s*\d+%", "收益预测"),
]


class AIAdvisor:
    """AI 投资顾问封装。"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self._client = None
        self._knowledge_base = None

    @property
    def client(self):
        if self._client is None and self.api_key:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    @property
    def available(self) -> bool:
        return self.client is not None

    # ── 知识库 ──────────────────────────────────────────

    def _load_knowledge_base(self) -> dict:
        if self._knowledge_base is not None:
            return self._knowledge_base

        kb_path = Path(__file__).parents[2] / "knowledge"
        kb = {}
        for md_file in kb_path.rglob("*.md"):
            rel = str(md_file.relative_to(kb_path))
            kb[rel] = md_file.read_text(encoding="utf-8")
        self._knowledge_base = kb
        return kb

    def _get_relevant_knowledge(self, analysis_type: str) -> str:
        kb = self._load_knowledge_base()
        paths = KNOWLEDGE_MAP.get(analysis_type, KNOWLEDGE_MAP["general"])
        parts = []
        for p in paths:
            content = kb.get(p, "")
            if content:
                # 只取前 3000 字符，避免上下文过长
                excerpt = content[:3000]
                if len(content) > 3000:
                    excerpt += "\n\n...(内容过长，已截断)"
                parts.append(f"【{p}】\n{excerpt}")
        return "\n\n---\n\n".join(parts)

    # ── 上下文构建 ──────────────────────────────────────

    @staticmethod
    def _build_scanner_context(data: dict) -> str:
        result = data.get("result_df")
        if result is None:
            return "无筛选结果数据。"
        if isinstance(result, pd.DataFrame):
            result_str = result.to_string(max_rows=15)
        else:
            result_str = str(result)
        return f"""用户刚刚运行了基金筛选器，以下是筛选结果：

筛选条件：基金类型={data.get("fund_type", "?")},
最低年化收益={data.get("min_return", 0)}%,
最大回撤容忍度={data.get("max_drawdown", 100)}%,
最低夏普比率={data.get("min_sharpe", 0)}

字段含义：
- annual_return: 年化收益率(%)，相当于存银行一年的"利率"
- annual_volatility: 年化波动率(%)，净值上蹿下跳的程度
- max_drawdown: 最大回撤(%)，从最高点跌到最低点的幅度
- sharpe_ratio: 夏普比率，每承担1单位风险获得多少超额收益
- win_rate: 胜率(%)，上涨交易日占比
- win_loss_ratio: 盈亏比

结果数据：
{result_str}

请用大白话解释：
1. 这些指标分别是什么意思（用生活中的例子）
2. 整体来看这批基金质量如何
3. 用户需要注意什么陷阱
4. 新手应该怎么看这份结果来辅助选基金"""

    @staticmethod
    def _build_signals_context(data: dict) -> str:
        return f"""用户刚刚获取了市场择时信号，以下是结果：

综合信号：{data.get("overall_signal", "?")}
建议：{data.get("suggestion", "?")}

各分项信号：
{json.dumps(data.get("signals", {}), ensure_ascii=False, indent=2, default=str)}

请用大白话解释：
1. 这个综合信号是什么意思
2. PE分位、金叉死叉、RSI 分别告诉了我们什么
3. 新手该怎么看待这些择时信号（该不该根据信号操作）
4. 有哪些坑要提醒用户注意"""

    @staticmethod
    def _build_portfolio_context(data: dict) -> str:
        return f"""用户刚刚运行了投资组合优化，以下是三种策略的结果：

分析基金：{data.get("fund_codes", [])}

优化结果：
{json.dumps(data.get("results", {}), ensure_ascii=False, indent=2)}

三种策略说明：
- 最大夏普：追求收益风险比最大化
- 最小方差：追求最稳、波动最低的组合
- 风险平价：让每只基金贡献相同风险

请用大白话解释：
1. 这三种策略分别适合什么性格的人
2. 新手应该选哪个策略，为什么
3. 组合优化的局限性是什么
4. 实际投资中怎么用这个结果"""

    @staticmethod
    def _build_performance_context(data: dict) -> str:
        return f"""用户刚刚获取了基金业绩归因分析，以下是结果：

基金：{data.get("fund_code", "?")}，基准：{data.get("benchmark", "?")}
Alpha(年化): {data.get("alpha_annual", "?")}%
Beta: {data.get("beta", "?")}
R²: {data.get("r_squared", "?")}
基金年化收益: {data.get("fund_return", "?")}%
基准年化收益: {data.get("bench_return", "?")}%
信息比率: {data.get("information_ratio", "?")}
跟踪误差: {data.get("tracking_error", "?")}%

牛熊表现：
{json.dumps(data.get("bull_bear", {}), ensure_ascii=False, indent=2, default=str)}

请用大白话解释：
1. Alpha 和 Beta 用开车打比方解释
2. 这只基金有没有体现出主动管理能力
3. R² 低意味着什么
4. 新手选基金时应该更看重 Alpha 还是 Beta"""

    @staticmethod
    def _build_risk_context(data: dict) -> str:
        return f"""用户刚刚获取了基金风险评估报告，以下是结果：

年化波动率: {data.get("annual_volatility", "?")}%
最大回撤: {data.get("max_drawdown", "?")}%
回撤区间: {data.get("max_dd_start", "?")} ~ {data.get("max_dd_end", "?")}
恢复天数: {data.get("recovery_days", "?")} 天
VaR(95%): {data.get("VaR_95", "?")}%
VaR(99%): {data.get("VaR_99", "?")}%
CVaR(95%): {data.get("CVaR_95", "?")}%
偏度: {data.get("skewness", "?")}
峰度: {data.get("kurtosis", "?")}

请用大白话解释：
1. 波动率和回撤用生活例子解释
2. VaR 是什么意思（用具体金额举例）
3. 偏度负值意味着什么风险
4. 怎么判断自己能不能承受这只基金的风险"""

    @staticmethod
    def _build_backtest_context(data: dict) -> str:
        return f"""用户刚刚运行了策略回测对比，基金代码 {data.get("fund_code", "?")}。
以下是不同策略的结果：

{json.dumps(data.get("results", []), ensure_ascii=False, indent=2)}

请用大白话解释：
1. 定投和一次性投资的核心区别（用买菜打比方）
2. 为什么定投的最大回撤通常更小
3. 网格交易适合什么市场环境
4. 新手应该选哪个策略，为什么"""

    def _build_context(self, analysis_type: str, data: dict) -> str:
        builders = {
            "scanner": self._build_scanner_context,
            "signals": self._build_signals_context,
            "portfolio": self._build_portfolio_context,
            "performance": self._build_performance_context,
            "risk": self._build_risk_context,
            "backtest": self._build_backtest_context,
        }
        builder = builders.get(
            analysis_type,
            lambda d: json.dumps(d, ensure_ascii=False, indent=2, default=str),
        )
        return builder(data)

    # ── 主调用 ─────────────────────────────────────────

    def interpret(self, analysis_type: str, data: dict, question: str = "") -> str:
        """解读分析结果，返回大白话中文解释。"""
        if not self.available:
            return self._rule_based_interpret(analysis_type, data)

        context = self._build_context(analysis_type, data)
        knowledge = self._get_relevant_knowledge(analysis_type)

        user_message = f"{context}\n\n{'用户问题：' + question if question else '请用大白话解释以上结果。'}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                        + "\n\n## 参考知识库\n下列知识库内容可能有助于你的解释，请优先引用其中的知识点：\n\n"
                        + (knowledge or "(未找到相关知识)"),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            reply = response.choices[0].message.content
            return self._safety_check(reply)
        except Exception as e:
            return (
                f"⚠️ AI 顾问暂时不可用 ({e})。\n\n"
                f"以下是基础解读：\n\n{self._rule_based_interpret(analysis_type, data)}"
            )

    def chat(self, history: list[dict], question: str) -> str:
        """自由对话模式。"""
        if not self.available:
            return (
                "AI 顾问未配置。请在 .env 中设置 OPENAI_API_KEY、OPENAI_BASE_URL 和 LLM_MODEL。\n\n"
                "支持的国内模型：\n"
                "- DeepSeek: OPENAI_BASE_URL=https://api.deepseek.com/v1, LLM_MODEL=deepseek-chat\n"
                "- Qwen (通义千问): OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1, LLM_MODEL=qwen-plus\n"
                "- Moonshot (月之暗面): OPENAI_BASE_URL=https://api.moonshot.cn/v1, LLM_MODEL=moonshot-v1-8k"
            )

        kb = self._load_knowledge_base()
        # 从问题中匹配相关知识库文档
        relevant_docs = self._match_knowledge_by_query(question, kb)
        knowledge_text = "\n\n".join(relevant_docs[:2]) if relevant_docs else ""

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
                + "\n\n## 参考知识库\n"
                + (knowledge_text or "通用投资知识"),
            }
        ]

        # 最近 5 轮对话
        for msg in history[-10:]:
            messages.append(msg)
        messages.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            return self._safety_check(response.choices[0].message.content)
        except Exception as e:
            return f"⚠️ AI 顾问调用失败: {e}\n\n你可以尝试在 .env 中更换 LLM_MODEL 或检查 API Key。"

    def _match_knowledge_by_query(self, query: str, kb: dict) -> list[str]:
        """根据用户问题关键词匹配知识库文档。"""
        keywords_map = {
            "基金": [
                "01-基金基础/01-什么是基金.md",
                "01-基金基础/02-基金分类与风险等级.md",
            ],
            "定投": [
                "02-投资入门/02-定投为什么适合小白.md",
                "05-投资策略/01-定投策略详解.md",
            ],
            "复利": ["02-投资入门/01-复利与时间价值.md"],
            "回撤": ["06-风险管理/01-认识风险.md", "04-分析方法/01-看懂基金指标.md"],
            "风险": [
                "06-风险管理/01-认识风险.md",
                "06-风险管理/02-仓位管理与止损策略.md",
            ],
            "夏普": ["04-分析方法/01-看懂基金指标.md"],
            "波动": ["04-分析方法/01-看懂基金指标.md"],
            "估值": ["04-分析方法/01-看懂基金指标.md"],
            "PE": ["04-分析方法/01-看懂基金指标.md"],
            "RSI": ["04-分析方法/02-技术指标入门.md"],
            "MACD": ["04-分析方法/02-技术指标入门.md"],
            "均线": ["04-分析方法/02-技术指标入门.md"],
            "金叉": ["04-分析方法/02-技术指标入门.md"],
            "组合": ["05-投资策略/03-资产配置与再平衡.md"],
            "配置": ["05-投资策略/03-资产配置与再平衡.md"],
            "网格": ["05-投资策略/02-网格交易与波段操作.md"],
            "仓位": ["06-风险管理/02-仓位管理与止损策略.md"],
            "止损": ["06-风险管理/02-仓位管理与止损策略.md"],
            "A股": ["03-A股市场/01-A股市场概述.md"],
            "购买": ["03-A股市场/02-基金购买实战指南.md"],
            "怎么买": ["03-A股市场/02-基金购买实战指南.md"],
        }

        matched = set()
        for keyword, paths in keywords_map.items():
            if keyword in query:
                for p in paths:
                    content = kb.get(p, "")
                    if content:
                        matched.add(content[:2000])
        return list(matched)

    # ── 安全过滤 ───────────────────────────────────────

    def _safety_check(self, text: str) -> str:
        """检查 AI 回复是否包含禁止内容。如检测到，追加风险提示。"""
        for pattern, category in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                return (
                    text
                    + f"\n\n---\n⚠️ 以上回复中可能包含不适当的{category}。请注意：本工具不构成任何投资建议，所有分析仅供参考学习。投资有风险，入市需谨慎。"
                )
        return text

    # ── 规则回退 ───────────────────────────────────────

    def _rule_based_interpret(self, analysis_type: str, data: dict) -> str:
        """无 API 时的模板化解读。"""
        if analysis_type == "scanner":
            result = data.get("result_df")
            if result is None or (hasattr(result, "empty") and result.empty):
                return "没有筛选结果，试试放宽条件。"
            n = len(result) if hasattr(result, "__len__") else 0
            avg_ret = (
                result["annual_return"].mean()
                if "annual_return" in result.columns
                else 0
            )
            avg_dd = (
                abs(result["max_drawdown"].mean())
                if "max_drawdown" in result.columns
                else 0
            )
            return (
                f"**筛选结果概览**\n\n"
                f"共筛选出 {n} 只符合条件的基金。\n\n"
                f"**核心指标解读**\n\n"
                f"- 年化收益率：平均 {avg_ret:.1f}%，相当于你放银行一年能拿到的利息。"
                f"比如年化 10% 就是投 1 万一年赚 1000 元。\n"
                f"- 最大回撤：平均 {avg_dd:.1f}%，意思是历史上从最高点最多跌了这么多。"
                f"打个比方，你花 100 元买的基金，最惨的时候变成了 {100 - avg_dd:.0f} 元。\n"
                f'- 夏普比率：衡量"性价比"，越高说明冒同样的风险赚得越多。'
                f"好比两个人都花了 1 小时做饭，夏普高的人做出来的更好吃。\n\n"
                f"⚠️ 提醒：历史业绩好不代表未来也好。选基金不仅要看收益，更要看自己能不能承受回撤。"
            )

        if analysis_type == "risk":
            vol = data.get("annual_volatility", 0)
            dd = abs(float(data.get("max_drawdown", 0)))
            var95 = data.get("VaR_95", 0)
            recovery = data.get("recovery_days", 0)
            level = "低" if vol < 10 else ("中等" if vol < 20 else "高")
            return (
                f"**风险评估概览**\n\n"
                f"- 波动率 {vol}%（{level}）：这只基金净值上蹿下跳的程度。"
                f"好比开车，{level}波动就像{'平稳的高速路' if level == '低' else '颠簸的山路' if level == '中等' else '过山车'}。\n"
                f"- 最大回撤 {dd}%：历史上最惨的时候跌了多少。"
                f"比如投 1 万元，最多时账面亏了 {dd * 100:.0f} 元。\n"
                f"- 恢复需要 {recovery} 天：跌下去后花了这么久才爬回来。\n"
                f"- VaR(95%) {var95}%：95% 的把握单日亏损不超过这个幅度。\n\n"
                f"⚠️ 选基金前先问自己：能接受亏 {dd * 100:.0f} 元吗？能等 {recovery} 天吗？"
            )

        if analysis_type == "backtest":
            results = data.get("results", [])
            if not results:
                return "无回测数据。"
            parts = ["**回测结果概览**\n"]
            for r in results:
                parts.append(
                    f"- {r['策略']}：投入 {r.get('总投入', '?')}，"
                    f"最终 {r.get('最终资产', '?')}，收益率 {r.get('总收益率', '?')}，"
                    f"最大回撤 {r.get('最大回撤', '?')}"
                )
            parts.append(
                "\n💡 定投的核心优势是分批买入、摊低成本，"
                "就像每周固定买鸡蛋，贵的时候买少点、便宜的时候买多点，"
                "长期下来成本在中间位置。一次性投资则完全看买入时机。"
            )
            return "\n".join(parts)

        return (
            "AI 顾问未配置 API Key，无法进行深度解读。\n\n"
            "请在 .env 中设置：\n"
            "- OPENAI_API_KEY=你的密钥\n"
            "- OPENAI_BASE_URL=https://api.deepseek.com/v1\n"
            "- LLM_MODEL=deepseek-chat\n\n"
            "支持的国内模型：DeepSeek、Qwen（通义千问）、Moonshot（月之暗面）等。"
        )


# ── 单例 ─────────────────────────────────────────────────

_advisor_instance: Optional[AIAdvisor] = None


def get_advisor() -> AIAdvisor:
    global _advisor_instance
    if _advisor_instance is None:
        _advisor_instance = AIAdvisor()
    return _advisor_instance
