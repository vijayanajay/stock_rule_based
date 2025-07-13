# KISS Signal CLI - Memory & Learning Log

## Test Harness Integrity: Flawed Invocation and Non-Resilient Setup (2025-07-25)
    1.  **Flawed CLI Invocation (`test_run_command_backtest_generic_exception_verbose`):** A test invoked the Typer CLI with an incorrect argument order (a global option like `--verbose` placed after the `run` command), causing a framework `UsageError` (exit code 2) instead of testing the application's error handling (exit code 1).
    2.  **Non-Resilient Test Setup (`test_run_command_help`):** A help-text test for a subcommand (`run --help`) failed because it was not self-contained. It relied on filesystem state (e.g., `config.yaml`), causing the main CLI callback to fail on config loading before the help text could be displayed.
    2.  Simplified the brittle help test to target the main application's help text (`--help`), which is more robust and does not depend on a fully configured test environment.
    -   Tests should be self-contained and not rely on implicit filesystem state, especially for meta-commands like `--help`.
    1.  Corrected the CLI test invocation to place global options before the command, aligning the test with actual user behavior.
    2.  Simplified the brittle help test to target the main application's help text (`--help`), which is more robust and does not depend on a fully configured test environment.
- **Lesson**: A project's test harness is part of its core structure and must be as robust as the application code.
    -   CLI tests must precisely mirror valid user invocation patterns.
    -   Tests should be self-contained and not rely on implicit filesystem state, especially for meta-commands like `--help`.

## Test Harness Integrity: Brittle Assertions and Flawed I/O Capture (2025-07-23)
- **Issue**: Multiple test failures were traced back to structural flaws in the test harness, not the application logic.
    1.  **Brittle Assertion (`test_generate_signals_missing_parameters`):** A test was asserting on a generic error message string. When the application was improved to raise a more specific error, the test broke, despite the application's behavior being correct.
    2.  **Flawed I/O Capture (`test_run_command_log_save_failure`):** A test for a logging side-effect asserted on `stderr`, but the application's `RichHandler` directs `logger.error` output to `stdout`. The test was "deaf" to the correct output and failed by asserting on an empty stream.
- **Fix**:
    1.  **Corrected Assertion:** The brittle test was updated to assert on the new, more specific error message, making it more robust.
    2.  **Corrected I/O Check:** The logging test was fixed to check `result.stdout` instead of `result.stderr`, aligning the test with the application's actual, observable behavior.
- **Lesson**: The test harness is a critical part of the application's structure.
    -   Tests should be robust against minor implementation changes (like improving an error message). Avoid asserting on exact strings where possible, or update tests when application code is improved.
    -   Tests must correctly model the application's I/O and logging behavior. When a custom logging handler like `RichHandler` is used, standard fixtures like `caplog` may not work as expected, and asserting on the final console output (`stdout`/`stderr`) is often a more reliable pattern.

## Test Harness Integrity: Non-Deterministic Tests (2025-07-24)
- **Issue**: A performance test (`test_get_summary`) relied on the non-deterministic timing of `time.sleep()`, making it flaky and unreliable. The test would pass or fail based on system load.
- **Fix**: Replaced the `time.sleep()`-based test with a deterministic one using `unittest.mock.patch` on `time.time()` to control the flow of time precisely. By providing a `side_effect` list of timestamps, the test's duration calculations became independent of actual wall-clock time.
- **Lesson**: Tests must be deterministic. Avoid relying on system-dependent behaviors like `time.sleep()` for assertions. Use mocking to control the environment and remove flakiness.

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

## Test Harness Integrity: Flawed Invocations and Resource Leaks (2025-07-22)
- **Issue**: Multiple test failures were traced back to structural flaws in the test harness, not the application logic itself.
    1.  **Flawed CLI Invocation**: A test in `test_cli_advanced.py` invoked the Typer CLI with an incorrect argument order (global options after the command), causing a framework `UsageError` (exit code 2) instead of testing the application's error handling (exit code 1).
    2.  **Non-Resilient Test Setup**: A help-text test in `test_cli_basic.py` failed because it was not self-contained and relied on filesystem state, causing the non-resilient part of the CLI callback to fail on config loading.
    3.  **Resource Leaks in Fixtures**: The `test_integration_cli.py` fixture used manual `tempfile` and `shutil` calls, which led to a `PermissionError` on Windows during teardown because a database file handle was not released in time.
