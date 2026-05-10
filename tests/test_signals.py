"""市场择时信号测试 — 均线、RSI 信号。"""

import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.strategy.signals import ma_signal, rsi_signal


@pytest.fixture
def uptrend_nav_df():
    """持续上涨 120 天（带波动）。"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=120)
    trend = np.array([1.0 + i * 0.005 for i in range(120)])
    noise = np.random.normal(0, 0.02, 120)
    nav = pd.Series(trend + noise)
    return pd.DataFrame({"date": dates, "nav": nav})


@pytest.fixture
def downtrend_nav_df():
    """持续下跌 120 天（带波动）。"""
    np.random.seed(99)
    dates = pd.date_range("2024-01-01", periods=120)
    trend = np.array([2.0 - i * 0.005 for i in range(120)])
    noise = np.random.normal(0, 0.02, 120)
    nav = pd.Series(trend + noise)
    return pd.DataFrame({"date": dates, "nav": nav})


@pytest.fixture
def crossover_nav_df():
    """金叉场景：先跌后涨。"""
    dates = pd.date_range("2024-01-01", periods=200)
    # 前100天缓慢下跌，后100天快速上涨
    nav = pd.Series(
        [1.0 - i * 0.001 for i in range(100)]
        + [0.9 + i * 0.004 for i in range(100)]
    )
    return pd.DataFrame({"date": dates, "nav": nav})


class TestMASignal:
    def test_uptrend_hold_or_buy(self, uptrend_nav_df):
        result = ma_signal(uptrend_nav_df)
        assert result["signal"] in ["HOLD", "BUY"]

    def test_downtrend_wait_or_sell(self, downtrend_nav_df):
        result = ma_signal(downtrend_nav_df)
        assert result["signal"] in ["WAIT", "SELL"]

    def test_returns_all_keys(self, uptrend_nav_df):
        result = ma_signal(uptrend_nav_df)
        assert "signal" in result
        assert "ma20" in result
        assert "ma60" in result
        assert "gap_pct" in result
        assert "detail" in result

    def test_insufficient_data(self):
        """数据不足 60 天 → 返回 N/A。"""
        dates = pd.date_range("2024-01-01", periods=30)
        nav_df = pd.DataFrame({
            "date": dates,
            "nav": pd.Series([1.0 + i * 0.01 for i in range(30)]),
        })
        result = ma_signal(nav_df)
        assert result["signal"] == "N/A"

    def test_gap_pct_sign_matches_direction(self, uptrend_nav_df):
        """上涨趋势中 MA20 > MA60 → gap_pct 为正。"""
        result = ma_signal(uptrend_nav_df)
        if result["signal"] in ("HOLD", "BUY"):
            assert result["gap_pct"] > 0


class TestRSISignal:
    def test_rsi_returns_all_keys(self, uptrend_nav_df):
        result = rsi_signal(uptrend_nav_df, window=14)
        assert "signal" in result
        assert "rsi" in result
        assert "action" in result

    def test_rsi_range(self, uptrend_nav_df):
        result = rsi_signal(uptrend_nav_df, window=14)
        assert 0 <= result["rsi"] <= 100

    def test_rsi_uptrend_high(self, uptrend_nav_df):
        """持续上涨 → RSI 偏高。"""
        result = rsi_signal(uptrend_nav_df, window=14)
        assert result["rsi"] > 50

    def test_rsi_downtrend_low(self, downtrend_nav_df):
        """持续下跌 → RSI 偏低。"""
        result = rsi_signal(downtrend_nav_df, window=14)
        assert result["rsi"] < 50

    def test_insufficient_data(self):
        dates = pd.date_range("2024-01-01", periods=10)
        nav_df = pd.DataFrame({
            "date": dates,
            "nav": pd.Series([1.0 + i * 0.01 for i in range(10)]),
        })
        result = rsi_signal(nav_df, window=14)
        assert result["signal"] == "N/A"
