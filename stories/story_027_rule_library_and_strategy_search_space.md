# Story 027: Restructure Rules Configuration for Future Composability

## Status: 📋 **READY FOR DEVELOPMENT**

**Priority:** HIGH (Foundation for Adaptive Strategy Engine)
**Estimated Story Points:** 2
**Prerequisites:** Story 026 Complete (Test coverage at 92%)
**Created:** 2025-07-30
**Reviewed:** 2025-07-30 (Kailash Nadh - Simplified for KISS)

**Kailash Nadh Approach**: Make minimal configuration changes to enable future composability without adding complexity we don't need yet.

## User Story
As a systematic trader, I want to restructure the rules configuration so that entry signals can be treated as composable components rather than a fixed hierarchy, enabling future stories to implement adaptive strategy selection without breaking existing functionality.

## Context & Rationale

The current system uses a rigid `baseline + layers` hierarchy for entry signals. This works for single-strategy execution but prevents future adaptive strategy discovery where we need to treat rules as composable components.

**Current Problem**: 
- `baseline` (single rule) + `layers` (confirmations) creates artificial hierarchy
- Future "Strategy Seeker" needs to test different combinations of entry rules
- Current structure assumes one baseline rule, making rule composition impossible

**KISS Solution**: 
Restructure configuration to treat all entry rules as equal components in an `entry_signals` list, while maintaining identical execution behavior.

**Business Value**: 
This change enables Story 028 (Strategy Seeker MVP) without requiring any behavior changes in the current system.

## Architectural Deep Dive

### Current System Analysis
The existing rules configuration follows a hierarchical pattern:
- `baseline: RuleDef` - Single primary entry signal
- `layers: List[RuleDef]` - Confirmation rules that must all be true
- `sell_conditions: List[RuleDef]` - Exit conditions
- `preconditions: List[RuleDef]` - Stock filters 
- `context_filters: List[RuleDef]` - Market filters

**Current Execution Flow**:
1. Check preconditions and context filters
2. Generate baseline signal
3. Apply each layer as AND condition
4. Execute trades with sell conditions

**Current Configuration**:
```yaml
baseline:
  name: "strong_bullish_engulfing"
  type: "engulfing_pattern"
  params: { min_body_ratio: 2.5 }

layers:
  - name: "confirm_with_extreme_volume"
    type: "volume_spike"
    params: { period: 20, spike_multiplier: 3.0 }
```

### Proposed Simple Changes

**Goal**: Enable future composability by treating entry signals as equal components, not hierarchy.

**Proposed Configuration**:
```yaml
entry_signals:  # Replaces baseline + layers
  - name: "strong_bullish_engulfing"
    type: "engulfing_pattern"
    params: { min_body_ratio: 2.5 }
  - name: "confirm_with_extreme_volume"
    type: "volume_spike"
    params: { period: 20, spike_multiplier: 3.0 }
```

**Execution Behavior**: Identical to current (all entry_signals AND together).

**What Changes**: Data structure only. Zero behavior changes.
**What Doesn't Change**: How rules are executed, validated, or combined.

## Technical Implementation Goals

### Phase 1: Configuration Structure Only (Story 027)
1. **Update RulesConfig**: Replace `baseline + layers` with `entry_signals`
2. **Update Configuration Loading**: Handle new structure
3. **Update Existing Usage**: Replace `baseline + layers` references
4. **Zero Behavior Changes**: System executes identically

**What NOT to Build**:
- No adaptive strategy selection (Story 028)
- No rule discovery algorithms (Story 029)
- No multiple strategy execution
- No new rule functions

**Success Criteria**: All existing tests pass with zero functional changes.

## Detailed Acceptance Criteria

### AC-1: Update RulesConfig Model
**File**: `src/kiss_signal/config.py`

**Requirements**:
- [x] Remove `baseline: RuleDef` field from RulesConfig
- [x] Remove `layers: List[RuleDef]` field from RulesConfig
- [x] Add `entry_signals: List[RuleDef]` field to RulesConfig
- [x] Rename `sell_conditions` to `exit_conditions` for consistency
- [x] Keep `preconditions` and `context_filters` unchanged
- [x] Maintain validation and type hints

**Implementation**:
```python
class RulesConfig(BaseModel):
    """Updated configuration for composable entry signals."""
    preconditions: List[RuleDef] = Field(default_factory=list)
    context_filters: List[RuleDef] = Field(default_factory=list)
    entry_signals: List[RuleDef] = Field(default_factory=list)  # NEW
    exit_conditions: List[RuleDef] = Field(default_factory=list)  # RENAMED
    validation: Optional[Dict[str, Any]] = None
```

### AC-2: Update Configuration File
**File**: `config/rules.yaml`

