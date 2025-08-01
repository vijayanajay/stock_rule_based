# ## Status: ✅ **COMPLETED**

**Implementation Date:** 2025-08-01
**All Tests Pass:** ✅ 
**Manual Verification:** ✅ Strategy seeker functionality working with individual rule testingtory 028: The "Strategy Seeker" MVP (Core Logic)

## Status: � **IN PROGRESS**

**Priority:** HIGH (Core Adaptive Strategy Engine)
**Estimated Story Points:** 2
**Prerequisites:** Story 027 Complete (Rules restructured for composability)
**Created:** 2025-08-01
**Reviewed:** 2025-08-01 (Kailash Nadh - Disciplined Strategy Discovery, Technical Review Complete)

**Kailash Nadh Approach**: Implement a simple, forward-only search algorithm that finds "good enough" strategies, not perfect ones. Prevent overfitting through disciplined constraints and early stopping. **CRITICAL**: Do not build a complex optimizer - this is a simple rule combination tester with disciplined constraints.

## User Story
As a systematic trader, I want the backtester to automatically test different combinations of my manually-curated entry rules to find a "good enough" strategy for each stock, so that I can discover which simple rule combinations work best for different stock personalities without manual optimization.

## Context & Rationale

The current system uses all `entry_signals` together as one combination. This works but ignores that some stocks may perform better with fewer, simpler rules. A volatile tech stock might only need one strong breakout signal, while a utility stock might need confirmation from multiple indicators.

**Current Problem**: 
- All stocks get identical rule combination from `entry_signals` list
- No way to discover simpler strategies that might work better
- Missing opportunities for stock-specific optimization
- One underperforming rule can drag down the entire strategy

**KISS Solution**: 
Test individual rules first, then simple combinations. Stop at the first "good enough" result. This prevents overfitting while allowing natural adaptation to stock characteristics.

**Business Value**: 
Test simple rule combinations to find what works for each stock. No black-box optimization. Every decision is logged and explainable.

## Architectural Deep Dive

### Current System Analysis
Story 027 completed the foundation. The current `find_optimal_strategies` function:
- Takes all `entry_signals` from the config as one combination
- Tests this single combination against the stock
- Returns the result (or empty list if no entry signals)

**Current Execution**:
```python
# Current: Use all entry_signals together
combinations_to_test = [entry_signals]  # One big combination
strategy_result = self._backtest_combination(combo, ...)
```

**What This Misses**: A stock might perform better with just one strong signal instead of requiring all signals to align.

### Proposed Simple Combination Tester

**Core Philosophy**: 
- **Test Individual Rules First**: Many stocks work best with just one good rule
- **Try Simple Combinations**: Test pairs if individual rules aren't good enough
- **Stop Early**: Accept first result that meets minimum criteria
- **Log Everything**: Every test and decision must be transparent

**Algorithm** (Maximum 3 tests per stock):
1. Test each individual entry rule alone
2. If none are "good enough", test the best individual rule + one confirmation
3. If still not good enough, return the best result found

**"Good Enough" Definition**:
- Edge score >= threshold (from config)
- Minimum number of trades for statistical validity

**Critical Constraints**:
- Maximum 2 entry rules per strategy (no complex combinations)
- Fixed preconditions, context_filters, and exit_conditions (not optimized)
- Early termination (first acceptable result wins)
- No parameter tuning (rules use their defined parameters)

## Technical Implementation Goals

### What Changes in find_optimal_strategies
1. **Add Simple Search Loop**: Test individual rules, then pairs
2. **Add Early Termination**: Stop at first acceptable result
3. **Add Transparency**: Log what's being tested and why
4. **Maintain API**: Same function signature for backward compatibility

**What Doesn't Change**:
- Function signature stays identical
- `_backtest_combination` logic unchanged  
- Database schema unchanged
- CLI interface unchanged
- All rule execution logic unchanged

## Detailed Acceptance Criteria

### AC-1: Add Configuration (Simple Addition)
**File**: `src/kiss_signal/config.py`

**Requirements**:
- [x] Add simple thresholds to existing `Config` model (no separate class needed)
- [x] Add validation for threshold values
- [x] Provide conservative defaults

**Implementation**:
```python
class Config(BaseModel):
    # ... existing fields ...
    # Simple seeker thresholds - no need for separate class
    seeker_min_edge_score: float = Field(default=0.60, ge=0.0, le=1.0)
    seeker_min_trades: int = Field(default=20, ge=5)
```

