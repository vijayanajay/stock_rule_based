# Rule Functions Documentation

This document describes all technical indicator functions available in the KISS Signal CLI system.

## Core Philosophy
All rule functions follow these principles:
- **Pure functions**: No side effects, deterministic output
- **Pandas vectorized**: High performance with no explicit loops
- **Consistent interface**: All functions accept DataFrame and return boolean Series
- **Defensive programming**: Comprehensive input validation and error handling

## Function Categories

### 1. Moving Average Indicators

#### SMA Crossover
**Function:** `sma_crossover(price_data, fast_period=10, slow_period=20)`  
**Purpose:** Generate buy signals when fast SMA crosses above slow SMA  
**Signal:** Fast SMA > Slow SMA AND previous: Fast SMA <= Slow SMA  
**Usage:** Primary trend-following signal for momentum strategies  
**Parameters:**
- `fast_period`: Fast moving average period (default: 10)
- `slow_period`: Slow moving average period (default: 20)
- Constraint: fast_period < slow_period

**Example:**
```python
signals = sma_crossover(price_data, fast_period=5, slow_period=20)
```

#### EMA Crossover  
**Function:** `ema_crossover(price_data, fast_period=10, slow_period=20)`  
**Purpose:** Generate buy signals when fast EMA crosses above slow EMA  
**Signal:** Fast EMA > Slow EMA AND previous: Fast EMA <= Slow EMA  
**Usage:** More responsive alternative to SMA crossover  
**Math:** Uses pandas exponential smoothing with `ewm(span=period)`

### 2. Momentum Indicators

#### RSI Oversold (Confirmation)
**Function:** `rsi_oversold(price_data, period=14, oversold_threshold=30.0)`  
**Purpose:** Confirmation filter based on RSI momentum  
**Signal:** RSI > 40 OR (RSI >= 30 AND previous RSI < 30)  
**Usage:** Confirm other signals when momentum is favorable  
**Math:** Wilder's RSI calculation with exponential smoothing

#### MACD Crossover
**Function:** `macd_crossover(price_data, fast_period=12, slow_period=26, signal_period=9)`  
**Purpose:** Generate signals when MACD line crosses above signal line  
**Signal:** MACD > Signal AND previous: MACD <= Signal  
**Usage:** Momentum confirmation for trend changes  
**Math:** MACD = EMA(12) - EMA(26), Signal = EMA(MACD, 9)

### 3. Volume Indicators

#### Volume Spike
**Function:** `volume_spike(price_data, period=20, spike_multiplier=2.0, price_change_threshold=0.01)`  
**Purpose:** Detect unusual volume with price confirmation  
**Signal:** Volume > 2x average AND |price_change| > 1%  
**Usage:** Confirmation filter for momentum trades  
**Parameters:**
- `period`: Rolling average period for volume calculation (default: 20)
- `spike_multiplier`: Volume threshold multiplier (default: 2.0 = 200% of average)  
- `price_change_threshold`: Minimum price change percentage (default: 0.01 = 1%)

**Conditions:**
1. Current volume > spike_multiplier × rolling_average(volume, period)
2. |daily_price_change| > price_change_threshold
3. Both conditions must occur on same day

### 4. Candlestick Patterns

#### Hammer Pattern
**Function:** `hammer_pattern(price_data, body_ratio=0.3, shadow_ratio=2.0)`  
**Purpose:** Single-candle reversal pattern detection  
**Signal:** Small body, long lower shadow, small upper shadow  
**Usage:** Reversal signal at support levels  

**Mathematical Definition:**
- Body = |close - open|
- Lower shadow = min(open, close) - low  
- Upper shadow = high - max(open, close)
- Total range = high - low

**Conditions:**
1. Body ≤ body_ratio × total_range (default: 30%)
2. Lower_shadow ≥ shadow_ratio × body (default: 200%)
3. Upper_shadow ≤ body

#### Engulfing Pattern  
**Function:** `engulfing_pattern(price_data, min_body_ratio=1.2)`  
**Purpose:** Two-candle bullish reversal pattern  
**Signal:** Current green candle engulfs previous red candle  
**Usage:** Strong reversal signal with high reliability

**Conditions:**
1. Previous candle: red (close < open)
2. Current candle: green (close > open)  
3. Current body ≥ min_body_ratio × previous body (default: 120%)
4. Current close > previous open (engulfs top)
5. Current open < previous close (engulfs bottom)

### 5. Volatility Indicators

#### Bollinger Squeeze
**Function:** `bollinger_squeeze(price_data, period=20, std_dev=2.0, squeeze_threshold=0.1)`  
**Purpose:** Breakout signals after Bollinger Band squeeze  
**Signal:** Price breaks above upper band after period of low volatility  
**Usage:** Volatility breakout strategy

**Mathematical Definition:**
- Bollinger Bands: SMA ± (std_dev × rolling_std)
- Band width = (Upper Band - Lower Band) / Middle Band
- Squeeze: band width < squeeze_threshold
- Signal: price > upper_band AND was_in_squeeze

**Algorithm:**
1. Calculate 20-period SMA and standard deviation
2. Upper band = SMA + (2.0 × std), Lower band = SMA - (2.0 × std)
3. Detect squeeze when normalized band width < 0.1 (10%)
4. Signal when price breaks above upper band after squeeze period

## Performance Guidelines

### Benchmark Targets (1000 rows)
- `volume_spike()`: < 50ms
- `hammer_pattern()`: < 30ms  
- `engulfing_pattern()`: < 40ms
- `macd_crossover()`: < 60ms
- `bollinger_squeeze()`: < 80ms

### Optimization Techniques
- Use `pd.Series.rolling()` instead of manual loops
- Prefer `pd.DataFrame[['col1', 'col2']].min(axis=1)` over `apply(min)`
- Cache expensive calculations (EMA, rolling averages)
- Use `fillna(False)` instead of complex null handling

## Error Handling

### Common Validation Patterns
```python
# Column validation
_validate_ohlcv_columns(price_data, ['close', 'volume'])

# Parameter validation  
if period <= 0:
    raise ValueError(f"period ({period}) must be > 0")

# Data sufficiency
if len(price_data) < period:
    logger.warning(f"Insufficient data: {len(price_data)} rows, need {period}")
    return pd.Series(False, index=price_data.index)
```

### Standard Return Pattern
All functions return boolean Series with:
- `True` for buy signal rows
- `False` for all other rows
- Proper index alignment with input DataFrame
- `fillna(False)` to handle NaN values

## Integration Points

### With Backtester
- Functions work directly with `generate_signals()` 
- Signal counting for strategy optimization
- Parameter sweeping for optimization

### With Reporter  
- Signal counting and formatting
- Support for new signal types
- Performance reporting integration

### With Configuration
- Parameter validation follows rules.yaml schema
- Supports all parameter types and constraints
- Clear error messages for invalid configurations

### With CLI
- `--verbose` flag logs signal counts for debugging
- Progress display during rule evaluation
- Real-time feedback on signal generation

## Helper Functions

### `calculate_rsi(prices, period=14)`
**Purpose:** Calculate Relative Strength Index using Wilder's method  
**Returns:** RSI values (0-100 range)  
**Used by:** `rsi_oversold()` function

### `_validate_ohlcv_columns(price_data, required)`
**Purpose:** Validate required columns exist in DataFrame  
**Raises:** ValueError with clear message if columns missing  
**Used by:** All indicator functions for input validation
