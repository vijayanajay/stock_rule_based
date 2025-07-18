# Story 019: Implement Basic Market Context Filter

## Status: � InProg(ress (Implementation Started - 2025-07-18)

**Priority:** High (Market context is essential for better signal quality)
**Estimated Story Points:** 3 (Reduced from 8 after KISS review - focus on one simple filter)
**Prerequisites:** Story 018 (ATR-Based Dynamic Exit Conditions) ✅ Complete
**Created:** 2025-07-17
**Reviewed:** 2025-07-17 (Kailash Nadh - Technical Architecture - SIMPLIFIED FOR KISS)

## User Story
As a trader, I want to implement a simple market context filter that prevents signals during unfavorable market conditions so that I avoid trading against the overall market trend, leading to better risk-adjusted returns.

## Context & Rationale

The current system generates signals based purely on individual stock patterns without considering basic market conditions. This violates the fundamental trading principle: **"Don't fight the tape."**

**KISS Approach**: Start with ONE simple market filter instead of building a complex framework.

**Single Context Filter to Implement:**
- **Market Above SMA Filter**: Only allow signals when NIFTY 50 is above its configurable SMA period

This single filter will:
- Reduce signals during bear markets (when most strategies underperform)
- Improve risk-adjusted returns by avoiding counter-trend trades
- Allow configuration of different SMA periods (20, 50, 200 day) without code changes
- Provide measurable business value before adding complexity

## Architectural Deep Dive

### Current System Analysis
The existing architecture follows a clean modular monolith pattern:
- `RulesConfig` in `config.py` defines `baseline`, `layers`, and `sell_conditions`
- `Backtester._generate_signals()` applies rules via `getattr(rules, rule_type, None)`
- Each rule function follows signature: `(price_data: pd.DataFrame, **params) -> pd.Series`

### Proposed Simple Changes

#### 1. Add One Simple Function
Add `market_above_sma()` function to `rules.py` that checks if NIFTY > configurable SMA period.

#### 2. Add Simple Configuration Field
Extend `RulesConfig` with optional `context_filters: List[RuleDef] = []` field.

#### 3. Add Basic Market Data Support
Extend `data.py` to fetch and cache NIFTY 50 data (^NSEI).

#### 4. Integrate in Backtester
Modify `_backtest_combination()` to apply context filters before generating signals.

**No Frameworks, No Registries, No Complex Configuration** - Just solve the immediate business need.

## Technical Implementation Goals

### Single Phase: Simple Market Filter (Story 019)
1. **Simple Rule Function**: `market_above_sma()` - one function, configurable parameters
2. **Simple Configuration**: `context_filters` with one filter definition
3. **Basic Data Support**: Fetch and cache NIFTY 50 data
4. **Basic Integration**: Apply context filters in backtester
5. **Measure Impact**: Prove business value before adding complexity

**Next Steps (Future Stories)**:
- Story 020: Add stock outperformance filter (if market filter proves valuable)
- Story 021: Add RSI overbought filter (if previous filters prove valuable)

## Detailed Acceptance Criteria

### AC-1: Simple Market Context Function
**File**: `src/kiss_signal/rules.py`
**Function Signature**: `market_above_sma(market_data: pd.DataFrame, period: int = 50) -> pd.Series`

**Implementation Requirements**:
- [ ] **Single Purpose**: Check if market index is above configurable SMA period
- [ ] **Clear Logic**: Simple, readable function with no abstraction layers
- [ ] **Data Validation**: Use existing `_validate_ohlcv_columns()` pattern
- [ ] **Edge Case Handling**: Return `pd.Series(False, index=market_data.index)` if insufficient data
- [ ] **Clear Logging**: Simple debug message with signal count

**Simple Implementation**:
```python
def market_above_sma(market_data: pd.DataFrame, period: int = 50) -> pd.Series:
    """Check if market index is above its Simple Moving Average.
    
    This represents a bullish market regime where long strategies 
    typically perform better.
    
    Args:
        market_data: DataFrame with OHLCV data for market index (e.g., NIFTY 50)
        period: SMA period in days (default: 50)
        
    Returns:
        Boolean Series with True when market is above SMA
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
```

**Unit Tests Required**:
- [ ] Test with different SMA periods (20, 50, 200)
- [ ] Test with bullish market data (price consistently above SMA)
- [ ] Test with bearish market data (price consistently below SMA)
- [ ] Test with insufficient data (< period rows)
- [ ] Test with missing data (NaN values)
- [ ] Test with invalid period (0, negative)
- [ ] Test crossover scenarios (price crossing above/below SMA)

### AC-2: Simple Configuration Extension
**File**: `src/kiss_signal/config.py`

