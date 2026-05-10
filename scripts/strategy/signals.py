"""市场择时信号 — 基于估值、均线、市场情绪的买卖信号。

用法:
    python scripts/strategy/signals.py --code 110020
    python scripts/strategy/signals.py --index 000300
"""

import argparse
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav, DataSourceError
from scripts.data.fetch_index import _get_index_valuation, PE_HISTORY, _estimate_pe_percentile

try:
    import akshare as ak
except ImportError:
    ak = None


def pe_signal(index_code: str) -> dict:
    """基于 PE 估值分位的择时信号。

    PE 分位 < 30% → 低估，可以多买
    PE 分位 30-70% → 合理，正常买入
    PE 分位 > 70% → 高估，减少或暂停
    """
    history = PE_HISTORY.get(index_code)
    if not history:
        return {"signal": "N/A", "reason": f"指数 {index_code} 无历史PE数据"}

    try:
        df = ak.index_value_hist_funddb()
        latest = df[df["指数代码"] == index_code]
        if latest.empty:
            return {"signal": "N/A", "reason": "无法获取当前PE"}

        current_pe = float(latest["市盈率"].values[0])
        percentile = _estimate_pe_percentile(current_pe, history)

        if percentile < 30:
            signal = "BUY"
            action = "低估区间，可加大定投(1.5倍)"
        elif percentile > 70:
            signal = "SELL"
            action = "高估区间，减少定投(0.5倍)或暂停"
        else:
            signal = "HOLD"
            action = "合理估值，正常定投"

        return {
            "signal": signal,
            "current_pe": round(current_pe, 2),
            "percentile": percentile,
            "median_pe": history["median"],
            "action": action,
        }
    except Exception as e:
        return {"signal": "N/A", "reason": str(e)}


def ma_signal(nav_df: pd.DataFrame) -> dict:
    """基于均线交叉的择时信号。

    MA20 > MA60 → 短期趋势向上，可持有
    MA20 < MA60 → 短期趋势向下，谨慎
    """
    if len(nav_df) < 60:
        return {"signal": "N/A", "reason": "数据不足(需60个交易日以上)"}

    close = nav_df["nav"]
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    latest_ma20 = ma20.iloc[-1]
    latest_ma60 = ma60.iloc[-1]
    prev_ma20 = ma20.iloc[-2]
    prev_ma60 = ma60.iloc[-2]
    current_nav = close.iloc[-1]

    if pd.isna(latest_ma60):
        return {"signal": "N/A", "reason": "MA60 数据不足"}

    if latest_ma20 > latest_ma60 and prev_ma20 <= prev_ma60:
        signal = "BUY"
        detail = "金叉 — MA20 上穿 MA60，短期趋势转好"
    elif latest_ma20 < latest_ma60 and prev_ma20 >= prev_ma60:
        signal = "SELL"
        detail = "死叉 — MA20 下穿 MA60，短期趋势转差"
    elif latest_ma20 > latest_ma60:
        signal = "HOLD"
        detail = "多头排列 — 短期在长期之上，趋势向好"
    else:
        signal = "WAIT"
        detail = "空头排列 — 短期在长期之下，等待方向明确"

    return {
        "signal": signal,
        "current_nav": round(current_nav, 4),
        "ma20": round(latest_ma20, 4),
        "ma60": round(latest_ma60, 4),
        "gap_pct": round((latest_ma20 - latest_ma60) / latest_ma60 * 100, 2),
        "detail": detail,
    }


def rsi_signal(nav_df: pd.DataFrame, window: int = 14) -> dict:
    """基于 RSI 的超买超卖信号。"""
    from scripts.utils.indicators import rsi

    if len(nav_df) < window + 2:
        return {"signal": "N/A", "reason": f"数据不足(需{window+2}个交易日以上)"}

    rsi_series = rsi(nav_df["nav"], window)
    current_rsi = rsi_series.iloc[-1]

    if pd.isna(current_rsi):
        return {"signal": "N/A", "reason": "RSI 计算失败"}

    if current_rsi < 30:
        signal = "BUY"
        action = "超卖区间，可能反弹"
    elif current_rsi > 70:
        signal = "SELL"
        action = "超买区间，可能回调"
    else:
        signal = "HOLD"
        action = "正常区间"

    return {
        "signal": signal,
        "rsi": round(float(current_rsi), 1),
        "action": action,
    }


def composite_signal(fund_code: str = None, index_code: str = "000300") -> dict:
    """综合多种信号给出最终建议。"""
    signals = {}

    if index_code:
        pe = pe_signal(index_code)
        signals["PE估值"] = pe

    if fund_code:
        try:
            nav_df = get_fund_nav(fund_code)
            signals["均线"] = ma_signal(nav_df)
            signals["RSI"] = rsi_signal(nav_df)
        except DataSourceError:
            pass

    buy_count = sum(1 for s in signals.values() if s.get("signal") == "BUY")
    sell_count = sum(1 for s in signals.values() if s.get("signal") == "SELL")
    hold_count = sum(1 for s in signals.values() if s.get("signal") == "HOLD")

    if buy_count >= 2:
        overall = "BUY"
        suggestion = "多个信号指向低估/超卖，可考虑加大定投"
    elif sell_count >= 2:
        overall = "SELL"
        suggestion = "多个信号指向高估/超买，建议减少定投或暂停"
    else:
        overall = "HOLD"
        suggestion = "信号中性，维持正常定投节奏"

    return {
        "overall_signal": overall,
        "suggestion": suggestion,
        "signals": signals,
    }


def main():
    parser = argparse.ArgumentParser(description="市场择时信号")
    parser.add_argument("--code", type=str, help="基金代码(用于均线/RSI)")
    parser.add_argument("--index", type=str, default="000300",
                        help="指数代码(用于PE估值)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  市场择时信号")
    print(f"{'='*60}\n")

    result = composite_signal(args.code, args.index)

    print(f"[SIG] 综合信号: {result['overall_signal']}")
    print(f"[TIP] 建议: {result['suggestion']}")

    for name, s in result["signals"].items():
        signal = s.get("signal", "?")
        tag = {"BUY": "[BUY]", "SELL": "[SELL]", "HOLD": "[HOLD]", "WAIT": "[WAIT]"}.get(
            signal, "[?]"
        )
        print(f"\n{tag} [{name}]: {signal}")
        for k, v in s.items():
            if k != "signal":
                print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
