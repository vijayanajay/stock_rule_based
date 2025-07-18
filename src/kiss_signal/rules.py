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
    "price_above_sma",
    # New functions (Story 015)
    "sma_cross_under",
    "stop_loss_pct",
    "take_profit_pct",
    # New functions (Story 018) - ATR-based exits
    "calculate_atr",
    "stop_loss_atr",
    "take_profit_atr",
    # New functions (Story 019) - Market context filters
    "market_above_sma",
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


def price_above_sma(price_data: pd.DataFrame, period: int = 50) -> pd.Series:
    """
    Generates a confirmation signal if the closing price is above its SMA.
    """
    _validate_ohlcv_columns(price_data, ['close'])
    if len(price_data) < period:
        return pd.Series(False, index=price_data.index)
    sma = price_data['close'].rolling(window=period).mean()
    signals = price_data['close'] > sma
    return signals.fillna(False)

# =============================================================================
# Story 015: Dynamic Exit Conditions
# =============================================================================

def sma_cross_under(price_data: pd.DataFrame, fast_period: int, slow_period: int) -> pd.Series:
    """
    Generates sell signals when the fast SMA crosses below the slow SMA.
    
    Args:
        price_data: DataFrame with OHLCV data
        fast_period: Period for the fast SMA
        slow_period: Period for the slow SMA
        
    Returns:
        Boolean Series where True indicates a bearish crossover
    """
    _validate_ohlcv_columns(price_data, ['close'])
    
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be less than slow_period ({slow_period})")
    
    if len(price_data) < slow_period + 1:
        return pd.Series(False, index=price_data.index)
    
    # Calculate SMAs
    fast_sma = price_data['close'].rolling(window=fast_period).mean()
    slow_sma = price_data['close'].rolling(window=slow_period).mean()
    
    # Check for crossover: fast was above slow, now it's below
    previous_above = (fast_sma.shift(1) > slow_sma.shift(1))
    current_below = (fast_sma < slow_sma)
    crossover = previous_above & current_below
    
    logger.debug(f"SMA cross under signals: {crossover.sum()} triggers")
    return crossover.fillna(False)


def stop_loss_pct(price_data: pd.DataFrame, percentage: float) -> pd.Series:
    """
    Placeholder rule for percentage-based stop loss.
    
    This rule's logic is special-cased by the backtester and reporter.
    The actual stop-loss check is performed against daily price movements,
    not as a boolean signal like other rules.
    
    Args:
        price_data: DataFrame with OHLCV data (unused)
        percentage: Stop loss percentage (must be > 0)
        
    Returns:
        Series of all False values (logic handled elsewhere)
    """
    if percentage <= 0:
        raise ValueError(f"percentage must be > 0, got {percentage}")
    
    logger.debug(f"Stop loss percentage: {percentage:.1%}")
    return pd.Series(False, index=price_data.index)


def take_profit_pct(price_data: pd.DataFrame, percentage: float) -> pd.Series:
    """
    Placeholder rule for percentage-based take profit.
    
    This rule's logic is special-cased by the backtester and reporter.
    The actual take-profit check is performed against daily price movements,
    not as a boolean signal like other rules.
    
    Args:
        price_data: DataFrame with OHLCV data (unused)
        percentage: Take profit percentage (must be > 0)
        
    Returns:
        Series of all False values (logic handled elsewhere)
    """
    if percentage <= 0:
        raise ValueError(f"percentage must be > 0, got {percentage}")
    
    logger.debug(f"Take profit percentage: {percentage:.1%}")
    return pd.Series(False, index=price_data.index)

# =============================================================================
# Story 018: ATR-Based Dynamic Exit Conditions
# =============================================================================