**Schema Changes**:
```python
class RulesConfig(BaseModel):
    """Defines the structure of the rules.yaml file."""
    baseline: RuleDef
    layers: List[RuleDef] = []
    sell_conditions: List[RuleDef] = Field(default_factory=list)
    context_filters: List[RuleDef] = Field(default_factory=list)  # NEW SIMPLE FIELD
    validation: Optional[Dict[str, Any]] = None
```

**Simple Configuration Example**:
```yaml
# Add to existing rules.yaml
context_filters:
  - name: "filter_market_is_bullish"
    type: "market_above_sma"
    description: "Context 1: Don't fight the tape. The NIFTY 50 index must be above its 50-day SMA."
    params:
      index_symbol: "^NSEI"
      period: 50
```

### AC-3: Basic Market Data Support
**File**: `src/kiss_signal/data.py`

**New Simple Function**: `get_market_data`
```python
def get_market_data(
    index_symbol: str,
    cache_dir: Path,
    years: int = 1,
    freeze_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get market index data for context filtering.
    
    Simplified version of get_price_data specifically for market indices.
    
    Args:
        index_symbol: Market index symbol (e.g., '^NSEI')
        cache_dir: Path to cache directory
        years: Number of years of data
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with market index OHLCV data
    """
    # Use different cache filename pattern for indices
    cache_file = cache_dir / f"{index_symbol.replace('^', 'INDEX_')}.csv"
    
    # Same logic as get_price_data but for market indices
    if freeze_date or not _needs_refresh(index_symbol, cache_dir, 30):
        if cache_file.exists():
            return _load_market_cache(cache_file)
    
    # Download fresh data
    logger.info(f"Downloading market index data for {index_symbol}")
    data = _fetch_symbol_data(index_symbol, years)
    if data is not None:
        _save_market_cache(data, cache_file)
        return data
    else:
        raise ValueError(f"Failed to fetch market data for {index_symbol}")

def _load_market_cache(cache_file: Path) -> pd.DataFrame:
    """Load market index data from cache."""
    # Same as _load_symbol_cache

def _save_market_cache(data: pd.DataFrame, cache_file: Path) -> None:
    """Save market index data to cache."""
    # Same as _save_symbol_cache
```

### AC-4: Simple Backtester Integration
**File**: `src/kiss_signal/backtester.py`

**Simple Integration in `_backtest_combination`**:
```python
def _backtest_combination(
    self,
    combo: List[Any],
    price_data: pd.DataFrame,
    rules_config: RulesConfig,
    edge_score_weights: EdgeScoreWeights,
    symbol: str,
) -> Optional[Dict[str, Any]]:
    """Modified to include simple context filters check."""
    try:
        # NEW: Apply context filters first if any are defined
        if rules_config.context_filters:
            context_signals = self._apply_context_filters(
                price_data, rules_config.context_filters, symbol
            )
            
            # If no favorable context periods, skip expensive rule evaluation
            if not context_signals.any():
                logger.debug(f"No favorable context for {symbol}, skipping")
                return None
        else:
            # No context filters - allow all periods
            context_signals = pd.Series(True, index=price_data.index)
        
        # Generate combined signal for the rule combination
        entry_signals: Optional[pd.Series] = None
        for rule_def in combo:
            rule_signals = self._generate_signals(rule_def, price_data)
            if entry_signals is None:
                entry_signals = rule_signals.copy()
            else:
                entry_signals &= rule_signals
        
        if entry_signals is None:
            logger.warning(f"Could not generate entry signals for combo: {[r.name for r in combo]}")
            return None
        
        # Apply context filters to final signals
        final_entry_signals = entry_signals & context_signals
        
        # Rest of the method unchanged, but use final_entry_signals
        # ...

def _apply_context_filters(
    self,
    stock_data: pd.DataFrame,
    context_filters: List[RuleDef],
    symbol: str
) -> pd.Series:
    """Apply context filters and return combined boolean series."""
    if not context_filters:
        return pd.Series(True, index=stock_data.index)
    
    # Initialize with all True
    combined_signals = pd.Series(True, index=stock_data.index)
    
    for filter_def in context_filters:
        try:
            if filter_def.type == "market_above_sma":
                # Get market data
                index_symbol = filter_def.params["index_symbol"]
                market_data = self._get_market_data_cached(index_symbol)
                
                # Apply the filter
                filter_params = {k: v for k, v in filter_def.params.items() if k != "index_symbol"}
                filter_signals = getattr(rules, filter_def.type)(market_data, **filter_params)
                
                # Align with stock data and apply AND logic
                aligned_filter = filter_signals.reindex(stock_data.index, method='ffill').fillna(False)
                combined_signals &= aligned_filter
                
                # Log filter effectiveness
                filter_count = aligned_filter.sum()
                logger.debug(f"Context filter '{filter_def.name}' for {symbol}: "
                            f"{filter_count}/{len(aligned_filter)} days pass "
                            f"({filter_count/len(aligned_filter)*100:.1f}%)")
            else:
                raise ValueError(f"Unknown context filter type: {filter_def.type}")
                
        except Exception as e:
            logger.error(f"Error applying context filter '{filter_def.name}' to {symbol}: {e}")
            # Fail-safe: if context filter fails, exclude all signals
            return pd.Series(False, index=stock_data.index)
    
    combined_count = combined_signals.sum()
    logger.info(f"Combined context filters for {symbol}: "
               f"{combined_count}/{len(combined_signals)} days pass "
               f"({combined_count/len(combined_signals)*100:.1f}%)")
    
    return combined_signals

def _get_market_data_cached(self, index_symbol: str) -> pd.DataFrame:
    """Get market data with caching for backtesting."""
    if not hasattr(self, '_market_cache'):
        self._market_cache = {}
    
    if index_symbol not in self._market_cache:
        from .data import get_market_data
        self._market_cache[index_symbol] = get_market_data(
            index_symbol=index_symbol,
            cache_dir=Path("data"),  # TODO: Get from config
            years=2,  # Buffer for lookback calculations
            freeze_date=getattr(self, 'freeze_date', None)
        )
    return self._market_cache[index_symbol]
```

