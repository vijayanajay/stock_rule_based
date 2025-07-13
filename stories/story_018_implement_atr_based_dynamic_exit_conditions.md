# Story 18: Implement ATR-Based Dynamic Exit Conditions

## Status: 📋 READY FOR DEVELOPMENT

**Priority:** High (Volatility-adaptive risk management is essential for robust trading strategies)
**Estimated Story Points:** 5
**Prerequisites:** Story 017 (Per-Stock Strategy Analysis) ✅ Complete
**Created:** 2025-07-13

## User Story
As a trader, I want to implement ATR-based stop losses and take profits so that my exit levels adapt to each stock's volatility rather than using fixed percentages, enabling better risk-adjusted returns across different market conditions and stock characteristics.

## Context & Rationale

The current system uses fixed percentage-based exits (5% stop loss, 15% take profit) which ignore the fundamental difference in volatility between stocks. A 5% move in a high-volatility stock like YES BANK might be normal price action, while the same move in a stable stock like NESTLEIND could signal a significant trend change.

**Average True Range (ATR)** is a volatility indicator that measures the average range between high and low prices over a specified period. Using ATR multiples for exits provides:

- **Volatility-Adaptive Risk Management**: Stop losses that expand/contract based on each stock's natural volatility
- **Consistent Risk-Reward Ratios**: 2x ATR stop loss + 4x ATR take profit = systematic 2:1 reward/risk across all stocks
- **Market-Responsive Exits**: ATR naturally adjusts during high/low volatility periods
- **Stock-Specific Optimization**: Each stock gets exits tuned to its historical price behavior

This story implements the ATR calculation and two new exit rule types (`stop_loss_atr`, `take_profit_atr`) while maintaining the existing fixed percentage options for backward compatibility.

## Technical Implementation Goals

1. **Pure ATR Function**: Calculate Average True Range using standard formula
2. **ATR-Based Exit Rules**: Implement `stop_loss_atr` and `take_profit_atr` rule types
3. **Backtester Integration**: Seamlessly handle ATR exits alongside existing exit types
4. **Configuration Support**: Enable ATR exits in `rules.yaml` with validation
5. **Performance Optimization**: Efficient ATR calculation that doesn't slow down backtesting

## Acceptance Criteria

### AC-1: ATR Calculation Implementation
**Core ATR Function (`src/kiss_signal/rules.py`):**
- [ ] Implement `calculate_atr(price_data: pd.DataFrame, period: int = 14) -> pd.Series`
- [ ] Function uses standard ATR formula: `TR = max(H-L, abs(H-C_prev), abs(L-C_prev))`
- [ ] Returns smoothed average using Wilder's smoothing (like RSI)
- [ ] Handles edge cases: insufficient data, missing values, first period
- [ ] Validates required OHLC columns exist
- [ ] Function is pure (no side effects) and type-hinted
- [ ] Comprehensive unit tests with known ATR values for validation

**Mathematical Specification:**
```python
# True Range for each period
TR = max(
    high - low,
    abs(high - previous_close), 
    abs(low - previous_close)
)

# ATR using Wilder's smoothing (like RSI calculation)
ATR = ewm(TR, alpha=1/period).mean()
```

### AC-2: ATR-Based Exit Rule Functions
**Stop Loss ATR Function (`src/kiss_signal/rules.py`):**
- [ ] Implement `stop_loss_atr(price_data: pd.DataFrame, entry_price: float, period: int = 14, multiplier: float = 2.0) -> bool`
- [ ] Function calculates current ATR and checks if `current_price <= entry_price - (multiplier * current_ATR)`
- [ ] Handles missing ATR data gracefully (returns False if insufficient data)
- [ ] Validates parameters: `period >= 2`, `multiplier > 0`, `entry_price > 0`

**Take Profit ATR Function (`src/kiss_signal/rules.py`):**
- [ ] Implement `take_profit_atr(price_data: pd.DataFrame, entry_price: float, period: int = 14, multiplier: float = 4.0) -> bool`
- [ ] Function calculates current ATR and checks if `current_price >= entry_price + (multiplier * current_ATR)`
- [ ] Same validation and error handling as stop loss version

