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
    # New functions (Story 013)
    "volume_spike",
    "hammer_pattern", 
    "engulfing_pattern",
    "macd_crossover",
    "bollinger_squeeze",
]

logger = logging.getLogger(__name__)


def _validate_ohlcv_columns(price_data: pd.DataFrame, required: list[str]) -> None:
    """Validate required columns exist in DataFrame."""
    missing = [col for col in required if col not in price_data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


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


def volume_spike(price_data: pd.DataFrame,
                period: int = 20,
                spike_multiplier: float = 2.0,
                price_change_threshold: float = 0.01) -> pd.Series:
    """Detect volume spikes with price confirmation.
    
    Signal when:
    1. Volume > spike_multiplier * rolling_average(volume, period)
    2. |price_change| > price_change_threshold (1%)
    3. Both conditions on same day
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close', 'volume' columns)
        period: Rolling average period for volume calculation
        spike_multiplier: Volume threshold multiplier (2.0 = 200% of average)
        price_change_threshold: Minimum price change percentage (0.01 = 1%)
        
    Returns:
        Boolean Series with True for volume spike signals
        
    Raises:
        ValueError: If missing required columns or invalid parameters
    """
    if period <= 0:
        raise ValueError(f"period ({period}) must be > 0")
    if spike_multiplier <= 1.0:
        raise ValueError(f"spike_multiplier ({spike_multiplier}) must be > 1.0")
    if price_change_threshold <= 0:
        raise ValueError(f"price_change_threshold ({price_change_threshold}) must be > 0")
        
    _validate_ohlcv_columns(price_data, ['close', 'volume'])
    
    if len(price_data) < period:
        logger.warning(f"Insufficient data for volume spike: {len(price_data)} rows, need {period}")
        return pd.Series(False, index=price_data.index)
    
    # Volume condition
    avg_volume = price_data['volume'].rolling(period, min_periods=period).mean()
    volume_condition = price_data['volume'] > (spike_multiplier * avg_volume)
    
    # Price change condition  
    price_change = price_data['close'].pct_change().abs()
    price_condition = price_change > price_change_threshold
    
    signals = volume_condition & price_condition
    
    logger.debug(f"Volume spike signals: {signals.sum()} triggers")
    return signals.fillna(False)


def hammer_pattern(price_data: pd.DataFrame,
                  body_ratio: float = 0.3,
                  shadow_ratio: float = 2.0) -> pd.Series:
    """Detect hammer/hanging man candlestick patterns.
    
    Conditions:
    1. Body ≤ body_ratio * total_range
    2. Lower_shadow ≥ shadow_ratio * body
    3. Upper_shadow ≤ lower_shadow / 2.0
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'open', 'high', 'low', 'close' columns)
        body_ratio: Maximum body size as ratio of total range (0.3 = 30%)
        shadow_ratio: Minimum lower shadow as ratio of body size (2.0 = 200%)
        
    Returns:
        Boolean Series with True for hammer pattern signals
        
    Raises:
        ValueError: If missing required columns or invalid parameters
    """
    if not (0 < body_ratio < 1):
        raise ValueError(f"body_ratio ({body_ratio}) must be between 0 and 1")
    if shadow_ratio <= 0:
        raise ValueError(f"shadow_ratio ({shadow_ratio}) must be > 0")
        
    _validate_ohlcv_columns(price_data, ['open', 'high', 'low', 'close'])
    
    if len(price_data) == 0:
        return pd.Series(False, index=price_data.index)
    
    body = (price_data['close'] - price_data['open']).abs()
    total_range = price_data['high'] - price_data['low']
    lower_shadow = price_data[['open', 'close']].min(axis=1) - price_data['low']
    upper_shadow = price_data['high'] - price_data[['open', 'close']].max(axis=1)
    
    # Exclude doji candles (zero body) to avoid division by zero
    has_body = body > 0
    
    # Hammer conditions
    small_body = body <= (body_ratio * total_range)
    long_lower_shadow = has_body & (lower_shadow >= (shadow_ratio * body))
    small_upper_shadow = upper_shadow <= (lower_shadow / 2.0)
    
    signals = has_body & small_body & long_lower_shadow & small_upper_shadow
    
    logger.debug(f"Hammer pattern signals: {signals.sum()} triggers")
    return signals.fillna(False)


def engulfing_pattern(price_data: pd.DataFrame,
                     min_body_ratio: float = 1.2) -> pd.Series:
    """Detect bullish engulfing candlestick patterns.
    
    Conditions:
    1. Previous candle: red (close < open)
    2. Current candle: green (close > open)  
    3. Current body >= min_body_ratio * previous body
    4. Current close > previous open
    5. Current open < previous close
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'open', 'close' columns)
        min_body_ratio: Minimum current body size as ratio of previous body (1.2 = 120%)
        
    Returns:
        Boolean Series with True for engulfing pattern signals
        
    Raises:
        ValueError: If missing required columns or invalid parameters
    """
    if min_body_ratio <= 1.0:
        raise ValueError(f"min_body_ratio ({min_body_ratio}) must be > 1.0")
        
    _validate_ohlcv_columns(price_data, ['open', 'close'])
    
    if len(price_data) < 2:
        logger.warning(f"Insufficient data for engulfing pattern: {len(price_data)} rows, need 2")
        return pd.Series(False, index=price_data.index)
    
    current_body = (price_data['close'] - price_data['open']).abs()
    prev_body = current_body.shift(1)
    
    # Color conditions
    prev_red = price_data['close'].shift(1) < price_data['open'].shift(1)
    current_green = price_data['close'] > price_data['open']
    
    # Engulfing conditions
    body_size_ok = current_body >= (min_body_ratio * prev_body)
    engulfs_high = price_data['close'] > price_data['open'].shift(1)
    engulfs_low = price_data['open'] <= price_data['close'].shift(1)
    
    signals = prev_red & current_green & body_size_ok & engulfs_high & engulfs_low
    
    logger.debug(f"Engulfing pattern signals: {signals.sum()} triggers")
    return signals.fillna(False)


def macd_crossover(price_data: pd.DataFrame,
                  fast_period: int = 12,
                  slow_period: int = 26,
                  signal_period: int = 9) -> pd.Series:
    """Generate signals when MACD line crosses above signal line.
    
    Formula: MACD = EMA(fast) - EMA(slow), Signal = EMA(MACD, signal_period)
    Buy when MACD crosses above Signal
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close' column)
        fast_period: Fast EMA period for MACD calculation
        slow_period: Slow EMA period for MACD calculation  
        signal_period: Signal line EMA period
        
    Returns:
        Boolean Series with True for MACD crossover signals
        
    Raises:
        ValueError: If missing required columns or invalid parameters
    """
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")
    if signal_period <= 0:
        raise ValueError(f"signal_period ({signal_period}) must be > 0")
        
    _validate_ohlcv_columns(price_data, ['close'])
    
    min_required = slow_period + signal_period
    if len(price_data) < min_required:
        logger.warning(f"Insufficient data for MACD: {len(price_data)} rows, need {min_required}")
        return pd.Series(False, index=price_data.index)
    
    # Calculate MACD
    ema_fast = price_data['close'].ewm(span=fast_period).mean()
    ema_slow = price_data['close'].ewm(span=slow_period).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period).mean()
    
    # Crossover detection
    signals = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    
    logger.debug(f"MACD crossover signals: {signals.sum()} triggers")
    return signals.fillna(False)


