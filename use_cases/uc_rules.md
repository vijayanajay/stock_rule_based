| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_RULES_BS_UC007 – Evaluate Technical Indicator Rule | Date: 08/07/24 |

# KS_RULES_BS_UC007 – Evaluate Technical Indicator Rule

**1. Brief Description**

This use case allows an actor to evaluate a specific technical indicator rule (e.g., SMA Crossover, RSI Oversold) against a series of historical price data to generate a boolean series of trading signals.

The use case can be called:
- By the Backtester module to generate entry signals during strategy evaluation.
- By the Reporter module to check for live signals on the latest price data.

**2. Actors**

**2.1 Primary Actors**
1. **Backtester Module** – Requires signal generation for backtesting.
2. **Reporter Module** – Requires signal generation for identifying new trades.

**2.2 Secondary Actors**
- pandas Library

**3. Conditions**

**3.1 Pre-Condition**
- A pandas DataFrame containing historical OHLCV price data is available.
- The parameters for the specific rule (e.g., `fast_period`, `slow_period`) are valid.

**3.2 Post Conditions on success**
1. A boolean pandas Series is returned, with the same index as the input price data.
2. `True` values in the series indicate a buy signal occurred on that date.

**3.3 Post Conditions on Failure**
1. An exception (`ValueError`) is raised for invalid parameters.
2. An empty or all-`False` series is returned for insufficient data.

**4. Trigger**

1. A request to evaluate a rule is issued by a Primary Actor. This request must contain:
    a. A pandas DataFrame of price data (`price_data`).
    b. Rule-specific parameters (e.g., `fast_period`, `slow_period` for `sma_crossover`).

**5. Main Flow: KS_RULES_BS_UC007.MF – Evaluate SMA Crossover Rule**

10. The system receives the `price_data` DataFrame, a `fast_period`, and a `slow_period`.
    10.10. The system validates that price_data is not empty.
    <<len(price_data) > 0>>
    10.20. The system validates that required 'close' column exists.
    <<'close' in price_data.columns>>

20. The system validates that the parameters are logical.
    20.10. The system checks that fast_period is positive.
    <<fast_period > 0>>
    20.20. The system checks that slow_period is positive.
    <<slow_period > 0>>
    20.30. The system checks that fast_period is less than slow_period.
    <<fast_period < slow_period>>
    *See Exception Flow 1: KS_RULES_BS_UC007.XF01 – Invalid Parameters*

30. The system checks if there is enough data to perform the calculation.
    30.10. The system validates minimum data length against slow_period.
    <<len(price_data) >= slow_period>>
    30.20. The system logs warning if data is insufficient.
    *See Exception Flow 2: KS_RULES_BS_UC007.XF02 – Insufficient Data*

40. The system calculates the fast Simple Moving Average (SMA) on the 'close' price series.
    40.10. The system applies rolling window calculation for fast SMA with min_periods requirement.
    <<fast_sma = close_prices.rolling(window=fast_period, min_periods=fast_period).mean()>>
    40.20. The min_periods parameter ensures no SMA values are calculated until sufficient data exists.
    40.30. The system handles NaN values in early periods due to insufficient data for the rolling window.
    40.40. Rolling window uses pandas efficient vectorized operations for performance.

50. The system calculates the slow Simple Moving Average (SMA).
    50.10. The system applies rolling window calculation for slow SMA with min_periods requirement.
    <<slow_sma = close_prices.rolling(window=slow_period, min_periods=slow_period).mean()>>
    50.20. The slow SMA requires more historical data points than fast SMA due to longer period.
    50.30. The system handles NaN values in early periods due to insufficient data for the rolling window.
    50.40. Both SMAs use arithmetic mean calculation over their respective rolling windows.

60. The system identifies the points where the fast SMA crossed above the slow SMA (bullish crossover).
    60.10. The system detects crossover using current and previous period comparison.
    <<signals = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))>>
    60.20. The crossover logic requires fast SMA to be above slow SMA currently AND below/equal previously.
    60.30. The shift(1) operation accesses the previous period's values for comparison.
    60.40. The system fills NaN values with False for early periods where insufficient data exists.
    <<signals = signals.fillna(False)>>
    60.50. The boolean AND operation ensures both conditions are met simultaneously.
    60.60. The system logs debug information about signal count if debug logging is enabled.
    <<logger.debug(f"SMA crossover signals: {signals.sum()} triggers")>>

