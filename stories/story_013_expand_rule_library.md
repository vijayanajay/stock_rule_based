# Story 013: Expand Rule Library - 5 New Indicators

**Status:** Ready for Development  
**Estimated Story Points:** 8  
**Priority:** Medium (Enhances trading signal diversity)  
**Created:** 2025-07-01  
**Prerequisites:** Story 003 (Rule Functions) ✅ Complete

## User Story
As a technical trader, I want 5 additional rule functions (2 candlestick patterns + 3 technical indicators) implemented in the KISS Signal CLI so that I can build more diverse and robust trading strategies while keeping the system simple and maintainable.

## Context
The current system has 3 basic indicators (SMA crossover, RSI oversold, EMA crossover). To improve signal quality and provide more strategy options, we need to expand the rule library with proven technical patterns while maintaining the modular-monolith architecture and keeping functions pure and simple.

## Rule Selection (Kailash Nadh Philosophy: Simple, Effective, Well-tested)

### Candlestick Patterns (2)
1. **Hammer/Hanging Man** - Single candle reversal pattern, mathematically simple
2. **Engulfing Pattern** - Two-candle pattern, clear bullish/bearish logic

### Technical Indicators (3)
3. **MACD Crossover** - Classic momentum indicator, widely used
4. **Bollinger Band Squeeze** - Volatility breakout, combines SMA + standard deviation  
5. **Volume Spike** - Simple volume analysis, no complex calculations

## Directory Structure

```
d:\Code\stock_rule_based\
├── src\
│   └── kiss_signal\
│       └── rules.py               # ✏️ MODIFY: Add 5 new rule functions
├── config\
│   └── rules.yaml                 # ✏️ MODIFY: Add new rule definitions
├── tests\
│   ├── test_rule_funcs.py         # ✏️ MODIFY: Add tests for new rules
│   └── test_integration_rules.py  # ✏️ MODIFY: Integration tests
└── docs\
    └── rule_functions.md          # ✏️ MODIFY: Document new indicators
```

## Acceptance Criteria

### Core Functionality
- [ ] **AC-1:** Implement `hammer_pattern()` function with configurable body/shadow ratios
- [ ] **AC-2:** Implement `engulfing_pattern()` function for bullish/bearish detection
- [ ] **AC-3:** Implement `macd_crossover()` function with configurable periods
- [ ] **AC-4:** Implement `bollinger_squeeze()` function with breakout detection
- [ ] **AC-5:** Implement `volume_spike()` function with rolling average comparison

### Code Quality
- [ ] **AC-6:** All functions follow existing patterns (pure, typed, logged)
- [ ] **AC-7:** All functions handle edge cases (insufficient data, NaN values)
- [ ] **AC-8:** No new external dependencies beyond current stack
- [ ] **AC-9:** Functions complete in <100ms for 1000-row DataFrames

### Testing
- [ ] **AC-10:** Unit tests for each rule with valid signal generation
- [ ] **AC-11:** Edge case tests (empty data, insufficient periods, invalid params)
- [ ] **AC-12:** Integration tests with real NSE data samples
- [ ] **AC-13:** All tests pass with 95%+ coverage on new code

### Configuration
- [ ] **AC-14:** Add rule definitions to `rules.yaml` with sensible defaults
- [ ] **AC-15:** Add validation constraints for all parameters
- [ ] **AC-16:** Update `__all__` exports in rules.py

### Documentation
- [ ] **AC-17:** Document each function with clear docstrings (Args, Returns, Raises)
- [ ] **AC-18:** Update `docs/rule_functions.md` with new indicator descriptions
- [ ] **AC-19:** Include mathematical formulas and signal interpretation

## Technical Specifications

### 1. Hammer Pattern Function
```python
def hammer_pattern(price_data: pd.DataFrame, 
                  body_ratio: float = 0.3, 
                  shadow_ratio: float = 2.0) -> pd.Series:
    """Detect hammer/hanging man candlestick patterns."""
```
- Body size ≤ body_ratio * (high - low)
- Lower shadow ≥ shadow_ratio * body size
- Upper shadow ≤ body size
- Returns bullish signals at low prices, bearish at high prices

### 2. Engulfing Pattern Function  
```python
def engulfing_pattern(price_data: pd.DataFrame, 
                     min_body_ratio: float = 1.2) -> pd.Series:
    """Detect bullish/bearish engulfing patterns."""
```
- Current candle body completely engulfs previous candle body
- Opposite colors (green engulfs red for bullish signal)
- Current body ≥ min_body_ratio * previous body

