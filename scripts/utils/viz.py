"""可视化工具 — 基金净值走势、收益分布、对比图表。

基于 matplotlib，所有函数返回 Figure 对象，方便在 Jupyter 中展示。
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "DejaVu Sans"
]
matplotlib.rcParams["axes.unicode_minus"] = False

COLORS = {
    "primary": "#2563EB",
    "secondary": "#F97316",
    "green": "#16A34A",
    "red": "#DC2626",
    "purple": "#7C3AED",
    "gray": "#9CA3AF",
    "bg": "#F8FAFC",
}


def plot_nav(
    df: pd.DataFrame,
    title: str = "基金净值走势",
    show_ma: bool = True,
    figsize: tuple = (14, 6),
) -> plt.Figure:
    """绘制基金净值走势图。

    Args:
        df: 包含 date, nav 列的 DataFrame
        title: 图表标题
        show_ma: 是否显示 20/60 日均线
        figsize: 图表尺寸
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(COLORS["bg"])

    ax.plot(
        df["date"], df["nav"],
        color=COLORS["primary"], linewidth=1.5, label="净值", zorder=3,
    )

    if show_ma and len(df) >= 20:
        ma20 = df["nav"].rolling(20).mean()
        ax.plot(
            df["date"], ma20,
            color=COLORS["secondary"], linewidth=1, alpha=0.7, label="MA20",
        )
    if show_ma and len(df) >= 60:
        ma60 = df["nav"].rolling(60).mean()
        ax.plot(
            df["date"], ma60,
            color=COLORS["purple"], linewidth=1, alpha=0.7, label="MA60",
        )

    ax.fill_between(
        df["date"], df["nav"].min(), df["nav"],
        alpha=0.05, color=COLORS["primary"],
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("单位净值 (元)", fontsize=11)
    ax.legend(loc="upper left", frameon=True, facecolor="white")
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.4f"))
    ax.grid(True, alpha=0.3, linestyle="--")
    fig.tight_layout()
    return fig


def plot_return_distribution(
    daily_returns: pd.Series,
    title: str = "日收益率分布",
    figsize: tuple = (12, 5),
) -> plt.Figure:
    """绘制日收益率分布直方图。

    Args:
        daily_returns: 日收益率序列 (小数，如 0.01 = 1%)
        title: 图表标题
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    returns_pct = daily_returns.dropna() * 100

    ax1.hist(
        returns_pct, bins=50, color=COLORS["primary"],
        edgecolor="white", alpha=0.8,
    )
    ax1.axvline(0, color=COLORS["red"], linestyle="--", alpha=0.5)
    ax1.axvline(returns_pct.mean(), color=COLORS["secondary"],
                linestyle="-", alpha=0.8, label=f'均值 {returns_pct.mean():.2f}%')
    ax1.set_title("日收益率直方图", fontsize=12, fontweight="bold")
    ax1.set_xlabel("日收益率 (%)")
    ax1.set_ylabel("频率")
    ax1.legend()

    returns_pct.plot(
        ax=ax2, color=COLORS["primary"], alpha=0.7, linewidth=0.5,
    )
    ax2.axhline(0, color=COLORS["red"], linestyle="--", alpha=0.5)
    ax2.set_title("日收益率时序", fontsize=12, fontweight="bold")
    ax2.set_xlabel("")
    ax2.set_ylabel("日收益率 (%)")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_drawdown(
    df: pd.DataFrame,
    title: str = "回撤分析",
    figsize: tuple = (14, 8),
) -> plt.Figure:
    """绘制净值走势 + 回撤区域的组合图。

    Args:
        df: 包含 date, nav 列的 DataFrame
        title: 图表标题
    """
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    rolling_max = df["nav"].cummax()
    drawdown = (df["nav"] - rolling_max) / rolling_max * 100

    ax1.plot(
        df["date"], df["nav"],
        color=COLORS["primary"], linewidth=1.5, label="净值",
    )
    ax1.fill_between(
        df["date"], df["nav"], rolling_max,
        where=(df["nav"] < rolling_max),
        alpha=0.15, color=COLORS["red"], label="回撤区域",
    )
    ax1.set_title(title, fontsize=13, fontweight="bold")
    ax1.set_ylabel("单位净值 (元)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3, linestyle="--")

    ax2.fill_between(
        df["date"], 0, drawdown,
        color=COLORS["red"], alpha=0.3,
    )
    ax2.plot(
        df["date"], drawdown,
        color=COLORS["red"], linewidth=0.8,
    )
    ax2.set_ylabel("回撤 (%)")
    ax2.set_xlabel("")
    max_dd = drawdown.min()
    ax2.axhline(
        max_dd, color=COLORS["gray"], linestyle="--",
        alpha=0.5, label=f"最大回撤 {max_dd:.1f}%",
    )
    ax2.legend(loc="lower left")
    ax2.grid(True, alpha=0.3, linestyle="--")

    fig.tight_layout()
    return fig


def plot_comparison(
    funds: dict,
    title: str = "基金收益对比",
    figsize: tuple = (14, 6),
) -> plt.Figure:
    """对比多只基金的归一化走势（基准 1.0）。

    Args:
        funds: {基金名称: DataFrame(含 date, nav)} 的字典
        title: 图表标题
    """
    fig, ax = plt.subplots(figsize=figsize)
    colors_list = list(COLORS.values())

    for i, (name, df) in enumerate(funds.items()):
        normalized = df["nav"] / df["nav"].iloc[0]
        color = colors_list[i % len(colors_list)]
        ax.plot(
            df["date"], normalized,
            color=color, linewidth=1.5, label=name,
        )

    ax.axhline(1.0, color="black", linestyle="--", alpha=0.3, linewidth=0.8)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("累计收益 (基准=1.0)", fontsize=11)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda y, _: f"{y:.2f}")
    )

    final_returns = []
    for name, df in funds.items():
        ret = (df["nav"].iloc[-1] / df["nav"].iloc[0] - 1) * 100
        final_returns.append(f"{name}: {ret:+.1f}%")

    ax.text(
        0.02, 0.02, " | ".join(final_returns),
        transform=ax.transAxes, fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    fig.tight_layout()
    return fig


def plot_risk_return_scatter(
    stats: pd.DataFrame,
    title: str = "风险-收益散点图",
    figsize: tuple = (10, 8),
) -> plt.Figure:
    """绘制风险-收益散点图（每个点代表一只基金）。

    Args:
        stats: 包含 name, annual_return(年化收益%), annual_volatility(年化波动率%)
               列的 DataFrame
        title: 图表标题
    """
    fig, ax = plt.subplots(figsize=figsize)

    scatter = ax.scatter(
        stats["annual_volatility"], stats["annual_return"],
        c=stats["annual_return"] / stats["annual_volatility"],
        cmap="RdYlGn", s=80, edgecolors="white", linewidth=1, zorder=5,
    )

    for _, row in stats.iterrows():
        ax.annotate(
            row["name"],
            (row["annual_volatility"], row["annual_return"]),
            fontsize=8, ha="center", va="bottom",
            textcoords="offset points", xytext=(0, 5),
        )

    volatilities = np.linspace(
        stats["annual_volatility"].min() * 0.8,
        stats["annual_volatility"].max() * 1.2, 100,
    )
    for sharpe, ls, label in [
        (0.5, ":", "夏普=0.5"), (1.0, "--", "夏普=1.0"),
        (2.0, "-.", "夏普=2.0"),
    ]:
        ax.plot(
            volatilities, volatilities * sharpe,
            color=COLORS["gray"], linestyle=ls,
            alpha=0.4, label=label, linewidth=0.8,
        )

    ax.set_xlabel("年化波动率 (%)", fontsize=11)
    ax.set_ylabel("年化收益率 (%)", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3, linestyle="--")
    plt.colorbar(scatter, ax=ax, label="夏普比率")

    fig.tight_layout()
    return fig