## Simple Success Metrics

### SM-1: Functional Validation
- [ ] **Rule Function**: `market_above_sma()` passes unit tests with edge cases
- [ ] **Configuration**: `context_filters` loads without errors
- [ ] **Data Integration**: Market index data fetching and caching works correctly
- [ ] **Backtester Pipeline**: Full integration test with context filters completes successfully

### SM-2: Business Impact Validation
- [ ] **Signal Reduction**: Market filter reduces signals during bear markets by 50-80%
- [ ] **Performance Impact**: Context filter evaluation adds <5% to total backtest time
- [ ] **Edge Score Improvement**: At least 30% of strategies show improved edge scores with context filter
- [ ] **Practical Value**: Demonstrable improvement in risk-adjusted returns

### SM-3: Technical Quality
- [ ] **Backward Compatibility**: All existing tests pass with empty `context_filters`
- [ ] **Error Handling**: Market data failures gracefully degrade to no filtering
- [ ] **Logging**: Clear debug information for troubleshooting
- [ ] **Simple Code**: Function is <20 lines, easy to understand and debug

## Implementation Task Breakdown

### Task 019.1: Simple Market Filter Function (1 story point)
**Owner**: Backend Developer
**Dependencies**: None
**Deliverables**:
- [ ] `market_above_sma()` function (20 LOC)
- [ ] Add function to `__all__` exports in `rules.py`
- [ ] Unit tests for the function (60 LOC)

**Files Modified**:
- `src/kiss_signal/rules.py` (+20 LOC)
- `tests/test_rule_funcs.py` (+60 LOC)

### Task 019.2: Simple Configuration Extension (1 story point)
**Owner**: Backend Developer  
**Dependencies**: Task 019.1
**Deliverables**:
- [ ] Add `context_filters: List[RuleDef]` to `RulesConfig`
- [ ] Update example in `rules.yaml`
- [ ] Test configuration loading

**Files Modified**:
- `src/kiss_signal/config.py` (+2 LOC)
- `config/rules.yaml` (+5 LOC)
- `tests/test_config.py` (+30 LOC)

### Task 019.3: Simple Data Support (1 story point)
**Owner**: Backend Developer
**Dependencies**: None  
**Deliverables**:
- [ ] `get_market_data()` function
- [ ] Market index data caching
- [ ] Test market data fetching

**Files Modified**:
- `src/kiss_signal/data.py` (+40 LOC)
- `tests/test_data.py` (+40 LOC)

### Task 019.4: Simple Backtester Integration (1 story point)
**Owner**: Backend Developer
**Dependencies**: Tasks 019.1, 019.2, 019.3
**Deliverables**:
- [ ] Modify `_backtest_combination()` to apply context filters
- [ ] Add `_apply_context_filters()` method
- [ ] Add market data caching in backtester
- [ ] Integration test

**Files Modified**:
- `src/kiss_signal/backtester.py` (+50 LOC)
- `tests/test_backtester.py` (+50 LOC)

## Risk Assessment & Mitigation

### Low Risks (Simple Implementation)
1. **Market Data Availability**: Index data might have gaps
   - *Mitigation*: Simple error handling, fallback to no filtering, clear logging
   