### 3. MACD Crossover Function
```python
def macd_crossover(price_data: pd.DataFrame,
                  fast_period: int = 12,
                  slow_period: int = 26, 
                  signal_period: int = 9) -> pd.Series:
    """Generate signals when MACD line crosses above signal line."""
```
- MACD = EMA(fast) - EMA(slow)
- Signal = EMA(MACD, signal_period)
- Buy when MACD crosses above Signal

### 4. Bollinger Squeeze Function
```python
def bollinger_squeeze(price_data: pd.DataFrame,
                     period: int = 20,
                     std_dev: float = 2.0,
                     squeeze_threshold: float = 0.1) -> pd.Series:
    """Detect breakouts from Bollinger Band squeezes."""
```
- Band width = (Upper Band - Lower Band) / Middle Band
- Squeeze when band width < squeeze_threshold
- Signal when price breaks above upper band after squeeze

### 5. Volume Spike Function
```python
def volume_spike(price_data: pd.DataFrame,
                period: int = 20,
                spike_multiplier: float = 2.0) -> pd.Series:
    """Detect unusual volume spikes with price confirmation."""
```
- Volume > spike_multiplier * rolling_average(volume, period)
- Price movement > 1% in same direction
- Confirmation of momentum with volume

## Implementation Approach

### Phase 1: Core Functions (≤ 15 LOC each)
1. Implement each function in `src/kiss_signal/rules.py`
2. Follow existing patterns for error handling and logging
3. Add to `__all__` exports

### Phase 2: Testing (Comprehensive coverage)
1. Unit tests for each function with synthetic data
2. Edge case handling (empty DataFrames, insufficient data)
3. Integration tests with real NSE data samples
4. Performance validation (<100ms execution)

### Phase 3: Configuration
1. Add rule definitions to `config/rules.yaml`
2. Add parameter validation constraints
3. Test rule loading and validation

### Phase 4: Documentation
1. Update function docstrings with mathematical details
2. Document in `docs/rule_functions.md`
3. Include usage examples and parameter guidance

## Definition of Done Checklist

### Code Quality ✅
- [ ] All functions are pure (no side effects)
- [ ] Full type hints on all parameters and returns  
- [ ] Logging with `logging.getLogger(__name__)`
- [ ] Error handling for invalid inputs and edge cases
- [ ] No external dependencies beyond approved stack

### Testing ✅  
- [ ] `pytest` passes (100% new tests)
- [ ] `mypy` passes (no type errors)
- [ ] Coverage ≥ 95% on new functions
- [ ] Performance tests validate <100ms execution

### Integration ✅
- [ ] Functions integrate with existing backtester
- [ ] Rules can be used in strategy optimization
- [ ] Configuration loading works correctly
- [ ] No breaking changes to existing functionality

### Documentation ✅
- [ ] Docstrings follow existing patterns
- [ ] Mathematical formulas documented
- [ ] Parameter ranges and defaults explained
- [ ] Usage examples provided

## Technical Constraints

### Performance
- Each function must complete in <100ms for 1000-row DataFrames
- Memory usage should not exceed 50MB per function call
- No unnecessary copying of large DataFrames

### Code Style
- Follow existing patterns in `rules.py`
- Use pandas vectorized operations (no loops)
- Maintain backward compatibility with existing rules
- Keep functions ≤ 20 lines of core logic

### Data Requirements
- All functions work with standard OHLCV DataFrame format
- Handle missing data gracefully (return False for signals)
- Support partial data (fewer rows than required periods)
- Validate input parameters at function entry

## Risk Mitigation

### Technical Risks
- **Risk:** New functions break existing backtester
- **Mitigation:** Comprehensive integration testing, no changes to function signatures

- **Risk:** Performance degradation with complex calculations  
- **Mitigation:** Benchmark tests, vectorized pandas operations only

- **Risk:** Signal quality issues with new indicators
- **Mitigation:** Validate against known market patterns, conservative defaults

### Scope Risks  
- **Risk:** Feature creep (adding more than 5 rules)
- **Mitigation:** Strict scope adherence, defer additional rules to future stories

- **Risk:** Over-engineering complex parameter validation
- **Mitigation:** Simple validation following existing patterns

## Success Metrics

1. **5 new rule functions** implemented and tested
2. **All tests passing** (158+ tests, maintaining 91%+ overall coverage)
3. **Performance maintained** (<1s total execution time for all rules)
4. **Zero regressions** in existing functionality
5. **Documentation complete** for all new indicators

## Next Steps After Completion

