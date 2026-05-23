"""风险分析工具 — 波动率、最大回撤、VaR、风险归因。

用法:
    python scripts/analysis/risk.py --code 110020
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav


def max_drawdown(nav: pd.Series) -> dict:
    """计算最大回撤及相关指标。

    Returns:
        dict: max_drawdown(最大回撤%), max_dd_start(开始日期),
              max_dd_end(结束日期), max_dd_recovery(恢复天数),
              avg_drawdown(平均回撤%), drawdown_count(回撤次数)
    """
    rolling_max = nav.cummax()
    drawdown = (nav - rolling_max) / rolling_max

    max_dd = drawdown.min()

    max_dd_end_idx = drawdown.idxmin()
    max_dd_start_idx = rolling_max[:max_dd_end_idx][
        rolling_max[:max_dd_end_idx] == rolling_max[max_dd_end_idx]
    ].index[-1]

    recovery_mask = drawdown.loc[max_dd_end_idx:] == 0
    recovery_days = 0
    if recovery_mask.any():
        recovery_date = drawdown.loc[max_dd_end_idx:][recovery_mask].index[0]
        recovery_days = (recovery_date - max_dd_end_idx).days

    dd_periods = []
    in_dd = False
    dd_start = None
    for i, val in drawdown.items():
        if val < -0.001 and not in_dd:
            in_dd = True
            dd_start = i
        elif val >= -0.001 and in_dd:
            in_dd = False
            dd_periods.append((dd_start, i, drawdown.loc[dd_start:i].min()))

    avg_dd = np.mean([d[2] for d in dd_periods]) if dd_periods else 0

    return {
        "max_drawdown": round(max_dd * 100, 2),
        "max_dd_start": max_dd_start_idx.date(),
        "max_dd_end": max_dd_end_idx.date(),
        "recovery_days": recovery_days,
        "avg_drawdown": round(avg_dd * 100, 2),
        "drawdown_count": len(dd_periods),
    }


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """历史模拟法计算 Value at Risk。

    例如 VaR(95%) = -2% 意味着：有 95% 的把握单日亏损不超过 2%。
    """
    return np.percentile(returns.dropna(), (1 - confidence) * 100)


def cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """Conditional VaR — 超过 VaR 那部分损失的平均值。"""
    var = historical_var(returns, confidence)
    tail = returns.dropna()[returns.dropna() <= var]
    return tail.mean() if len(tail) > 0 else var


def rolling_risk(nav_df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """计算滚动风险指标。"""
    df = nav_df.copy()
    df["rolling_vol"] = df["daily_return"].rolling(window).std() * np.sqrt(252) * 100
    df["rolling_max_dd"] = (
        df["nav"].rolling(window).apply(lambda x: (x / x.cummax() - 1).min() * 100)
    )
    return df


def risk_report(fund_code: str) -> dict:
    """生成完整的风险评估报告。"""
    nav_df = get_fund_nav(fund_code)
    returns = nav_df["daily_return"].dropna()

    if returns.empty:
        return {"error": "数据不足"}

    nav_series = nav_df.set_index("date")["nav"]
    dd_info = max_drawdown(nav_series)

    annual_vol = returns.std() * np.sqrt(252)

    skew = stats.skew(returns.dropna())
    kurt = stats.kurtosis(returns.dropna())

    var_95 = historical_var(returns, 0.95)
    var_99 = historical_var(returns, 0.99)
    cvar_95 = cvar(returns, 0.95)

    return {
        "annual_volatility": round(annual_vol * 100, 2),
        "daily_volatility": round(returns.std() * 100, 2),
        "skewness": round(skew, 2),
        "kurtosis": round(kurt, 2),
        "VaR_95": round(var_95 * 100, 2),
        "VaR_99": round(var_99 * 100, 2),
        "CVaR_95": round(cvar_95 * 100, 2),
        **dd_info,
    }


def main():
    parser = argparse.ArgumentParser(description="基金风险分析工具")
    parser.add_argument("--code", type=str, default="110020", help="基金代码")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  风险评估报告 — {args.code}")
    print(f"{'=' * 60}")

    try:
        report = risk_report(args.code)

        if "error" in report:
            print(f"  [ERR] {report['error']}")
            return

        print("\n[CHART] 波动率指标:")
        print(f"  年化波动率: {report['annual_volatility']}%")
        print(f"  日均波动率: {report['daily_volatility']}%")
        print(
            f"  偏度: {report['skewness']}  {'(左偏=暴跌风险)' if report['skewness'] < -0.5 else ''}"
        )
        print(
            f"  峰度: {report['kurtosis']}  {'(尖峰=极端值风险)' if report['kurtosis'] > 2 else ''}"
        )

        print("\n[CHART] 回撤指标:")
        print(f"  最大回撤: {report['max_drawdown']}%")
        print(f"  回撤区间: {report['max_dd_start']} ~ {report['max_dd_end']}")
        print(f"  恢复天数: {report['recovery_days']} 天")
        print(f"  平均回撤: {report['avg_drawdown']}%")
        print(f"  回撤次数: {report['drawdown_count']}")

        print("\n[WARN] 风险价值 (VaR):")
        print(f"  VaR(95%): {report['VaR_95']}%  — 95%把握单日亏损不超过此值")
        print(f"  VaR(99%): {report['VaR_99']}%  — 99%把握单日亏损不超过此值")
        print(f"  CVaR(95%): {report['CVaR_95']}% — 极端情况下的平均亏损")

        print("\n[TIP] 解读:")
        vol = report["annual_volatility"]
        if vol < 10:
            print(f"  低波动 ({vol}%)，适合保守型投资者")
        elif vol < 20:
            print(f"  中波动 ({vol}%)，适合稳健型投资者")
        else:
            print(f"  高波动 ({vol}%)，适合进取型投资者")

        dd = abs(report["max_drawdown"])
        print(f"  最大回撤 {dd}% — 每投1万元，最坏情况亏{int(dd * 100)}元")

    except Exception as e:
        print(f"  [ERR] 分析失败: {e}")


if __name__ == "__main__":
    main()