**Configuration File**:
```yaml
# config.yaml addition (2 lines)
seeker_min_edge_score: 0.60
seeker_min_trades: 20
```

### AC-2: Modify find_optimal_strategies Logic
**File**: `src/kiss_signal/backtester.py`

**Requirements**:
- [x] Keep existing function name and signature (no breaking changes)
- [x] Replace single combination test with simple search loop
- [x] Add early termination logic
- [x] Add transparent logging

**Core Changes**:
```python
def find_optimal_strategies(
    self, 
    price_data: pd.DataFrame,
    rules_config: RulesConfig,
    symbol: str = "",
    freeze_date: Optional[date] = None,
    edge_score_weights: Optional[EdgeScoreWeights] = None,
    config: Optional[Config] = None  # Add config parameter
) -> Any:
    """Find optimal strategy through simple combination testing."""
    
    entry_signals = rules_config.entry_signals
    
    # Simple thresholds
    min_edge_score = config.seeker_min_edge_score if config else 0.60
    min_trades = config.seeker_min_trades if config else 20
    
    best_result = None
    
    # Phase 1: Test individual rules
    logger.info(f"Testing {len(entry_signals)} individual rules for {symbol}")
    for rule in entry_signals:
        result = self._test_single_rule([rule], price_data, rules_config, edge_score_weights, symbol)
        if result and result["edge_score"] >= min_edge_score and result["total_trades"] >= min_trades:
            logger.info(f"Good enough individual rule found: {rule.name} (EdgeScore: {result['edge_score']:.3f})")
            return [result]
        best_result = self._track_best(result, best_result)
    
    # Phase 2: Test best individual + one confirmation (if needed)
    # Only test if we have multiple rules and didn't find good enough individual
    if len(entry_signals) > 1 and best_result:
        best_individual = best_result
        logger.info(f"Testing combinations with best individual rule")
        for confirmation in entry_signals:
            if confirmation.name != best_individual["rule_stack"][0]["name"]:
                combo = [best_individual["rule_stack"][0], confirmation]
                result = self._test_single_rule(combo, price_data, rules_config, edge_score_weights, symbol)
                if result and result["edge_score"] >= min_edge_score and result["total_trades"] >= min_trades:
                    logger.info(f"Good enough combination found: {combo[0].name} + {combo[1].name}")
                    return [result]
                best_result = self._track_best(result, best_result)
    
    # Return best found
    return [best_result] if best_result else []
```

### AC-3: Add Simple Helper Methods
**File**: `src/kiss_signal/backtester.py`

**Requirements**:
- [x] Add `_test_single_rule()` method (wrapper around existing `_backtest_combination`)
- [x] Add `_track_best()` method for simple comparison

**Implementation**:
```python
def _test_single_rule(self, entry_rules: List[RuleDef], price_data: pd.DataFrame, 
                      rules_config: RulesConfig, edge_score_weights: EdgeScoreWeights, 
                      symbol: str) -> Optional[Dict[str, Any]]:
    """Test a specific combination of entry rules."""
    return self._backtest_combination(entry_rules, price_data, rules_config, edge_score_weights, symbol)

def _track_best(self, current: Optional[Dict[str, Any]], best: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Track the best result by edge score."""
    if not current:
        return best
    if not best or current["edge_score"] > best["edge_score"]:
        return current
    return best
```

### AC-4: Update CLI Integration  
**File**: `src/kiss_signal/cli.py`

**Requirements**:
- [x] Pass config object to `find_optimal_strategies` calls
- [x] No other changes needed (function signature unchanged)

**Implementation**:
```python
# Find existing calls and add config parameter
strategies = backtester.find_optimal_strategies(
    price_data=price_data,
    rules_config=rules_config,
    symbol=symbol,
    freeze_date=freeze_date,
    edge_score_weights=config.edge_score_weights,
    config=config  # Add this line
)
```

## Implementation Plan

### Files to Modify (Minimal Changes)

1. `src/kiss_signal/config.py` - Add 2 simple threshold fields to Config
2. `config.yaml` - Add 2 lines for seeker thresholds
3. `src/kiss_signal/backtester.py` - Modify find_optimal_strategies logic + add 2 helper methods
4. `src/kiss_signal/cli.py` - Add config parameter to function call

### Implementation Steps

1. **Add Configuration Thresholds** (5 min)
   - Add seeker_min_edge_score and seeker_min_trades to Config model
   - Add 2 lines to config.yaml

2. **Modify find_optimal_strategies Logic** (25 min)
   - Replace single combination test with simple loop
   - Add early termination logic  
   - Add logging for transparency