70. The system returns the boolean `signals` Series.
    70.10. The system ensures the returned series has the same index as input data.
    70.20. The system logs debug information about signal count if enabled.

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_RULES_BS_UC007.XF01 – Invalid Parameters**

10. At **step 20 of the main flow**, the system determines the parameters are invalid.
    <<fast_period >= slow_period>>
20. The system raises a `ValueError` with a descriptive message.
99. The use case ends.

**6.2 Exception Flow 2: KS_RULES_BS_UC007.XF02 – Insufficient Data**

10. At **step 30 of the main flow**, the system determines there is not enough data for the calculation.
    <<len(price_data) < slow_period>>
20. The system logs a warning and returns an empty or all-`False` boolean Series.
99. The use case ends.

**6.3 Alternative Flow 1: KS_RULES_BS_UC007.AF01 – EMA Crossover Rule**

10. At **step 40 of the main flow**, the system processes an EMA crossover rule instead of SMA.
20. The system calculates fast EMA using exponential weighted moving average.
    <<fast_ema = close_prices.ewm(span=fast_period, adjust=False).mean()>>
30. The system calculates slow EMA using exponential weighted moving average.
    <<slow_ema = close_prices.ewm(span=slow_period, adjust=False).mean()>>
40. The system detects EMA crossover using same logic as SMA crossover.
    <<signals = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))>>
50. The flow continues from **step 70 of the main flow**.

**6.4 Alternative Flow 2: KS_RULES_BS_UC007.AF02 – RSI Oversold Rule**

10. At **step 40 of the main flow**, the system processes an RSI oversold rule instead of SMA crossover.
20. The system calculates RSI using the calculate_rsi helper function.
    <<rsi = calculate_rsi(price_data['close'], period)>>
30. The calculate_rsi function computes price changes and separates gains from losses.
    <<delta = prices.diff(); gains = delta.where(delta > 0, 0); losses = -delta.where(delta < 0, 0)>>
40. The system applies Wilder's exponential smoothing to average gains and losses.
    <<alpha = 1.0 / period; avg_gains = gains.ewm(alpha=alpha, adjust=False).mean(); avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()>>
50. The system calculates RSI using the standard formula with division by zero protection.
    <<rs = avg_gains / avg_losses.where(avg_losses != 0, 1e-10); rsi = 100 - (100 / (1 + rs))>>
60. The system detects oversold recovery signals when RSI crosses below threshold.
    <<signals = (rsi < oversold_threshold) & (rsi.shift(1) >= oversold_threshold)>>
70. The flow continues from **step 70 of the main flow**.

**7. Notes / Assumptions**

- All rule functions in the `rules.py` module are pure functions with no side effects.
- The sma_crossover function specifically detects bullish crossovers (fast > slow after fast <= slow).
- The rsi_oversold function calculates RSI using Wilder's exponential smoothing method with alpha = 1/period.
- The rsi_oversold function detects recovery signals when RSI crosses below oversold threshold.
- The ema_crossover function uses pandas ewm(span=period, adjust=False) for exponential moving averages.
- The calculate_rsi helper function implements standard RSI calculation with gain/loss smoothing and division by zero protection.
- All rule functions return boolean pandas Series with the same index as input price data.
- NaN handling ensures early periods (insufficient data) return False signals rather than NaN.
- Rule functions validate input parameters and raise ValueError for invalid configurations (e.g., fast_period >= slow_period).
- Debug logging provides signal counts for troubleshooting rule effectiveness.
- The system uses min_periods parameter in rolling calculations to ensure sufficient data before computing averages.
- RSI calculation handles edge cases with 1e-10 minimum value to avoid division by zero.
- All crossover functions use shift(1) to compare current vs previous period values for signal detection.

**8. Issues**

| No: | Description: | Date | Action: | Status |
|---|---|---|---|---|
| 1. | | | | |

**9. Revision History**

| Date | Rev | Who | Description | Reference |
|---|---|---|---|---|
| 08/07/24 | 1.0 | AI | Initial document creation. | |

**10. Reference Documentation**

| Document Name | Version | Description | Location |
|---|---|---|---|
| `src/kiss_signal/rules.py` | | Source code for the rule functions module with technical indicator implementations. | Git Repository |
| `pandas` | | Data manipulation library for rolling calculations and time series operations. | PyPI |