**Function Signatures:**
```python
def calculate_atr(price_data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range indicator."""

def stop_loss_atr(
    price_data: pd.DataFrame, 
    entry_price: float, 
    period: int = 14, 
    multiplier: float = 2.0
) -> bool:
    """Check if ATR-based stop loss condition is triggered."""

def take_profit_atr(
    price_data: pd.DataFrame, 
    entry_price: float, 
    period: int = 14, 
    multiplier: float = 4.0  
) -> bool:
    """Check if ATR-based take profit condition is triggered."""
```

### AC-3: Backtester Integration
**Enhanced Exit Signal Generation (`src/kiss_signal/backtester.py`):**
- [ ] Modify `_generate_exit_signals()` to handle `stop_loss_atr` and `take_profit_atr` rule types
- [ ] ATR-based exits integrate with existing position tracking (need entry prices)
- [ ] ATR stops take precedence over percentage stops when both are configured
- [ ] Proper error handling for insufficient ATR data (log warning, fall back to time-based exit)
- [ ] Performance optimization: cache ATR calculation per symbol during backtesting

**Entry Price Tracking Enhancement:**
- [ ] Ensure entry prices are available to ATR exit functions during signal generation
- [ ] Handle multiple overlapping positions per symbol (use most recent entry price)
- [ ] Graceful fallback if entry price unavailable (skip ATR check, use other exits)

### AC-4: Configuration Integration
**Rules Configuration (`config/rules.yaml`):**
- [ ] Add validation constraints for ATR parameters in `validation` section
- [ ] Document ATR exit examples in configuration comments
- [ ] Support backward compatibility with existing percentage-based exits

**Example Configuration Addition:**
```yaml
sell_conditions:
  - name: "atr_stop_loss_2x"
    type: "stop_loss_atr"
    description: "Primary Risk Control: Exit if price drops 2x the 14-day ATR from entry. This adapts to each stock's volatility."
    params:
      period: 14
      multiplier: 2.0

  - name: "atr_take_profit_4x"
    type: "take_profit_atr"
    description: "Profit Target: Exit if price rises 4x the 14-day ATR from entry. Enforces a 2:1 Reward/Risk ratio."
    params:
      period: 14
      multiplier: 4.0

  - name: "trend_break_exit"
    type: "sma_cross_under"
    description: "Dynamic Exit: Exit if the short-term trend breaks (10-day SMA crosses below 20-day SMA)."
    params:
      fast_period: 10
      slow_period: 20

# Validation constraints
validation:
  stop_loss_atr:
    period: {min: 5, max: 50}
    multiplier: {min: 0.5, max: 5.0}
  take_profit_atr:
    period: {min: 5, max: 50} 
    multiplier: {min: 1.0, max: 10.0}
```

### AC-5: Performance & Quality Assurance
**Code Quality:**
- [ ] All new functions pass `mypy --strict` type checking
- [ ] Functions added to `__all__` exports in `rules.py`
- [ ] Comprehensive docstrings with examples and edge cases
- [ ] No circular imports or dependency issues

**Performance Requirements:**
- [ ] ATR calculation adds < 10ms per symbol during backtesting
- [ ] Memory usage remains constant (no memory leaks in ATR calculation)
- [ ] Bulk ATR calculation efficient for 100+ symbols

**Integration Testing:**
- [ ] End-to-end test: `quickedge run` with ATR exits generates valid reports
- [ ] Backtesting with ATR exits produces expected metrics (Sharpe, win rate, etc.)
- [ ] Mixed exit conditions (ATR + percentage + indicator) work correctly together
- [ ] ATR exits integrate with per-stock strategy analysis from Story 017

## Architectural Considerations

### ATR Calculation Strategy
**Mathematical Accuracy:**
- Use Wilder's smoothing method (same as RSI) for consistency
- Handle the initial period where ATR is undefined (first 14 days)
- Ensure numerical stability for extreme price movements

**Performance Considerations:**
- Calculate ATR once per symbol and reuse across multiple exit checks
- Use pandas vectorized operations for bulk ATR calculation
- Cache ATR values during backtesting to avoid recalculation

### Exit Rule Integration
**Rule Type Hierarchy:**
- ATR-based exits take precedence over percentage-based when both configured
- Indicator exits (SMA cross under) checked alongside ATR exits
- Time-based exits remain as ultimate fallback

