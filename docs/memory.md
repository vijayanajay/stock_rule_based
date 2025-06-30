# KISS Signal CLI - Memory & Learning Log

## AI Coding Pitfalls (Most Common)

### NEVER Reference Non-Existent Methods/Attributes
- `dm.cache_dir`, `dm._validate_data_quality()`, `dm._save_symbol_cache()`
- **Fix**: DELETE broken tests immediately (H-3: prefer deletion)
- **Prevention**: Always verify method signatures exist before writing tests

### Import Anti-Patterns  
- Unused imports: `datetime.datetime`, `datetime.timedelta` 
- Undefined modules: `data` without proper import path
- **Fix**: Remove all unused/incorrect imports
- **Prevention**: Only import what's actually used

### Third-Party Library Pitfalls
- **VectorBT**: NEVER use `size_type='shares'` (invalid enum), use documented defaults
- **Typer**: Use `str` parameters for file paths, convert to `Path` inside functions
- **Rich**: Avoid `console.print()`, `console.save_text()` in `finally` blocks (OS errors)
- **Prevention**: Validate parameters against library documentation

## Test/Component Desynchronization (Major Pattern)

### Root Cause: Tests not updated when components are refactored
- Missing method signatures: `_calculate_win_percentage()` 
- Wrong data types: `str` vs `pathlib.Path`
- Obsolete keywords: `min_trades` vs `min_trades_threshold`
- Missing CLI arguments: `--config`, `--rules` requirements

### Prevention Checklist
- [ ] Update all tests when changing component APIs
- [ ] Run mypy on test files before commit
- [ ] Verify CLI tests use correct argument order (`--verbose` before `run`)
- [ ] Remove tests for deleted functionality immediately
## Data Contract Violations (Critical Pattern)

### Pydantic Model vs Dict Contract Mismatches
- **Root Cause**: Components expecting dicts but receiving Pydantic models (or vice versa)
- **Example**: Backtester expected `rules_config['baseline']` but received `RulesConfig.baseline`
- **Symptom**: `TypeError: 'RulesConfig' object is not subscriptable`
- **Fix**: Update component to accept Pydantic models and use attribute access
- **Prevention**: Keep type hints current; use `RulesConfig` not `dict` in signatures

### Pydantic Attribute Access Anti-Pattern
- **Issue**: Using `.get()` method on Pydantic objects (RuleDef, etc.)
- **Error**: `AttributeError: 'RuleDef' object has no attribute 'get'`
- **Fix**: Use direct attribute access (`rule.name`, `rule.type`, `rule.params`)
- **Prevention**: Remember Pydantic models are NOT dicts - use attributes, not dict methods

### Test Data Temporal Coverage
- **Issue**: Test data ending before freeze/analysis dates
- **Example**: Data to 2023-12-31 but freeze date 2024-06-01 = no backtest data
- **Fix**: Ensure test data covers analysis period + buffer
- **Prevention**: Generate test data to at least 6 months after latest analysis date

### Cache/Data Loading Boundaries
- **Issue**: DataFrames need `date` column for caching, `DatetimeIndex` after loading
- **VectorBT Requirements**: DatetimeIndex must have frequency set (use `pd.infer_freq()` or `asfreq('D')`)
- **Column Names**: Must be lowercase (`close` not `Close`) - enforce in `_load_symbol_cache`
- **Prevention**: Data loaders must guarantee contracts regardless of source (API/cache/file)

### Config Object Mismatches
- **Type vs Name**: Use `rule.get('name', rule['type'])` for display, `type` for execution
- **API Drift**: `rules_config` dict vs `rule_stack` list - keep signatures synchronized
- **Prevention**: Components should accept raw config and parse internally

## CLI Framework Issues (Recurring)

### Typer Path Handling
- **Issue**: `Path` type hints trigger `exists=True` validation before app logic
- **Fix**: Use `str` parameters, convert to `Path` inside functions
- **Prevention**: Avoid framework "magic" for critical validation paths

### Test Invocation Syntax
- **Issue**: Global options (`--verbose`) must come BEFORE command (`run`)
- **Wrong**: `run --verbose --config x`
- **Correct**: `--verbose run --config x`
- **Prevention**: Test CLI syntax exactly as users would type it

### Resilient Parsing
- **Issue**: Main callbacks executing during `--help` generation
- **Fix**: Use `if ctx.resilient_parsing: return` at callback start
- **Prevention**: Keep main callbacks lightweight for meta-commands

## State Management Anti-Patterns

### Reporter State Consistency
- **Issue**: Reading state AFTER writing new state (double-counting)
- **Fix**: Read existing state BEFORE making changes, report separately
- **Prevention**: Clear separation of "read state" vs "write state" phases

### Resource Leaks
- **Issue**: File handles left open during test cleanup (`logging.handlers`)
- **Fix**: Explicit `handler.close()` before removing handlers
- **Prevention**: Use context managers or explicit cleanup in `finally` blocks

## Performance & I/O Robustness

### Environment-Sensitive Operations
- **Avoid**: `rich.console` operations in `finally` blocks (triggers OS errors)
- **Use**: `console.export_text()` + `Path.write_text()` for log saving
- **Prevention**: Standard Python I/O in critical teardown paths

### VectorBT Integration
- **Issue**: Manual loops instead of vectorized operations
- **Correct**: `entry_signals.vbt.fshift(hold_period)` for time-based exits
- **Prevention**: Use library-idiomatic patterns, avoid manual implementations

## Historical Issues Archive

