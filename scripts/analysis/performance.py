"""业绩归因分析 — CAPM alpha/beta、滚动分析、牛熊市表现、信息比率。

用法:
    python scripts/analysis/performance.py --code 110020 --benchmark 000300
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav, DataSourceError
from scripts.data.fetch_index import INDEX_MAP, PE_HISTORY

try:
    import akshare as ak
except ImportError:
    ak = None


def _get_benchmark_returns(benchmark_code: str) -> pd.Series:
    """获取指数日收益率作为基准。"""
    from datetime import date, timedelta

    end_date = date.today().strftime("%Y%m%d")
    start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")

    prefix = "sh" if benchmark_code.startswith("000") else "sz"
    df = ak.stock_zh_index_daily_em(symbol=f"{prefix}{benchmark_code}")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["bench_return"] = df["close"].pct_change()
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    return df.set_index("date")["bench_return"].dropna()


def capm_alpha_beta(
    fund_returns: pd.Series, benchmark_returns: pd.Series,
    rf_annual: float = 0.02,
) -> dict:
    """CAPM 模型计算 alpha 和 beta。

    Alpha = 基金实际收益 - CAPM 预期收益
    Beta = 基金对市场波动的敏感度
    """
    aligned = pd.DataFrame({
        "fund": fund_returns,
        "bench": benchmark_returns,
    }).dropna()

    if len(aligned) < 30:
        return {"alpha": None, "beta": None, "error": "数据不足(需30个交易日以上)"}

    rf_daily = rf_annual / 252

    slope, intercept, r_value, p_value, std_err = stats.linregress(
        aligned["bench"], aligned["fund"]
    )

    alpha_daily = intercept
    alpha_annual = alpha_daily * 252
    beta = slope
    r_squared = r_value ** 2

    annual_ret = aligned["fund"].mean() * 252
    annual_bench = aligned["bench"].mean() * 252
    expected_ret = rf_annual + beta * (annual_bench - rf_annual)

    return {
        "alpha_annual": round(alpha_annual * 100, 2),
        "alpha_daily_bp": round(alpha_daily * 10000, 2),
        "beta": round(beta, 2),
        "r_squared": round(r_squared, 2),
        "fund_return": round(annual_ret * 100, 2),
        "bench_return": round(annual_bench * 100, 2),
        "expected_return": round(expected_ret * 100, 2),
        "p_value": round(p_value, 4),
    }


def rolling_alpha_beta(
    fund_returns: pd.Series, benchmark_returns: pd.Series,
    window: int = 60,
) -> pd.DataFrame:
    """滚动窗口计算 alpha 和 beta。"""
    aligned = pd.DataFrame({
        "fund": fund_returns,
        "bench": benchmark_returns,
    }).dropna()

    if len(aligned) < window:
        return pd.DataFrame()

    rf_daily = 0.02 / 252

    results = []
    for i in range(window, len(aligned)):
        window_fund = aligned["fund"].iloc[i-window:i]
        window_bench = aligned["bench"].iloc[i-window:i]

        slope, intercept, r_value, p_value, _ = stats.linregress(
            window_bench, window_fund
        )

        results.append({
            "date": aligned.index[i],
            "alpha_daily": intercept,
            "beta": slope,
            "r_squared": r_value ** 2,
        })

    df = pd.DataFrame(results)
    df["alpha_annual"] = df["alpha_daily"] * 252 * 100
    return df


def information_ratio(
    fund_returns: pd.Series, benchmark_returns: pd.Series,
) -> float:
    """信息比率 — 主动管理带来的超额收益 / 跟踪误差。"""
    aligned = pd.DataFrame({
        "fund": fund_returns,
        "bench": benchmark_returns,
    }).dropna()

    excess = aligned["fund"] - aligned["bench"]
    if excess.std() == 0:
        return 0.0

    te = excess.std() * np.sqrt(252)
    ir = excess.mean() / excess.std() * np.sqrt(252)
    return {"information_ratio": round(ir, 2), "tracking_error": round(te * 100, 2)}


def tracking_error(
    fund_returns: pd.Series, benchmark_returns: pd.Series,
) -> float:
    """跟踪误差 — 基金收益与基准收益的偏离程度。"""
    aligned = pd.DataFrame({
        "fund": fund_returns,
        "bench": benchmark_returns,
    }).dropna()

    excess = aligned["fund"] - aligned["bench"]
    return round(excess.std() * np.sqrt(252) * 100, 2)


def bull_bear_analysis(
    fund_returns: pd.Series, benchmark_returns: pd.Series,
) -> dict:
    """分析基金在牛市和熊市中的表现差异。"""
    aligned = pd.DataFrame({
        "fund": fund_returns,
        "bench": benchmark_returns,
    }).dropna()

    median_bench = aligned["bench"].median()
    bull_mask = aligned["bench"] > median_bench
    bear_mask = aligned["bench"] <= median_bench

    bull_fund = aligned["fund"][bull_mask].mean() * 252 * 100 if bull_mask.sum() > 0 else None
    bull_bench = aligned["bench"][bull_mask].mean() * 252 * 100 if bull_mask.sum() > 0 else None
    bear_fund = aligned["fund"][bear_mask].mean() * 252 * 100 if bear_mask.sum() > 0 else None
    bear_bench = aligned["bench"][bear_mask].mean() * 252 * 100 if bear_mask.sum() > 0 else None

    upside_capture = None
    downside_capture = None
    if bull_bench is not None and bull_bench != 0:
        upside_capture = round(bull_fund / bull_bench * 100, 1)
    if bear_bench is not None and bear_bench != 0:
        downside_capture = round(bear_fund / bear_bench * 100, 1)

    return {
        "bull_fund_return": round(bull_fund, 2) if bull_fund else None,
        "bull_bench_return": round(bull_bench, 2) if bull_bench else None,
        "bear_fund_return": round(bear_fund, 2) if bear_fund else None,
        "bear_bench_return": round(bear_bench, 2) if bear_bench else None,
        "upside_capture": upside_capture,
        "downside_capture": downside_capture,
    }


def performance_report(fund_code: str, benchmark_code: str = "000300") -> dict:
    """生成完整的业绩归因报告。

    Args:
        fund_code: 基金代码
        benchmark_code: 基准指数代码，默认沪深300

    Returns:
        dict: 包含 alpha, beta, IR, TE, 牛熊分析等指标
    """
    nav_df = get_fund_nav(fund_code)
    nav_df["date"] = pd.to_datetime(nav_df["date"])
    fund_returns = nav_df.set_index("date")["daily_return"].dropna()

    bench_returns = _get_benchmark_returns(benchmark_code)

    capm = capm_alpha_beta(fund_returns, bench_returns)
    ir_data = information_ratio(fund_returns, bench_returns)
    te = tracking_error(fund_returns, bench_returns)
    bb = bull_bear_analysis(fund_returns, bench_returns)
    rolling = rolling_alpha_beta(fund_returns, bench_returns)

    benchmark_name = INDEX_MAP.get(benchmark_code, {}).get("name", benchmark_code)

    return {
        "fund_code": fund_code,
        "benchmark_code": benchmark_code,
        "benchmark_name": benchmark_name,
        **capm,
        "information_ratio": ir_data["information_ratio"],
        "tracking_error": ir_data["tracking_error"],
        "bull_bear": bb,
        "rolling": rolling,
    }


def main():
    parser = argparse.ArgumentParser(description="基金业绩归因分析")
    parser.add_argument("--code", type=str, default="110020", help="基金代码")
    parser.add_argument("--benchmark", type=str, default="000300", help="基准指数代码")
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  业绩归因分析")
    print(f"{'='*65}")

    try:
        report = performance_report(args.code, args.benchmark)
    except DataSourceError as e:
        print(f"  [ERR] {e}")
        return
    except Exception as e:
        print(f"  [ERR] 分析失败: {e}")
        return

    bm_name = report["benchmark_name"]
    print(f"  基金: {report['fund_code']}  |  基准: {bm_name} ({report['benchmark_code']})")

    print(f"\n[CHART] CAPM 归因:")
    if report.get("beta") is not None:
        print(f"  Alpha(年化): {report['alpha_annual']}% "
              f"({'超额收益' if report['alpha_annual'] > 0 else '跑输基准'})")
        print(f"  Beta: {report['beta']}  "
              f"({'激进' if report['beta'] > 1.1 else '保守' if report['beta'] < 0.9 else '与市场同步'})")
        print(f"  R²: {report['r_squared']}  "
              f"({'高拟合度' if report['r_squared'] > 0.7 else '拟合度低，Alpha意义有限'})")
        print(f"  基金年化收益: {report['fund_return']}%")
        print(f"  {bm_name}年化收益: {report['bench_return']}%")
        print(f"  CAPM预期收益: {report['expected_return']}%")
        print(f"  p值: {report['p_value']}  "
              f"({'统计显著' if report['p_value'] < 0.05 else '不显著，Alpha可能来自运气'})")
    else:
        print(f"  {report.get('error', '计算失败')}")

    print(f"\n[CHART] 主动管理能力:")
    print(f"  信息比率: {report['information_ratio']}  "
          f"({'优秀' if report['information_ratio'] > 0.5 else '良好' if report['information_ratio'] > 0 else '跑输'})")
    print(f"  跟踪误差: {report['tracking_error']}%  "
          f"({'积极管理' if report['tracking_error'] > 8 else '接近指数' if report['tracking_error'] < 3 else '适度偏离'})")

    bb = report["bull_bear"]
    if bb.get("upside_capture") is not None:
        print(f"\n[CHART] 牛熊市表现:")
        print(f"  上涨市: 基金 {bb['bull_fund_return']}%  |  基准 {bb['bull_bench_return']}%")
        print(f"  下跌市: 基金 {bb['bear_fund_return']}%  |  基准 {bb['bear_bench_return']}%")
        print(f"  上涨捕获率: {bb['upside_capture']}%  "
              f"({'涨时跟得上' if bb['upside_capture'] > 90 else '涨时跑输'})")
        print(f"  下跌捕获率: {bb['downside_capture']}%  "
              f"({'跌时跌得更少' if bb['downside_capture'] < 100 else '跌时跌得更多'})")

    rolling = report.get("rolling")
    if rolling is not None and not rolling.empty:
        latest_alpha = rolling["alpha_annual"].iloc[-1]
        latest_beta = rolling["beta"].iloc[-1]
        alpha_change = latest_alpha - rolling["alpha_annual"].mean()
        beta_change = latest_beta - rolling["beta"].mean()
        print(f"\n[CHART] 滚动分析 (最新 vs 均值):")
        print(f"  当前Alpha: {latest_alpha:.1f}%  (偏离均值 {alpha_change:+.1f}%)")
        print(f"  当前Beta: {latest_beta:.2f}  (偏离均值 {beta_change:+.2f})")
        print(f"  滚动窗口: 60天")

    print(f"\n[TIP] 解读指南:")
    print(f"  1. Alpha>0 且显著 → 基金经理有选股/择时能力")
    print(f"  2. Beta<1 → 防御型，熊市可能跌得少")
    print(f"  3. IR>0.5 → 主动管理能力优秀")
    print(f"  4. 上涨捕获率>100且下跌捕获率<100 → 理想的主动基金")
    print(f"  5. R²过低时Alpha不可靠，改用IR评估")


if __name__ == "__main__":
    main()