def calculate_atr(price_data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range indicator.
    
    ATR measures volatility by calculating the average of true ranges over a period.
    Uses Wilder's smoothing method (same as RSI) for consistency.
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'high', 'low', 'close' columns)
        period: ATR calculation period (default 14)
        
    Returns:
        Series of ATR values, aligned with price_data index
        
    Raises:
        ValueError: If missing required columns or invalid parameters
        
    Example:
        >>> atr = calculate_atr(price_data, period=14)
        >>> print(f"Current ATR: {atr.iloc[-1]:.2f}")
    """
    if period <= 1:
        raise ValueError(f"period ({period}) must be > 1")
    
    # Handle empty DataFrame
    if len(price_data) == 0:
        return pd.Series(dtype=float, name='atr')
        
    _validate_ohlcv_columns(price_data, ['high', 'low', 'close'])
    
    # If we have some data but less than the requested period,
    # adapt by using the available data length as the period
    # This is a key improvement for handling the early rows in a dataset
    if len(price_data) < period:
        if len(price_data) >= 3:  # Need at least 3 points for a meaningful ATR calculation
            # Dynamically adjust the period to use all available data
            # This ensures we can calculate ATR values even at the beginning of a dataset
            adjusted_period = len(price_data)
            # Use debug level instead of info to reduce log noise in logs
            logger.debug(f"Adapting ATR calculation: using {adjusted_period} rows instead of {period}")
            period = adjusted_period
        else:
            # When we have fewer than 3 data points, we can't calculate a meaningful ATR
            # Use debug level instead of warning to reduce log noise
            logger.debug(f"Insufficient data for ATR: {len(price_data)} rows, need at least 3")
            # Return a Series filled with NaN values with the same index as the input data
            # This ensures alignment with the original data for any subsequent calculations
            return pd.Series(float('nan'), index=price_data.index)
    
    # Calculate True Range for each period
    # TR = max(H-L, abs(H-C_prev), abs(L-C_prev))
    high = price_data['high']
    low = price_data['low']
    close = price_data['close']
    prev_close = close.shift(1)
    
    tr1 = high - low  # High - Low
    tr2 = (high - prev_close).abs()  # abs(High - Previous Close)
    tr3 = (low - prev_close).abs()   # abs(Low - Previous Close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # First period has no previous close, so TR = H - L only
    true_range.iloc[0] = high.iloc[0] - low.iloc[0]
    
    # Apply Wilder's smoothing (same as RSI calculation)
    # ATR = EWM with alpha = 1/period, but only start calculation after period-1 values
    alpha = 1.0 / period
    atr = true_range.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    
    logger.debug(f"Calculated ATR: {atr.count()} valid values")
    return atr


def stop_loss_atr(
    price_data: pd.DataFrame, 
    entry_price: float, 
    period: int = 14, 
    multiplier: float = 2.0
) -> bool:
    """Check if ATR-based stop loss condition is triggered.
    
    Stop loss triggers when current price drops below entry_price - (multiplier * current_ATR).
    This provides volatility-adaptive risk management that adjusts to each stock's characteristics.
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'high', 'low', 'close' columns)
        entry_price: Price at which position was entered
        period: ATR calculation period (default 14)
        multiplier: ATR multiplier for stop distance (default 2.0)
        
    Returns:
        True if stop loss is triggered, False otherwise
        
    Raises:
        ValueError: If invalid parameters
        
    Example:
        >>> triggered = stop_loss_atr(price_data, entry_price=100.0, multiplier=2.0)
        >>> if triggered:
        ...     print("Stop loss triggered - exit position")
    """
    if period <= 1:
        raise ValueError(f"period ({period}) must be > 1")
    if multiplier <= 0:
        raise ValueError(f"multiplier ({multiplier}) must be > 0")
    if entry_price <= 0:
        raise ValueError(f"entry_price ({entry_price}) must be > 0")
    
    if len(price_data) == 0:
        return False
        
    # Calculate current ATR
    atr = calculate_atr(price_data, period)
    if pd.isna(atr.iloc[-1]):
        logger.debug("ATR calculation returned NaN, skipping ATR stop loss check")
        return False
    
    current_price = price_data['close'].iloc[-1]
    current_atr = atr.iloc[-1]
    stop_level = entry_price - (multiplier * current_atr)
    
    triggered = current_price <= stop_level
    
    if triggered:
        logger.debug(f"ATR stop loss triggered: price={current_price:.2f}, "
                    f"stop_level={stop_level:.2f}, entry={entry_price:.2f}, "
                    f"atr={current_atr:.2f}, multiplier={multiplier}")
    
    return triggered


def take_profit_atr(
    price_data: pd.DataFrame, 
    entry_price: float, 
    period: int = 14, 
    multiplier: float = 4.0
) -> bool:
    """Check if ATR-based take profit condition is triggered.
    
    Take profit triggers when current price rises above entry_price + (multiplier * current_ATR).
    This provides volatility-adaptive profit targets that maintain consistent risk-reward ratios.
    
    Args:
        price_data: DataFrame with OHLCV data (must have 'high', 'low', 'close' columns)
        entry_price: Price at which position was entered
        period: ATR calculation period (default 14)
        multiplier: ATR multiplier for profit target distance (default 4.0)
        
    Returns:
        True if take profit is triggered, False otherwise
        
    Raises:
        ValueError: If invalid parameters
        
    Example:
        >>> triggered = take_profit_atr(price_data, entry_price=100.0, multiplier=4.0)
        >>> if triggered:
        ...     print("Take profit triggered - exit position with profit")
    """
    if period <= 1:
        raise ValueError(f"period ({period}) must be > 1")
    if multiplier <= 0:
        raise ValueError(f"multiplier ({multiplier}) must be > 0")
    if entry_price <= 0:
        raise ValueError(f"entry_price ({entry_price}) must be > 0")
    
    if len(price_data) == 0:
        return False
        
    # Calculate current ATR
    atr = calculate_atr(price_data, period)
    if pd.isna(atr.iloc[-1]):
        logger.debug("ATR calculation returned NaN, skipping ATR take profit check")
        return False
    
    current_price = price_data['close'].iloc[-1]
    current_atr = atr.iloc[-1]
    profit_level = entry_price + (multiplier * current_atr)
    
    triggered = current_price >= profit_level
    
    if triggered:
        logger.debug(f"ATR take profit triggered: price={current_price:.2f}, "
                    f"profit_level={profit_level:.2f}, entry={entry_price:.2f}, "
                    f"atr={current_atr:.2f}, multiplier={multiplier}")
    
    return triggered


# =============================================================================
# Story 019: Market Context Filters
# =============================================================================

def market_above_sma(market_data: pd.DataFrame, period: int = 50) -> pd.Series:
    """Check if market index is above its Simple Moving Average.
    
    This represents a bullish market regime where long strategies 
    typically perform better.
    
    Args:
        market_data: DataFrame with OHLCV data for market index (e.g., NIFTY 50)
        period: SMA period in days (default: 50)
        
    Returns:
        Boolean Series with True when market is above SMA
        
    Raises:
        ValueError: If invalid parameters or missing required columns
        
    Example:
        >>> bullish_periods = market_above_sma(nifty_data, period=50)
        >>> print(f"Market bullish {bullish_periods.sum()} out of {len(bullish_periods)} days")
    """
    _validate_ohlcv_columns(market_data, ['close'])
    
    if period <= 0:
        raise ValueError(f"SMA period must be positive, got {period}")
    
    # Check sufficient data for SMA calculation
    if len(market_data) < period:
        logger.warning(f"Insufficient market data: {len(market_data)} rows, need {period}")
        return pd.Series(False, index=market_data.index)
    
    # Calculate SMA
    sma = market_data['close'].rolling(window=period).mean()
    
    # Market is bullish when price > SMA
    bullish_signals = market_data['close'] > sma
    
    signal_count = bullish_signals.sum()
    total_periods = len(bullish_signals)
    logger.debug(f"Market above {period}-day SMA: {signal_count}/{total_periods} days "
                f"({signal_count/total_periods*100:.1f}%)")
    
    return bullish_signals.fillna(False)
