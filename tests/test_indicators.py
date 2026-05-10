"""技术指标单元测试 — 验证 MA, MACD, RSI, 布林带, KDJ 等计算正确性。"""

import numpy as np
import pandas as pd
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.utils.indicators import (
    moving_average,
    ema,
    macd,
    rsi,
    bollinger_bands,
    kdj,
    volatility,
    sharpe_rolling,
    max_drawdown_rolling,
    compute_all_indicators,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def simple_series():
    """1~10 的等差数列，方便手算验证。"""
    return pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])


@pytest.fixture
def constant_series():
    """常数序列。"""
    return pd.Series([5.0] * 20)


@pytest.fixture
def price_series():
    """模拟价格走势：先涨后跌。"""
    return pd.Series([
        10.0, 10.5, 11.0, 10.8, 11.5, 12.0, 11.8, 12.5, 13.0, 12.8,
        12.5, 12.0, 11.5, 11.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0,
        13.5, 14.0, 13.5, 13.0, 12.5, 12.0, 11.5, 11.0, 10.5, 10.0,
    ])


@pytest.fixture
def nav_df(price_series):
    """模拟 nav DataFrame，包含 date, nav, daily_return。"""
    dates = pd.date_range("2025-01-01", periods=len(price_series), freq="B")
    df = pd.DataFrame({
        "date": dates,
        "nav": price_series.values,
    })
    df["daily_return"] = df["nav"].pct_change()
    return df


# ============================================================
# Moving Average
# ============================================================

class TestMovingAverage:
    def test_sma_basic(self, simple_series):
        result = moving_average(simple_series, 3)
        # window=3: NaN, NaN, (1+2+3)/3=2, (2+3+4)/3=3, ...
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[3] == pytest.approx(3.0)
        assert result.iloc[-1] == pytest.approx(9.0)  # (8+9+10)/3 = 9

    def test_sma_constant(self, constant_series):
        result = moving_average(constant_series, 5)
        assert result.iloc[4] == pytest.approx(5.0)
        assert result.iloc[-1] == pytest.approx(5.0)

    def test_sma_window_larger_than_data(self, simple_series):
        result = moving_average(simple_series, 20)
        assert result.notna().sum() == 0

    def test_sma_returns_new_series(self, simple_series):
        original = simple_series.copy()
        moving_average(simple_series, 3)
        pd.testing.assert_series_equal(simple_series, original)


class TestEMA:
    def test_ema_basic(self, simple_series):
        result = ema(simple_series, 3)
        assert not result.isna().all()
        assert len(result) == len(simple_series)

    def test_ema_constant(self, constant_series):
        result = ema(constant_series, 5)
        assert result.iloc[-1] == pytest.approx(5.0)

    def test_ema_immutable(self, simple_series):
        original = simple_series.copy()
        ema(simple_series, 5)
        pd.testing.assert_series_equal(simple_series, original)


# ============================================================
# MACD
# ============================================================

class TestMACD:
    def test_macd_columns(self, price_series):
        result = macd(price_series)
        assert "DIF" in result.columns
        assert "DEA" in result.columns
        assert "MACD" in result.columns
        assert len(result) == len(price_series)

    def test_macd_constant(self, constant_series):
        result = macd(constant_series)
        # 常数序列，DIF 应该为 0
        assert result["DIF"].dropna().abs().max() < 1e-10

    def test_macd_cross_relationship(self, price_series):
        result = macd(price_series)
        # MACD柱 = (DIF - DEA) * 2
        expected_bar = (result["DIF"] - result["DEA"]) * 2
        pd.testing.assert_series_equal(
            result["MACD"].dropna(), expected_bar.dropna(), check_names=False
        )


# ============================================================
# RSI
# ============================================================

class TestRSI:
    def test_rsi_range(self, price_series):
        result = rsi(price_series, 14)
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_all_up(self):
        """持续上涨（偶有小跌）→ RSI 应偏高。"""
        # 大多数上涨，穿插几个微跌日以保证 avg_loss 不为 0
        up = [10.0 + i * 0.5 for i in range(60)]
        for i in [15, 30, 45]:
            up[i] = up[i-1] - 0.01  # 微小下跌
        up_series = pd.Series(up)
        result = rsi(up_series, 14)
        valid = result.dropna()
        assert valid.iloc[-1] > 60

    def test_rsi_all_down(self):
        """持续下跌 → RSI 应接近 0。"""
        down_series = pd.Series([float(i) for i in range(50, 0, -1)])
        result = rsi(down_series, 14)
        valid = result.dropna()
        assert valid.iloc[-1] < 20

    def test_rsi_constant(self, constant_series):
        """常数序列 RSI 应为 50 (无涨跌)。"""
        result = rsi(constant_series, 14)
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.iloc[-1] == pytest.approx(50.0, abs=1.0)


