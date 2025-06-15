# Story 003: Rule Functions & Technical Indicators

**Status:** Draft  
**Estimated Story Points:** 6  
**Priority:** High (Enables backtesting and signal generation)  
**Created:** 2025-06-16  
**Prerequisites:** Story 002 (Data Manager) ✅ Complete

## User Story
As a technical trader, I want the core rule functions and technical indicators implemented so that I can define trading rules in `rules.yaml` and have them properly evaluated against price data.

## Context
This story implements the foundation for rule-based signal generation by creating the technical indicator functions and rule evaluation logic. These functions will be used by both the backtester (for strategy optimization) and signal generator (for live signal generation).

## Acceptance Criteria

### AC1: Core Technical Indicators
- [ ] Implement `sma_crossover()` function with configurable periods
- [ ] Implement `rsi_oversold()` function with configurable period and threshold  
- [ ] Implement helper function `calculate_rsi()` for RSI calculations
- [ ] Implement `ema_crossover()` function as alternative to SMA
- [ ] All indicators return boolean pandas Series for buy signals

### AC2: Rule Configuration Support
- [ ] Parse rule parameters from `rules.yaml` configuration
- [ ] Support parameterized rules (e.g., different SMA periods per rule)
- [ ] Validate rule parameters against expected ranges
- [ ] Provide clear error messages for invalid rule configurations
- [ ] Support rule naming and metadata storage

### AC3: Rule Evaluation Engine
- [ ] Implement `evaluate_rule()` function that dispatches to correct indicator
- [ ] Support multiple rule types: `sma_crossover`, `rsi_oversold`, `ema_crossover`
- [ ] Handle missing data gracefully (skip signals during warmup periods)
- [ ] Return standardized boolean series aligned with price data index
- [ ] Add comprehensive logging for rule evaluation debugging

### AC4: Performance & Data Quality
- [ ] Optimize indicator calculations for 3+ years of daily data
- [ ] Handle edge cases: insufficient data, NaN values, zero volumes
- [ ] Validate price data before indicator calculations
- [ ] Implement proper warmup periods for each indicator type
- [ ] Cache indicator calculations when possible

### AC5: Integration & Testing
- [ ] Update `rules.yaml` with working rule definitions and parameters
- [ ] Create comprehensive unit tests for each indicator function
- [ ] Test rule evaluation with real NSE data samples
- [ ] Validate that signals align correctly with price data timestamps
- [ ] Test parameter validation and error handling

## Technical Requirements

### Rule Function Signatures
```python
def sma_crossover(price_data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> pd.Series:
    """SMA crossover signals when fast > slow."""

def rsi_oversold(price_data: pd.DataFrame, period: int = 14, oversold_threshold: float = 30.0) -> pd.Series:
    """RSI oversold signals when RSI < threshold."""

def ema_crossover(price_data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> pd.Series:
    """EMA crossover signals when fast > slow."""
```

### Sample rules.yaml Structure
```yaml
rules:
  - name: "sma_10_20"
    type: "sma_crossover"
    params:
      fast_period: 10
      slow_period: 20
  - name: "rsi_oversold_30"
    type: "rsi_oversold" 
    params:
      period: 14
      oversold_threshold: 30.0
```

### Data Quality Standards
- Handle minimum data requirements (e.g., 50+ days for 20-period SMA)
- Return empty signals during insufficient data periods
- Align all signal timestamps with price data timestamps
- Preserve data types and index consistency

## Definition of Done
1. ✅ All 3 core indicator functions implemented and working
2. ✅ `rules.yaml` updated with functional rule definitions
3. ✅ Rule evaluation engine can process any rule from config
4. ✅ Unit tests pass for all indicator functions with sample data
5. ✅ Manual testing with real NSE data shows proper signal generation
6. ✅ `mypy` passes with no type errors
7. ✅ No performance regressions (rules evaluate within 1 second per symbol)
8. ✅ Integration test: `quickedge run --freeze-data 2025-01-01` can evaluate rules

## Implementation Notes
- Keep each indicator function under 25 lines as per coding guidelines
- Use pandas vectorized operations for performance
- Import talib or similar only if absolutely necessary (prefer pure pandas)
- Add detailed docstrings with parameter explanations
- Use consistent logging patterns with module logger

