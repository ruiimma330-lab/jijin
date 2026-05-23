#!/usr/bin/env python3
"""基金筛选器 — 多维度筛选和排序。

用法:
    python scripts/analysis/fund_scanner.py                  # 默认筛选
    python scripts/analysis/fund_scanner.py --type mix       # 按类型
    python scripts/analysis/fund_scanner.py --min-return 10  # 年化10%以上
    python scripts/analysis/fund_scanner.py --max-drawdown 15# 最大回撤15%以内
    python scripts/analysis/fund_scanner.py --top 10         # 前10名
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_list, get_fund_nav, get_fund_ranking

SCORE_WEIGHTS = {"return": 0.4, "drawdown": 0.3, "sharpe": 0.3}


def calculate_metrics(nav_df: pd.DataFrame) -> dict:
    """从净值数据计算单只基金的核心指标。"""
    if nav_df.empty or len(nav_df) < 20:
        return {}

    nav = nav_df["nav"]
    if "daily_return" not in nav_df.columns:
        return {}
    returns = nav_df["daily_return"].dropna()

    if returns.empty:
        return {}

    days = (nav_df["date"].max() - nav_df["date"].min()).days
    total_return = nav.iloc[-1] / nav.iloc[0] - 1

    annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
    annual_vol = returns.std() * np.sqrt(252)

    rolling_max = nav.cummax()
    drawdown_series = (nav - rolling_max) / rolling_max
    max_drawdown = drawdown_series.min()

    rf = 0.02
    sharpe = (annual_return - rf) / annual_vol if annual_vol > 0 else 0

    positive_days = (returns > 0).mean()
    avg_positive = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_negative = returns[returns < 0].mean() if (returns < 0).any() else 0
    win_loss_ratio = abs(avg_positive / avg_negative) if avg_negative != 0 else 0

    return {
        "annual_return": round(annual_return * 100, 2),
        "annual_volatility": round(annual_vol * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "win_rate": round(positive_days * 100, 1),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "data_days": days,
    }


def _score_fund(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """对筛选后的基金计算综合评分并排序。

    评分 = 年化收益×权重 - 最大回撤×权重 + 夏普比率×15×权重
    """
    df = df.copy()
    df["score"] = (
        df["annual_return"] * SCORE_WEIGHTS["return"]
        - df["max_drawdown"].abs() * SCORE_WEIGHTS["drawdown"]
        + df["sharpe_ratio"] * 15 * SCORE_WEIGHTS["sharpe"]
    )
    df = df.sort_values("score", ascending=False).head(top_n)
    return df.drop(columns=["score"]).reset_index(drop=True)


def scan_funds(
    fund_type: str = "mix",
    min_return: float = 0,
    max_drawdown: float = 100,
    min_sharpe: float = 0,
    top_n: int = 20,
) -> pd.DataFrame:
    """扫描基金，按多维指标筛选和排名。

    Args:
        fund_type: 基金类型
        min_return: 最低年化收益(%)
        max_drawdown: 最大可接受回撤(%)
        min_sharpe: 最低夏普比率
        top_n: 返回前N名

    Returns:
        包含各项指标的 DataFrame
    """
    print(
        f"[SCAN] 正在扫描基金 (类型={fund_type}, 收益>={min_return}%, "
        f"回撤<={max_drawdown}%, 夏普>={min_sharpe})..."
    )

    try:
        ranking = get_fund_ranking(fund_type=fund_type, top_n=50)
    except Exception as e:
        print(f"[WARN] 无法获取排名数据: {e}，尝试从基金列表逐个获取...")
        fund_list = get_fund_list(fund_type=fund_type)
        codes = fund_list["code"].head(30).tolist()
        ranking = pd.DataFrame({"code": codes})

    results = []
    total = min(len(ranking), 30)
    for i, row in ranking.head(30).iterrows():
        code = row["code"]
        name = row.get("name", "")
        print(f"  [{i + 1}/{total}] 分析 {code} {name}...", end="\r")
        try:
            nav_df = get_fund_nav(code)
            metrics = calculate_metrics(nav_df)
            if metrics:
                metrics["code"] = code
                metrics["name"] = name
                results.append(metrics)
        except Exception as e:
            print(f"\n  [WARN] 获取 {code} 数据失败: {e}")
            continue

    print(f"\n  完成，成功分析 {len(results)} 只基金")

    df = pd.DataFrame(results)
    if df.empty:
        return df

    filtered = df[
        (df["annual_return"] >= min_return)
        & (df["max_drawdown"].abs() <= max_drawdown)
        & (df["sharpe_ratio"] >= min_sharpe)
    ].copy()

    return _score_fund(filtered, top_n)


def main():
    parser = argparse.ArgumentParser(description="基金多维度筛选器")
    parser.add_argument(
        "--type", default="mix", choices=["stock", "bond", "mix", "index", "all"]
    )
    parser.add_argument("--min-return", type=float, default=0, help="最低年化收益(%%)")
    parser.add_argument(
        "--max-drawdown", type=float, default=100, help="最大可接受回撤(%%)"
    )
    parser.add_argument("--min-sharpe", type=float, default=0, help="最低夏普比率")
    parser.add_argument("--top", type=int, default=20, help="返回前N名")
    args = parser.parse_args()

    result = scan_funds(
        fund_type=args.type,
        min_return=args.min_return,
        max_drawdown=args.max_drawdown,
        min_sharpe=args.min_sharpe,
        top_n=args.top,
    )

    if result.empty:
        print("\n没有找到符合条件的基金，试试放宽条件。")
        return

    print(f"\n{'=' * 90}")
    print(f"  筛选结果 (Top {len(result)})")
    print(f"{'=' * 90}")
    print(result.to_string(index=False))

    print("\n[TIP] 历史业绩不代表未来。筛选只是第一步，还需要深入了解。")
    print("[TIP] 推荐: 宽基指数基金(如沪深300)对新手更友好，费率低、确定性高。")


if __name__ == "__main__":
    main()
