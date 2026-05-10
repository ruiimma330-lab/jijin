"""风险指标测试 — max_drawdown, VaR, CVaR, rolling_risk."""

import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.analysis.risk import max_drawdown, historical_var, cvar, rolling_risk


@pytest.fixture
def simple_nav():
    """简单净值序列：1.0 → 1.5 → 0.8 → 恢复"""
    return pd.Series([1.0, 1.2, 1.5, 1.1, 0.8, 0.9, 1.0, 1.48, 1.5],
                     index=pd.date_range("2024-01-01", periods=9))


@pytest.fixture
def uptrend_nav():
    """持续上涨，无回撤。"""
    return pd.Series([1.0 + i * 0.01 for i in range(100)],
                     index=pd.date_range("2024-01-01", periods=100))


@pytest.fixture
def returns_series():
    """随机收益率序列。"""
    np.random.seed(42)
    return pd.Series(np.random.normal(0.0005, 0.015, 252))


class TestMaxDrawdown:
    def test_max_dd_basic(self, simple_nav):
        result = max_drawdown(simple_nav)
        # 最高点 1.5，最低点 0.8 → (0.8-1.5)/1.5 = -46.67%
        assert result["max_drawdown"] == pytest.approx(-46.67, abs=0.01)
        assert result["drawdown_count"] > 0

    def test_max_dd_uptrend(self, uptrend_nav):
        result = max_drawdown(uptrend_nav)
        assert result["max_drawdown"] == 0.0
        assert result["drawdown_count"] == 0
        assert result["avg_drawdown"] == 0.0

    def test_max_dd_returns_dict(self, simple_nav):
        result = max_drawdown(simple_nav)
        assert "max_drawdown" in result
        assert "max_dd_start" in result
        assert "max_dd_end" in result
        assert "recovery_days" in result
        assert "avg_drawdown" in result
        assert "drawdown_count" in result

    def test_max_dd_single_point(self):
        nav = pd.Series([1.0], index=pd.to_datetime(["2024-01-01"]))
        result = max_drawdown(nav)
        assert result["max_drawdown"] == 0.0

    def test_max_dd_double_bottom(self):
        """两次回撤场景。"""
        nav = pd.Series([1.0, 0.7, 1.0, 0.7, 1.0],
                        index=pd.date_range("2024-01-01", periods=5))
        result = max_drawdown(nav)
        assert result["max_drawdown"] == pytest.approx(-30.0, abs=0.1)
        assert result["drawdown_count"] >= 2


class TestHistoricalVaR:
    def test_var_95(self, returns_series):
        var = historical_var(returns_series, 0.95)
        # 95% VaR 应该是负值（损失）
        assert var < 0

    def test_var_99_more_extreme_than_95(self, returns_series):
        var95 = historical_var(returns_series, 0.95)
        var99 = historical_var(returns_series, 0.99)
        assert var99 < var95  # 99% 更极端

    def test_var_constant(self):
        returns = pd.Series([0.01] * 100)
        var = historical_var(returns, 0.95)
        assert var == 0.01  # 所有值相同


class TestCVaR:
    def test_cvar_more_extreme_than_var(self, returns_series):
        var95 = historical_var(returns_series, 0.95)
        cvar95 = cvar(returns_series, 0.95)
        assert cvar95 <= var95  # CVaR ≤ VaR（更极端的平均）

    def test_cvar_constant(self):
        returns = pd.Series([0.01] * 100)
        result = cvar(returns, 0.95)
        assert result == pytest.approx(0.01)


class TestRollingRisk:
    def test_rolling_vol_output(self):
        nav_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=120),
            "nav": np.linspace(1.0, 1.5, 120),
            "daily_return": [0.001] * 120,
        })
        result = rolling_risk(nav_df, window=60)
        assert "rolling_vol" in result.columns
        assert "rolling_max_dd" in result.columns
        assert len(result) == 120

    def test_rolling_vol_near_constant(self):
        """恒定日收益 → 滚动波动率接近 0。"""
        nav_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=120),
            "nav": np.linspace(1.0, 1.5, 120),
            "daily_return": [0.0005] * 120,
        })
        result = rolling_risk(nav_df, window=60)
        valid = result["rolling_vol"].dropna()
        assert (valid < 0.1).all()  # 波动率接近0