### CLI Testing Antipatterns (2025-06-15)
- **Issue**: `UsageError` (exit code 2) vs expected application errors
- **Causes**: Manual `os.chdir()`, implicit CWD dependencies, wrong `typer` patterns
- **Fix**: Use `runner.isolated_filesystem()`, `typer.Typer()` app, explicit paths

### Config Synchronization (2025-06-16)  
- **Issue**: Pydantic models missing consumer-required fields (`cache_dir`, `hold_period`)
- **Fix**: Keep config as strict shared interface, patch source libraries directly
- **Prevention**: Single canonical config, complete test environments

### Component API Desynchronization (2025-06-23 to 2025-06-29)
- **Pattern**: Refactoring breaks component contracts, tests not updated
- **Examples**: Wrong method signatures, obsolete keywords, missing CLI args
- **Fix**: Update internal logic, tests, and consumers in lockstep
- **Prevention**: Treat tests as first-class API consumers

### Data Contract Violations (2025-06-24 to 2025-06-27)
- **Pattern**: Cache requires `date` column, loader expects `DatetimeIndex` 
- **VectorBT**: Requires frequency on DatetimeIndex (`pd.infer_freq()`)
- **Fix**: Enforce contracts at data boundary regardless of source
- **Prevention**: Data loaders guarantee schema consistency

### Resource Management (2025-06-25 to 2025-06-26)
- **Issue**: Unclosed file handles, brittle I/O tests
- **Fix**: `handler.close()` before removing, avoid environment-dependent tests
- **Prevention**: Robust cleanup, test success paths only

### State Management (2025-06-28 to 2025-07-21)
- **Pattern**: Incorrect sequence of read/write operations
- **Examples**: Display names vs execution types, pre/post-run state confusion
- **Fix**: Read existing state before modifications, clear data flow separation
- **Prevention**: Single responsibility for state transitions

## Signal Combination Logic Flaw (Structural Issue)

### Root Cause: Invalid signal initialization in backtester
- **Issue**: Starting with `pd.Series(True, index=price_data.index)` and ANDing with rule signals
- **Problem**: Rule signals are sparse (few True values), ANDing with all-True series produces zero signals
- **Symptom**: All strategies generate 0 trades regardless of data quality or rule configurations
- **Fix**: Start with first rule's signals, then AND subsequent rules: `entry_signals = rule_signals.copy()` 
- **Lesson**: Signal combination requires understanding signal density - don't start with universal True state

## Data Contract Mismatches (Pydantic vs Dict) (2025-07-21)
- **Issue**: Modules had inconsistent expectations for data structures. The `backtester` produces results containing Pydantic `RuleDef` objects, but consumers like the `persistence` layer serialize them to dictionaries (for JSON). Test mocks were also returning raw dictionaries instead of Pydantic objects. This led to `AttributeError` when functions expected an object but received a dictionary (e.g., `dict.key` vs `dict['key']`).
- **Fix**: Enforced the data contract at module boundaries.
    1.  Updated all test mocks to return Pydantic model instances (`RuleDef`, `RulesConfig`) where the real code would, ensuring tests accurately reflect the application's data flow.
    2.  Updated tests that directly called functions to instantiate the correct Pydantic models as inputs, rather than passing raw dictionaries.
    3.  Made consumer functions (like the CLI's display helper) more robust by using `getattr(obj, 'attr', default)` to handle both object and dictionary-like structures where appropriate, although fixing the source (the tests) was the primary solution.
- **Lesson**: When passing data objects between modules, especially across serialization boundaries (like persistence or test mocks), ensure the data types are consistent. Test mocks must return data with the same type and structure as the real implementation to be effective. Enforce Pydantic model contracts in function signatures and test inputs.

## 🚨 CRITICAL: asfreq() NaN Value Bug (2025-06-30)
**STRICT RULE: NEVER IGNORE THIS PATTERN**

- **Issue**: `pandas.asfreq('D')` creates NaN values for weekends/holidays, breaking all SMA/EMA calculations
- **Symptom**: All rolling calculations return NaN → 0 signals generated → 0 trades → strategy failure
- **Root Cause**: `asfreq()` fills missing calendar days with NaN; rolling windows can't handle NaN data
- **Critical Fix Pattern**: ALWAYS forward-fill after `asfreq()`:
  ```python
  # Handle NaN values created by asfreq - forward fill to preserve trading data
  if price_data.isnull().any().any():
      price_data = price_data.ffill()
      logger.debug(f"Forward-filled NaN values after frequency adjustment for {symbol}")
  ```
- **Evidence**: Application went from 0 signals to 20+ signals per symbol after fix
- **Prevention**: ANY time `asfreq()` is used, immediately check for and handle NaN values
- **Memory Aid**: asfreq = "as frequency" = calendar gaps = NaN poison = ALWAYS ffill()

## Rule Implementation Drift: Strict vs. Standard Definitions (2025-07-01)
- **Issue**: The `engulfing_pattern` rule failed to detect a valid pattern because its implementation used a strict less-than (`<`) comparison for the low engulfment (`current_open < prev_close`) instead of the standard less-than-or-equal-to (`<=`). This caused the rule to miss edge-case signals where the open of the current candle was exactly at the close of the previous one.
- **Symptom**: Tests for `engulfing_pattern` failed on valid edge-case data. Backtests would silently miss valid trading signals, leading to suboptimal strategy discovery.
- **Fix**: The comparison was changed from `<` to `<=` to align with the standard financial definition of the pattern.
- **Lesson**: Financial rule implementations must be rigorously validated against their standard definitions, including edge cases. A seemingly minor logical error (like `<` vs. `<=`) can represent a significant "implementation drift" from the intended strategy, creating a structural flaw in the rule library. Future rule development should include a "definitional review" step to ensure the code accurately reflects the financial concept it represents.
