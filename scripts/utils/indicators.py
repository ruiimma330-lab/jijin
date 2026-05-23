"""技术指标计算 — MA, MACD, RSI, 布林带, KDJ。

所有函数接收 pd.Series，返回新的 pd.Series 或 pd.DataFrame。
不修改原始数据。
"""

import numpy as np
import pandas as pd


def moving_average(series: pd.Series, window: int) -> pd.Series:
    """简单移动平均线 SMA。"""
    return series.rolling(window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """指数移动平均线 EMA。"""
    return series.ewm(span=window, adjust=False).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD 指标。

    Returns:
        DataFrame: DIF(快慢线差), DEA(信号线), MACD(柱状图)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    macd_bar = (dif - dea) * 2
    return pd.DataFrame({"DIF": dif, "DEA": dea, "MACD": macd_bar})


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """相对强弱指标 RSI。

    RSI > 70 通常认为超买，< 30 超卖。
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_value = 100 - (100 / (1 + rs))
    return rsi_value


def bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """布林带。

    Returns:
        DataFrame: middle(中轨), upper(上轨), lower(下轨), width(带宽)
    """
    middle = moving_average(close, window)
    std = close.rolling(window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    width = (upper - lower) / middle * 100
    return pd.DataFrame(
        {
            "middle": middle,
            "upper": upper,
            "lower": lower,
            "width": width,
        }
    )


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """KDJ 随机指标。

    Returns:
        DataFrame: K, D, J 三线
    """
    lowest_low = low.rolling(n).min()
    highest_high = high.rolling(n).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)

    k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
    d = k.ewm(alpha=1 / m2, adjust=False).mean()
    j = 3 * k - 2 * d

    return pd.DataFrame({"K": k, "D": d, "J": j})


def volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """滚动波动率（年化）。"""
    return returns.rolling(window).std() * np.sqrt(252) * 100


def sharpe_rolling(
    returns: pd.Series,
    window: int = 60,
    rf: float = 0.02,
) -> pd.Series:
    """滚动夏普比率。"""
    roll_ret = returns.rolling(window).mean() * 252
    roll_vol = returns.rolling(window).std() * np.sqrt(252)
    return (roll_ret - rf) / roll_vol.replace(0, np.nan)


def max_drawdown_rolling(nav: pd.Series, window: int = 60) -> pd.Series:
    """滚动最大回撤。"""
    return nav.rolling(window).apply(lambda x: (x / x.cummax() - 1).min()) * 100


def compute_all_indicators(nav_df: pd.DataFrame) -> pd.DataFrame:
    """一次性计算所有常用技术指标。

    Args:
        nav_df: 包含 date, nav, daily_return 列的 DataFrame

    Returns:
        新增多列技术指标的 DataFrame (新对象，不修改原数据)
    """
    result = nav_df.copy()
    close = result["nav"]
    returns = result["daily_return"]

    result["MA20"] = moving_average(close, 20)
    result["MA60"] = moving_average(close, 60)
    result["MA120"] = moving_average(close, 120)

    macd_df = macd(close)
    result["MACD_DIF"] = macd_df["DIF"]
    result["MACD_DEA"] = macd_df["DEA"]
    result["MACD_BAR"] = macd_df["MACD"]

    result["RSI14"] = rsi(close, 14)

    bb = bollinger_bands(close)
    result["BB_upper"] = bb["upper"]
    result["BB_middle"] = bb["middle"]
    result["BB_lower"] = bb["lower"]

    result["vol_20d"] = volatility(returns, 20)
    result["max_dd_60d"] = max_drawdown_rolling(close, 60)

    return result
