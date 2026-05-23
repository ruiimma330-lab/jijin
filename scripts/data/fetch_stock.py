#!/usr/bin/env python3
"""股票数据获取工具 — 查看个股行情、财务指标、市场概况。

用法:
    python scripts/data/fetch_stock.py --code 600519        # 查看个股走势
    python scripts/data/fetch_stock.py --code 600519 --financial  # 财务数据
    python scripts/data/fetch_stock.py --market              # 市场总览
    python scripts/data/fetch_stock.py --sector 白酒          # 行业板块
"""

import argparse
import os
import sys
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import DataSourceError, _ensure_ak

try:
    import akshare as ak
except ImportError:
    ak = None


def get_stock_daily(
    code: str,
    days: int = 180,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """获取个股日线数据。

    Args:
        code: 股票代码，如 "600519"
        days: 获取天数
        adjust: 复权方式 — "qfq"(前复权), "hfq"(后复权), ""(不复权)

    Returns:
        DataFrame: date, open, close, high, low, volume, amount, turnover
    """
    _ensure_ak()
    start_date = (date.today() - timedelta(days=days + 30)).strftime("%Y%m%d")
    end_date = date.today().strftime("%Y%m%d")

    df = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    if df is None or df.empty:
        raise DataSourceError(f"未找到股票 {code} 的行情数据")

    df = df.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    col_order = [
        c
        for c in [
            "date",
            "open",
            "close",
            "high",
            "low",
            "volume",
            "amount",
            "turnover",
        ]
        if c in df.columns
    ]
    df = df[col_order].sort_values("date").tail(days)
    return df.reset_index(drop=True)


def get_stock_financial(code: str) -> dict:
    """获取个股主要财务指标。

    Returns:
        dict: PE, PB, ROE, 营收增速, 净利润增速, 总市值等
    """
    _ensure_ak()

    try:
        info = ak.stock_individual_info_em(symbol=code)

        pe = None
        pb = None
        total_mv = None
        for _, row in info.iterrows():
            if row["item"] == "市盈率-动态":
                pe = float(row["value"]) if row["value"] != "-" else None
            elif row["item"] == "市净率":
                pb = float(row["value"]) if row["value"] != "-" else None
            elif row["item"] == "总市值":
                val = row["value"]
                if "亿" in str(val):
                    total_mv = float(str(val).replace("亿", ""))
    except Exception:
        info = pd.DataFrame()

    try:
        fin = ak.stock_financial_analysis_indicator(symbol=code)
    except Exception:
        fin = pd.DataFrame()

    roe = None
    revenue_growth = None
    profit_growth = None
    if not fin.empty:
        # 不同版本的 akshare 字段可能不同
        for col in fin.columns:
            col_lower = str(col).lower()
            if "roe" in col_lower and "摊薄" in str(col):
                roe = float(fin[col].iloc[0]) if pd.notna(fin[col].iloc[0]) else None
            if "营收" in str(col) and "增长" in str(col):
                revenue_growth = (
                    float(fin[col].iloc[0]) if pd.notna(fin[col].iloc[0]) else None
                )
            if "净利润" in str(col) and "增长" in str(col):
                profit_growth = (
                    float(fin[col].iloc[0]) if pd.notna(fin[col].iloc[0]) else None
                )

    return {
        "code": code,
        "pe": round(pe, 2) if pe else None,
        "pb": round(pb, 2) if pb else None,
        "total_mv": round(total_mv, 2) if total_mv else None,
        "roe": round(roe, 2) if roe else None,
        "revenue_growth": round(revenue_growth, 2) if revenue_growth else None,
        "profit_growth": round(profit_growth, 2) if profit_growth else None,
    }


def get_market_overview() -> pd.DataFrame:
    """获取市场总览 — 主要指数行情、涨跌家数。"""
    _ensure_ak()

    print(f"\n{'=' * 70}")
    print(f"  A股市场总览 — {date.today()}")
    print(f"{'=' * 70}")

    indices = [
        ("sh000001", "上证指数"),
        ("sz399001", "深证成指"),
        ("sh000300", "沪深300"),
        ("sz399006", "创业板指"),
        ("sh000688", "科创50"),
        ("sz399673", "创业板50"),
    ]

    rows = []
    for symbol, name in indices:
        try:
            df = ak.stock_zh_index_daily_em(symbol=symbol)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                chg_pct = (
                    (float(latest["close"]) - float(latest["open"]))
                    / float(latest["open"])
                    * 100
                )
                rows.append(
                    {
                        "指数": name,
                        "最新": round(float(latest["close"]), 2),
                        "涨跌幅": f"{chg_pct:+.2f}%",
                        "成交额(亿)": round(float(latest.get("amount", 0)) / 1e8, 1),
                    }
                )
        except Exception:
            pass

    if rows:
        result = pd.DataFrame(rows)
        print(result.to_string(index=False))
    else:
        print("暂无指数数据")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def get_sector_list() -> pd.DataFrame:
    """获取行业板块行情。"""
    _ensure_ak()

    try:
        df = ak.stock_board_industry_name_em()
        df = df.rename(
            columns={
                "板块名称": "name",
                "最新价": "price",
                "涨跌幅": "change_pct",
                "总市值": "total_mv",
                "换手率": "turnover",
                "上涨家数": "up_count",
                "下跌家数": "down_count",
            }
        )
        cols = [
            c
            for c in [
                "name",
                "price",
                "change_pct",
                "turnover",
                "up_count",
                "down_count",
                "total_mv",
            ]
            if c in df.columns
        ]
        return df[cols].head(30)
    except Exception as e:
        raise DataSourceError(f"获取板块数据失败: {e}")


def get_sector_stocks(sector_name: str) -> pd.DataFrame:
    """获取行业板块的成分股。

    Args:
        sector_name: 行业名称，如 "白酒"、"新能源汽车"
    """
    _ensure_ak()

    try:
        df = ak.stock_board_industry_cons_em(symbol=sector_name)
        df = df.rename(
            columns={
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "涨跌幅": "change_pct",
                "市盈率-动态": "pe",
            }
        )
        cols = [
            c for c in ["code", "name", "price", "change_pct", "pe"] if c in df.columns
        ]
        return df[cols]
    except Exception as e:
        raise DataSourceError(f"获取板块成分股失败: {e}")


def show_stock_trend(code: str, days: int = 180):
    """展示个股走势和基本信息。"""
    print(f"\n{'=' * 70}")
    print(f"  个股走势 — {code}")
    print(f"{'=' * 70}")

    # 财务快照
    try:
        fin = get_stock_financial(code)
        if fin:
            items = []
            if fin["pe"]:
                items.append(f"PE={fin['pe']}")
            if fin["pb"]:
                items.append(f"PB={fin['pb']}")
            if fin["roe"]:
                items.append(f"ROE={fin['roe']}%")
            if fin["total_mv"]:
                items.append(f"市值={fin['total_mv']}亿")
            if fin["revenue_growth"]:
                items.append(f"营收增速={fin['revenue_growth']}%")
            if fin["profit_growth"]:
                items.append(f"利润增速={fin['profit_growth']}%")
            if items:
                print(f"  财务: {' | '.join(items)}")
    except Exception:
        pass

    # 走势数据
    try:
        df = get_stock_daily(code, days)
        latest = df.iloc[-1]
        first = df.iloc[0]
        change = (latest["close"] - first["close"]) / first["close"] * 100

        print(f"  期间: {df['date'].iloc[0].date()} ~ {latest['date'].date()}")
        print(f"  最新价: {latest['close']:.2f}  |  涨跌: {change:+.2f}%")

        if len(df) >= 20:
            ma20 = df["close"].rolling(20).mean().iloc[-1]
            ma60 = df["close"].rolling(60).mean().iloc[-1] if len(df) >= 60 else None
            print(f"  MA20: {ma20:.2f}", end="")
            if ma60 and pd.notna(ma60):
                trend = "上涨趋势" if ma20 > ma60 else "下跌趋势"
                print(f"  |  MA60: {ma60:.2f}  |  {trend}")
            else:
                print()

        print("\n  近10个交易日:")
        recent = df.tail(10)[["date", "close", "volume", "turnover"]].copy()
        recent["date"] = recent["date"].dt.date
        print(recent.to_string(index=False))

    except DataSourceError as e:
        print(f"  [ERR] {e}")


def main():
    parser = argparse.ArgumentParser(description="股票数据查询工具")
    parser.add_argument("--code", type=str, help="股票代码 (如 600519)")
    parser.add_argument("--days", type=int, default=180, help="查看天数")
    parser.add_argument("--financial", action="store_true", help="查看财务数据")
    parser.add_argument("--market", action="store_true", help="市场总览")
    parser.add_argument("--sector", type=str, help="行业板块名称")
    args = parser.parse_args()

    if args.market:
        get_market_overview()
        return

    if args.sector:
        print(f"\n{'=' * 70}")
        print(f"  行业板块 — {args.sector}")
        print(f"{'=' * 70}")
        try:
            stocks = get_sector_stocks(args.sector)
            print(stocks.head(20).to_string(index=False))
        except DataSourceError as e:
            print(f"  [ERR] {e}")
        return

    if args.code:
        if args.financial:
            print(f"\n{'=' * 70}")
            print(f"  财务数据 — {args.code}")
            print(f"{'=' * 70}")
            try:
                fin = get_stock_financial(args.code)
                for k, v in fin.items():
                    if v is not None:
                        print(f"  {k}: {v}")
            except Exception as e:
                print(f"  [ERR] {e}")
        else:
            show_stock_trend(args.code, args.days)
    else:
        # 无参数：显示市场总览
        get_market_overview()


if __name__ == "__main__":
    main()
