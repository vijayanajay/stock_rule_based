# Story 019: Implement Basic Market Context Filter

## Status: 📝 DRAFT (Simplified for KISS Compliance - Ready for Implementation)

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
- **Market Bullish Filter**: Only allow signals when NIFTY 50 is above its 50-day Simple Moving Average

This single filter will:
- Reduce signals during bear markets (when most strategies underperform)
- Improve risk-adjusted returns by avoiding counter-trend trades
- Provide measurable business value before adding complexity

## Architectural Deep Dive

### Current System Analysis
The existing architecture follows a clean modular monolith pattern:
- `RulesConfig` in `config.py` defines `baseline`, `layers`, and `sell_conditions`
- `Backtester._generate_signals()` applies rules via `getattr(rules, rule_type, None)`
- Each rule function follows signature: `(price_data: pd.DataFrame, **params) -> pd.Series`

### Proposed Simple Changes

#### 1. Add One Simple Function
Add `is_market_bullish()` function to `rules.py` that checks if NIFTY > 50-day SMA.

#### 2. Add Simple Configuration Field
Extend `RulesConfig` with optional `market_bullish_required: bool = False` field.

#### 3. Add Basic Market Data Support
Extend `data.py` to fetch and cache NIFTY 50 data (^NSEI).

#### 4. Integrate in Backtester
Modify `_backtest_combination()` to check market condition before generating signals.

**No Frameworks, No Registries, No Complex Configuration** - Just solve the immediate business need.

## Technical Implementation Goals

### Single Phase: Simple Market Filter (Story 019)
1. **Simple Rule Function**: `is_market_bullish()` - one function, one purpose
2. **Simple Configuration**: `market_bullish_required: bool` in `RulesConfig`
3. **Basic Data Support**: Fetch and cache NIFTY 50 data
4. **Basic Integration**: Check market condition in backtester
5. **Measure Impact**: Prove business value before adding complexity

**Next Steps (Future Stories)**:
- Story 020: Add stock outperformance filter (if market filter proves valuable)
- Story 021: Add RSI overbought filter (if previous filters prove valuable)

## Detailed Acceptance Criteria

### AC-1: Simple Market Context Function
**File**: `src/kiss_signal/rules.py`
**Function Signature**: `is_market_bullish(market_data: pd.DataFrame) -> pd.Series`

**Implementation Requirements**:
- [ ] **Single Purpose**: Check if market (NIFTY 50) is above 50-day SMA
- [ ] **Clear Logic**: Simple, readable function with no abstraction layers
- [ ] **Data Validation**: Use existing `_validate_ohlcv_columns()` pattern
- [ ] **Edge Case Handling**: Return `pd.Series(False, index=market_data.index)` if insufficient data
- [ ] **Clear Logging**: Simple debug message with signal count

**Simple Implementation**:
```python
def is_market_bullish(market_data: pd.DataFrame) -> pd.Series:
    """Check if market (NIFTY 50) is above 50-day Simple Moving Average.
    
    This represents a bullish market regime where long strategies 
    typically perform better.
    
    Args:
        market_data: DataFrame with OHLCV data for NIFTY 50
        
    Returns:
        Boolean Series with True when market is bullish (price > 50-day SMA)
    """
    _validate_ohlcv_columns(market_data, ['close'])
    
    # Check sufficient data for 50-day SMA
    if len(market_data) < 50:
        logger.warning(f"Insufficient market data: {len(market_data)} rows, need 50")
        return pd.Series(False, index=market_data.index)
    
    # Calculate 50-day SMA
    sma_50 = market_data['close'].rolling(window=50).mean()
    
    # Market is bullish when price > SMA
    bullish_signals = market_data['close'] > sma_50
    
    signal_count = bullish_signals.sum()
    total_periods = len(bullish_signals)
    logger.debug(f"Market bullish (NIFTY > 50-day SMA): {signal_count}/{total_periods} days "
                f"({signal_count/total_periods*100:.1f}%)")
    
    return bullish_signals.fillna(False)
```

**Unit Tests Required**:
- [ ] Test with bullish market data (price consistently above SMA)
- [ ] Test with bearish market data (price consistently below SMA)
- [ ] Test with insufficient data (< 50 rows)
- [ ] Test with missing data (NaN values)
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
    market_bullish_required: bool = False  # NEW SIMPLE FIELD
    validation: Optional[Dict[str, Any]] = None