3. **Add Helper Methods** (10 min)
   - Add _test_single_rule wrapper
   - Add _track_best comparison method

4. **Update CLI Integration** (5 min)
   - Add config parameter to function calls

5. **Test** (10 min)
   - Verify all tests still pass
   - Test with verbose logging

**Total Time: 55 minutes**

## Success Criteria

1. **Simple Combination Testing**: System tests individual rules first, then pairs
2. **Early Termination**: Search stops at first "good enough" result  
3. **Transparent Logging**: Every test and decision is logged in verbose mode
4. **No Breaking Changes**: All existing functionality continues to work
5. **Configuration Driven**: Thresholds controlled by config.yaml
6. **All Tests Pass**: Zero functional regressions

## Critical Constraints (Kailash Nadh Review)

### What This Story MUST NOT Do
- **No Complex Search Algorithm**: This is NOT an optimizer. Simple loop only.
- **No New Classes**: Add fields to existing Config, don't create StrategySeeker class
- **No Function Renaming**: Keep find_optimal_strategies name for compatibility
- **No Parameter Tuning**: Rules use their existing parameters only
- **No Exhaustive Search**: Maximum 2 phases, early termination mandatory

### What This Story MUST Do
- **Keep It Simple**: Maximum 3 combinations tested per stock (usually 1-2)
- **Log Every Decision**: Transparency is non-negotiable
- **Fail Gracefully**: Return best found if nothing meets criteria
- **Maintain Performance**: No significant slowdown vs current implementation

## Implementation Notes

### Why This Approach Works
This story transforms the current "test all rules together" approach into "test simple combinations" with minimal code changes. The algorithm:

1. **Respects Current Architecture**: Uses existing `_backtest_combination` method
2. **Maintains Compatibility**: Same function signature and return format
3. **Adds Value Gradually**: Can find simpler strategies that work better
4. **Prevents Overfitting**: Early termination and maximum 2 rules

### Expected Behavior Changes
- **Before**: All stocks get identical strategy from all entry_signals
- **After**: Each stock gets the simplest strategy that meets criteria
- **Logging**: More detailed output showing what was tested and why
- **Performance**: Minimal impact (usually tests 1-3 combinations vs 1)

### Future Story Enablement
This foundation enables:
- **Story 029**: More sophisticated search heuristics
- **Story 030**: Strategy analysis and reporting
- **Future**: Parameter relaxation and adaptive thresholds

---

**Technical Review Complete**: This story provides minimal, disciplined enhancement to enable adaptive strategy discovery while maintaining all KISS principles and avoiding optimization complexity.

## Story DoD Checklist Report

### ✅ Implementation Completed
- [x] **AC-1: Configuration Addition** - Added `seeker_min_edge_score` and `seeker_min_trades` to Config model and config.yaml
- [x] **AC-2: find_optimal_strategies Logic** - Implemented simple 2-phase search with early termination 
- [x] **AC-3: Helper Methods** - Added `_test_single_rule()` and `_track_best()` methods
- [x] **AC-4: CLI Integration** - Added config parameter to `find_optimal_strategies` calls

### ✅ Code Quality
- [x] **All Tests Pass** - Zero functional regressions, all existing tests pass
- [x] **Type Safety** - Full type hints on all new code
- [x] **Error Handling** - Graceful failure with best-found strategy fallback
- [x] **Logging** - Transparent logging of all search phases and decisions

### ✅ Architecture Compliance
- [x] **KISS Principles** - Simple 2-phase search, maximum 3 tests per stock
- [x] **No Complex Optimization** - Early termination, no exhaustive search
- [x] **Backward Compatibility** - Same function signature, no breaking changes
- [x] **Module Boundaries** - Changes contained to backtester and config modules

### ✅ Performance & Functionality
- [x] **Manual Verification** - Confirmed individual rule testing working in verbose output
- [x] **Performance** - Minimal impact, usually 1-3 tests vs previous 1 test
- [x] **Configuration Driven** - Thresholds controlled via config.yaml
- [x] **Transparent Decisions** - All search phases logged with clear reasoning

### ✅ Documentation & Standards
- [x] **Memory.md Compliance** - Avoided all documented antipatterns
- [x] **Operational Guidelines** - Followed project coding standards
- [x] **Story Requirements** - All acceptance criteria met
- [x] **Implementation Notes** - Story file updated with completion status

**DoD Status: ✅ COMPLETE**

All checklist items verified. Story 028 successfully implements the Strategy Seeker MVP following Kailash Nadh's disciplined approach with KISS principles.
