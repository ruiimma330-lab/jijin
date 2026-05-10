"""相关性分析测试 — 矩阵解读、投资建议。"""

import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.analysis.correlation import interpret_correlation


@pytest.fixture
def high_corr_matrix():
    """高度相关的 3x3 矩阵。"""
    codes = ["A", "B", "C"]
    data = np.array([
        [1.00, 0.92, 0.85],
        [0.92, 1.00, 0.88],
        [0.85, 0.88, 1.00],
    ])
    return pd.DataFrame(data, index=codes, columns=codes)


@pytest.fixture
def low_corr_matrix():
    """低相关的 3x3 矩阵。"""
    codes = ["股票A", "债券B", "黄金C"]
    data = np.array([
        [1.00, 0.15, 0.05],
        [0.15, 1.00, 0.20],
        [0.05, 0.20, 1.00],
    ])
    return pd.DataFrame(data, index=codes, columns=codes)


@pytest.fixture
def mixed_corr_matrix():
    """混合相关矩阵。"""
    codes = ["A", "B", "C", "D"]
    data = np.array([
        [1.00, 0.90, 0.20, 0.10],
        [0.90, 1.00, 0.15, 0.05],
        [0.20, 0.15, 1.00, 0.95],
        [0.10, 0.05, 0.95, 1.00],
    ])
    return pd.DataFrame(data, index=codes, columns=codes)


class TestInterpretCorrelation:
    def test_high_corr_warning(self, high_corr_matrix):
        insights = interpret_correlation(high_corr_matrix)
        assert len(insights) > 0
        assert any("高度相关" in i for i in insights)

    def test_low_corr_positive(self, low_corr_matrix):
        insights = interpret_correlation(low_corr_matrix)
        assert any("相关性低" in i or "分散风险" in i for i in insights)

    def test_returns_list(self, high_corr_matrix):
        insights = interpret_correlation(high_corr_matrix)
        assert isinstance(insights, list)

    def test_high_pairs_identified(self, high_corr_matrix):
        insights = interpret_correlation(high_corr_matrix)
        # A-B (0.92) 和 A-C (0.85) 和 B-C (0.88) 都 > 0.80
        high_insights = [i for i in insights if "高度相关" in i]
        assert len(high_insights) >= 2

    def test_low_pairs_identified(self, low_corr_matrix):
        insights = interpret_correlation(low_corr_matrix)
        low_insights = [i for i in insights if "相关性低" in i or "分散风险" in i]
        assert len(low_insights) > 0

    def test_mixed_detects_both(self, mixed_corr_matrix):
        insights = interpret_correlation(mixed_corr_matrix)
        has_high = any("高度相关" in i for i in insights)
        has_low = any("相关性低" in i or "分散风险" in i for i in insights)
        assert has_high and has_low

    def test_empty_2x2(self):
        """2x2 矩阵，中等相关性。"""
        corr = pd.DataFrame(
            [[1.0, 0.5], [0.5, 1.0]],
            index=["X", "Y"], columns=["X", "Y"],
        )
        insights = interpret_correlation(corr)
        # 0.5 既不高也不低 → 适中
        assert any("适中" in i or "一般" in i for i in insights)
