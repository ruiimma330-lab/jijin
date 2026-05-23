"""策略回测引擎 — 支持定投、一次性投资、网格交易。

用法:
    python scripts/strategy/backtest.py --code 110020
    python scripts/strategy/backtest.py --code 110020 --strategy dca
    python scripts/strategy/backtest.py --code 110020 --strategy lump
    python scripts/strategy/backtest.py --code 110020 --strategy grid
"""

import argparse
import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav, DataSourceError


@dataclass(frozen=True)
class BacktestResult:
    """回测结果（不可变）。"""

    strategy: str
    fund_code: str
    total_invested: float
    final_value: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    invest_dates: list = field(repr=False)
    values: list = field(repr=False)


def _compute_metrics(
    nav_df: pd.DataFrame,
    cashflows: pd.DataFrame,
    final_shares: float,
    final_cash: float = 0.0,
) -> dict:
    """从回测数据计算绩效指标。"""
    total_invested = cashflows["amount"].sum()
    if total_invested == 0:
        return {
            "total_invested": 0,
            "final_value": 0,
            "total_return": 0,
            "annual_return": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
        }

    final_nav = nav_df["nav"].iloc[-1]
    final_value = final_shares * final_nav + final_cash
    gross_invested = cashflows.loc[cashflows["amount"] > 0, "amount"].sum()
    total_return = (final_value - gross_invested) / gross_invested * 100

    nav = nav_df.set_index("date")["nav"]
    cf_sorted = cashflows.sort_values("date")
    cf_records = list(cf_sorted.itertuples(index=False, name=None))
    n_cf = len(cf_records)

    values = []
    shares = 0
    cf_idx = 0
    for d in nav.index:
        while cf_idx < n_cf and cf_records[cf_idx][0] <= d:
            shares += cf_records[cf_idx][1] / nav.loc[d]
            cf_idx += 1
        values.append(shares * nav.loc[d])

    val_series = pd.Series(values, index=nav.index)
    daily_ret = val_series.pct_change().dropna()

    days = (nav.index[-1] - nav.index[0]).days
    ann_ret = (1 + total_return / 100) ** (365 / days) - 1 if days > 0 else 0

    dd = (val_series / val_series.cummax() - 1).min() * 100
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0

    return {
        "total_invested": round(total_invested, 2),
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 2),
        "annual_return": round(ann_ret * 100, 2),
        "max_drawdown": round(dd, 2),
        "sharpe_ratio": round(sharpe, 2),
    }


def backtest_dca(
    nav_df: pd.DataFrame,
    amount: float = 1000,
    frequency: str = "monthly",
) -> BacktestResult:
    """定投策略回测 — 固定时间、固定金额买入。

    Args:
        nav_df: 净值数据
        amount: 每次定投金额
        frequency: 定投频率 "weekly" | "biweekly" | "monthly"
    """
    freq_days = {"weekly": 7, "biweekly": 14, "monthly": 30}
    interval = freq_days.get(frequency, 30)

    dates = nav_df["date"].tolist()
    invest_dates = [dates[0]]
    last_date = dates[0]
    for d in dates[1:]:
        if (d - last_date).days >= interval:
            invest_dates.append(d)
            last_date = d

    cashflows = []
    shares = 0
    nav_map = nav_df.set_index("date")["nav"]

    for d in invest_dates:
        nav_at_date = nav_map.loc[d]
        shares += amount / nav_at_date
        cashflows.append({"date": d, "amount": amount})

    cashflows_df = pd.DataFrame(cashflows)
    metrics = _compute_metrics(nav_df, cashflows_df, shares)

    return BacktestResult(
        strategy=f"定投({frequency})",
        fund_code="",
        invest_dates=invest_dates,
        values=[],
        **metrics,
    )


def backtest_lump(nav_df: pd.DataFrame, amount: float = 10000) -> BacktestResult:
    """一次性投资回测 — 期初全仓买入。"""
    first_nav = nav_df["nav"].iloc[0]
    shares = amount / first_nav
    cashflows_df = pd.DataFrame([{"date": nav_df["date"].iloc[0], "amount": amount}])
    metrics = _compute_metrics(nav_df, cashflows_df, shares)

    return BacktestResult(
        strategy="一次性投资",
        fund_code="",
        invest_dates=[nav_df["date"].iloc[0]],
        values=[],
        **metrics,
    )


