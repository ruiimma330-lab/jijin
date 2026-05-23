"""资产相关性分析 — 计算和可视化基金/指数间的相关性。

用法:
    python scripts/analysis/correlation.py --codes 110020,001632,050027,000001
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import get_fund_nav, DataSourceError


def compute_correlation(fund_codes: list[str]) -> pd.DataFrame:
    """计算基金间的日收益率相关性矩阵。

    Args:
        fund_codes: 基金代码列表
    Returns:
        相关性矩阵 DataFrame
    """
    all_returns = {}
    names = {}

    for code in fund_codes:
        try:
            nav_df = get_fund_nav(code)
            nav_df["date"] = pd.to_datetime(nav_df["date"])
            returns = nav_df.set_index("date")["daily_return"].dropna()
            if len(returns) > 0:
                all_returns[code] = returns
                names[code] = code
        except DataSourceError:
            print(f"  ⚠️ 跳过 {code} (无数据)")

    if len(all_returns) < 2:
        print("  ❌ 至少需要2只有效基金")
        return pd.DataFrame()

    returns_df = pd.DataFrame(all_returns).dropna()
    corr_matrix = returns_df.corr()
    corr_matrix.index = [f"{c}" for c in corr_matrix.index]
    corr_matrix.columns = [f"{c}" for c in corr_matrix.columns]

    return corr_matrix


def plot_correlation_heatmap(
    corr_matrix: pd.DataFrame, title: str = "基金相关性热力图"
):
    """绘制相关性热力图。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".2f",
        cmap="RdYlBu_r",
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        mask=mask,
        linewidths=1,
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    fig.tight_layout()
    return fig


def interpret_correlation(corr_matrix: pd.DataFrame) -> list[str]:
    """解读相关性矩阵，给出投资建议。"""
    insights = []
    codes = corr_matrix.columns.tolist()

    high_pairs = []
    low_pairs = []

    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            val = corr_matrix.iloc[i, j]
            if val > 0.80:
                high_pairs.append((codes[i], codes[j], val))
            if val < 0.30:
                low_pairs.append((codes[i], codes[j], val))

    if high_pairs:
        for c1, c2, val in high_pairs:
            insights.append(
                f"⚠️ {c1} 与 {c2} 高度相关 (r={val:.2f}) — 同时持有无法分散风险"
            )

    if low_pairs:
        for c1, c2, val in low_pairs:
            insights.append(
                f"✅ {c1} 与 {c2} 相关性低 (r={val:.2f}) — 搭配持有可分散风险"
            )

    if not high_pairs and not low_pairs:
        insights.append("各基金间相关性适中，组合分散化效果一般")

    return insights


def main():
    parser = argparse.ArgumentParser(description="资产相关性分析")
    parser.add_argument(
        "--codes",
        type=str,
        default="110020,001632,050027,000001",
        help="基金代码，逗号分隔",
    )
    args = parser.parse_args()

    fund_codes = [c.strip() for c in args.codes.split(",")]

    print(f"\n{'=' * 70}")
    print("  资产相关性分析")
    print(f"{'=' * 70}")
    print(f"  分析基金: {', '.join(fund_codes)}\n")

    corr = compute_correlation(fund_codes)

    if corr.empty:
        return

    print("  相关性矩阵:")
    print(corr.to_string())

    print("\n  📊 解读:")
    insights = interpret_correlation(corr)
    for insight in insights:
        print(f"  {insight}")

    print("\n  💡 建议:")
    print("  1. 相关性 > 0.8: 两只基金走势高度同步，只需持有其一")
    print("  2. 相关性 < 0.3: 搭配可有效分散风险")
    print("  3. 理想组合: 包含不同资产类别 (股票+债券+商品)")
    print("  4. 至少加入一只债券基金，可大幅降低组合波动")


if __name__ == "__main__":
    main()