def bollinger_squeeze(price_data: pd.DataFrame,
                     period: int = 20,
                     std_dev: float = 2.0,
                     squeeze_threshold: float = 0.1) -> pd.Series:
    """Detect breakout signals after Bollinger Band squeeze.
    
    Band width = (Upper Band - Lower Band) / Middle Band
    Squeeze when band width < squeeze_threshold
    Signal when price breaks above upper band after squeeze
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'close' column)
        period: Period for moving average and standard deviation
        std_dev: Standard deviation multiplier for bands
        squeeze_threshold: Band width threshold for squeeze detection
        
    Returns:
        Boolean Series with True for breakout signals after squeeze
        
    Raises:
        ValueError: If missing required columns or invalid parameters
    """
    if period <= 0:
        raise ValueError(f"period ({period}) must be > 0")
    if std_dev <= 0:
        raise ValueError(f"std_dev ({std_dev}) must be > 0")
    if squeeze_threshold <= 0:
        raise ValueError(f"squeeze_threshold ({squeeze_threshold}) must be > 0")
        
    _validate_ohlcv_columns(price_data, ['close'])
    
    if len(price_data) < period + 5:  # Need extra periods to detect squeeze
        logger.warning(f"Insufficient data for Bollinger squeeze: {len(price_data)} rows, need {period + 5}")
        return pd.Series(False, index=price_data.index)
    
    # Bollinger Bands
    sma = price_data['close'].rolling(period).mean()
    std = price_data['close'].rolling(period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    
    # Band width (normalized)
    band_width = (upper_band - lower_band) / sma
    
    # Squeeze detection (band width below threshold)
    in_squeeze = band_width < squeeze_threshold
    was_in_squeeze = in_squeeze.shift(1)
    
    # Breakout detection (price above upper band after squeeze)
    breakout = (price_data['close'] > upper_band) & was_in_squeeze
    
    logger.debug(f"Bollinger squeeze signals: {breakout.sum()} triggers")
    return breakout.fillna(False)
