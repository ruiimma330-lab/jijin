#!/usr/bin/env python3
"""指数数据获取工具 — 查看指数行情和估值。

用法:
    python scripts/data/fetch_index.py                    # 查看主要指数估值
    python scripts/data/fetch_index.py --index 000300     # 查看沪深300走势
    python scripts/data/fetch_index.py --index 000905     # 查看中证500走势
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

INDEX_MAP = {
    "000300": {"name": "沪深300", "code": "000300"},
    "000905": {"name": "中证500", "code": "000905"},
    "399006": {"name": "创业板指", "code": "399006"},
    "000688": {"name": "科创50", "code": "000688"},
    "000016": {"name": "上证50", "code": "000016"},
    "399673": {"name": "创业板50", "code": "399673"},
}

PE_HISTORY = {
    "000300": {"min": 8.0, "max": 48.0, "median": 13.5},
    "000905": {"min": 15.0, "max": 92.0, "median": 31.0},
    "399006": {"min": 27.0, "max": 137.0, "median": 52.0},
    "000688": {"min": 30.0, "max": 105.0, "median": 55.0},
    "000016": {"min": 6.5, "max": 34.0, "median": 11.0},
}


def _estimate_pe_percentile(current_pe: float, history: dict) -> float:
    """用历史极值估算当前 PE 所处的分位。"""
    if current_pe <= history["min"]:
        return 0.0
    if current_pe >= history["max"]:
        return 100.0
    percentile = (
        (current_pe - history["min"])
        / (history["max"] - history["min"])
        * 100
    )
    return round(percentile, 1)


def _get_index_valuation() -> pd.DataFrame:
    """获取主要指数的当前估值数据。"""
    _ensure_ak()
    try:
        df = ak.index_value_hist_funddb()
    except Exception:
        try:
            df = ak.stock_zh_index_value_csindex(symbol="000300")
        except Exception as e:
            raise DataSourceError(f"获取指数估值失败: {e}")

    return df


def show_valuation():
    """展示主要指数估值一览。"""
    print(f"\n{'='*70}")
    print("  主要指数估值一览")
    print(f"{'='*70}")

    rows = []
    for index_code, info in INDEX_MAP.items():
        try:
            _ensure_ak()
            df = ak.index_value_hist_funddb()
            latest = df[df["指数代码"] == index_code]
            if not latest.empty:
                pe = float(latest["市盈率"].values[0])
            else:
                pe = None
        except Exception:
            pe = None

        if pe is not None and index_code in PE_HISTORY:
            pct = _estimate_pe_percentile(pe, PE_HISTORY[index_code])
            level = (
                "低估" if pct < 30 else ("高估" if pct > 70 else "合理")
            )
            rows.append({
                "指数": info["name"],
                "代码": index_code,
                "当前PE": round(pe, 2),
                "历史中位数": PE_HISTORY[index_code]["median"],
                "分位": f"{pct}%",
                "状态": level,
            })

    if not rows:
        print("暂无指数估值数据，请检查网络或数据源")
        return

    result = pd.DataFrame(rows)
    print(result.to_string(index=False))


def show_index_trend(index_code: str, days: int = 180):
    """展示单只指数的近期走势。"""
    info = INDEX_MAP.get(index_code, {"name": index_code})
    name = info["name"] if isinstance(info, dict) else index_code

    print(f"\n{'='*70}")
    print(f"  {name} ({index_code}) 近期走势")
    print(f"{'='*70}")

    try:
        _ensure_ak()
        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
        df = ak.stock_zh_index_daily_em(
            symbol=f"sh{index_code}" if index_code.startswith("000")
            else f"sz{index_code}"
        )
        if df is None or df.empty:
            print("暂无数据")
            return

        df = df.rename(columns={
            "date": "date", "close": "close", "open": "open",
            "high": "high", "low": "low", "volume": "volume",
        })
        available = [c for c in ["date", "close", "open", "high", "low"]
                     if c in df.columns]

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

        latest_close = df["close"].iloc[-1] if "close" in df.columns else None
        if latest_close:
            start_close = df["close"].iloc[0]
            change = (latest_close - start_close) / start_close * 100
            print(f"期间: {start_date} ~ {end_date}")
            print(f"最新: {latest_close:.2f}  |  涨跌: {change:+.2f}%")

        if len(df) >= 2:
            df["ma20"] = df["close"].rolling(20).mean()
            df["ma60"] = df["close"].rolling(60).mean()
            latest_ma20 = df["ma20"].iloc[-1]
            latest_ma60 = df["ma60"].iloc[-1]
            if pd.notna(latest_ma20) and pd.notna(latest_ma60):
                trend = "上涨趋势" if latest_ma20 > latest_ma60 else "下跌趋势"
                print(f"MA20: {latest_ma20:.2f}  |  MA60: {latest_ma60:.2f}  |  {trend}")

        print(f"\n近20个交易日:")
        recent = df.tail(20).copy()
        cols = [c for c in ["date", "close", "volume"] if c in recent.columns]
        if "date" in recent.columns:
            recent["date"] = recent["date"].dt.date
        print(recent[cols].to_string(index=False))

    except Exception as e:
        print(f"数据获取失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="指数数据查询工具")
    parser.add_argument("--index", type=str, help="指数代码 (如 000300)")
    parser.add_argument(
        "--days", type=int, default=180, help="查看天数 (默认 180)"
    )
    args = parser.parse_args()

    if args.index:
        show_index_trend(args.index, args.days)
    else:
        show_valuation()


if __name__ == "__main__":
    main()