```

**Simple Configuration Example**:
```yaml
# Add to existing rules.yaml
market_bullish_required: true  # Only trade when NIFTY > 50-day SMA
```

### AC-3: Basic Market Data Support
**File**: `src/kiss_signal/data.py`

**New Simple Function**: `get_nifty_data`
```python
def get_nifty_data(
    cache_dir: Path,
    years: int = 1,
    freeze_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get NIFTY 50 index data for market context filtering.
    
    Simplified version of get_price_data specifically for market index.
    
    Args:
        cache_dir: Path to cache directory
        years: Number of years of data
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with NIFTY 50 OHLCV data
    """
    symbol = "^NSEI"
    cache_file = cache_dir / f"NIFTY50.csv"
    
    # Same logic as get_price_data but for NIFTY
    if freeze_date or not _needs_refresh(symbol, cache_dir, 30):
        if cache_file.exists():
            return _load_nifty_cache(cache_file)
    
    # Download fresh data
    logger.info("Downloading NIFTY 50 data")
    data = _fetch_symbol_data(symbol, years)
    if data is not None:
        _save_nifty_cache(data, cache_file)
        return data
    else:
        raise ValueError("Failed to fetch NIFTY 50 data")

def _load_nifty_cache(cache_file: Path) -> pd.DataFrame:
    """Load NIFTY data from cache."""
    # Same as _load_symbol_cache

def _save_nifty_cache(data: pd.DataFrame, cache_file: Path) -> None:
    """Save NIFTY data to cache."""
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
    """Modified to include simple market bullish check."""
    try:
        # NEW: Check market condition first if required
        if rules_config.market_bullish_required:
            market_data = self._get_nifty_data_cached()
            market_bullish = getattr(rules, 'is_market_bullish')(market_data)
            
            # If market is never bullish, skip expensive rule evaluation
            if not market_bullish.any():
                logger.debug(f"Market not bullish for {symbol}, skipping")
                return None
        
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
        
        # Apply market filter to final signals if required
        if rules_config.market_bullish_required:
            # Align market signals with stock signals
            aligned_market_signals = market_bullish.reindex(entry_signals.index, method='ffill').fillna(False)
            final_entry_signals = entry_signals & aligned_market_signals
        else:
            final_entry_signals = entry_signals
        
        # Rest of the method unchanged, but use final_entry_signals
        # ...

def _get_nifty_data_cached(self) -> pd.DataFrame:
    """Get NIFTY data with caching for backtesting."""
    if not hasattr(self, '_nifty_cache'):
        from .data import get_nifty_data
        self._nifty_cache = get_nifty_data(
            cache_dir=Path("data"),  # TODO: Get from config
            years=2,  # Buffer for lookback calculations
            freeze_date=getattr(self, 'freeze_date', None)
        )
    return self._nifty_cache
```

## Simple Success Metrics

### SM-1: Functional Validation
- [ ] **Rule Function**: `is_market_bullish()` passes unit tests with edge cases
- [ ] **Configuration**: `market_bullish_required` loads without errors
- [ ] **Data Integration**: NIFTY 50 data fetching and caching works correctly
- [ ] **Backtester Pipeline**: Full integration test with market filter completes successfully

### SM-2: Business Impact Validation
- [ ] **Signal Reduction**: Market filter reduces signals during bear markets by 50-80%
- [ ] **Performance Impact**: Market filter adds <5% to total backtest time
- [ ] **Edge Score Improvement**: At least 30% of strategies show improved edge scores with market filter
- [ ] **Practical Value**: Demonstrable improvement in risk-adjusted returns

### SM-3: Technical Quality
- [ ] **Backward Compatibility**: All existing tests pass with `market_bullish_required: false`
- [ ] **Error Handling**: NIFTY data failures gracefully degrade to no filtering
- [ ] **Logging**: Clear debug information for troubleshooting
- [ ] **Simple Code**: Function is <20 lines, easy to understand and debug

## Implementation Task Breakdown

### Task 019.1: Simple Market Filter Function (1 story point)
**Owner**: Backend Developer
**Dependencies**: None
**Deliverables**:
- [ ] `is_market_bullish()` function (15 LOC)
- [ ] Add function to `__all__` exports in `rules.py`
- [ ] Unit tests for the function (50 LOC)

**Files Modified**:
- `src/kiss_signal/rules.py` (+15 LOC)
- `tests/test_rule_funcs.py` (+50 LOC)

### Task 019.2: Simple Configuration Extension (1 story point)
**Owner**: Backend Developer  
**Dependencies**: Task 019.1
**Deliverables**:
- [ ] Add `market_bullish_required: bool` to `RulesConfig`
- [ ] Update example in `rules.yaml`
- [ ] Test configuration loading

**Files Modified**:
- `src/kiss_signal/config.py` (+2 LOC)
- `config/rules.yaml` (+2 LOC)
- `tests/test_config.py` (+20 LOC)

### Task 019.3: Simple Data Support (1 story point)
**Owner**: Backend Developer
**Dependencies**: None  
**Deliverables**:
- [ ] `get_nifty_data()` function
- [ ] NIFTY data caching
- [ ] Test NIFTY data fetching

**Files Modified**:
- `src/kiss_signal/data.py` (+30 LOC)
- `tests/test_data.py` (+30 LOC)

### Task 019.4: Simple Backtester Integration (1 story point)
**Owner**: Backend Developer
**Dependencies**: Tasks 019.1, 019.2, 019.3
**Deliverables**:
- [ ] Modify `_backtest_combination()` to check market condition
- [ ] Add NIFTY data caching in backtester
- [ ] Integration test

**Files Modified**:
- `src/kiss_signal/backtester.py` (+25 LOC)
- `tests/test_backtester.py` (+40 LOC)

## Risk Assessment & Mitigation

### Low Risks (Simple Implementation)
1. **NIFTY Data Availability**: ^NSEI data might have gaps
   - *Mitigation*: Simple error handling, fallback to no filtering, clear logging
   
2. **Performance**: Additional market data fetching
   - *Mitigation*: Simple caching, single market data fetch per backtest

3. **Data Alignment**: Stock vs market data date mismatches  
   - *Mitigation*: Simple pandas reindex with forward fill

### Minimal Risks
1. **Configuration Error**: User sets `market_bullish_required: true` incorrectly
   - *Mitigation*: Simple boolean field, hard to misconfigure
   
2. **Backward Compatibility**: Existing configurations breaking
   - *Mitigation*: Optional field with `False` default

## Post-Implementation Monitoring

### Key Metrics to Track
1. **Signal Reduction Rate**: Expected 50-80% reduction during bear markets
2. **Performance Impact**: <5% increase in backtesting time
3. **Edge Score Improvement**: Improvement in edge scores for filtered strategies
4. **Error Rates**: Monitor NIFTY data fetching issues

### Success Criteria (1 week post-deployment)
- [ ] No bugs or performance regressions
- [ ] Market filter demonstrably improves strategy performance during bear markets
- [ ] Simple configuration adoption by users
- [ ] Stable NIFTY data fetching

## Next Possible Stories

### Story 020: Add Stock Outperformance Filter (2 story points)
**Description**: Add second simple filter for stock vs market performance
**Justification**: Only if Story 019 proves valuable

### Story 021: Add RSI Overbought Filter (2 story points)  
**Description**: Avoid signals when market RSI > 70
**Justification**: Only if previous filters prove valuable

### Story 022: Configuration-Driven Context Filters (5 story points)
**Description**: Make filters configurable through YAML (if we have 3+ hardcoded filters)
**Justification**: Only after proving value with hardcoded filters

## KISS Principle Compliance Check

✅ **Tiny Diffs**: Total addition <75 LOC across all files
✅ **Single Purpose**: One simple function doing one thing  
✅ **Simple Configuration**: Single boolean field
✅ **No Frameworks**: No registries, no abstractions
✅ **Backward Compatible**: Optional feature with safe default
✅ **Testable**: Simple function with clear inputs/outputs
✅ **Debuggable**: Easy to understand what went wrong
✅ **Minimal Dependencies**: No new external libraries
✅ **Prove First**: Solve immediate problem, measure impact

**ARCHITECTURAL BENEFITS**:
- **Simple Solution**: One function for one business need
- **No Over-Engineering**: No premature abstractions
- **Measurable Impact**: Clear before/after comparison
- **Future-Friendly**: Easy to extend if proven valuable

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
- [ ] **Simple Schema**: `RulesConfig` handles `market_bullish_required` boolean
- [ ] **Clear Errors**: Invalid configurations fail with clear error messages  
- [ ] **Documentation**: Simple example in `rules.yaml`
- [ ] **Business Impact**: Measurable improvement in bear market performance

### Production Readiness
- [ ] **Simple Error Handling**: Graceful degradation when NIFTY data unavailable
- [ ] **Clear Logging**: Appropriate logging for debugging
- [ ] **No Memory Leaks**: Simple implementation with no resource issues
- [ ] **Success Metrics**: Clear measurement of filter effectiveness

---

**Story Estimation Rationale**:
Reduced from 8 points to 3 points after KISS simplification:
- **Single Function** (-3 points): One simple function vs complex framework
- **Simple Configuration** (-1 point): Boolean field vs complex YAML structures  
- **No Registries** (-1 point): Direct implementation vs abstraction layers
- **Prove Value First** (+0 points): Start simple, add complexity only if needed

**KISS Compliance**:
- **No Premature Abstractions**: Hardcode the most common use case
- **Tiny Diffs**: <75 total LOC addition
- **Single Purpose**: One function does one thing well
- **Debuggable**: Clear failure modes and error messages
- **Measurable**: Easy to prove business value before adding complexity
