"""基金筛选器测试 — calculate_metrics, _score_fund。"""

import numpy as np
import pandas as pd
import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.analysis.fund_scanner import calculate_metrics, _score_fund, SCORE_WEIGHTS


@pytest.fixture
def rising_nav_df():
    """持续上涨的净值数据（252 个交易日 ≈ 1 年）。"""
    dates = pd.date_range("2024-01-01", periods=252)
    nav = pd.Series([1.0 + i * 0.002 for i in range(252)])
    daily_return = nav.pct_change()
    return pd.DataFrame({"date": dates, "nav": nav, "daily_return": daily_return})


@pytest.fixture
def volatile_nav_df():
    """震荡上涨的净值数据。"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=252)
    returns = np.random.normal(0.0005, 0.015, 252)
    nav = (1 + pd.Series(returns)).cumprod()
    nav = nav * 1.0 / nav.iloc[0]  # 从 1.0 开始
    return pd.DataFrame({
        "date": dates,
        "nav": nav,
        "daily_return": pd.Series(returns),
    })


@pytest.fixture
def short_nav_df():
    """数据不足 20 个交易日的净值。"""
    dates = pd.date_range("2024-01-01", periods=10)
    nav = pd.Series([1.0 + i * 0.01 for i in range(10)])
    daily_return = nav.pct_change()
    return pd.DataFrame({"date": dates, "nav": nav, "daily_return": daily_return})


@pytest.fixture
def score_df():
    """模拟评分用的基金 DataFrame。"""
    return pd.DataFrame({
        "code": ["000001", "000002", "000003", "000004", "000005"],
        "name": ["基金A", "基金B", "基金C", "基金D", "基金E"],
        "annual_return": [15.0, 8.0, 20.0, 5.0, 12.0],
        "max_drawdown": [-10.0, -5.0, -25.0, -3.0, -15.0],
        "sharpe_ratio": [1.2, 0.8, 1.5, 0.3, 1.0],
        "annual_volatility": [12.0, 8.0, 18.0, 5.0, 14.0],
        "win_rate": [55.0, 52.0, 60.0, 48.0, 54.0],
    })


class TestCalculateMetrics:
    def test_rising_market(self, rising_nav_df):
        metrics = calculate_metrics(rising_nav_df)
        assert metrics["annual_return"] > 0
        assert metrics["max_drawdown"] <= 0  # 持续上涨 → 回撤很小或为零
        assert metrics["sharpe_ratio"] > 0
        assert metrics["data_days"] == 251

    def test_all_keys_present(self, volatile_nav_df):
        metrics = calculate_metrics(volatile_nav_df)
        for key in [
            "annual_return", "annual_volatility", "max_drawdown",
            "sharpe_ratio", "win_rate", "win_loss_ratio", "data_days",
        ]:
            assert key in metrics

    def test_insufficient_data(self, short_nav_df):
        metrics = calculate_metrics(short_nav_df)
        assert metrics == {}

    def test_empty_df(self):
        df = pd.DataFrame({"date": [], "nav": [], "daily_return": []})
        metrics = calculate_metrics(df)
        assert metrics == {}

    def test_no_daily_return_column(self):
        """没有 daily_return 列 → 返回空。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "nav": np.linspace(1.0, 1.5, 30),
        })
        metrics = calculate_metrics(df)
        assert metrics == {}

    def test_win_rate_in_range(self, volatile_nav_df):
        metrics = calculate_metrics(volatile_nav_df)
        assert 0 <= metrics["win_rate"] <= 100

    def test_max_drawdown_negative(self, volatile_nav_df):
        metrics = calculate_metrics(volatile_nav_df)
        assert metrics["max_drawdown"] <= 0

    def test_flat_nav_zero_return(self):
        """净值完全不变 → 收益为 0。"""
        dates = pd.date_range("2024-01-01", periods=60)
        nav = pd.Series([1.0] * 60)
        daily_return = nav.pct_change()
        df = pd.DataFrame({"date": dates, "nav": nav, "daily_return": daily_return})
        metrics = calculate_metrics(df)
        assert metrics["annual_return"] == pytest.approx(0.0, abs=0.1)
        assert metrics["annual_volatility"] == pytest.approx(0.0, abs=0.1)


class TestScoreFund:
    def test_top_n(self, score_df):
        result = _score_fund(score_df, top_n=3)
        assert len(result) == 3

    def test_top_all(self, score_df):
        result = _score_fund(score_df, top_n=10)
        assert len(result) == 5  # 只有 5 只基金

    def test_sorted_descending(self, score_df):
        """结果按分数降序排列。"""
        result = _score_fund(score_df, top_n=5)
        returns = result["annual_return"].tolist()
        # 第一名的年化收益 >= 最后一名的年化收益
        # (因为评分综合考虑了收益、回撤、夏普)
        top_total = (
            result.iloc[0]["annual_return"] * SCORE_WEIGHTS["return"]
            - abs(result.iloc[0]["max_drawdown"]) * SCORE_WEIGHTS["drawdown"]
            + result.iloc[0]["sharpe_ratio"] * 15 * SCORE_WEIGHTS["sharpe"]
        )
        bottom_total = (
            result.iloc[-1]["annual_return"] * SCORE_WEIGHTS["return"]
            - abs(result.iloc[-1]["max_drawdown"]) * SCORE_WEIGHTS["drawdown"]
            + result.iloc[-1]["sharpe_ratio"] * 15 * SCORE_WEIGHTS["sharpe"]
        )
        assert top_total >= bottom_total

    def test_no_score_column_in_result(self, score_df):
        result = _score_fund(score_df, top_n=3)
        assert "score" not in result.columns

    def test_preserves_original_columns(self, score_df):
        result = _score_fund(score_df, top_n=3)
        for col in ["code", "name", "annual_return", "max_drawdown", "sharpe_ratio"]:
            assert col in result.columns

    def test_does_not_mutate_input(self, score_df):
        original_cols = score_df.columns.tolist()
        _score_fund(score_df, top_n=3)
        assert score_df.columns.tolist() == original_cols
        assert "score" not in score_df.columns

    def test_correct_ranking_order(self, score_df):
        """基金C（20%收益、1.5夏普、-25%回撤）vs 基金D（5%收益、0.3夏普、-3%回撤）。

        基金C 评分 = 20*0.4 - 25*0.3 + 1.5*15*0.3 = 8 - 7.5 + 6.75 = 7.25
        基金D 评分 = 5*0.4 - 3*0.3 + 0.3*15*0.3 = 2 - 0.9 + 1.35 = 2.45
        """
        result = _score_fund(score_df, top_n=5)
        codes = result["code"].tolist()
        c_idx = codes.index("000003")
        d_idx = codes.index("000004")
        assert c_idx < d_idx  # C 排在 D 前面


class TestScoreWeights:
    def test_weights_sum(self):
        """权重总和应该接近 1（或至少各分量有定义）。"""
        total = sum(SCORE_WEIGHTS.values())
        assert total == pytest.approx(1.0)