**Requirements**:
- [x] Replace `baseline` section with first entry in `entry_signals`
- [x] Move `layers` content into `entry_signals` list
- [x] Rename `sell_conditions` to `exit_conditions`
- [x] Preserve all existing rule definitions and parameters
- [x] Maintain identical functional behavior

**Current Structure → New Structure**:
```yaml
# OLD
baseline:
  name: "strong_bullish_engulfing"
  type: "engulfing_pattern"
layers:
  - name: "confirm_with_extreme_volume"
    type: "volume_spike"

# NEW  
entry_signals:
  - name: "strong_bullish_engulfing"
    type: "engulfing_pattern"
  - name: "confirm_with_extreme_volume"
    type: "volume_spike"
```

### AC-3: Update Strategy Combination Logic
**File**: `src/kiss_signal/config.py`

**Function**: `get_active_strategy_combinations()`

**Requirements**:
- [x] Update function to use `entry_signals` instead of `baseline + layers`
- [x] Generate identical strategy combinations as before
- [x] Maintain JSON serialization format
- [x] No changes to combination logic - just data source

**Implementation**:
```python
def get_active_strategy_combinations(rules_config: RulesConfig) -> List[str]:
    """Generate strategy combinations from entry_signals."""
    combinations: List[str] = []
    
    if not rules_config.entry_signals:
        return combinations
        
    # Current behavior: All entry_signals AND together
    combo = [rule.model_dump() for rule in rules_config.entry_signals]
    combinations.append(json.dumps(combo))
    
    return combinations
```

### AC-4: Update All References
**Files**: Any file using `rules_config.baseline` or `rules_config.layers`

**Requirements**:
- [x] Search codebase for `baseline` and `layers` references
- [x] Update to use `entry_signals` where appropriate
- [x] Update `sell_conditions` references to `exit_conditions`
- [x] Ensure all tests pass without functional changes

### AC-5: Configuration Validation
**File**: `src/kiss_signal/config.py`

**Requirements**:
- [x] Validate `entry_signals` list is not empty (if required)
- [x] Validate unique rule names within `entry_signals`
- [x] Preserve existing validation for all other fields
- [x] Clear error messages for validation failures

## Quality Gates

- [ ] All existing tests pass (`pytest` success rate: 100%)
- [ ] `mypy` type checking passes with new structure
- [ ] Configuration loads successfully with new format
- [ ] No performance regression in any operations
- [ ] Zero functional behavior changes

## Implementation Plan

### Files to Modify

**Primary Changes (Required)**:
- `src/kiss_signal/config.py` - Update RulesConfig model and get_active_strategy_combinations()
- `config/rules.yaml` - Restructure baseline+layers to entry_signals

**Secondary Changes (Search and Replace)**:
- Any file referencing `rules_config.baseline` or `rules_config.layers`
- Any file referencing `rules_config.sell_conditions` → `rules_config.exit_conditions`
- Update tests that validate configuration structure

**Files to Search**:
```bash
grep -r "\.baseline\|\.layers\|sell_conditions" src/ tests/
```

### Implementation Steps

1. **Update RulesConfig Model** (5 min)
   - Replace baseline/layers with entry_signals
   - Rename sell_conditions to exit_conditions
   
2. **Update rules.yaml** (5 min)  
   - Move baseline to first entry_signals item
   - Move layers to remaining entry_signals items
   - Rename sell_conditions section
   
3. **Update get_active_strategy_combinations()** (10 min)
   - Change from baseline+layers to entry_signals
   - Maintain identical combination logic
   
4. **Find and Fix References** (15 min)
   - Search for baseline/layers usage
   - Update to entry_signals
   - Update sell_conditions references
   
5. **Run Tests** (5 min)
   - Verify all tests pass
   - Fix any remaining reference issues

**Total Estimated Time: 40 minutes**

## Success Criteria

1. **Configuration Loads**: New structure loads without errors
2. **All Tests Pass**: Zero functional regressions  
3. **Type Safety**: mypy validation passes
4. **Identical Behavior**: System executes exactly as before

## Implementation Notes

### Kailash Nadh Principles Applied
- **Minimal Change**: Only restructure data, don't change behavior
- **Clear Purpose**: Enable future composability without current complexity
- **Discipline**: Don't build adaptive features yet (Story 028)
- **Measurable**: Success = no regressions + structure ready for next story

### What This Story Does NOT Do
- **No Strategy Selection Logic**: Current system still uses all entry_signals
- **No Rule Discovery**: No automatic rule combination testing
- **No New Rule Functions**: Zero new trading logic
- **No Behavior Changes**: System executes identically

### Future Story Enablement
This story enables:
- **Story 028**: Strategy Seeker can iterate through entry_signals
- **Story 029**: Adaptive heuristics can test rule combinations  
- **Future**: Clean composable architecture for strategy discovery

---
**Ready for Development**: This story provides the minimal foundation needed for adaptive strategy discovery while maintaining system stability and zero functional changes.