**Entry Price Management:**
- Leverage existing position tracking for entry price availability
- Handle edge case where entry price is unavailable (new positions)
- Support multiple concurrent positions per symbol

### Configuration Design
**Backward Compatibility:**
- Existing percentage-based exits continue working unchanged
- New ATR parameters validated independently
- Clear error messages for invalid ATR configurations

**Extensibility:**
- ATR calculation available for future rule types (trailing stops, volatility filters)
- Pattern supports adding other volatility-based indicators (Bollinger Bands width, etc.)

## Detailed Task Breakdown

### Task 1: Core ATR Implementation (1.5 SP)
**File:** `src/kiss_signal/rules.py`
- [ ] Implement `calculate_atr()` function with Wilder's smoothing
- [ ] Add comprehensive unit tests with known ATR values
- [ ] Handle edge cases: insufficient data, NaN values, zero ranges
- [ ] Optimize for pandas vectorization
- [ ] Add function to `__all__` exports

**Mathematical Validation:**
- Use sample OHLC data with known ATR values for testing
- Verify calculation matches popular charting software (TradingView, MetaTrader)
- Test edge cases: gaps, limit up/down days, holiday periods

### Task 2: ATR Exit Functions (1.5 SP)
**File:** `src/kiss_signal/rules.py`
- [ ] Implement `stop_loss_atr()` and `take_profit_atr()` functions
- [ ] Parameter validation and error handling
- [ ] Unit tests for various market scenarios
- [ ] Integration with existing position data structures
- [ ] Performance optimization for backtesting loop

**Test Scenarios:**
- High volatility stock (ATR = 5% of price)
- Low volatility stock (ATR = 1% of price)  
- Trending vs choppy market conditions
- Gap up/down scenarios affecting ATR

### Task 3: Backtester Integration (1.5 SP)
**File:** `src/kiss_signal/backtester.py`
- [ ] Modify `_generate_exit_signals()` for ATR exit types
- [ ] Entry price tracking enhancement
- [ ] ATR caching for performance
- [ ] Error handling and fallback logic
- [ ] Integration testing with existing exit types

**Implementation Details:**
```python
# In _generate_exit_signals()
elif rule_def.type in ['stop_loss_atr', 'take_profit_atr']:
    # Get entry price from position tracking
    entry_price = self._get_current_entry_price(symbol, current_date)
    if entry_price is not None:
        if rule_def.type == 'stop_loss_atr':
            triggered = stop_loss_atr(price_data, entry_price, **rule_def.params)
        else:  # take_profit_atr
            triggered = take_profit_atr(price_data, entry_price, **rule_def.params)
        
        if triggered:
            exit_signals_list.append(pd.Series([True], index=[current_date]))
```

### Task 4: Configuration & Validation (0.5 SP)
**Files:** `config/rules.yaml`, `src/kiss_signal/config.py`
- [ ] Add ATR exit examples to rules.yaml
- [ ] Implement validation constraints for ATR parameters
- [ ] Update documentation with ATR exit usage
- [ ] Test configuration loading and validation

**Validation Logic:**
```python
# In config validation
'stop_loss_atr': {
    'period': {'min': 5, 'max': 50},
    'multiplier': {'min': 0.5, 'max': 5.0}
},
'take_profit_atr': {
    'period': {'min': 5, 'max': 50}, 
    'multiplier': {'min': 1.0, 'max': 10.0}
}
```

### Task 5: Testing & Documentation (1.0 SP)
**Files:** `tests/test_rule_funcs.py`, `tests/test_backtester.py`
- [ ] Comprehensive unit tests for ATR functions
- [ ] Integration tests for ATR exits in backtesting
- [ ] End-to-end CLI tests with ATR configuration
- [ ] Performance benchmarks for ATR calculation
- [ ] Update documentation with ATR examples

**Test Coverage Goals:**
- ATR calculation: 95%+ coverage including edge cases
- Exit functions: 90%+ coverage including error conditions
- Backtester integration: 85%+ coverage including fallback scenarios

## Expected Business Impact