def backtest_grid(
    nav_df: pd.DataFrame,
    initial_amount: float = 10000,
    grid_pct: float = 5.0,
) -> BacktestResult:
    """网格交易回测 — 跌了买，涨了卖。

    Args:
        nav_df: 净值数据
        initial_amount: 初始投入
        grid_pct: 网格间距(%)
    """
    nav = nav_df.set_index("date")["nav"]
    grid_step = grid_pct / 100

    base_nav = nav.iloc[0]
    cash = initial_amount / 2
    shares = initial_amount / 2 / base_nav

    buy_levels = [base_nav * (1 - grid_step * (i + 1)) for i in range(10)]
    buy_used = {lvl: False for lvl in buy_levels}
    sell_levels = [base_nav * (1 + grid_step * (i + 1)) for i in range(10)]
    sell_used = {lvl: False for lvl in sell_levels}
    grid_unit = initial_amount * grid_step / 100
    pending_sells = []

    cashflows = [{"date": nav.index[0], "amount": initial_amount / 2}]

    for d in nav.index[1:]:
        current_nav = nav.loc[d]

        for buy_price, held_shares in list(pending_sells):
            sell_target = buy_price * (1 + 2 * grid_step)
            if current_nav >= sell_target:
                sell_value = held_shares * current_nav
                shares -= held_shares
                cash += sell_value
                cashflows.append({"date": d, "amount": -sell_value})
                pending_sells.remove((buy_price, held_shares))

        for lvl in buy_levels:
            if current_nav <= lvl and not buy_used[lvl]:
                if cash >= grid_unit:
                    bought = grid_unit / current_nav
                    shares += bought
                    cash -= grid_unit
                    buy_used[lvl] = True
                    pending_sells.append((lvl, bought))
                    cashflows.append({"date": d, "amount": grid_unit})

        for lvl in sell_levels:
            if current_nav >= lvl and not sell_used[lvl]:
                if shares * current_nav >= grid_unit:
                    sold = grid_unit / current_nav
                    shares -= sold
                    cash += grid_unit
                    sell_used[lvl] = True
                    cashflows.append({"date": d, "amount": -grid_unit})

    cashflows_df = (
        pd.DataFrame(cashflows)
        if cashflows
        else pd.DataFrame([{"date": nav.index[0], "amount": 0}])
    )
    metrics = _compute_metrics(nav_df, cashflows_df, shares, final_cash=cash)

    return BacktestResult(
        strategy=f"网格交易(间距{grid_pct}%)",
        fund_code="",
        invest_dates=[],
        values=[],
        **metrics,
    )


def compare_strategies(
    fund_code: str,
    amount: float = 10000,
    monthly_amount: float = 1000,
) -> None:
    """对比多种策略在同一只基金上的表现。"""
    print(f"\n{'=' * 80}")
    print(f"  策略回测对比 — 基金 {fund_code}")
    print(f"{'=' * 80}")

    try:
        nav_df = get_fund_nav(fund_code)
    except DataSourceError as e:
        print(f"  [ERR] {e}")
        return

    if nav_df.empty:
        print("  [ERR] 无数据")
        return

    date_range = f"{nav_df['date'].min().date()} ~ {nav_df['date'].max().date()}"
    print(f"  数据范围: {date_range}\n")

    results = []

    r1 = backtest_lump(nav_df, amount)
    results.append(r1)

    r2 = backtest_dca(nav_df, monthly_amount, "monthly")
    results.append(r2)

    r3 = backtest_dca(nav_df, monthly_amount / 4, "weekly")
    results.append(r3)

    print(
        f"  {'策略':<20} {'总投入':>10} {'最终资产':>12} "
        f"{'总收益':>8} {'年化':>8} {'最大回撤':>8} {'夏普':>6}"
    )
    print(f"  {'-' * 76}")

    for r in results:
        print(
            f"  {r.strategy:<20} {r.total_invested:>10,.0f} "
            f"{r.final_value:>12,.0f} {r.total_return:>7.1f}% "
            f"{r.annual_return:>7.1f}% {r.max_drawdown:>7.1f}% "
            f"{r.sharpe_ratio:>6.2f}"
        )

    print("\n  [TIP] 分析:")
    best = max(results, key=lambda x: x.total_return)
    print(f"  总收益最高: {best.strategy} ({best.total_return:.1f}%)")

    best_sharpe = max(results, key=lambda x: x.sharpe_ratio)
    print(
        f"  风险调整后最佳: {best_sharpe.strategy} (夏普 {best_sharpe.sharpe_ratio:.2f})"
    )


def main():
    parser = argparse.ArgumentParser(description="基金策略回测引擎")
    parser.add_argument("--code", type=str, default="110020", help="基金代码")
    parser.add_argument(
        "--strategy",
        type=str,
        default="compare",
        choices=["compare", "dca", "lump", "grid"],
        help="策略类型 (默认 compare 对比全部)",
    )
    parser.add_argument("--amount", type=float, default=10000, help="一次性投入金额")
    parser.add_argument("--monthly", type=float, default=1000, help="每月定投金额")
    parser.add_argument("--grid-pct", type=float, default=5.0, help="网格间距(%)")
    args = parser.parse_args()

    if args.strategy == "compare":
        compare_strategies(args.code, args.amount, args.monthly)
        return

    try:
        nav_df = get_fund_nav(args.code)
    except DataSourceError as e:
        print(f"[ERR] {e}")
        return

    if nav_df.empty:
        print("无数据")
        return

    if args.strategy == "dca":
        result = backtest_dca(nav_df, args.monthly, "monthly")
    elif args.strategy == "lump":
        result = backtest_lump(nav_df, args.amount)
    elif args.strategy == "grid":
        result = backtest_grid(nav_df, args.amount, args.grid_pct)
    else:
        print("未知策略")
        return

    print(f"\n  [CHART] {result.strategy} 回测结果:")
    print(f"  总投入: {result.total_invested:,.0f}")
    print(f"  最终资产: {result.final_value:,.0f}")
    print(f"  总收益率: {result.total_return:.1f}%")
    print(f"  年化收益率: {result.annual_return:.1f}%")
    print(f"  最大回撤: {result.max_drawdown:.1f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")


if __name__ == "__main__":
    main()