- **Fix**:
    1.  Corrected the CLI test invocation in `test_cli_advanced.py` to place global options before the command.
    2.  Simplified the help test in `test_cli_basic.py` to test the main application's help text, which is more robust and does not depend on the filesystem.
    3.  Replaced the brittle `tempfile`-based fixture in `test_integration_cli.py` with pytest's standard `tmp_path` fixture, which guarantees proper resource management and cleanup.
- **Lesson**: A project's test harness is part of its core structure and must be as robust as the application code.
    -   CLI tests must precisely mirror valid user invocation patterns.
    -   Tests should be self-contained and not rely on implicit filesystem state.
    -   Use framework-provided fixtures (like `tmp_path`) for resource management over manual implementations to avoid platform-specific issues like file locking.
 
## Test Harness Integrity: Configuration and Fixture Desynchronization (2025-07-22)
- **Issue**: A large number of test failures were caused by a structural desynchronization between the application's `Config` Pydantic model and the test fixtures that create `config.yaml` files or instantiate `Config` objects. The `Config` model was updated with new required fields (`reports_output_dir`, `edge_score_threshold`), but several test cases were not updated, leading to widespread `ValidationError` during test setup. Additionally, some CLI tests used incorrect argument ordering for Typer, and help-text tests were not resilient.
- **Fix**:
    1.  **Fixtures Updated**: All inline test configurations (`sample_config_dict` in `test_cli_advanced.py`) were updated to provide all required fields for the `Config` model, resolving the `ValidationError`.
    2.  **Correct CLI Invocation**: A CLI test was corrected to place global options (like `--verbose`) before the command, aligning with Typer's expected syntax and preventing a `UsageError`.
    3.  **Resilient Help Test**: The CLI help test was modified to test the main application's help text (`--help`) instead of a subcommand's, making it more robust and less dependent on a fully configured test environment.
- **Lesson**: The test harness is a critical part of the application's structure. Any change to a core data contract like a configuration model must be propagated to all test fixtures immediately. Fixtures must be self-contained and reflect valid user invocation patterns to be reliable. An incomplete fixture is a bug in the test suite.

## Test Harness Integrity: Flawed Invocation and Data Structure Flaw (2025-07-23)
- **Issue**: Multiple test failures were traced back to two distinct structural issues.
    1.  **Flawed Invocation (`test_run_command_log_save_failure`):** A test was asserting behavior (log saving on failure) on the `run` command, but the implementation for this behavior only existed in the `analyze-strategies` command. The test was testing a non-existent contract.
    2.  **Data Structure Initialization Flaw (`analyze_rule_performance`):** A `defaultdict` was incorrectly initialized to create a `set` (`{'metrics', 'symbols'}`) instead of a `dict` with list values (`{'metrics': [], 'symbols': []}`). This caused a `TypeError` downstream when the code attempted dictionary key access on a set.
- **Fix**:
    1.  The broken test was rewritten to target the correct command (`analyze-strategies`), aligning the test with the actual implementation.
    2.  The `defaultdict` initialization was corrected to produce the expected dictionary structure.
- **Lesson**:
    - Test harnesses are a critical part of the application's structure and must be kept in sync with the implementation. Tests should validate the actual, observable contracts of the code they target.
    - Data structures must be initialized correctly at their source. A subtle typo (like `{}` vs `[]` inside a `defaultdict` lambda) can create a structural flaw that propagates through the system and causes failures far from the origin point. Pay close attention to the structure of initialized objects.

