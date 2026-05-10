"""持仓 CSV 解析器 — 自动识别支付宝/微信/天天基金导出的持仓文件。

支持格式:
- 支付宝基金导出
- 微信理财通导出
- 天天基金导出
- 通用格式 (至少含基金代码和持仓金额两列)
"""

import csv
import io
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class PortfolioHolding:
    fund_code: str
    fund_name: str = ""
    fund_type: Optional[str] = None
    holding_amount: float = 0.0
    holding_shares: Optional[float] = None
    cost_basis: Optional[float] = None
    latest_nav: Optional[float] = None
    daily_return: Optional[float] = None
    total_return: Optional[float] = None
    return_rate: Optional[float] = None
    platform: str = "unknown"


@dataclass
class ParseResult:
    success: bool
    holdings: list[PortfolioHolding] = field(default_factory=list)
    platform: str = "unknown"
    error: str = ""
    warnings: list[str] = field(default_factory=list)


# ── 列名模糊匹配 ──────────────────────────────────────────

# 基金代码的模式
CODE_PATTERNS = [
    ["基金代码", "代码", "code", "symbol", "产品代码"],
]

# 基金名称的模式
NAME_PATTERNS = [
    ["基金名称", "名称", "基金简称", "name", "产品名称", "简称"],
]

# 持仓金额的模式 (元)
AMOUNT_PATTERNS = [
    ["持仓金额", "持有金额", "市值", "持仓市值", "当前市值",
     "amount", "value", "市场价值"],
]

# 持仓份额的模式
SHARES_PATTERNS = [
    ["持仓份额", "持有份额", "份额", "shares", "units"],
]

# 最新净值
NAV_PATTERNS = [
    ["最新净值", "单位净值", "净值", "nav", "当前净值"],
]

# 成本价
COST_PATTERNS = [
    ["成本价", "持仓成本", "买入均价", "cost", "成本净值"],
]

# 昨日收益
DAILY_RETURN_PATTERNS = [
    ["昨日收益", "日收益", "当日收益", "daily_return"],
]

# 累计收益
TOTAL_RETURN_PATTERNS = [
    ["累计收益", "持有收益", "total_return", "总收益", "累计盈亏"],
]

# 持有收益率
RETURN_RATE_PATTERNS = [
    ["持有收益率", "收益率", "return_rate", "累计收益率"],
]


def _find_column(columns: list[str], patterns: list[list[str]]) -> Optional[str]:
    """从列名列表中按模糊匹配找到目标列。"""
    for col in columns:
        col_lower = col.strip().lower()
        for group in patterns:
            for pat in group:
                if pat.lower() in col_lower or col_lower in pat.lower():
                    return col
    return None


