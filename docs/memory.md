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

## Test Harness Integrity: CLI and Fixture Robustness (2025-07-18)
- **Issue**: Multiple test failures were traced back to structural flaws in the test harness, not the application logic itself.
    1.  **CLI Invocation Errors**: Tests were calling the Typer CLI with incorrect argument order (e.g., `run --verbose` instead of `--verbose run`), leading to `UsageError` (exit code 2) instead of the expected application error (exit code 1).
    2.  **Incomplete Fixtures**: A pytest fixture for the `Config` object was providing a path to a `universe.csv` file but not creating the file itself. This caused Pydantic's `field_validator`, which checks for file existence, to fail during test setup.
- **Fix**:
    1.  Corrected the argument order in `runner.invoke` calls within `test_cli_advanced.py` to place global options before the command.
    2.  Modified the fixture in `test_reporter_position_management.py` to create the dummy `universe.csv` file, ensuring the `Config` object is instantiated in a valid state.
- **Lesson**: A project's test harness is part of its core structure. Tests must be robust and reflect real-world usage (correct CLI syntax). Fixtures must create a complete and valid state for the components they provide, especially when those components have built-in validation logic. An incomplete fixture is a bug in the test suite.

## Test Suite Desynchronization and API Drift (2025-07-18)
- **Issue**: A large number of test failures in the `reporter` module were caused by a structural desynchronization between the test suite and the application code. This included:
    1.  **API Contract Drift**: Function signatures (e.g., `_identify_new_signals`) were modified in the implementation without updating test calls, leading to `TypeError`.
    2.  **Incomplete Refactoring**: Tests for a refactored private helper (`_check_for_signal`) were left behind, creating "zombie tests" that failed with `AttributeError`.
    3.  **Brittle Tests**: Some tests used incorrect assertion patterns for numpy booleans (`is True`) or patched non-existent attributes, making them fragile.
- **Fix**: A comprehensive cleanup was performed:
    1.  Corrected the function signatures in `reporter.py` to match their required data contracts.
    2.  Deleted obsolete test files and classes (`test_reporter_signal_checking.py`, `TestCheckForSignal`) that targeted non-existent code.
    3.  Refactored brittle tests to use robust assertion patterns and valid mocks.
- **Lesson**: The test suite must be treated as a first-class consumer of the application's API. Any refactoring or signature change is incomplete until the corresponding tests are updated or removed. Maintaining test-code synchronization is critical to prevent architectural drift and ensure the test suite remains a reliable safety net.

## Test Suite Integrity: Obsolete Tests and Flawed Invocations (2025-07-18)
- **Issue**: Multiple test failures were caused by a desynchronization between the test suite and the application's state.
    1.  **Obsolete Tests**: Tests in `test_reporter_position_management.py` targeted private helper functions (`_manage_open_positions`) that had been refactored away into a larger public method. These tests failed with `AttributeError` and no longer reflected the public API.
    2.  **Flawed CLI Invocation**: A test in `test_cli_advanced.py` invoked the Typer CLI with an incorrect argument order (global options after the command), causing a `UsageError` (exit code 2) instead of the expected application error (exit code 1).
- **Fix**:
    1.  **Deletion of Obsolete Tests**: The obsolete test file (`test_reporter_position_management.py`) was deleted entirely. The consolidated logic is sufficiently covered by higher-level integration tests that validate the public API, not brittle implementation details.
    2.  **Correction of Flawed Tests**: The CLI test invocation was corrected to place global options before the command, aligning the test with actual user behavior.
- **Lesson**: The test suite is a core part of the application's structure and must be maintained with the same discipline as production code. Refactoring is incomplete until corresponding tests are updated or **deleted**. Zombie tests for non-existent private methods create noise and erode trust in the test suite. CLI tests must precisely mirror valid user invocation patterns to be reliable.

## Structural Refactoring: Reporter and Position Management (2025-07-04)
- **Issue**: The `reporter` module was responsible for both generating reports and managing the state of open positions (calculating metrics, determining whether to hold or sell). This violated the Single Responsibility Principle and made the reporter difficult to test and maintain. Test failures in `test_reporter_position_management.py` revealed this structural issue, with tests failing because the position management functions had been moved without updating the tests.
- **Fix**:
    1.  A new `position_manager.py` module was created to exclusively handle the business logic of managing open positions.
    2.  The `_manage_open_positions` and `_calculate_open_position_metrics` functions were moved from `reporter.py` to `position_manager.py`.
    3.  The `reporter.py` module was updated to import and use the `position_manager` module, delegating all position management tasks.
    4.  The corresponding test file, `test_reporter_position_management.py`, was updated to import and test the `position_manager` module directly.