1. **Story 014:** Strategy optimization with expanded rule set
2. **Story 015:** Enhanced reporting with new signal types  
3. **Story 016:** Performance tuning for larger rule combinations

---

*This story follows KISS principles: Keep functions simple, reuse existing patterns, minimize dependencies, focus on proven technical indicators with mathematical clarity.*

---

## 📋 IMPLEMENTATION REVIEW (Kailash Nadh)

*Reviewed: 2025-07-01*

### ✅ What's Good
- **Smart rule selection**: 5 functions with clear mathematical definitions
- **Realistic constraints**: <100ms performance target is achievable
- **No dependencies**: Sticks to pandas/typing stack
- **Clear phases**: Logical implementation order

### ⚠️ Areas Needing Detail

#### 1. Implementation Order Missing
Current story doesn't specify build sequence. Dependencies matter.

#### 2. Mathematical Formulas Too Vague  
"Body size ≤ body_ratio * (high - low)" needs exact pandas operations.

#### 3. Testing Strategy Generic
"95% coverage" means nothing without specific test scenarios.

#### 4. Column Requirements Unclear
Which functions need Volume vs just OHLC?

---

## 🛠️ DETAILED IMPLEMENTATION TASKS

### **Phase 1: Foundation Setup (Day 1)**

#### Task 1.1: Update `__all__` exports in rules.py
```python
__all__ = [
    "sma_crossover", "rsi_oversold", "ema_crossover", "calculate_rsi",
    # New functions
    "volume_spike", "hammer_pattern", "engulfing_pattern", 
    "macd_crossover", "bollinger_squeeze"
]
```

#### Task 1.2: Add column validation helper
```python
def _validate_ohlcv_columns(price_data: pd.DataFrame, required: list[str]) -> None:
    """Validate required columns exist in DataFrame."""
    missing = [col for col in required if col not in price_data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
```

### **Phase 2: Implement Functions (Days 2-3)**

#### Task 2.1: Volume Spike (EASIEST - Start here)
**Required columns:** `['close', 'volume']`
**Formula:**
```python
def volume_spike(price_data: pd.DataFrame,
                period: int = 20,
                spike_multiplier: float = 2.0,
                price_change_threshold: float = 0.01) -> pd.Series:
    """Detect volume spikes with price confirmation.
    
    Signal when:
    1. Volume > spike_multiplier * rolling_average(volume, period)
    2. |price_change| > price_change_threshold (1%)
    3. Both conditions on same day
    """
    _validate_ohlcv_columns(price_data, ['close', 'volume'])
    
    if len(price_data) < period:
        return pd.Series(False, index=price_data.index)
    
    # Volume condition
    avg_volume = price_data['volume'].rolling(period, min_periods=period).mean()
    volume_condition = price_data['volume'] > (spike_multiplier * avg_volume)
    
    # Price change condition  
    price_change = price_data['close'].pct_change().abs()
    price_condition = price_change > price_change_threshold
    
    signals = volume_condition & price_condition
    return signals.fillna(False)
```

#### Task 2.2: Hammer Pattern
**Required columns:** `['open', 'high', 'low', 'close']`
**Mathematical Definition:**
- Body = |close - open|
- Lower shadow = min(open, close) - low  
- Upper shadow = high - max(open, close)
- Total range = high - low

```python
def hammer_pattern(price_data: pd.DataFrame,
                  body_ratio: float = 0.3,
                  shadow_ratio: float = 2.0) -> pd.Series:
    """Detect hammer/hanging man patterns.
    
    Conditions:
    1. Body ≤ body_ratio * total_range
    2. Lower_shadow ≥ shadow_ratio * body
    3. Upper_shadow ≤ body
    """
    _validate_ohlcv_columns(price_data, ['open', 'high', 'low', 'close'])
    
    if len(price_data) == 0:
        return pd.Series(False, index=price_data.index)
    
    body = (price_data['close'] - price_data['open']).abs()
    total_range = price_data['high'] - price_data['low']
    lower_shadow = price_data[['open', 'close']].min(axis=1) - price_data['low']
    upper_shadow = price_data['high'] - price_data[['open', 'close']].max(axis=1)
    
    # Hammer conditions
    small_body = body <= (body_ratio * total_range)
    long_lower_shadow = lower_shadow >= (shadow_ratio * body)
    small_upper_shadow = upper_shadow <= body
    
    signals = small_body & long_lower_shadow & small_upper_shadow
    return signals.fillna(False)
```

