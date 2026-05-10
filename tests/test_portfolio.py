"""投资组合优化测试 — 均值方差、风险平价、有效前沿。"""

import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.strategy.portfolio import (
    portfolio_metrics, max_sharpe_optimize, risk_parity_optimize,
    min_variance_optimize, efficient_frontier,
)


@pytest.fixture
def mean_returns():
    """三资产 — 年化预期收益。"""
    return np.array([0.10, 0.15, 0.05])  # 10%, 15%, 5%


@pytest.fixture
def cov_matrix():
    """三资产 — 年化协方差矩阵。"""
    return np.array([
        [0.04, 0.01, 0.00],
        [0.01, 0.09, 0.00],
        [0.00, 0.00, 0.01],
    ])


@pytest.fixture
def equal_weights():
    return np.array([1/3, 1/3, 1/3])


class TestPortfolioMetrics:
    def test_equal_weight_return(self, mean_returns, cov_matrix, equal_weights):
        ret, vol, sharpe = portfolio_metrics(equal_weights, mean_returns, cov_matrix)
        expected_ret = np.dot(equal_weights, mean_returns)
        assert ret == pytest.approx(expected_ret, abs=0.001)

    def test_equal_weight_vol_positive(self, mean_returns, cov_matrix, equal_weights):
        _, vol, _ = portfolio_metrics(equal_weights, mean_returns, cov_matrix)
        assert vol > 0

    def test_sharpe_equals_zero_when_vol_zero(self, mean_returns):
        """零波动率 → 夏普 = 0（不会除零）。"""
        zero_cov = np.zeros((3, 3))
        _, _, sharpe = portfolio_metrics(
            np.array([1/3, 1/3, 1/3]), mean_returns, zero_cov
        )
        assert sharpe == 0.0

    def test_100pct_asset_matches_individual(self, mean_returns, cov_matrix):
        """100% 配置单资产 → 收益/波动等于该资产自身。"""
        for i in range(3):
            w = np.zeros(3)
            w[i] = 1.0
            ret, vol, _ = portfolio_metrics(w, mean_returns, cov_matrix)
            assert ret == pytest.approx(mean_returns[i], abs=0.001)
            assert vol == pytest.approx(np.sqrt(cov_matrix[i, i]), abs=0.001)


class TestMaxSharpeOptimize:
    def test_weights_sum_to_one(self, mean_returns, cov_matrix):
        w, ret, vol, sharpe = max_sharpe_optimize(mean_returns, cov_matrix)
        assert sum(w) == pytest.approx(1.0, abs=0.01)
        assert all(0 <= wi <= 1 for wi in w)

    def test_sharpe_higher_than_equal_weight(self, mean_returns, cov_matrix, equal_weights):
        w, _, _, opt_sharpe = max_sharpe_optimize(mean_returns, cov_matrix)
        _, _, eq_sharpe = portfolio_metrics(equal_weights, mean_returns, cov_matrix)
        assert opt_sharpe >= eq_sharpe - 0.01  # 最优化应该至少不差


class TestMinVarianceOptimize:
    def test_weights_sum_to_one(self, cov_matrix):
        w, ret, vol, sharpe = min_variance_optimize(cov_matrix)
        assert sum(w) == pytest.approx(1.0, abs=0.01)

    def test_lower_vol_than_equal_weight(self, cov_matrix, equal_weights):
        w, _, opt_vol, _ = min_variance_optimize(cov_matrix)
        _, eq_vol, _ = portfolio_metrics(equal_weights, np.zeros(3), cov_matrix)
        assert opt_vol <= eq_vol + 0.001  # 最稳组合应该波动更低

    def test_allocates_more_to_low_vol_asset(self, cov_matrix):
        """最小方差 → 更多配置到低波动资产（第3个资产，方差0.01）。"""
        w, _, _, _ = min_variance_optimize(cov_matrix)
        assert w[2] > w[1]  # 第三个资产波动最低，应该配置更多


class TestRiskParity:
    def test_weights_sum_to_one(self, cov_matrix):
        w, ret, vol, sharpe = risk_parity_optimize(cov_matrix)
        assert sum(w) == pytest.approx(1.0, abs=0.01)
        assert all(wi > 0 for wi in w)  # 风险平价不排斥任何资产

    def test_all_assets_included(self, cov_matrix):
        """风险平价给每个资产都分配权重。"""
        w, _, _, _ = risk_parity_optimize(cov_matrix)
        assert all(w > 0.01)


class TestEfficientFrontier:
    def test_returns_dataframe(self, mean_returns, cov_matrix):
        ef = efficient_frontier(mean_returns, cov_matrix, points=25)
        assert isinstance(ef, pd.DataFrame)
        assert len(ef) > 0
        assert "return" in ef.columns
        assert "volatility" in ef.columns
        assert "sharpe" in ef.columns

    def test_monotonic_volatility(self, mean_returns, cov_matrix):
        """更高收益 → 更高波动（剔除无效点后应单调）。"""
        ef = efficient_frontier(mean_returns, cov_matrix, points=50)
        # 有效前沿在均值-方差空间中呈凸形，剔除尾部无效点后单调
        mid = ef.iloc[len(ef) // 2:]
        assert mid["volatility"].is_monotonic_increasing