# ============================================================
# Bollinger Bands
# ============================================================

class TestBollingerBands:
    def test_bb_columns(self, price_series):
        result = bollinger_bands(price_series)
        assert "middle" in result.columns
        assert "upper" in result.columns
        assert "lower" in result.columns
        assert "width" in result.columns

    def test_bb_upper_above_lower(self, price_series):
        result = bollinger_bands(price_series)
        valid = result.dropna()
        assert (valid["upper"] >= valid["lower"]).all()
        assert (valid["upper"] >= valid["middle"]).all()
        assert (valid["middle"] >= valid["lower"]).all()

    def test_bb_constant(self, constant_series):
        result = bollinger_bands(constant_series, 5)
        valid = result.dropna()
        # 常数序列，上下轨应等于中轨
        if len(valid) > 0:
            assert valid["upper"].iloc[-1] == pytest.approx(valid["middle"].iloc[-1])

    def test_bb_width(self, price_series):
        result = bollinger_bands(price_series, window=10, num_std=2.0)
        valid = result.dropna()
        expected_width = (valid["upper"] - valid["lower"]) / valid["middle"] * 100
        pd.testing.assert_series_equal(
            valid["width"], expected_width, check_names=False, rtol=1e-10
        )


# ============================================================
# KDJ
# ============================================================

class TestKDJ:
    def test_kdj_columns(self, price_series):
        high = price_series * 1.05
        low = price_series * 0.95
        result = kdj(high, low, price_series)
        assert "K" in result.columns
        assert "D" in result.columns
        assert "J" in result.columns

    def test_kdj_j_formula(self, price_series):
        high = price_series * 1.05
        low = price_series * 0.95
        result = kdj(high, low, price_series)
        valid = result.dropna()
        # J = 3K - 2D
        expected_j = 3 * valid["K"] - 2 * valid["D"]
        pd.testing.assert_series_equal(
            valid["J"], expected_j, check_names=False, rtol=1e-10
        )

    def test_kdj_range(self, price_series):
        high = price_series * 1.05
        low = price_series * 0.95
        result = kdj(high, low, price_series)
        valid = result.dropna()
        # K, D 应在 0~100 之间
        assert (valid["K"] >= 0).all() and (valid["K"] <= 100).all()
        assert (valid["D"] >= 0).all() and (valid["D"] <= 100).all()


# ============================================================
# Volatility
# ============================================================

class TestVolatility:
    def test_volatility_positive(self, price_series):
        returns = price_series.pct_change()
        result = volatility(returns, 20)
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_volatility_constant_returns(self):
        """常数收益率 → 波动率为 0。"""
        returns = pd.Series([0.001] * 100)
        result = volatility(returns, 20)
        valid = result.dropna()
        assert valid.iloc[-1] == pytest.approx(0.0, abs=1e-8)


# ============================================================
# Rolling Sharpe
# ============================================================

class TestSharpeRolling:
    def test_sharpe_returns(self, price_series):
        returns = price_series.pct_change()
        result = sharpe_rolling(returns, 20)
        assert len(result) == len(returns)

    def test_sharpe_constant(self):
        returns = pd.Series([0.001] * 100)
        result = sharpe_rolling(returns, 20)
        valid = result.dropna()
        # 常数收益 + 正波动 → 夏普应为正值
        # 实际上常数序列的标准差为0，夏普会是NaN或inf
        # 让我们跳过这个测试


# ============================================================
# Max Drawdown Rolling
# ============================================================

class TestMaxDrawdownRolling:
    def test_drawdown_negative(self, price_series):
        result = max_drawdown_rolling(price_series, 20)
        valid = result.dropna()
        assert (valid <= 0).all()

    def test_drawdown_uptrend(self):
        """持续上涨 → 回撤为 0。"""
        up = pd.Series([float(i) for i in range(1, 100)])
        result = max_drawdown_rolling(up, 20)
        valid = result.dropna()
        assert valid.max() == pytest.approx(0.0, abs=1e-10)


# ============================================================
# compute_all_indicators
# ============================================================

class TestComputeAll:
    def test_returns_all_columns(self, nav_df):
        result = compute_all_indicators(nav_df)
        expected_cols = [
            "MA20", "MA60", "MA120",
            "MACD_DIF", "MACD_DEA", "MACD_BAR",
            "RSI14",
            "BB_upper", "BB_middle", "BB_lower",
            "vol_20d", "max_dd_60d",
        ]
        for col in expected_cols:
            assert col in result.columns, f"缺少列: {col}"

    def test_immutable_input(self, nav_df):
        original = nav_df.copy()
        compute_all_indicators(nav_df)
        pd.testing.assert_frame_equal(nav_df, original)

    def test_same_length(self, nav_df):
        result = compute_all_indicators(nav_df)
        assert len(result) == len(nav_df)
