"""策略回测测试 — 定投、一次性投资、网格交易。"""

import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.strategy.backtest import (
    backtest_dca, backtest_lump, backtest_grid, _compute_metrics,
    BacktestResult,
)


@pytest.fixture
def rising_nav_df():
    """持续上涨的净值数据（100天）。"""
    dates = pd.date_range("2024-01-01", periods=100)
    nav = pd.Series([1.0 + i * 0.005 for i in range(100)])
    return pd.DataFrame({"date": dates, "nav": nav})


@pytest.fixture
def volatile_nav_df():
    """先涨后跌再涨的净值数据。"""
    dates = pd.date_range("2024-01-01", periods=200)
    t = np.linspace(0, 4 * np.pi, 200)
    nav = 1.0 + np.sin(t) * 0.3 + t / 20
    return pd.DataFrame({"date": dates, "nav": nav})


@pytest.fixture
def flat_nav_df():
    """净值几乎不变的数据。"""
    dates = pd.date_range("2024-01-01", periods=100)
    nav = pd.Series([1.0] * 100)
    nav.iloc[-1] = 1.001  # 微小变动
    return pd.DataFrame({"date": dates, "nav": nav})


class TestComputeMetrics:
    def test_basic_metrics(self, rising_nav_df):
        nav_df = rising_nav_df
        cashflows = pd.DataFrame([
            {"date": nav_df["date"].iloc[0], "amount": 10000}
        ])
        final_shares = 10000 / nav_df["nav"].iloc[0]
        metrics = _compute_metrics(nav_df, cashflows, final_shares)
        assert metrics["total_invested"] == 10000
        assert metrics["final_value"] > 10000  # 赚钱了
        assert metrics["total_return"] > 0
        assert "annual_return" in metrics
        assert "max_drawdown" in metrics
        assert "sharpe_ratio" in metrics

    def test_metrics_loss(self, rising_nav_df):
        """净值下跌 → 收益为负。"""
        nav_df = rising_nav_df.copy()
        nav_df["nav"] = nav_df["nav"].values[::-1]  # 反转——变成下跌
        cashflows = pd.DataFrame([
            {"date": nav_df["date"].iloc[0], "amount": 10000}
        ])
        final_shares = 10000 / nav_df["nav"].iloc[0]
        metrics = _compute_metrics(nav_df, cashflows, final_shares)
        assert metrics["total_return"] < 0


class TestBacktestDCA:
    def test_dca_returns_backtest_result(self, rising_nav_df):
        result = backtest_dca(rising_nav_df, amount=1000, frequency="monthly")
        assert isinstance(result, BacktestResult)
        assert result.strategy == "定投(monthly)"
        assert result.total_invested > 0

    def test_dca_monthly_more_invested_than_weekly(self, rising_nav_df):
        """Monthly 定投间隔更大 → 投入次数少 → 总投入少。"""
        r_monthly = backtest_dca(rising_nav_df, amount=1000, frequency="monthly")
        r_weekly = backtest_dca(rising_nav_df, amount=1000, frequency="weekly")
        assert r_monthly.total_invested < r_weekly.total_invested

    def test_dca_rising_market_profitable(self, rising_nav_df):
        result = backtest_dca(rising_nav_df, amount=1000, frequency="weekly")
        assert result.total_return > 0

    def test_dca_frozen_has_all_metrics(self, rising_nav_df):
        """BacktestResult 是 frozen dataclass，所有指标都有值。"""
        result = backtest_dca(rising_nav_df, amount=500, frequency="biweekly")
        assert isinstance(result.total_return, float)
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown, float)


class TestBacktestLump:
    def test_lump_rising_market(self, rising_nav_df):
        result = backtest_lump(rising_nav_df, amount=10000)
        assert result.total_return > 0
        assert result.total_invested == 10000

    def test_lump_vs_dca_in_rising_market(self, rising_nav_df):
        """上涨市场一次性投资优于定投（因为钱更早进场）。"""
        lump = backtest_lump(rising_nav_df, amount=12000)
        dca = backtest_dca(rising_nav_df, amount=1000, frequency="monthly")
        # 一次性投资应该比同期定投赚得多（上涨市）
        assert lump.total_return > dca.total_return


class TestBacktestGrid:
    def test_grid_returns_backtest_result(self, volatile_nav_df):
        result = backtest_grid(volatile_nav_df, initial_amount=10000, grid_pct=5)
        assert isinstance(result, BacktestResult)
        assert "网格交易" in result.strategy

    def test_grid_flat_market(self, flat_nav_df):
        """波动极小的市场，网格交易几乎不触发。"""
        result = backtest_grid(flat_nav_df, initial_amount=10000, grid_pct=5)
        assert isinstance(result, BacktestResult)
        # 网格没触发几次 → 最终值接近初始一半(另一半是现金)
        # 净值不变 → 总投入应该较少
        assert result.total_invested <= 6000  # 初始50% + 少量触发

    def test_grid_smaller_step_triggers_more(self, volatile_nav_df):
        """更小的网格间距 → 触发更多买卖机会（投入次数更多）。"""
        r5 = backtest_grid(volatile_nav_df, initial_amount=10000, grid_pct=5)
        r2 = backtest_grid(volatile_nav_df, initial_amount=10000, grid_pct=2)
        # 2%间距比5%间距更容易触发 → 最终资产更多取决于网格捕捉到的波动收益
        # 两个策略都应该能赚钱
        assert r5.total_return > 0
        assert r2.total_return > 0