## Dependencies
- pandas for data manipulation and calculations
- Existing `rules.yaml` configuration structure
- DataManager for price data access
- Integration with upcoming SignalGenerator and Backtester modules

## Risk Mitigation
- Start with simple SMA/RSI indicators before adding complex ones
- Validate indicator calculations against known values
- Test with various market conditions (trending, sideways, volatile)
- Ensure proper handling of corporate actions and data gaps

## Detailed Implementation Tasks

### Phase 1: Core Indicator Functions (2-3 hours)

#### Task 1.1: Implement SMA Crossover Function
- [ ] Add `sma_crossover()` function to `rule_funcs.py`
- [ ] Calculate fast and slow SMAs using pandas `.rolling().mean()`
- [ ] Detect crossover points where fast SMA crosses above slow SMA
- [ ] Return boolean Series with True for buy signals
- [ ] Handle insufficient data gracefully (return empty signals)
- [ ] Add comprehensive logging for debugging
- [ ] **Validation**: Test with known data and manual calculations

#### Task 1.2: Implement RSI Calculation Helper
- [ ] Complete `calculate_rsi()` function in `rule_funcs.py`
- [ ] Calculate price changes using `.diff()`
- [ ] Separate gains and losses using conditional logic
- [ ] Apply exponential smoothing for average gains/losses
- [ ] Return RSI values (0-100 range)
- [ ] Handle edge cases: all gains, all losses, insufficient data
- [ ] **Validation**: Compare against known RSI calculations

#### Task 1.3: Implement RSI Oversold Function
- [ ] Complete `rsi_oversold()` function using `calculate_rsi()`
- [ ] Generate buy signals when RSI crosses below threshold
- [ ] Add optional recovery logic (RSI bouncing back above threshold)
- [ ] Handle warmup period (typically 14+ days for RSI)
- [ ] Return boolean Series aligned with price data
- [ ] **Validation**: Test with trending and sideways markets

#### Task 1.4: Implement EMA Crossover Function
- [ ] Add `ema_crossover()` function to `rule_funcs.py`
- [ ] Calculate fast and slow EMAs using pandas `.ewm().mean()`
- [ ] Detect crossover points where fast EMA crosses above slow EMA
- [ ] Handle smoothing factor calculation (alpha = 2/(period+1))
- [ ] Ensure proper initialization for EMA calculations
- [ ] **Validation**: Compare EMA vs SMA performance characteristics

### Phase 2: Rule Configuration Engine (1-2 hours)

#### Task 2.1: Update rules.yaml Structure
- [ ] Expand `rules.yaml` with working rule definitions
- [ ] Add parameter validation ranges and defaults
- [ ] Include rule descriptions and expected behavior
- [ ] Add metadata: creation date, author, version
- [ ] Document parameter meanings and valid ranges
- [ ] **Structure**:
  ```yaml
  rules:
    - name: "sma_10_20_crossover"
      type: "sma_crossover"
      description: "Buy when 10-day SMA crosses above 20-day SMA"
      params:
        fast_period: 10
        slow_period: 20
      validation:
        fast_period: {min: 5, max: 50}
        slow_period: {min: 10, max: 200}
  ```

#### Task 2.2: Implement Rule Parameter Validation
- [ ] Add `validate_rule_params()` function to `rule_funcs.py`
- [ ] Check parameter types (int, float) and ranges
- [ ] Validate logical constraints (fast_period < slow_period)
- [ ] Return clear error messages for invalid parameters
- [ ] Support default parameter substitution
- [ ] **Test Cases**: Invalid types, out-of-range values, logical errors

#### Task 2.3: Create Rule Registry System
- [ ] Add `RULE_REGISTRY` dictionary mapping rule types to functions
- [ ] Implement `get_rule_function()` helper for rule lookup
- [ ] Add support for rule aliases and backward compatibility
- [ ] Validate that all configured rules have implementations
- [ ] **Registry Structure**:
  ```python
  RULE_REGISTRY = {
      "sma_crossover": sma_crossover,
      "rsi_oversold": rsi_oversold,
      "ema_crossover": ema_crossover,
  }
  ```

### Phase 3: Rule Evaluation Engine (1-2 hours)

