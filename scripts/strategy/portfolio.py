"""投资组合优化 — 均值方差优化、风险平价、有效前沿。

用法:
    python scripts/strategy/portfolio.py --codes 110020,001632,050027
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav, DataSourceError


def portfolio_returns(
    fund_codes: list[str],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """获取多只基金的日收益率矩阵。

    Returns:
        returns_df: 日收益率 DataFrame
        mean_returns: 年化平均收益 (array)
        cov_matrix: 年化协方差矩阵
    """
    all_returns = {}
    for code in fund_codes:
        try:
            nav_df = get_fund_nav(code)
            nav_df["date"] = pd.to_datetime(nav_df["date"])
            returns = nav_df.set_index("date")["daily_return"].dropna()
            if len(returns) > 0:
                all_returns[code] = returns
        except DataSourceError:
            print(f"  [WARN] 跳过 {code} (无数据)")

    if len(all_returns) < 2:
        raise ValueError("至少需要2只有效基金")

    returns_df = pd.DataFrame(all_returns).dropna()
    mean_returns = returns_df.mean().to_numpy() * 252
    cov_matrix = returns_df.cov().to_numpy() * 252

    return returns_df, mean_returns, cov_matrix


def portfolio_metrics(
    weights: np.ndarray, mean_returns: np.ndarray, cov_matrix: np.ndarray,
    rf: float = 0.02,
) -> tuple[float, float, float]:
    """计算组合的收益、风险、夏普比率。

    Returns:
        (年化收益, 年化波动率, 夏普比率)
    """
    port_return = np.dot(weights, mean_returns)
    port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
    sharpe = (port_return - rf) / port_vol if port_vol > 0 else 0
    return port_return, port_vol, sharpe


def max_sharpe_optimize(
    mean_returns: np.ndarray, cov_matrix: np.ndarray, rf: float = 0.02,
) -> tuple[np.ndarray, float, float, float]:
    """最大化夏普比率 — 均值方差优化。

    Returns:
        (最优权重, 年化收益, 年化波动率, 夏普比率)
    """
    n = len(mean_returns)

    def neg_sharpe(w):
        ret, vol, _ = portfolio_metrics(w, mean_returns, cov_matrix, rf)
        sharpe = (ret - rf) / vol if vol > 0 else -999
        return -sharpe

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.05, 0.50) for _ in range(n)]
    x0 = np.array([1/n] * n)

    result = minimize(
        neg_sharpe, x0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": 5000, "ftol": 1e-10},
    )

    if not result.success:
        weights = x0
    else:
        weights = result.x / result.x.sum()

    ret, vol, sharpe = portfolio_metrics(weights, mean_returns, cov_matrix, rf)
    return weights, ret, vol, sharpe


def risk_parity_optimize(
    cov_matrix: np.ndarray,
) -> tuple[np.ndarray, float, float, float]:
    """风险平价优化 — 每个资产贡献相同的风险。

    Returns:
        (权重, 年化收益, 年化波动率, 夏普比率)
    """
    n = len(cov_matrix)

    def risk_concentration(w):
        port_vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
        marginal_risk = np.dot(cov_matrix, w)
        risk_contrib = w * marginal_risk / port_vol
        target = port_vol / n
        return np.sum((risk_contrib - target) ** 2)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.01, 1.0) for _ in range(n)]
    x0 = np.array([1/n] * n)

    result = minimize(
        risk_concentration, x0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": 5000},
    )

    weights = result.x / result.x.sum() if result.success else x0

    mean_returns = np.zeros(n)
    ret, vol, sharpe = portfolio_metrics(weights, mean_returns, cov_matrix)
    return weights, ret, vol, sharpe


def min_variance_optimize(cov_matrix: np.ndarray) -> tuple[np.ndarray, float, float, float]:
    """最小方差优化 — 追求最稳的组合。"""
    n = len(cov_matrix)

    def port_vol(w):
        return np.sqrt(np.dot(w, np.dot(cov_matrix, w)))

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.05, 0.50) for _ in range(n)]
    x0 = np.array([1/n] * n)

    result = minimize(port_vol, x0, method="SLSQP",
                      bounds=bounds, constraints=constraints)

    weights = result.x / result.x.sum() if result.success else x0
    mean_returns = np.zeros(n)
    ret, vol, sharpe = portfolio_metrics(weights, mean_returns, cov_matrix)
    return weights, ret, vol, sharpe


def efficient_frontier(
    mean_returns: np.ndarray, cov_matrix: np.ndarray,
    points: int = 50,
) -> pd.DataFrame:
    """计算有效前沿上的样本点。"""
    n = len(mean_returns)
    target_returns = np.linspace(
        mean_returns.min() * 0.5, mean_returns.max() * 1.2, points,
    )

    frontier = []
    for target in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w: np.dot(w, mean_returns) - target},
        ]
        bounds = [(0.0, 1.0) for _ in range(n)]
        x0 = np.array([1/n] * n)

        def port_vol_fn(w):
            return np.sqrt(np.dot(w, np.dot(cov_matrix, w)))

        result = minimize(port_vol_fn, x0, method="SLSQP",
                          bounds=bounds, constraints=constraints)
        if result.success:
            vol = np.sqrt(np.dot(result.x, np.dot(cov_matrix, result.x)))
            frontier.append({
                "return": round(target * 100, 2),
                "volatility": round(vol * 100, 2),
                "sharpe": round((target - 0.02) / vol, 2) if vol > 0 else 0,
            })

    return pd.DataFrame(frontier)


def optimize_portfolio(fund_codes: list[str]) -> dict:
    """对一组基金进行全面的组合优化分析。"""
    returns_df, mean_returns, cov_matrix = portfolio_returns(fund_codes)

    results = {}

    w, ret, vol, sharpe = max_sharpe_optimize(mean_returns, cov_matrix)
    results["最大夏普"] = {
        "weights": w, "return": ret, "volatility": vol, "sharpe": sharpe,
    }

    w, ret, vol, sharpe = min_variance_optimize(cov_matrix)
    results["最小方差"] = {
        "weights": w, "return": ret, "volatility": vol, "sharpe": sharpe,
    }

    w, ret, vol, sharpe = risk_parity_optimize(cov_matrix)
    results["风险平价"] = {
        "weights": w, "return": ret, "volatility": vol, "sharpe": sharpe,
    }

    returns_df_nonzero = mean_returns.copy()
    has_neg = (returns_df_nonzero < 0).any()

    return {
        "fund_codes": fund_codes,
        "results": results,
        "mean_returns": mean_returns,
        "cov_matrix": cov_matrix,
        "returns_df": returns_df,
        "has_negative_mean": has_neg,
    }


def main():
    parser = argparse.ArgumentParser(description="投资组合优化器")
    parser.add_argument(
        "--codes", type=str, default="110020,001632,050027",
        help="基金代码，逗号分隔",
    )
    args = parser.parse_args()

    fund_codes = [c.strip() for c in args.codes.split(",")]

    print(f"\n{'='*70}")
    print(f"  投资组合优化")
    print(f"{'='*70}")
    print(f"  基金: {', '.join(fund_codes)}\n")

    try:
        result = optimize_portfolio(fund_codes)
    except ValueError as e:
        print(f"  [ERR] {e}")
        return

    desc_map = {
        "最大夏普": "收益风险比最佳",
        "最小方差": "最稳组合",
        "风险平价": "各资产风险贡献相等",
    }

    for strategy, data in result["results"].items():
        print(f"  [CHART] {strategy} ({desc_map.get(strategy, '')}):")
        print(f"    收益: {data['return']*100:.1f}%  |  "
              f"波动: {data['volatility']*100:.1f}%  |  "
              f"夏普: {data['sharpe']:.2f}")
        print(f"    权重: ", end="")
        weights_str = ", ".join(
            f"{c}: {w*100:.0f}%" for c, w in zip(fund_codes, data["weights"])
        )
        print(weights_str)
        print()

    print(f"  [TIP] 建议:")
    print(f"  1. 新手推荐「风险平价」或「最小方差」，先求稳再求赚")
    print(f"  2. 每季度或半年再平衡一次，恢复目标权重")
    print(f"  3. 优化结果基于历史数据，未来可能偏离")
    print(f"  4. 加入债券基金可大幅降低组合波动")


if __name__ == "__main__":
    main()