#### Task 2.3: Engulfing Pattern  
**Required columns:** `['open', 'close']`
```python
def engulfing_pattern(price_data: pd.DataFrame,
                     min_body_ratio: float = 1.2) -> pd.Series:
    """Detect bullish engulfing patterns.
    
    Conditions:
    1. Previous candle: red (close < open)
    2. Current candle: green (close > open)  
    3. Current body >= min_body_ratio * previous body
    4. Current close > previous open
    5. Current open < previous close
    """
    _validate_ohlcv_columns(price_data, ['open', 'close'])
    
    if len(price_data) < 2:
        return pd.Series(False, index=price_data.index)
    
    current_body = (price_data['close'] - price_data['open']).abs()
    prev_body = current_body.shift(1)
    
    # Color conditions
    prev_red = price_data['close'].shift(1) < price_data['open'].shift(1)
    current_green = price_data['close'] > price_data['open']
    
    # Engulfing conditions
    body_size_ok = current_body >= (min_body_ratio * prev_body)
    engulfs_high = price_data['close'] > price_data['open'].shift(1)
    engulfs_low = price_data['open'] < price_data['close'].shift(1)
    
    signals = prev_red & current_green & body_size_ok & engulfs_high & engulfs_low
    return signals.fillna(False)
```

#### Task 2.4: MACD Crossover
**Required columns:** `['close']`
**Formula:** MACD = EMA(12) - EMA(26), Signal = EMA(MACD, 9)
```python
def macd_crossover(price_data: pd.DataFrame,
                  fast_period: int = 12,
                  slow_period: int = 26,
                  signal_period: int = 9) -> pd.Series:
    """MACD line crossing above signal line."""
    _validate_ohlcv_columns(price_data, ['close'])
    
    min_required = slow_period + signal_period
    if len(price_data) < min_required:
        return pd.Series(False, index=price_data.index)
    
    # Calculate MACD
    ema_fast = price_data['close'].ewm(span=fast_period).mean()
    ema_slow = price_data['close'].ewm(span=slow_period).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period).mean()
    
    # Crossover detection
    signals = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    return signals.fillna(False)
```

#### Task 2.5: Bollinger Squeeze (MOST COMPLEX)
**Required columns:** `['close']`
```python
def bollinger_squeeze(price_data: pd.DataFrame,
                     period: int = 20,
                     std_dev: float = 2.0,
                     squeeze_threshold: float = 0.1) -> pd.Series:
    """Breakout signals after Bollinger Band squeeze."""
    _validate_ohlcv_columns(price_data, ['close'])
    
    if len(price_data) < period + 5:  # Need extra periods to detect squeeze
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
    
    return breakout.fillna(False)
```

### **Phase 3: Testing Strategy (Day 4)**

#### Task 3.1: Create test data generators
```python
# In test_rule_funcs.py
def create_hammer_test_data() -> pd.DataFrame:
    """Generate synthetic data with known hammer pattern."""
    return pd.DataFrame({
        'open': [100, 95],
        'high': [101, 96], 
        'low': [99, 90],    # Large lower shadow
        'close': [100.5, 94.5],  # Small body
        'volume': [1000, 1200]
    })

def create_volume_spike_data() -> pd.DataFrame:
    """Generate data with volume spike pattern."""
    # 20 days normal volume, then spike
    volumes = [1000] * 20 + [3000]  # 3x spike
    closes = [100 + i*0.1 for i in range(20)] + [102]  # Price jump
    # ... return DataFrame
```

#### Task 3.2: Specific test scenarios
**For each function, test:**
1. **Happy path**: Known pattern should return True
2. **No signal**: Random data should return mostly False  
3. **Edge cases**: Empty DataFrame, single row, insufficient periods
4. **Parameter validation**: Invalid parameters raise ValueError
5. **Performance**: 1000 rows complete in <100ms

#### Task 3.3: Integration test with real data
```python
def test_new_rules_with_nse_data():
    """Test all new rules with cached NSE data."""
    symbol_data = load_symbol_cache('RELIANCE.NS')  # Use existing helper
    
    # Each function should run without errors
    volume_signals = volume_spike(symbol_data)
    hammer_signals = hammer_pattern(symbol_data)
    # ... etc
    
    # Verify reasonable signal frequency (not too many, not zero)
    assert 0.01 <= volume_signals.mean() <= 0.1  # 1-10% signal rate
```

### **Phase 4: Configuration Updates (Day 5)**

