"""业绩归因分析测试 — CAPM alpha/beta、信息比率、跟踪误差、牛熊分析。"""

import numpy as np
import pandas as pd
import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.analysis.performance import (
    capm_alpha_beta,
    information_ratio,
    tracking_error,
    bull_bear_analysis,
    rolling_alpha_beta,
)


@pytest.fixture
def perfect_correlation_returns():
    """基金收益完全跟随基准（beta=1, alpha=0）。"""
    np.random.seed(42)
    n = 252
    bench = pd.Series(np.random.normal(0.0005, 0.01, n), name="bench")
    fund = bench.copy()
    fund.name = "fund"
    return fund, bench


@pytest.fixture
def high_beta_returns():
    """基金 beta=1.5，波动比基准大 50%。"""
    np.random.seed(42)
    n = 252
    bench = pd.Series(np.random.normal(0.0005, 0.01, n), name="bench")
    fund = bench * 1.5 + 0.0002
    fund.name = "fund"
    return fund, bench


@pytest.fixture
def negative_alpha_returns():
    """基金持续跑输基准。"""
    np.random.seed(42)
    n = 252
    bench = pd.Series(np.random.normal(0.0008, 0.01, n), name="bench")
    fund = bench - 0.0005  # 每天跑输 5bp
    fund.name = "fund"
    return fund, bench


@pytest.fixture
def short_returns():
    """数据不足 30 个交易日。"""
    np.random.seed(42)
    n = 20
    bench = pd.Series(np.random.normal(0.0005, 0.01, n))
    fund = bench.copy()
    return fund, bench


class TestCapmAlphaBeta:
    def test_perfect_correlation(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = capm_alpha_beta(fund, bench)
        assert result["beta"] == pytest.approx(1.0, abs=0.05)
        assert abs(result["alpha_annual"]) < 5  # 接近 0
        assert result["r_squared"] > 0.95

    def test_high_beta(self, high_beta_returns):
        fund, bench = high_beta_returns
        result = capm_alpha_beta(fund, bench)
        assert result["beta"] == pytest.approx(1.5, abs=0.1)
        assert result["r_squared"] > 0.9

    def test_negative_alpha(self, negative_alpha_returns):
        fund, bench = negative_alpha_returns
        result = capm_alpha_beta(fund, bench)
        assert result["alpha_annual"] < 0
        assert "beta" in result

    def test_insufficient_data(self, short_returns):
        fund, bench = short_returns
        result = capm_alpha_beta(fund, bench)
        assert result["alpha"] is None
        assert result["beta"] is None
        assert "error" in result

    def test_all_keys_present(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = capm_alpha_beta(fund, bench)
        for key in [
            "alpha_annual", "alpha_daily_bp", "beta", "r_squared",
            "fund_return", "bench_return", "expected_return", "p_value",
        ]:
            assert key in result

    def test_beta_zero_on_uncorrelated(self):
        """不相关的基金 → beta 接近 0。"""
        np.random.seed(42)
        n = 252
        bench = pd.Series(np.random.normal(0.0005, 0.01, n))
        fund = pd.Series(np.random.normal(0.0005, 0.01, n))
        result = capm_alpha_beta(fund, bench)
        assert abs(result["beta"]) < 0.3


class TestInformationRatio:
    def test_positive_ir(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = information_ratio(fund, bench)
        assert "information_ratio" in result
        assert "tracking_error" in result
        assert isinstance(result["information_ratio"], float)
        assert isinstance(result["tracking_error"], float)

    def test_zero_excess_return(self):
        """完全相同的序列 → IR 为 0。"""
        np.random.seed(42)
        s = pd.Series(np.random.normal(0.0005, 0.01, 252))
        result = information_ratio(s, s.copy())
        assert result["information_ratio"] == pytest.approx(0.0, abs=0.01)

    def test_positive_ir_on_outperformance(self, negative_alpha_returns):
        """基金跑赢基准 → IR 应该为正。"""
        # negative_alpha 里 fund < bench，反转一下
        fund, bench = negative_alpha_returns
        result = information_ratio(bench, fund)  # bench 当作 fund → 超额为正
        assert result["information_ratio"] > 0


class TestTrackingError:
    def test_identical_series(self):
        """完全相同的序列 → 跟踪误差为 0。"""
        np.random.seed(42)
        s = pd.Series(np.random.normal(0.0005, 0.01, 252))
        te = tracking_error(s, s.copy())
        assert te == pytest.approx(0.0, abs=0.01)

    def test_different_series(self):
        """不同的序列 → 跟踪误差 > 0。"""
        np.random.seed(42)
        bench = pd.Series(np.random.normal(0.0005, 0.01, 252))
        fund = pd.Series(np.random.normal(0.0005, 0.02, 252))
        te = tracking_error(fund, bench)
        assert te > 0

    def test_returns_float(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        te = tracking_error(fund, bench)
        assert isinstance(te, float)


class TestBullBearAnalysis:
    def test_all_keys_present(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = bull_bear_analysis(fund, bench)
        for key in [
            "bull_fund_return", "bull_bench_return",
            "bear_fund_return", "bear_bench_return",
            "upside_capture", "downside_capture",
        ]:
            assert key in result

    def test_upside_downside_capture_valid_range(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = bull_bear_analysis(fund, bench)
        assert result["upside_capture"] is not None
        assert result["downside_capture"] is not None
        # 完美相关 → 捕获率都接近 100
        assert result["upside_capture"] == pytest.approx(100, abs=20)
        assert result["downside_capture"] == pytest.approx(100, abs=20)

    def test_asymmetric_capture(self):
        """基金上涨时跟得上，下跌时跌得更少。"""
        np.random.seed(42)
        n = 252
        bench = pd.Series(np.random.normal(0.0005, 0.01, n))
        # 上涨日放大 1.2 倍，下跌日只跌 0.8 倍
        fund = bench.where(bench > 0, bench * 0.8).where(bench <= 0, bench * 1.2)
        result = bull_bear_analysis(fund, bench)
        assert result["upside_capture"] > 100
        assert result["downside_capture"] < 100


class TestRollingAlphaBeta:
    def test_returns_dataframe(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = rolling_alpha_beta(fund, bench, window=60)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        for col in ["date", "alpha_daily", "beta", "r_squared", "alpha_annual"]:
            assert col in result.columns

    def test_insufficient_data(self, short_returns):
        fund, bench = short_returns
        result = rolling_alpha_beta(fund, bench, window=60)
        assert result.empty

    def test_beta_around_one(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        result = rolling_alpha_beta(fund, bench, window=60)
        assert result["beta"].mean() == pytest.approx(1.0, abs=0.1)

    def test_window_respected(self, perfect_correlation_returns):
        fund, bench = perfect_correlation_returns
        n = len(fund)
        result = rolling_alpha_beta(fund, bench, window=60)
        expected_rows = n - 60
        assert len(result) == expected_rows