def _safe_float(value) -> Optional[float]:
    """安全转为 float，失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(",", "").replace("，", "").replace("%", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def detect_platform(columns: list[str]) -> str:
    """根据列名特征判断导出平台。"""
    cols_str = " ".join(columns).lower()
    if "支付宝" in cols_str or "alipay" in cols_str:
        return "alipay"
    if "微信" in cols_str or "理财通" in cols_str or "wechat" in cols_str:
        return "wechat"
    if "天天基金" in cols_str or "tiantian" in cols_str:
        return "tiantian"
    return "generic"


def parse_csv(file_content: bytes, filename: str = "") -> ParseResult:
    """解析上传的 CSV 文件。

    Args:
        file_content: CSV 原始字节
        filename: 文件名 (用于提示)

    Returns:
        ParseResult: 包含解析成功的持仓列表和诊断信息
    """
    warnings = []

    # 尝试多种编码
    content_str = None
    for encoding in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"]:
        try:
            content_str = file_content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if content_str is None:
        return ParseResult(
            success=False,
            error="无法识别文件编码，请确认文件为 CSV 格式 (UTF-8/GBK)",
        )

    # 跳过空行，找到 header
    lines = content_str.strip().split("\n")
    if len(lines) < 2:
        return ParseResult(success=False, error="文件内容为空或只有一行")

    # 用 csv 模块解析
    try:
        reader = csv.reader(io.StringIO(content_str))
        rows = list(reader)
    except Exception as e:
        return ParseResult(success=False, error=f"CSV 解析失败: {e}")

    if len(rows) < 2:
        return ParseResult(success=False, error="文件至少需要一行标题和一行数据")

    header = [h.strip() for h in rows[0]]
    data_rows = rows[1:]

    # 检测平台
    platform = detect_platform(header)

    # 列映射
    code_col = _find_column(header, CODE_PATTERNS)
    name_col = _find_column(header, NAME_PATTERNS)
    amount_col = _find_column(header, AMOUNT_PATTERNS)
    shares_col = _find_column(header, SHARES_PATTERNS)
    nav_col = _find_column(header, NAV_PATTERNS)
    cost_col = _find_column(header, COST_PATTERNS)
    daily_ret_col = _find_column(header, DAILY_RETURN_PATTERNS)
    total_ret_col = _find_column(header, TOTAL_RETURN_PATTERNS)
    rate_col = _find_column(header, RETURN_RATE_PATTERNS)

    if code_col is None:
        return ParseResult(
            success=False,
            error=(
                '找不到「基金代码」列。\n\n'
                f"文件列名: {', '.join(header)}\n\n"
                '请确认文件包含至少一列类似「基金代码」或「代码」的列。'
            ),
        )

    if amount_col is None:
        # 没有金额列不算致命，设为 0
        warnings.append("未找到持仓金额列，金额将设为 0。支持的列名：持仓金额、市值等")

    # 构建列索引映射
    col_index = {h: i for i, h in enumerate(header)}

    holdings = []
    skipped = 0
    for row in data_rows:
        if not row or all(c.strip() == "" for c in row):
            continue

        try:
            code = row[col_index[code_col]].strip()
        except IndexError:
            skipped += 1
            continue

        if not code or len(code) < 4:
            skipped += 1
            continue

        # 确保是 6 位数字
        code = code.zfill(6) if code.isdigit() else code

        name = ""
        if name_col and name_col in col_index:
            try:
                name = row[col_index[name_col]].strip()
            except IndexError:
                pass

        amount = 0.0
        if amount_col and amount_col in col_index:
            try:
                amount = _safe_float(row[col_index[amount_col]]) or 0.0
            except IndexError:
                pass

        shares = None
        if shares_col and shares_col in col_index:
            try:
                shares = _safe_float(row[col_index[shares_col]])
            except IndexError:
                pass

        nav = None
        if nav_col and nav_col in col_index:
            try:
                nav = _safe_float(row[col_index[nav_col]])
            except IndexError:
                pass

        cost = None
        if cost_col and cost_col in col_index:
            try:
                cost = _safe_float(row[col_index[cost_col]])
            except IndexError:
                pass

        daily_ret = None
        if daily_ret_col and daily_ret_col in col_index:
            try:
                daily_ret = _safe_float(row[col_index[daily_ret_col]])
            except IndexError:
                pass

        total_ret = None
        if total_ret_col and total_ret_col in col_index:
            try:
                total_ret = _safe_float(row[col_index[total_ret_col]])
            except IndexError:
                pass

        ret_rate = None
        if rate_col and rate_col in col_index:
            try:
                ret_rate = _safe_float(row[col_index[rate_col]])
            except IndexError:
                pass

        holdings.append(PortfolioHolding(
            fund_code=code,
            fund_name=name,
            holding_amount=amount,
            holding_shares=shares,
            cost_basis=cost,
            latest_nav=nav,
            daily_return=daily_ret,
            total_return=total_ret,
            return_rate=ret_rate,
            platform=platform,
        ))

    if skipped > 0:
        warnings.append(f"跳过了 {skipped} 行无效数据")

    if not holdings:
        return ParseResult(success=False, error="未能解析出任何持仓记录。请检查文件格式。")

    return ParseResult(
        success=True,
        holdings=holdings,
        platform=platform,
        warnings=warnings,
    )


def holdings_to_dataframe(holdings: list[PortfolioHolding]) -> pd.DataFrame:
    """将持仓列表转为 DataFrame。"""
    if not holdings:
        return pd.DataFrame()
    return pd.DataFrame([{
        "基金代码": h.fund_code,
        "基金名称": h.fund_name,
        "持仓金额(元)": h.holding_amount,
        "持仓份额": h.holding_shares,
        "成本净值": h.cost_basis,
        "最新净值": h.latest_nav,
        "昨日收益(元)": h.daily_return,
        "累计收益(元)": h.total_return,
        "持有收益率(%)": h.return_rate,
        "数据来源": {"alipay": "支付宝", "wechat": "微信理财通", "tiantian": "天天基金"}.get(h.platform, h.platform),
    } for h in holdings])
