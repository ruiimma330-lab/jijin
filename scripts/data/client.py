"""统一数据客户端 — 封装 akshare，提供一致的基金/股票/指数数据接口。

所有数据获取脚本应通过此模块获取数据，方便后续切换数据源。
"""

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None


class DataSourceError(Exception):
    """数据源不可用时抛出。"""


@dataclass(frozen=True)
class FundInfo:
    """基金基本信息（不可变）。"""
    code: str
    name: str
    fund_type: str
    establish_date: Optional[date]
    company: str
    manager: str
    aum: float  # 资产规模(亿元)
    management_fee: float  # 管理费率(%)


def _ensure_ak():
    if ak is None:
        raise DataSourceError(
            "akshare 未安装。请运行: pip install akshare"
        )


def get_fund_list(fund_type: str = "all") -> pd.DataFrame:
    """获取公募基金列表。

    Args:
        fund_type: 基金类型筛选，可选 "stock"(股票型), "bond"(债券型),
                   "mix"(混合型), "money"(货币型), "index"(指数型), "all"(全部)

    Returns:
        DataFrame，包含 code, name, fund_type, establish_date, company 等字段
    """
    _ensure_ak()
    df = ak.fund_rating_all()
    df = df.rename(columns={
        "代码": "code",
        "简称": "name",
        "基金经理": "manager",
        "基金公司": "company",
        "类型": "fund_type",
    })
    available_cols = [c for c in [
        "code", "name", "fund_type", "company", "manager"
    ] if c in df.columns]
    result = df[available_cols].copy()
    if fund_type != "all":
        type_map = {
            "stock": "股票型",
            "bond": "债券型",
            "mix": "混合型",
            "money": "货币型",
            "index": "指数型",
        }
        target = type_map.get(fund_type, fund_type)
        result = result[result["fund_type"].str.contains(target, na=False)]
    return result.reset_index(drop=True)


def get_fund_nav(
    fund_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取单只基金的历史净值。

    Args:
        fund_code: 基金代码，如 "000001"
        start_date: 开始日期 "YYYYMMDD"，默认一年前
        end_date: 结束日期 "YYYYMMDD"，默认今天

    Returns:
        DataFrame，包含 date, nav(单位净值), accum_nav(累计净值),
        daily_return(日收益率)
    """
    _ensure_ak()
    if end_date is None:
        end_date = date.today().strftime("%Y%m%d")
    if start_date is None:
        start = date.today() - timedelta(days=365)
        start_date = start.strftime("%Y%m%d")

    df = ak.fund_open_fund_info_em(
        symbol=fund_code, indicator="单位净值走势"
    )
    if df is None or df.empty:
        raise DataSourceError(f"未找到基金 {fund_code} 的净值数据")

    df = df.rename(columns={
        "净值日期": "date", "单位净值": "nav", "日增长率": "daily_growth_pct",
    })
    df["date"] = pd.to_datetime(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"])
    df = df.sort_values("date").reset_index(drop=True)

    # 获取累计净值
    try:
        df_acc = ak.fund_open_fund_info_em(
            symbol=fund_code, indicator="累计净值走势"
        )
        df_acc = df_acc.rename(columns={"净值日期": "date", "累计净值": "accum_nav"})
        df_acc["date"] = pd.to_datetime(df_acc["date"])
        df_acc["accum_nav"] = pd.to_numeric(df_acc["accum_nav"], errors="coerce")
        df = df.merge(df_acc[["date", "accum_nav"]], on="date", how="left")
    except Exception:
        df["accum_nav"] = df["nav"]

    df["daily_return"] = df["nav"].pct_change()
    mask = (df["date"] >= pd.Timestamp(start_date)) & (
        df["date"] <= pd.Timestamp(end_date)
    )
    return df[mask].reset_index(drop=True)


def get_fund_ranking(
    fund_type: str = "all",
    top_n: int = 20,
) -> pd.DataFrame:
    """获取基金近期收益排名。

    Args:
        fund_type: 基金类型
        top_n: 返回前 N 名

    Returns:
        DataFrame，包含 code, name, return_1w, return_1m, return_3m,
        return_6m, return_1y, return_3y
    """
    _ensure_ak()
    type_map = {
        "all": "全部", "stock": "股票型", "bond": "债券型",
        "mix": "混合型", "index": "指数型", "money": "货币型",
        "qdii": "QDII", "fof": "FOF",
    }
    symbol = type_map.get(fund_type, fund_type)
    df = ak.fund_open_fund_rank_em(symbol=symbol)
    rename_map = {
        "基金代码": "code",
        "基金简称": "name",
        "近1周": "return_1w",
        "近1月": "return_1m",
        "近3月": "return_3m",
        "近6月": "return_6m",
        "近1年": "return_1y",
        "近2年": "return_2y",
        "近3年": "return_3y",
    }
    available = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=available)
    return_cols = [c for c in available.values() if c in df.columns and c not in ("code", "name")]
    result = df[["code", "name"] + return_cols].head(top_n)
    return result.reset_index(drop=True)


@lru_cache(maxsize=32)
def get_fund_info(fund_code: str) -> dict:
    """获取单只基金的基本信息（带缓存）。"""
    _ensure_ak()
    try:
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        return df.to_dict() if hasattr(df, "to_dict") else {}
    except Exception:
        return {}