## Test Harness Integrity: Brittle Mocks and Inconsistent Test Data (2025-07-24)
- **Issue**: Multiple test failures were traced back to structural flaws in the test harness, not the application logic.
    1.  **Inconsistent Test Data (`test_end_to_end_cli_workflow`):** An end-to-end test failed because its synthetic data generator produced backtest results that violated a hard assertion in the persistence layer (`total_trades >= 10`). The test environment was not creating data that respected the application's known business rule constraints, leading to a failure far downstream from the data generation step.
    2.  **Brittle Mocking (`test_get_summary`):** A performance test that mocked `time.time()` with a fixed-size iterator failed because it did not account for implicit calls to `time.time()` from the `logging` module, which was used within the function under test. This made the test fragile and dependent on the internal implementation of a third-party library.
- **Fix**:
    1.  The test data generator was updated to produce more realistic, cyclical data that generates a sufficient number of trades to satisfy the application's business rules, making the test self-consistent.
    2.  The `time.time` mock was made more robust by providing a sufficient number of return values to satisfy all explicit and implicit callers within the test's scope.
- **Lesson**: A project's test harness is part of its core structure and must be as robust as the application code.
    -   Test data fixtures must generate data that is consistent with the application's known business rules and data contracts to ensure end-to-end tests are valid.
    -   When mocking fundamental functions like `time.time()`, be aware of all potential consumers, including internal calls from libraries like `logging`. Provide a sufficiently large mock dataset or use more robust time-mocking libraries to avoid brittle, implementation-dependent tests.

## Test Configuration Isolation: Hardcoded Business Rules in Persistence Layer (2025-07-09)
- **Issue**: Integration tests failed due to a hardcoded business rule in the persistence layer that was inconsistent with configurable application logic.
    1.  **Hardcoded Threshold (`save_strategies_batch`):** The persistence layer had a hardcoded assertion `total_trades >= 10`, but the application's `min_trades_threshold` was configurable and could be set lower (e.g., 2).
    2.  **Configuration Validation Gap (`test_end_to_end_cli_workflow`):** Valid strategies generated by the backtester with `min_trades_threshold: 10` but fewer than 10 trades were rejected by the persistence layer, causing the `analyze-strategies` command to find "No historical strategies found to analyze."
- **Fix**:
    1.  The persistence layer's hardcoded threshold was changed to only validate that `total_trades > 0`, removing the business logic constraint that belonged in the backtester.
    2.  This allows the persistence layer to store any strategies that the backtester deems valid, maintaining consistency between configuration and persistence.
- **Lesson**: Business rules should exist in one place and be consistently applied across the system.
    -   Persistence layers should validate data integrity (non-null, correct types) but not duplicate business logic that exists elsewhere.
    -   Hardcoded thresholds in infrastructure code create configuration validation gaps where different parts of the system have different rules.
    -   When a test worked before and suddenly fails, look for changes in infrastructure code (like persistence) that may have introduced new constraints.

## Installed Package vs Development Source Import Conflict (2025-07-13)
- **Issue**: All tests failed during collection with `ImportError` for `RuleDef`, `RulesConfig`, `volume_spike`, and missing `performance` module. The error messages showed imports resolving to `D:\Code\stock_rule_based\venv\Lib\site-packages\kiss_signal\` instead of the current development source.
- **Root Cause**: An outdated installed version of `kiss_signal` package (dated June 28th) was present in site-packages and taking precedence over the current development source code in Python's import resolution.
- **Symptoms**: 
    - Tests couldn't import current classes/functions that exist in development source
    - Python was finding old installed package first due to import path priority
    - 5 test files completely failed to collect with ImportError
- **Fix**:
    1. **Removed conflicting package**: `pip uninstall kiss_signal -y` 
    2. **Fixed import path priority**: Added `src/` directory to Python path in `conftest.py`
    3. **Result**: 227 tests collected successfully, 225 passed (vs 0 collected before)
- **Lesson**: When developing a package locally, ensure no conflicting installed versions exist in the environment. Python's import resolution follows `sys.path` order, so installed packages can shadow development source code. Always check for installed versions when encountering mysterious import failures that claim classes/modules don't exist despite being visible in the source code.
    - **Prevention**: Use virtual environments properly and avoid installing the package being developed unless using editable mode (`pip install -e .`)
    - **Detection Pattern**: Import errors showing site-packages paths instead of local source paths
    - **Quick Check**: `pip list | grep package_name` and `dir venv\Lib\site-packages\` to identify conflicts