### Risk Management Improvement
**Volatility-Adaptive Exits:**
- High-volatility stocks get wider stops, avoiding premature exits on normal price action
- Low-volatility stocks get tighter stops, protecting capital in stable price environments
- Systematic 2:1 reward/risk ratio improves risk-adjusted returns

**Market Condition Responsiveness:**
- ATR naturally expands during volatile periods (earnings, market stress)
- ATR contracts during calm periods, allowing tighter risk control
- Exits adapt without manual intervention or configuration changes

### Strategic Performance Enhancement
**Expected Metrics Improvement:**
- Sharpe ratio: +0.1 to +0.3 improvement from better risk management
- Win rate: Slight decrease (wider stops) but larger average wins
- Maximum drawdown: 10-20% reduction from volatility-adaptive stops
- Return/risk: Improved due to systematic reward/risk ratios

**Stock-Specific Optimization:**
- Each stock gets exits calibrated to its historical volatility profile
- Reduces strategy performance variance across different volatility regimes
- Enables more consistent backtesting results across market conditions

## Out of Scope (This Story)

### Advanced ATR Features
- **Trailing ATR Stops**: Dynamic stops that move with favorable price movement
- **ATR Position Sizing**: Using ATR to determine position size based on volatility
- **ATR Trend Filters**: Using ATR to identify trending vs choppy markets
- **Multiple Timeframe ATR**: Daily vs intraday ATR calculations

### Alternative Volatility Measures
- **Bollinger Band Width**: Alternative volatility-based exits
- **Standard Deviation Stops**: Statistical volatility measures
- **Implied Volatility Integration**: Options-based volatility measures
- **Regime-Based Volatility**: Bull/bear market volatility adjustments

### Performance Optimizations
- **ATR Caching Across Runs**: Persistent ATR cache for faster subsequent runs
- **Parallel ATR Calculation**: Multi-threaded ATR computation for large universes
- **ATR Approximation Methods**: Faster but less accurate ATR estimates

## Definition of Done

- [ ] All acceptance criteria implemented and tested
- [ ] ATR calculation mathematically validated against known values
- [ ] ATR exits integrate seamlessly with existing exit types in backtester
- [ ] Configuration supports ATR exits with proper validation
- [ ] Comprehensive test coverage (>90% for new functions)
- [ ] Performance benchmarks show <10ms ATR calculation overhead per symbol
- [ ] End-to-end testing: `quickedge run` works with ATR configuration
- [ ] Documentation updated with ATR exit examples and best practices
- [ ] All code passes `mypy --strict` type checking
- [ ] Story 019 dependencies identified and documented

## Success Metrics

### Functional Validation
- [ ] ATR values match TradingView/MetaTrader calculations (±0.1% tolerance)
- [ ] ATR exits trigger at expected price levels in test scenarios
- [ ] Mixed exit conditions (ATR + percentage + trend) work without conflicts
- [ ] Configuration validation catches invalid ATR parameters

### Performance Validation  
- [ ] ATR calculation adds <10ms per symbol to backtesting runtime
- [ ] Memory usage stable during large universe backtesting (100+ symbols)
- [ ] No performance regression in existing percentage-based exits

### Integration Validation
- [ ] ATR exits appear correctly in strategy performance reports
- [ ] Per-stock analysis (Story 017) includes ATR exit performance metrics
- [ ] ATR strategies persist correctly in database with config tracking

## Next Story Dependencies

This story enables several potential follow-up stories:

### Story 019: Advanced ATR Features
- Trailing ATR stops that adjust with favorable price movement
- ATR-based position sizing for volatility-adjusted risk
- Multiple timeframe ATR analysis (daily vs weekly)

### Story 020: Alternative Volatility Exits  
- Bollinger Band-based exits using band width as volatility measure
- Standard deviation stops using statistical volatility
- Volatility regime detection for adaptive exit strategies

### Story 021: Exit Strategy Optimization
- Systematic testing of optimal ATR multipliers per stock
- Machine learning optimization of exit combinations
- Market condition-based exit selection

### Story 022: Real-time ATR Monitoring
- Intraday ATR calculation for day trading strategies
- Real-time ATR alerts when volatility spikes occur
- ATR-based market regime identification

Each follow-up story can leverage the core ATR infrastructure built in this story, ensuring incremental value delivery while maintaining the KISS principle of focused, well-scoped changes.