2. **Performance**: Additional market data fetching
   - *Mitigation*: Simple caching, single market data fetch per index per backtest

3. **Data Alignment**: Stock vs market data date mismatches  
   - *Mitigation*: Simple pandas reindex with forward fill

### Minimal Risks
1. **Configuration Error**: User misconfigures context filter parameters
   - *Mitigation*: Simple parameter validation, clear error messages
   
2. **Backward Compatibility**: Existing configurations breaking
   - *Mitigation*: Optional field with empty list default

## Post-Implementation Monitoring

### Key Metrics to Track
1. **Signal Reduction Rate**: Expected 50-80% reduction during bear markets
2. **Performance Impact**: <5% increase in backtesting time
3. **Edge Score Improvement**: Improvement in edge scores for filtered strategies
4. **Error Rates**: Monitor market data fetching issues

### Success Criteria (1 week post-deployment)
- [ ] No bugs or performance regressions
- [ ] Context filter demonstrably improves strategy performance during bear markets
- [ ] Simple configuration adoption by users
- [ ] Stable market data fetching

## Next Possible Stories

### Story 020: Add Market Above EMA Filter (2 story points)
**Description**: Add second simple filter for market above EMA (different from SMA)
**Justification**: Only if Story 019 proves valuable

### Story 021: Add Stock Outperformance Filter (3 story points)  
**Description**: Add filter for stock vs market performance comparison
**Justification**: Only if previous filters prove valuable

### Story 022: Add RSI Overbought Filter (2 story points)
**Description**: Avoid signals when market RSI > 70 (overbought conditions)
**Justification**: Only if we have 2+ proven context filters

## KISS Principle Compliance Check

✅ **Tiny Diffs**: Total addition <115 LOC across all files
✅ **Single Purpose**: One simple function doing one thing well  
✅ **Simple Configuration**: Single context filter with configurable parameters
✅ **No Complex Frameworks**: No registries, just one function and simple config
✅ **Backward Compatible**: Optional feature with safe default (empty list)
✅ **Testable**: Simple function with clear inputs/outputs
✅ **Debuggable**: Easy to understand what went wrong
✅ **Minimal Dependencies**: No new external libraries
✅ **Prove First**: Solve immediate problem, measure impact
✅ **Configurable**: Flexible SMA period without code changes

**ARCHITECTURAL BENEFITS**:
- **Simple Solution**: One function for one business need
- **No Over-Engineering**: No premature abstractions  
- **Configurable Parameters**: Flexible without complex frameworks
- **Measurable Impact**: Clear before/after comparison
- **Future-Friendly**: Easy to add more context filters if proven valuable

## Definition of Done (Simplified)

### Code Quality
- [ ] **Implementation Complete**: Simple market filter implemented and tested
- [ ] **Test Coverage**: >90% line coverage for new `is_market_bullish()` function
- [ ] **Type Safety**: Full type hints with mypy validation passing
- [ ] **Simple Documentation**: Clear docstring following established patterns
- [ ] **Code Review**: Peer review completed, focusing on simplicity

### Integration & Testing
- [ ] **Unit Tests**: Simple function has comprehensive unit test coverage
- [ ] **Integration Test**: End-to-end testing with market filter enabled
- [ ] **Performance Test**: <5% performance impact verified
- [ ] **Manual Testing**: Full run with market filter produces expected results
- [ ] **Regression Testing**: All existing tests continue to pass

### Configuration & Business Value
- [ ] **Simple Schema**: `RulesConfig` handles `context_filters` list
- [ ] **Clear Errors**: Invalid configurations fail with clear error messages  
- [ ] **Documentation**: Simple example in `rules.yaml`
- [ ] **Business Impact**: Measurable improvement in bear market performance

### Production Readiness
- [ ] **Simple Error Handling**: Graceful degradation when market data unavailable
- [ ] **Clear Logging**: Appropriate logging for debugging
- [ ] **No Memory Leaks**: Simple implementation with no resource issues
- [ ] **Success Metrics**: Clear measurement of filter effectiveness

---

**Story Estimation Rationale**:
Maintained at 3 points after configuration change:
- **Single Function** (1 point): One simple function with configurable parameters
- **Simple Configuration** (1 point): Context filters list vs boolean field (same complexity)  
- **No Registries** (1 point): Direct implementation vs abstraction layers
- **Prove Value First** (+0 points): Start simple, add complexity only if needed

**KISS Compliance**:
- **No Premature Abstractions**: One function for most common use case
- **Tiny Diffs**: <115 total LOC addition
- **Single Purpose**: One function does one thing well
- **Configurable**: Flexible parameters without complex frameworks
- **Debuggable**: Clear failure modes and error messages
- **Measurable**: Easy to prove business value before adding complexity