#### Task 3.1: Complete evaluate_rule() Function
- [ ] Enhance `evaluate_rule()` in `signal_generator.py`
- [ ] Parse rule configuration and extract parameters
- [ ] Validate parameters using `validate_rule_params()`
- [ ] Dispatch to correct indicator function via registry
- [ ] Handle exceptions gracefully with clear error messages
- [ ] Return standardized boolean Series
- [ ] Add performance timing for optimization

#### Task 3.2: Implement Multi-Rule Combination Logic
- [ ] Add `combine_rules()` function for AND/OR logic
- [ ] Support rule stack evaluation (multiple rules per signal)
- [ ] Handle timestamp alignment between different rules
- [ ] Implement rule weighting and voting mechanisms
- [ ] Add debugging output for rule combination results
- [ ] **Logic**: Currently focus on AND logic (all rules must trigger)

#### Task 3.3: Add Data Quality Validation
- [ ] Implement `validate_price_data()` function
- [ ] Check for: negative prices, zero volumes, large gaps
- [ ] Validate required columns: open, high, low, close, volume
- [ ] Handle missing data with interpolation or warnings
- [ ] Set minimum data requirements per indicator type
- [ ] Return data quality score and recommendations

### Phase 4: Testing & Integration (2-3 hours)

#### Task 4.1: Unit Tests for Indicator Functions
- [ ] Create `tests/test_rule_funcs.py`
- [ ] Test each indicator with synthetic data (known results)
- [ ] Test edge cases: insufficient data, NaN values, extreme values
- [ ] Test parameter validation and error conditions
- [ ] Achieve >90% code coverage for `rule_funcs.py`
- [ ] **Fixtures**: Create reusable test data sets

#### Task 4.2: Integration Tests with Real Data
- [ ] Create `tests/test_rule_integration.py`
- [ ] Test rule evaluation with actual NSE data samples
- [ ] Validate signal timing and alignment
- [ ] Test performance with 3+ years of data
- [ ] Verify memory usage stays reasonable
- [ ] **Data**: Use cached data from `data/cache/` for consistency

#### Task 4.3: Manual Testing & Validation
- [ ] Test `quickedge run --freeze-data 2025-01-01` with new rules
- [ ] Verify rule evaluation appears in CLI output
- [ ] Check verbose logging shows rule details
- [ ] Validate no performance regressions
- [ ] Test with multiple symbols and rule combinations
- [ ] **Documentation**: Record test results and observations

#### Task 4.4: Performance Optimization
- [ ] Profile indicator calculations with `cProfile`
- [ ] Optimize pandas operations for large datasets
- [ ] Add caching for expensive calculations
- [ ] Benchmark against performance requirements (1 second per symbol)
- [ ] Consider vectorization opportunities
- [ ] **Target**: Process 30 symbols × 3 years data < 30 seconds

### Phase 5: CLI Integration (1 hour)

#### Task 5.1: Update CLI Progress Display
- [ ] Add rule evaluation step to CLI pipeline
- [ ] Show rule count and evaluation progress
- [ ] Display timing information in verbose mode
- [ ] Add error handling for rule evaluation failures
- [ ] **Example Output**:
  ```
  [4/6] Evaluating trading rules...
        └─ Processing 5 rules for 30 symbols
        └─ SMA crossover: 15/30 symbols ✓
        └─ RSI oversold: 30/30 symbols ✓
  ```

#### Task 5.2: Add Rule Validation Command
- [ ] Add `quickedge validate-rules` command
- [ ] Check all rules in `rules.yaml` for validity
- [ ] Test rule evaluation with sample data
- [ ] Report any configuration or implementation issues
- [ ] **Output**: Summary report with pass/fail status per rule

## Task Dependencies
```
Phase 1 (Indicators) → Phase 2 (Configuration) → Phase 3 (Evaluation) → Phase 4 (Testing) → Phase 5 (Integration)
```

## Estimated Time Breakdown
- **Phase 1**: 2-3 hours (core implementation)
- **Phase 2**: 1-2 hours (configuration)
- **Phase 3**: 1-2 hours (evaluation engine)
- **Phase 4**: 2-3 hours (testing)
- **Phase 5**: 1 hour (integration)
- **Total**: 7-11 hours (matching 6 story points estimate)
