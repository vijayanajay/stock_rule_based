# Story 032: Implement Equal-Risk ATR Position Sizing - READY FOR DEVELOPMENT

## Status: **READY FOR DEVELOPMENT** ✅

**Priority:** CRITICAL (Fundamental Risk Management - Roadmap #3)  
**Estimated Story Points:** 3  
**Prerequisites:** ✅ **Story 031** (ATR-based exits are in place)  
**Created:** 2025-08-07  
**Reviewed:** 2025-08-07 (Following Kailash Nadh Evidence-Based Methodology)

## User Story
As a systematic trader, I want position sizes calculated based on risk percentage instead of unlimited leverage, so that performance metrics are realistic and strategies are comparable across different stock prices.

## Context & Rationale (Kailash Nadh Evidence-Based Review)

### Foundation Validated ✅
**Story 031 completion provides:**
- ✅ **ATR Infrastructure**: `calculate_atr()` proven in production use 
- ✅ **Chandelier Exit**: ATR-based exit logic working in `rules_chandelier_test.yaml`
- ✅ **Integration Points**: Backtester already takes `initial_capital` parameter

### REAL Problem (Not Academic Theory)
**Code Analysis Reveals:**
```python
# In cli.py - backtester is hardcoded to 100k, no config integration
bt = backtester.Backtester(
    hold_period=getattr(app_config, "hold_period", 20),
    min_trades_threshold=threshold,
    # ❌ MISSING: initial_capital from config
)

# In backtester.py - unlimited position sizes
portfolio = vbt.Portfolio.from_signals(
    # ... 
    size=np.inf,  # ❌ ABSURD: Unlimited leverage
)
```

**Immediate Impact:**
- Every "profitable" strategy assumes infinite capital - meaningless metrics
- Can't compare stocks of different prices (₹100 vs ₹3000 stocks)  
- One bad trade = account suicide
- Sharpe ratios artificially inflated by leverage dreams

### Why This Story Is ACTUALLY Critical
**Not theoretical - PRACTICAL:**
1. **MEASUREMENT PROBLEM**: Can't trust any current performance metrics
2. **COMPARISON PROBLEM**: High-price vs low-price stocks incomparable  
3. **RISK PROBLEM**: No position sizing = no risk management
4. **FOUNDATION PROBLEM**: All future work depends on realistic metrics

## Acceptance Criteria (Simplified & Practical)

### 1. Fix CLI Configuration Integration
**CURRENT BUG:**
```python
# src/kiss_signal/cli.py - backtester hardcoded, ignores config
bt = backtester.Backtester(
    hold_period=getattr(app_config, "hold_period", 20),
    min_trades_threshold=threshold,
    # ❌ MISSING: initial_capital
)
```

**FIX REQUIRED:**
```python
bt = backtester.Backtester(
    hold_period=getattr(app_config, "hold_period", 20),
    min_trades_threshold=threshold,
    initial_capital=getattr(app_config, "portfolio_initial_capital", 100000.0),
)
```

**Config Update:**
```yaml
# Add to config.yaml (with defaults that won't break existing setups)
portfolio_initial_capital: 100000.0
risk_per_trade_pct: 0.01  # 1% risk per trade
```

### 2. Replace Infinite Position Sizing
**Current locations that need fixing:**
- `_backtest_combination()` line ~118: `size=np.inf`
- `_backtest_single_strategy_oos()` line ~472: missing `size` parameter

**Solution:**
Replace `size=np.inf` with calculated risk-based sizing using existing ATR infrastructure.

### 3. Position Sizing Algorithm (Keep It Simple)
```python
def _calculate_risk_based_size(self, price_data: pd.DataFrame, 
                              entry_signals: pd.Series, 
                              exit_conditions: List[RuleDef]) -> pd.Series:
    """Calculate position sizes based on risk percentage and ATR."""
    # Find ATR-based stop rule, default to 2x ATR if none
    atr_multiplier = self._get_atr_multiplier(exit_conditions)
    
    # Use existing ATR calculation (proven in Story 031)
    atr_values = rules.calculate_atr(price_data, period=22)
    risk_per_share = atr_values * atr_multiplier
    
    # Fixed dollar risk per trade
    risk_amount = self.initial_capital * self.config.risk_per_trade_pct
    
    # Position sizes only where entries are True
    sizes = pd.Series(index=price_data.index, dtype=float)
    sizes[entry_signals] = risk_amount / risk_per_share[entry_signals]
    
    return sizes
```

### 4. Minimal Testing (Focus on Core Logic)
**Single test file:** `tests/test_position_sizing.py`

**Critical tests:**
1. High volatility stock gets smaller position size than low volatility stock
2. Risk percentage is respected (position_size * risk_per_share ≈ 1% of capital)
3. Integration: backtester uses calculated sizes, not `np.inf`

## Technical Implementation Plan (Actionable Steps)

### Step 1: Fix Config Integration (5 minutes)
```yaml
# Add to config.yaml (backwards compatible)
portfolio_initial_capital: 100000.0
risk_per_trade_pct: 0.01
```

```python
# Update Config class in src/kiss_signal/config.py
class Config(BaseModel):
    # ... existing fields ...
    portfolio_initial_capital: float = Field(default=100000.0, gt=0)
    risk_per_trade_pct: float = Field(default=0.01, gt=0, le=0.1)
```

```python
# Fix CLI in src/kiss_signal/cli.py line ~155
bt = backtester.Backtester(
    hold_period=getattr(app_config, "hold_period", 20),
    min_trades_threshold=threshold,
    initial_capital=getattr(app_config, "portfolio_initial_capital", 100000.0),
)
```

### Step 2: Add Risk Sizing Method (15 minutes)
```python
# Add to Backtester class in src/kiss_signal/backtester.py
def _get_atr_multiplier(self, exit_conditions: List[RuleDef]) -> float:
    """Find ATR multiplier from exit rules, default 2.0."""
    for rule in exit_conditions:
        if 'atr' in rule.type:
            return rule.params.get('multiplier', 2.0)
    return 2.0  # Sensible default

def _calculate_risk_based_size(self, price_data: pd.DataFrame, 
                              entry_signals: pd.Series, 
                              exit_conditions: List[RuleDef]) -> pd.Series:
    """Calculate position sizes based on ATR risk."""
    atr_multiplier = self._get_atr_multiplier(exit_conditions)
    atr_values = rules.calculate_atr(price_data, period=22)
    risk_per_share = atr_values * atr_multiplier
    
    risk_amount = self.initial_capital * 0.01  # 1% hardcoded for MVP
    sizes = pd.Series(index=price_data.index, dtype=float)
    sizes[entry_signals] = risk_amount / risk_per_share[entry_signals]
    
    return sizes
```

### Step 3: Replace size=np.inf (5 minutes)
```python
# In _backtest_combination, replace:
# size=np.inf,
# with:
size=self._calculate_risk_based_size(price_data, final_entry_signals, rules_config.exit_conditions),

# In _backtest_single_strategy_oos, add size parameter:
size=self._calculate_risk_based_size(test_data, entry_signals, rules_config.exit_conditions),
```

### Step 4: Create Validation Test (10 minutes)
```python
# tests/test_position_sizing.py
def test_position_sizing_works():
    """Basic test: volatility affects position size."""
    # Use existing test infrastructure
    # Create two price series with different ATR
    # Verify high ATR = smaller position size
```

## Success Metrics (Measurable Outcomes)

### Before/After Test
**BEFORE (Current broken state):**
```bash
quickedge run --symbols HDFCBANK.NS
# Reports: "Unlimited position size" - meaningless metrics
```

**AFTER (Fixed):**
```bash
quickedge run --symbols HDFCBANK.NS
# Reports: "Position size: 15 shares (₹1,000 risk)" - realistic metrics
```

### Validation Checklist
- [ ] Config loads `portfolio_initial_capital` and `risk_per_trade_pct`
- [ ] High-volatility stock gets smaller position size than low-volatility stock  
- [ ] No more `size=np.inf` in any backtesting calls
- [ ] Risk per trade ≈ 1% of portfolio (within ±0.1%)
- [ ] All existing tests still pass

### The Real Kailash Nadh Test
**Question:** If you run the same strategy on HDFCBANK.NS (₹1,650) vs WIPRO.NS (₹420), do you get comparable risk-adjusted returns?

**Current Answer:** No - different stock prices create incomparable results  
**Target Answer:** Yes - equal risk per trade makes strategies comparable

## Why This Story Is Essential (Kailash Nadh Reality Check)

**The Brutal Truth:**
All current performance metrics are **FANTASY** because they assume unlimited leverage. Every "winning" strategy is based on impossible position sizing.

**The Fix:**
Not complex position sizing algorithms. Just replace `size=np.inf` with reasonable position sizes based on risk.

**The Impact:**
- **Immediate:** Performance metrics become realistic and trustworthy
- **Practical:** Can compare strategies across different price stocks  
- **Foundation:** All future development depends on this working correctly

**Why Now:**
Story 031 gave us ATR infrastructure. This story uses it for the most critical purpose - making our metrics **REAL**.

This isn't feature development - it's **fixing a fundamental broken assumption** that invalidates everything else.

---

**READY FOR DEVELOPMENT:** ~35 minutes of work to fix a critical foundational flaw.
