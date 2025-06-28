"""Rules - Core Technical Indicator Implementation.

This module implements the technical analysis indicators used for signal generation.
All functions are pure and operate on pandas DataFrames with OHLCV data.
"""

import logging

import pandas as pd

__all__ = [
    "sma_crossover",
    "rsi_oversold", 
    "ema_crossover",
    "calculate_rsi",
]

logger = logging.getLogger(__name__)


def sma_crossover(price_data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> pd.Series:
    """Generate buy signals when fast SMA crosses above slow SMA.
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close' column)
        fast_period: Period for fast moving average
        slow_period: Period for slow moving average
        
    Returns:
        Boolean Series with True for buy signals, aligned with price_data index
        
    Raises:
        ValueError: If invalid parameters or insufficient data
    """
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")
    
    if len(price_data) < slow_period:
        logger.warning(f"Insufficient data: {len(price_data)} rows, need {slow_period}")
        return pd.Series(False, index=price_data.index)
    
    close_prices = price_data['close']
    fast_sma = close_prices.rolling(window=fast_period, min_periods=fast_period).mean()
    slow_sma = close_prices.rolling(window=slow_period, min_periods=slow_period).mean()
    
    # Crossover: fast crosses above slow
    signals = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
    
    logger.debug(f"SMA crossover signals: {signals.sum()} triggers")
    return signals.fillna(False)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Price series (typically close prices)
        period: RSI calculation period
        
    Returns:
        RSI values (0-100 range)
    """
    if len(prices) < period + 1:
        return pd.Series(float('nan'), index=prices.index)
    
    delta = prices.diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Use exponential smoothing (Wilder's method)
    alpha = 1.0 / period
    avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
    avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()
    
    # Avoid division by zero
    rs = avg_gains / avg_losses.where(avg_losses != 0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def rsi_oversold(price_data: pd.DataFrame, period: int = 14, oversold_threshold: float = 30.0) -> pd.Series:
    """Generate confirmation signals based on RSI momentum.
    
    This acts as a confirmation filter for other signals, allowing trades when:
    1. RSI shows bullish momentum (RSI > 40), OR
    2. RSI is recovering from oversold (was < 30, now >= 30)
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close' column)
        period: RSI calculation period
        oversold_threshold: RSI threshold for oversold condition
        
    Returns:
        Boolean Series with True for confirmation signals
    """
    if len(price_data) < period + 1:
        logger.warning(f"Insufficient data for RSI: {len(price_data)} rows, need {period + 1}")
        return pd.Series(False, index=price_data.index)
    
    rsi = calculate_rsi(price_data['close'], period)
    
    # Confirmation conditions:
    # 1. RSI shows momentum (> 40) - allows most healthy moves
    # 2. OR recovering from oversold (was < 30, now >= 30)
    bullish_momentum = rsi > 40.0
    recovering_from_oversold = (rsi >= oversold_threshold) & (rsi.shift(1) < oversold_threshold)
    
    signals = bullish_momentum | recovering_from_oversold
    
    logger.debug(f"RSI confirmation signals: {signals.sum()} triggers (momentum + recovery)")
    return signals.fillna(False)


def ema_crossover(price_data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> pd.Series:
    """Generate buy signals when fast EMA crosses above slow EMA.
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close' column)
        fast_period: Period for fast exponential moving average
        slow_period: Period for slow exponential moving average
        
    Returns:
        Boolean Series with True for buy signals
    """
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")
    
    if len(price_data) < slow_period:
        logger.warning(f"Insufficient data: {len(price_data)} rows, need {slow_period}")
        return pd.Series(False, index=price_data.index)
    
    close_prices = price_data['close']
    
    # Calculate EMAs using pandas exponential smoothing
    fast_ema = close_prices.ewm(span=fast_period, adjust=False).mean()
    slow_ema = close_prices.ewm(span=slow_period, adjust=False).mean()
      # Crossover: fast crosses above slow
    signals = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
    
    logger.debug(f"EMA crossover signals: {signals.sum()} triggers")
    return signals.fillna(False)