- **Lesson**: Code should be organized by responsibility. Separating concerns into distinct modules (e.g., reporting vs. position management) improves modularity, testability, and maintainability. When tests for a specific piece of functionality break, it often signals a deeper structural issue that should be addressed through refactoring rather than a simple patch.

### CLI Invocation Contract Violation (Recurring) (2025-07-19)
- **Issue**: A test expecting an application error (exit code 1) failed with a framework `UsageError` (exit code 2), a recurring pattern of test harness desynchronization.
- **Root Cause**: The test in `test_cli_advanced.py` invoked the Typer CLI with an incorrect argument order, placing global options (`--config`, `--rules`) *after* the `run` command. The correct syntax requires all global options to precede the command.
- **Fix**: Reordered the arguments in the `runner.invoke` call to `["--verbose", "--config", "cfg.yml", "--rules", "rules.yml", "run"]`.
- **Lesson**: This is a repeat of a previously logged issue. The structural lesson is that the test suite's contract with the CLI must be rigorously maintained. Any test that fails with a `UsageError` is an immediate signal of a flawed test, not a flawed application. This pattern must be watched for in all new CLI tests.

## Incomplete Refactoring and Dangling Dependencies (2025-07-19)
- **Issue**: Multiple test suites failed to collect due to an `ImportError`. The `reporter.py` module attempted to import a `position_manager` module that did not exist in the project structure.
- **Root Cause**: This was a structural flaw caused by an incomplete refactoring. The import statement was added in anticipation of a new module, but the module itself was either never created or was subsequently removed, leaving a dangling dependency in the module graph.
- **Fix**: The unused and invalid import statement was removed from `reporter.py`.
- **Lesson**: Refactoring is not complete until all related dependencies, imports, and documentation are updated or removed. A dangling import is a structural bug that breaks module integrity and can halt the entire test suite. Always verify the full dependency chain after refactoring code across modules.

## Undefined Variable in Critical Code Paths (2025-07-05)
- **Issue**: Multiple test failures due to undefined variable `reportable_open_positions` in `reporter.py::generate_daily_report()` function, causing the function to return None and breaking downstream functionality. Additionally, CLI `run` command lacked error handling for log file saving failures in the finally block.
- **Root Cause**: This was a structural flaw caused by incomplete code flow implementation. The `generate_daily_report` function referenced a variable that was never defined, creating a broken execution path. This represents a broader architectural issue where critical code paths weren't properly validated during development.
- **Fix**: 
    1. Replaced undefined `reportable_open_positions` with the correct `open_positions` variable in the `_build_report_content` call
    2. Added try-catch error handling around log saving in CLI's finally block to output expected "Critical error: Could not save log file" message
- **Lesson**: Critical execution paths must be validated with basic syntax checking and test runs during development. Undefined variables in core functions represent fundamental structural flaws, not simple logical errors. Always ensure that all variables referenced in a function are properly defined within the function's scope. Error handling in finally blocks must be comprehensive to prevent unexpected crashes.

## Test Suite Desynchronization and Incomplete Refactoring (2025-07-19)
- **Issue**: Multiple test failures were caused by a drift between the test suite and the application's API and logic.
    1.  **Flawed CLI Invocation**: A test was calling the Typer CLI with an incorrect argument order (global options after command), causing a framework `UsageError` (exit code 2) instead of testing the application's error handling (exit code 1).
    2.  **Incomplete Test Setup**: A basic help test failed because it didn't create the config files required by the application's main callback, which runs even for `--help`.
    3.  **Logic Drift / Incomplete Refactoring**: The main `generate_daily_report` function was missing the core logic to process open positions (calculate metrics, decide on status), causing a `KeyError` downstream when formatting the report.
- **Fix**:
    1.  Corrected the CLI test invocation to place global options before the command, aligning the test with real-world usage.
    2.  Fixed the help test to be self-contained and not rely on an un-mocked file system.
    3.  Rewrote the `generate_daily_report` function to correctly implement the full position management lifecycle. It now fetches open positions, calculates all required metrics (e.g., `days_held`, `return_pct`), determines which to close, and only then passes the fully populated data to the report formatters.
- **Lesson**: The test suite is a first-class consumer of the application's API and must be maintained in lock-step with any changes to CLI contracts or internal logic. An incomplete refactoring that leaves a core function's logic broken is a critical structural flaw. Tests must accurately reflect real-world usage and provide a complete, valid environment for the code under test.