#### Task 4.1: Add to rules.yaml
```yaml
# Add to layers section:
  - name: "volume_confirmation"
    type: "volume_spike"
    description: "Volume spike with 2x average and 1% price move"
    params:
      period: 20
      spike_multiplier: 2.0
      price_change_threshold: 0.01
      
  - name: "hammer_reversal"
    type: "hammer_pattern" 
    description: "Hammer/hanging man reversal pattern"
    params:
      body_ratio: 0.3
      shadow_ratio: 2.0
      
  - name: "bullish_engulfing"
    type: "engulfing_pattern"
    description: "Bullish engulfing pattern"
    params:
      min_body_ratio: 1.2
      
  - name: "macd_momentum"
    type: "macd_crossover"
    description: "MACD line crosses above signal line" 
    params:
      fast_period: 12
      slow_period: 26
      signal_period: 9
      
  - name: "bollinger_breakout"
    type: "bollinger_squeeze"
    description: "Breakout after Bollinger Band squeeze"
    params:
      period: 20
      std_dev: 2.0
      squeeze_threshold: 0.1

# Add to validation section:
validation:
  # ...existing validations...
  volume_spike:
    period: {min: 5, max: 50}
    spike_multiplier: {min: 1.5, max: 5.0}
    price_change_threshold: {min: 0.005, max: 0.05}
  hammer_pattern:
    body_ratio: {min: 0.1, max: 0.5}
    shadow_ratio: {min: 1.5, max: 3.0}
  engulfing_pattern:
    min_body_ratio: {min: 1.1, max: 2.0}
  macd_crossover:
    fast_period: {min: 5, max: 20}
    slow_period: {min: 15, max: 50}
    signal_period: {min: 5, max: 15}
  bollinger_squeeze:
    period: {min: 10, max: 50}
    std_dev: {min: 1.0, max: 3.0}
    squeeze_threshold: {min: 0.05, max: 0.2}
```

### **Phase 5: Documentation (Day 6)**

#### Task 5.1: Update rule_functions.md
```markdown
## Volume Spike
**Purpose:** Detect unusual volume with price confirmation
**Signal:** Volume > 2x average AND |price_change| > 1%
**Usage:** Confirmation filter for momentum trades
**Parameters:**
- `period`: Rolling average period (default: 20)
- `spike_multiplier`: Volume threshold multiplier (default: 2.0)
- `price_change_threshold`: Minimum price change (default: 0.01)

## Hammer Pattern  
**Purpose:** Single-candle reversal pattern detection
**Signal:** Small body, long lower shadow, small upper shadow
**Usage:** Reversal signal at support levels
**Math:** body ≤ 30% of range, lower_shadow ≥ 2x body, upper_shadow ≤ body

... [continue for each function]
```

---

## 🎯 SUCCESS CRITERIA (Measurable)

### Code Quality Metrics
- [ ] All 5 functions under 20 lines core logic
- [ ] Zero mypy errors
- [ ] Zero new dependencies in requirements.txt
- [ ] All functions use pandas vectorized operations (no explicit loops)

### Performance Benchmarks  
- [ ] `volume_spike(1000_rows)` < 50ms
- [ ] `hammer_pattern(1000_rows)` < 30ms  
- [ ] `engulfing_pattern(1000_rows)` < 40ms
- [ ] `macd_crossover(1000_rows)` < 60ms
- [ ] `bollinger_squeeze(1000_rows)` < 80ms

### Test Coverage Targets
- [ ] 20+ new unit tests (4 per function)
- [ ] 5+ integration tests with real NSE data
- [ ] 95%+ line coverage on new functions only
- [ ] All edge cases covered (empty data, insufficient periods)

### Integration Validation
- [ ] `quickedge run --freeze-data 2025-01-01` completes successfully
- [ ] New rules appear in backtester strategy optimization
- [ ] Reporter can handle new signal types
- [ ] No breaking changes to existing functionality

---

## ⚠️ IMPLEMENTATION NOTES

### Common Pitfalls to Avoid
1. **Over-parameterization**: Don't add parameters you won't use
2. **Complex validation**: Keep parameter checks simple (min/max only)
3. **Performance traps**: Avoid `.apply()`, use vectorized operations
4. **Copy overhead**: Work with views, not copies of DataFrames
5. **Test overkill**: Don't test every parameter combination

### Integration Points
- **Backtester**: New functions must work with `generate_signals()`
- **Reporter**: Signal counting and formatting must handle new types
- **Config**: Parameter validation follows existing patterns
- **CLI**: `--verbose` flag should log signal counts for new rules

### Performance Optimization
- Use `pd.Series.rolling()` instead of manual loops
- Prefer `pd.DataFrame[['col1', 'col2']].min(axis=1)` over `apply(min)`
- Cache expensive calculations (EMA, rolling averages)
- Use `fillna(False)` instead of complex null handling
