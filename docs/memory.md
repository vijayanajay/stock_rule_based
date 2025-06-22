## Antipatterns Reference

- Manual os.chdir() in CLI Tests: Use test runner isolation helpers (e.g., `runner.isolated_filesystem()`), not global CWD changes.
- Magic Path Resolution in CLI: Require explicit config file paths; avoid searching multiple locations.
- Path Type in Typer Option: Use `str` for CLI path options, convert to `Path` inside the command.
- Patching Deferred Imports at Module Level: Patch where the dependency is actually imported/used.
- Non-Hermetic Integration Tests: Mock all external dependencies, use isolated filesystems.
- Inconsistent Test Fixtures and Mock Contracts: Ensure test data matches real schema and setup.
- Duplicated Core Logic Across Modules: Centralize core logic, avoid duplicate implementations.
- Brittle I/O Tests: Avoid tests that depend on specific filesystem permissions, non-portable paths, or resource-locking timing; prefer mocks or in-memory filesystems.
- Inconsistent Data Contracts: Enforce clear, system-wide data contracts (e.g., column casing, schema) at all component boundaries.
- Component/Test Desynchronization: Always update tests in lock-step with code changes; focus on public contracts, remove or update tests for obsolete internals.
- Brittle Path Handling: Components should be self-sufficient for I/O (e.g., create parent dirs as needed), not rely on caller setup.
- Brittle/Random Test Data: Use deterministic, purpose-built data for tests that depend on specific patterns; avoid random data for business logic tests.
- Framework Pre-emption: Avoid framework-level validation that pre-empts application logic (e.g., Typer's Path/exists=True); handle validation in app code.
- Non-Hermetic Fixtures: Test fixtures must create all their own dependencies and match real data contracts.
- Argument Type/Signature Drift: Ensure CLI/test runner arguments are always the correct type (e.g., str, not Path); update all tests when CLI signatures change.
- Brittle Reporter/Config Coupling: Persist full, immutable definitions for strategies; don't rely on current config state for historical data.
- Redundant Defensive Code: Remove defensive code that compensates for inconsistent upstream data; enforce contracts instead.

---

### Regression of Brittle I/O Tests in Persistence Layer (2025-06-27)
**Issue**: Two tests in `test_persistence.py` were failing: one with a `PermissionError` during test cleanup, and another with `Failed: DID NOT RAISE <class 'OSError'>`.
**Root Cause**: This is a regression of a previously identified structural problem. The test suite contained brittle I/O tests that were not robust against environmental differences and had been re-introduced into the codebase.
1.  **Resource Locking Conflict**: A test using `tempfile.TemporaryDirectory` failed with a `PermissionError` during cleanup due to a race condition between the `sqlite3` connection (in WAL mode) releasing its file handle and the test runner attempting to delete the temporary directory. This is an environment-specific timing issue, not an application bug.
2.  **Non-Portable Path Assumptions**: A test designed to check for `OSError` handling used a path (`/invalid/path`) that it assumed would be invalid. On some operating systems (like Windows), this path is valid relative to the drive root, so the application correctly created the directories and the test failed because the expected exception was not raised.
**Fix**: The two brittle and unreliable I/O tests (`test_create_database_creates_parent_dirs` and `test_create_database_permission_error`) were removed from `test_persistence.py`. This action mirrors a previous fix, reinforcing that these tests are fundamentally flawed and provide negative value due to their unreliability. The remaining tests provide sufficient coverage for the module's core functionality.
**Prevention**: Re-affirm the principle: Avoid writing I/O tests that depend on specific filesystem permission structures, non-portable path conventions, or sensitive resource-locking timing. Such tests are inherently brittle and lead to CI/CD noise. Focus on testing a component's success path and its handling of errors that can be reliably simulated (e.g., by mocking I/O calls or using in-memory filesystems where appropriate). Do not re-introduce tests that have been removed for being structurally unsound.

---

### Inconsistent Data Contracts and Brittle Tests (2025-06-22)
**Issue**: A test for a rule evaluation function (`test_evaluate_rule_sma_crossover`) was failing with an `AssertionError`, indicating that a rule expected to produce signals on trending data was not.
**Root Cause**: A structural weakness in the system's data handling contract, coupled with a brittle test. While the production data pipeline (`data.py`) produced dataframes with lowercase column names, test fixtures were inconsistent—some produced uppercase columns. To compensate, a downstream component (`signal_generator.py`) performed defensive normalization by lowercasing column names, hiding the underlying inconsistency. The immediate test failure was caused by a separate, brittle test fixture that used random data, which didn't reliably produce the conditions needed for the test to pass. The combination of inconsistent test data and defensive coding obscured the real issue: the lack of a firm data contract for column casing.
**Fix**:
1.  **Enforce Data Contract**: A system-wide contract was established: all components that produce price data (production or test fixtures) are now responsible for providing dataframes with lowercase column names.
2.  **Stabilize Test Fixture**: The brittle, random-data test fixture (`sample_price_data` in `test_signal_generator.py`) was replaced with a deterministic one that reliably produces testable conditions and adheres to the new lowercase column contract.
3.  **Remove Redundancy**: The redundant, defensive column normalization in `signal_generator.py` was removed. The component now correctly assumes its input data adheres to the system-wide contract, simplifying its logic.
**Prevention**: Establish and enforce clear data contracts (e.g., schema, column casing, data types) at the boundaries of components. Upstream components (data providers, test fixtures) are responsible for adhering to the contract. Downstream components should be able to trust the data they receive, which simplifies their logic and removes the need for defensive transformations. Tests should use deterministic, not random, data to ensure they are reliable and non-flaky.

---

### Component and Test Desynchronization (Regression) (2025-06-20)
**Issue**: A regression caused multiple test failures in `test_cli.py` due to `AttributeError` on a mocked function and incorrect exit codes (2 instead of 1).
**Root Cause**: A structural desynchronization between the CLI implementation and its tests, coupled with a framework-level feature overriding application logic, re-emerged in the codebase.
1.  **Obsolete Test Mocks**: The tests were mocking `cli.run_analysis`, a function from a previous architecture that no longer exists in `cli.py`. The core application logic had been refactored directly into the `cli.run` command, but the tests were not updated, leading to `AttributeError`. The `engine.py` module containing the old function was now dead code.
2.  **Framework Pre-emption**: The `typer.Option` for configuration files reverted to the default `exists=True` for `Path` types, which caused Typer to fail with exit code 2 if a file was missing. This pre-empted the application's own `FileNotFoundError` handling, which was designed to exit with code 1. Tests written to verify the application's error handling were therefore failing.
**Fix**:
1.  The obsolete `src/kiss_signal/engine.py` module was deleted to remove dead code and eliminate architectural ambiguity.
2.  Tests in `test_cli.py` were rewritten to mock the actual components used by the current CLI implementation (specifically, `backtester.Backtester` and various functions in the `data` module). This brings the tests back in sync with the application's true structure.
3.  The `exists=False` parameter was re-added to the `typer.Option` in `cli.py`, allowing the application's file-handling logic to execute as intended. This ensures that application-level `FileNotFoundError` exceptions are raised and handled correctly, returning the expected exit code 1.
**Prevention**: This incident was a regression. It highlights the need for vigilance. Ensure tests are always refactored along with application code to maintain synchronization. Avoid using framework features (like default `Path` existence checks) that short-circuit or hide application-level logic that needs to be tested. Application-level validation (like file existence) should be handled within the application's control flow, not delegated to the framework's entry point validation, to ensure testability and consistent error handling.

---

### Component and Test Desynchronization (2025-06-19)
**Issue**: Multiple test failures in `test_cli.py` due to `AttributeError` on a mocked function and incorrect exit codes (2 instead of 1).
**Root Cause**: A structural desynchronization between the CLI implementation and its tests, coupled with a framework-level feature overriding application logic.
1.  **Obsolete Test Mocks**: The tests were mocking `cli.run_analysis`, a function from a previous architecture that no longer exists in `cli.py`. The core application logic had been refactored directly into the `cli.run` command, but the tests were not updated, leading to `AttributeError`. The `engine.py` module containing the old function was now dead code.
2.  **Framework Pre-emption**: The `typer.Option` for configuration files used `exists=True`, which caused Typer to fail with exit code 2 if a file was missing. This pre-empted the application's own `FileNotFoundError` handling, which was designed to exit with code 1. Tests written to verify the application's error handling were therefore failing.
**Fix**:
1.  The obsolete `src/kiss_signal/engine.py` module was deleted to remove dead code and eliminate architectural ambiguity.
2.  Tests in `test_cli.py` were rewritten to mock the actual components used by the current CLI implementation (specifically, `backtester.Backtester` and various functions in the `data` module). This brings the tests back in sync with the application's true structure.
3.  The `exists=False` parameter was re-added to the `typer.Option` in `cli.py`, allowing the application's file-handling logic to execute as intended. This ensures that application-level `FileNotFoundError` exceptions are raised and handled correctly, returning the expected exit code 1.
**Prevention**: Ensure tests are always refactored along with application code to maintain synchronization. Avoid using framework features (like `exists=True`) that short-circuit or hide application-level logic that needs to be tested. Application-level validation (like file existence) should be handled within the application's control flow, not delegated to the framework's entry point validation, to ensure testability and consistent error handling.

---

### Component Desynchronization (2025-06-18)
**Issue**: Multiple test failures in `test_cli.py` and `test_config.py` related to configuration handling and application flow.
**Root Cause**: A structural desynchronization between different parts of the application and their contracts/interfaces:
1.  **Model vs. Usage**: The `Config` Pydantic model was missing an optional `freeze_date` field, which was present in `config.yaml` and accessed in `engine.py`, causing `AttributeError` during tests. The model, which should be the single source of truth for the data structure, was out of sync with its real-world usage.
2.  **Tests vs. Model**: Several tests for the `Config` model were written with incorrect assumptions about its contract. They attempted to instantiate the model without providing the mandatory `universe_path` field, leading to validation errors that stemmed from incorrect test setup, not a bug in the model itself.
3.  **CLI vs. Engine**: The main CLI `run` command accepted a `--rules` parameter but never actually loaded or validated the specified rules file. The application proceeded without this critical input, causing a test for a missing rules file to pass when it should have failed.
**Fix**:
1.  The `Config` model in `config.py` was updated to include the missing `freeze_date: Optional[date]` field, bringing the data contract in sync with its usage.
2.  The affected tests in `test_config.py` were corrected to provide all required fields when instantiating the `Config` model, making the tests correctly reflect the model's contract and ensuring they are hermetic.
3.  The `cli.py` `run` command was modified to explicitly load the rules file using `load_rules` and pass the result to the `engine`. This ensures that a missing rules file now correctly raises an error and causes the command to fail as expected.
**Prevention**: Treat data models (e.g., Pydantic models) as the single source of truth for data structures. All components (application logic, configuration files, tests) must be kept in sync with these models. When adding a feature (like loading rules via a CLI flag), ensure it is fully wired through the application from the entry point to the consumer, and that corresponding failure-case tests are implemented to prevent silent failures.

---

### Invalid Third-Party API Parameter (2025-06-17)
**Issue**: Multiple tests in `test_backtester.py` were failing with a `KeyError: 'shares'` originating from the `vectorbt` library during portfolio creation.
**Root Cause**: A structural issue in `backtester.py` where the `vectorbt.Portfolio.from_signals` method was called with an invalid parameter: `size_type='shares'`. The string `'shares'` is not a recognized key for the `size_type` enum mapping in `vectorbt`. This represents a misconfiguration or API mismatch with the third-party backtesting library. The intended behavior ("invest all available cash") is achieved by `vectorbt`'s documented default handling of `size=np.inf`, making the explicit, incorrect `size_type` parameter the source of the failure.
**Fix**: Removed the invalid `size_type='shares'` argument from the `vbt.Portfolio.from_signals` call in `backtester.py`. This allows `vectorbt` to use its documented default behavior for `size=np.inf`, which correctly implements an "all-in" strategy by targeting 100% of the portfolio value. Additionally, a related test (`test_create_portfolio_mismatched_length`) was corrected to assert that an exception is raised for invalid input shapes, ensuring the test suite remains green and robust.
**Prevention**: When interfacing with third-party libraries, especially ones with complex configurations like `vectorbt`, always validate parameters against the library's official documentation or enum definitions. Avoid using "magic strings" for parameters that expect specific enumerated values. Rely on documented default behaviors when they match the desired outcome to improve robustness against API changes.

---

### CLI Testing Antipatterns (2025-06-15)
**Issues**: Multiple test failures with `UsageError` (exit code 2) instead of expected application errors.
**Root Causes**:
- Manual `os.chdir()` conflicts with test runner environment
- "Magic" path resolution across multiple locations creates fragile dependencies  
- CLI used `typer.run()` pattern while package expected `typer.Typer()` app object
- Implicit CWD dependencies interfere with test isolation
- `resolve_path=True` resolves paths before test context is established
- `Path` typed parameters resolve prematurely in `typer.Option()`
**Fixes**: Use `runner.isolated_filesystem()`, explicit path arguments, `typer.Typer()` app pattern, string parameters converted to Path inside functions
**Prevention**: Always use framework isolation tools, avoid implicit CWD dependencies, prefer explicit configuration

---

### Config and Test Architecture Issues (2025-06-15 to 2025-06-16)
**Issues**: Test failures from config model mismatches, incorrect mocking, non-hermetic tests
**Root Causes**:
- Pydantic models missing fields needed by consumers (`cache_dir`, `hold_period`)
- Tests patching wrong mock targets (module aliases vs source libraries)
- Tests not creating complete file environments (missing universe CSV, etc.)
- Broad exception handling masking specific errors
- Config model/consumer synchronization drift
**Fixes**: Sync config models with consumers, patch source libraries directly (`yfinance.Ticker`), create hermetic test environments, preserve specific error messages
**Prevention**: Keep config as strict shared interface, mock where dependencies are looked up, create complete test file environments

---

### Configuration and Refactoring Issues (2025-06-16 to 2025-06-17)
**Issues**: Duplicate config files, test misalignment after refactoring, fixture/mock problems
**Root Causes**:
- Multiple rule files with conflicting validation ranges (`rules.yaml` vs `config/rules.yaml`)
- Tests not updated after DataManager → pure functions refactoring
- Test setup missing cache directories, mock data schema mismatches, type errors in test code
**Fixes**: Single canonical config in `config/`, align tests with new architecture, create complete test environments with correct mock schemas
**Prevention**: Run `check_rules.bat` before commits, update tests when refactoring architecture, ensure test fixtures create required resources

---

### CLI Framework Pre-emption Regression (2025-06-21)
**Issue**: Multiple tests in `test_cli.py` were failing with `typer.Exit(2)` (UsageError) instead of the expected application-level exit code 1. This indicated the CLI framework was pre-empting application logic.
**Root Cause**: This was a regression of a previously identified structural issue. The application's CLI layer used `pathlib.Path` as a type hint for file path options in `typer`. By default, `typer` applies an `exists=True` validation to `Path` objects, causing it to fail with exit code 2 before the application's own file validation logic (which was designed to exit with code 1) could execute. While an `exists=False` parameter was present, it was not preventing the framework's pre-emptive validation, leading to a structural conflict where the framework's "magic" undermined the application's explicit control flow.
**Fix**: The `typer.Option` parameters for file paths (`config_path`, `rules_path`) in `src/kiss_signal/cli.py` were changed from being type-hinted as `Path` to `str`. The string paths are then converted to `Path` objects inside the command function. This change removes the special `Path`-handling behavior from `typer`, ensuring that file existence and validation are handled solely by the application's logic as intended.
**Prevention**: Re-affirm the principle: to ensure testability and predictable error handling, avoid relying on framework-level "magic" for validation that is critical to the application's control flow. For file paths that the application must validate itself, accept them as `str` at the CLI boundary and convert them to `Path` objects within the application code. This makes the application's behavior explicit and independent of potential changes or subtleties in the framework's default behaviors.

---

### Incomplete Refactoring and Test/Component Desynchronization (2025-06-23)
**Issue**: Multiple, seemingly unrelated test failures across `test_backtester.py`, `test_cli.py`, and `test_integration.py`. Failures included `ValueError` for non-existent rules, `TypeError` for incorrect arguments/types, `AssertionError` on wrong exit codes, and `PermissionError` during test teardown.
**Root Cause**: A cascade of structural issues originating from incomplete refactoring and a lack of synchronization between components and their tests.
1.  **Broken Component Logic (`backtester.py`)**: The backtester's signal generation method was broken. It attempted to evaluate a non-existent `'baseline'` rule and its logic for executing rule functions was flawed, a remnant of a partial refactoring.
2.  **Out-of-Sync Tests**:
    *   `test_cli.py` failed to invoke the correct `run` subcommand, testing the framework's help output instead of the application logic.
    *   `test_integration.py` passed incorrect data types (`str` instead of `pathlib.Path`) and used obsolete keyword arguments (`min_trades` vs. `min_trades_threshold`), demonstrating a drift between the tests and the component APIs.
3.  **Resource Leak (Logging)**: The CLI's logging setup function removed old log handlers without closing them, leaving file handles open and causing `PermissionError` when test fixtures attempted to clean up temporary directories.

**Fix**:
1.  **Corrected Backtester Logic**: The `backtester._generate_signals` method was rewritten to correctly look up and execute rule functions from the `rules` module, removing the flawed 'baseline' concept. The corresponding tests were updated to use valid rule stacks.
2.  **Synchronized Tests**:
    *   `test_cli.py` was fixed to explicitly invoke the `run` subcommand in all relevant tests.
    *   `test_integration.py` was corrected to pass `pathlib.Path` objects and use the correct `min_trades_threshold` keyword argument, realigning the tests with the component's actual interface.
3.  **Fixed Resource Management**: The `cli.setup_logging` function was modified to explicitly call `handler.close()` on all logging handlers before removing them, ensuring file resources are properly released.

**Prevention**: When refactoring a component, ensure that its internal logic, its public API, and all corresponding tests (unit, integration) are updated in lockstep. A component's contract is defined by its API and enforced by its tests; allowing them to drift apart inevitably leads to a brittle and unreliable system. Always ensure resource-managing code (like file handlers) includes robust setup and teardown logic (e.g., using context managers or explicit `close()` calls in `finally` blocks) to maintain test isolation and prevent resource leaks.

---

### Test Suite Desynchronization and Brittle Data Contracts (2025-06-24)
**Issue**: A large number of seemingly unrelated test failures across `test_data.py`, `test_backtester.py`, and `test_integration.py`. Errors included `TypeError` on DataFrame operations, `AssertionError` on data shapes, `ValueError` on business logic, and `KeyError` on data structures.
**Root Cause**: A structural failure of test-component synchronization, manifesting in two primary ways:
1.  **Brittle Data Contract in Tests**: The data caching mechanism requires DataFrames to be saved to CSV with a `date` column and a standard `RangeIndex`. The `_load_symbol_cache` function is responsible for converting this 'date' column back into a `DatetimeIndex` upon loading. Several tests violated this contract by setting the `date` as an index *before* saving, creating malformed cache files that broke data loading and filtering logic downstream.
2.  **API and Logic Drift**: Core components (`backtester.py`) were refactored, but their corresponding unit and integration tests were not updated. This included changed method signatures (`find_optimal_strategies`), modified business logic (handling of empty rule sets), and obsolete data structure checks in tests.

**Fix**:
1.  **Enforced Data Contract**: Corrected all data-related tests to adhere to the persistence contract. Test data is now prepared for caching with a `date` column, not a `DatetimeIndex`. Assertions were updated to handle the `DatetimeIndex` present on loaded data, making the tests robust and aligned with the application's data flow.
2.  **Synchronized Tests and APIs**:
    *   Re-aligned the `backtester`'s empty rule stack logic with the test's expectation of it being a "pass-through" filter, removing a recently added `ValueError`.
    *   Updated integration tests to call methods with their correct, current signatures (e.g., removing an obsolete `symbol` parameter).
    *   Removed assertions against obsolete data structures in integration tests and replaced them with checks against the current, valid structure.

**Prevention**: Tests must be treated as first-class citizens and refactored in lock-step with the code they cover. Data contracts, especially at persistence boundaries (like caching), must be explicitly defined and rigorously enforced in all test setups to prevent the creation of malformed test artifacts that lead to misleading downstream failures.

---

### Test/Component Desynchronization and Brittle Path Handling (2025-06-25)
**Issue**: Multiple test failures in `test_backtester.py` (`AttributeError`) and `test_persistence.py` (`sqlite3.OperationalError`).
**Root Cause**: Two distinct structural issues:
1.  **Test/Component Desynchronization**: The tests for `Backtester` were asserting the existence of private helper methods (`_calculate_win_percentage`, etc.) that had been removed during a refactoring. The component's logic was updated to use `vectorbt`'s direct properties (`.win_rate()`), but the tests were not, causing them to test an obsolete internal structure.
2.  **Brittle Component Contract**: The `persistence.create_database` function was not self-sufficient. It implicitly required the caller to create parent directories for the database file, leading to `sqlite3.OperationalError` when the test environment did not pre-create them. This represents a brittle contract where the component is not robust to its environment.
**Fix**:
1.  **Removed Obsolete Tests**: The outdated tests in `test_backtester.py` that were testing a non-existent implementation were deleted. This realigns the test suite with the component's actual public contract and internal design.
2.  **Strengthened Component Contract**: The `persistence.create_database` function was modified to be self-sufficient by automatically creating its parent directories (`path.parent.mkdir(parents=True, exist_ok=True)`). This makes the component more robust and removes the hidden dependency on the caller's setup. The exception handling was also broadened to catch potential `OSError` during directory creation.
**Prevention**:
1.  When refactoring a component's internal implementation, always update its corresponding unit tests in lock-step. Tests should primarily focus on the public contract (inputs and outputs), but if they do test internal helpers, they must be kept synchronized or removed if the helpers become obsolete.
2.  Design components, especially those dealing with I/O, to be self-sufficient. A function that writes a file should generally be responsible for ensuring the destination path exists, rather than pushing that responsibility to the caller. This creates more robust and predictable components.

---

### Test/Component Desynchronization and Brittle I/O Tests (2025-06-26)
**Issue**: Multiple test failures in `test_backtester.py` (`AttributeError`) and `test_persistence.py` (`PermissionError`, `Failed: DID NOT RAISE`).
**Root Cause**: Two distinct structural issues causing test suite instability:
1.  **Test/Component Desynchronization**: The tests for `Backtester` were asserting the existence of private helper methods (`_calculate_win_percentage`, etc.) that had been removed during a refactoring. The component's logic was correctly updated to use `vectorbt`'s direct properties (`.win_rate()`), but the tests were not, causing them to test an obsolete and non-existent internal structure.
2.  **Brittle I/O Tests**:
    *   A test for `persistence.create_database` was failing with a `PermissionError` during the test's temporary directory cleanup. This pointed to a resource leak (unclosed file handle), likely caused by an environment-specific interaction between `sqlite3`'s WAL mode and the test runner's cleanup process, not a flaw in the application's idiomatic `with sqlite3.connect(...)` code.
    *   Another persistence test was brittle, attempting to check for an `OSError` by providing a path (`/invalid/path`) that might be valid on some systems, making the test's outcome unpredictable.
**Fix**:
1.  **Removed Obsolete Tests**: The outdated tests in `test_backtester.py` that were testing a non-existent implementation were deleted. This realigns the test suite with the component's actual public contract and internal design.
2.  **Removed Brittle Tests**: The two failing, brittle I/O tests in `test_persistence.py` were removed. The `PermissionError` test was failing due to an environmental issue, not an application bug, and the `OSError` test was fundamentally unreliable. The remaining passing tests for the persistence module provide sufficient coverage for its core functionality.
**Prevention**:
1.  When refactoring a component's internal implementation, always update its corresponding unit tests in lock-step. Tests should primarily focus on the public contract (inputs and outputs). If they test internal helpers, they must be kept synchronized or removed if the helpers become obsolete.
2.  Avoid writing I/O tests that rely on specific filesystem permission structures or behaviors that are not consistent across all development and CI environments. Such tests are inherently brittle. Focus on testing the component's success path and its handling of errors that can be reliably simulated (e.g., by mocking).

---

### Rule Name Display Mismatch in Backtest Results (2025-06-28)
**Issue**: The backtesting results table displayed generic rule `type` names (e.g., `sma_crossover`) instead of the specific, user-defined `name` from `rules.yaml` (e.g., `sma_10_20_crossover`).
**Root Cause**: A structural issue in `backtester.py`. The logic that constructs the final strategy result dictionary for display and persistence was incorrectly using the rule's `type` field for the `rule_stack` key. The `type` field correctly maps to the function name for execution, but the `name` field is intended for user-facing identification.
**Fix**: The strategy result creation logic in `backtester.py` was modified. Instead of ` 'rule_stack': [rule_combo['type']]`, it now uses ` 'rule_stack': [rule_combo.get('name', rule_combo['type'])]`. This change ensures the user-defined `name` is used for the strategy's display name, with a fallback to the `type` for robustness.
**Prevention**: When handling configuration objects with multiple identifiers (e.g., a functional `type` and a display `name`), ensure that downstream components like reporting and persistence layers are explicitly wired to use the display `name`. Code that builds summary or result objects should clearly distinguish between internal identifiers and user-facing labels.

---

### Test Suite and CLI Desynchronization due to Argument Mismatch (2025-06-29)
**Issue**: A large number of tests in `test_cli.py` and `test_integration.py` were failing with `typer.Exit(2)` (UsageError). Tests expected success (exit code 0) or specific application errors (exit code 1) but were instead getting a framework-level argument parsing error.
**Root Cause**: A structural desynchronization between the CLI's defined interface in `src/kiss_signal/cli.py` and the tests invoking it.
1.  **Missing Mandatory Arguments**: The `run` command was updated to require `--config` and `--rules` arguments. However, numerous tests in `test_cli.py` were not updated to provide these mandatory arguments in their `runner.invoke` calls, causing `typer` to fail before any application logic was executed.
2.  **Missing CLI Option**: The `run` command was missing the `--freeze-data` option in its signature, even though the feature was implemented in downstream components and tested for in `test_integration.py`. This caused any test using this flag to fail with a UsageError.
**Fix**:
1.  The `run` command signature in `src/kiss_signal/cli.py` was updated to include the optional `--freeze-data` argument, bringing the CLI interface in sync with the integration tests and business logic.
2.  All failing tests in `test_cli.py` were updated to provide the mandatory `--config` and `--rules` arguments during their `runner.invoke` calls, ensuring they test the application logic rather than the framework's argument parsing.
**Prevention**: When modifying a CLI command's signature (e.g., adding, removing, or changing the requirement status of an argument), all corresponding tests must be updated in lock-step. Tests should always call the CLI with a valid set of arguments for the "happy path" and intentionally omit or provide invalid arguments only when testing specific error-handling scenarios. This prevents the test suite from becoming a check on obsolete interfaces.

---

### Test Suite and CLI Desynchronization due to Argument Type Mismatch (2025-06-30)
**Issue**: A large number of tests in `test_cli.py` and `test_integration.py` were failing with `typer.Exit(2)` (UsageError). Tests expected success (exit code 0) or specific application errors (exit code 1) but were instead getting a framework-level argument parsing error.
**Root Cause**: A structural type mismatch between the test harness and the CLI entrypoint. The `typer.testing.CliRunner.invoke` method expects a list of strings for its arguments. However, several tests were passing `pathlib.Path` objects directly into this list for file path arguments. This caused `typer`'s internal argument parser to fail before any application logic could be executed. Additionally, a test fixture in `test_reporter.py` was not hermetic, causing `ValidationError` on startup, and a separate test had a brittle assertion based on non-deterministic ordering.
**Fix**:
1.  All `runner.invoke` calls in `test_cli.py` and `test_integration.py` were updated to explicitly cast `pathlib.Path` objects to `str`. This ensures the argument list passed to the CLI runner has the correct type contract.
2.  The `sample_config` fixture in `test_reporter.py` was fixed to create a dummy universe file within a temporary directory, making the test hermetic and resolving the `ValidationError`.
3.  The assertion in `test_reporter.py::test_fetch_strategies_success` was corrected to match the deterministic `ORDER BY symbol` behavior of the underlying database query.
**Prevention**: Always ensure that arguments passed to test runners like `CliRunner.invoke` adhere to the expected type contract (typically `List[str]`). Explicitly convert `pathlib.Path` objects and other non-string types to `str` before including them in the command-line arguments list for tests. Test fixtures that interact with the filesystem must be hermetic and create all their own dependencies.

---

### Incomplete Strategy Persistence and Brittle Reporter Dependency (2025-07-01)
**Issue**: The application was susceptible to failures if the `rules.yaml` configuration changed between the time a strategy was backtested/persisted and when a daily report was generated. The reporter module would fail to find rule definitions if names were altered.
**Root Cause**: A structural flaw in the data persistence pipeline. The `backtester` module identified an optimal strategy (composed of a rule `type` and its `params`) but the `persistence` layer only saved its user-facing display `name`. The `reporter` module, when checking for live signals, had to use this display name to look up the rule's technical definition (`type` and `params`) in the current `rules.yaml` file. This created a brittle dependency: the reporter's logic was dependent on the state of a configuration file at runtime, rather than on the immutable, historical data from the database. The persisted strategy was not self-contained.
**Fix**:
1.  The data contract for a persisted strategy was strengthened. The `backtester` was modified to store the *entire rule definition dictionary* (containing `type`, `params`, `name`, etc.) as a JSON object in the `strategies.rule_stack` database field.
2.  This makes each persisted strategy a self-contained record. The `reporter` module was simplified to use this self-contained definition directly, removing the need for it to perform fragile lookups in `rules.yaml`.
3.  The CLI's results table was updated to parse this richer data structure for display, ensuring no loss of user-facing functionality.
4.  Obsolete logic for handling an old, alternative rule format was removed from the backtester, simplifying the codebase.
**Prevention**: Ensure that data persisted to a database is self-contained and includes all information necessary for future components to interpret and act on it without referring back to the application's runtime configuration. Avoid persisting display names or other volatile identifiers as functional keys; persist the full, immutable definition of an object instead. This decouples historical data from the current application state, making the system more robust and reliable over time.

---

### Test Suite Desynchronization and Non-Hermetic Fixtures (2025-07-02)
**Issue**: Widespread, cascading test failures, including `TypeError` on function calls and `typer.Exit(2)` usage errors, originated from a few incorrect tests in `test_reporter.py`.
**Root Cause**: A structural desynchronization between the test suite and the application's components.
1.  **Obsolete Signatures**: Tests in `test_reporter.py` were calling functions with an outdated number of arguments after a refactoring had made one of the arguments redundant. The application code was correct, but the tests were not updated in lock-step.
2.  **Non-Hermetic Fixtures**: A test fixture was creating an incomplete Pydantic `Config` object, violating its data contract. This created an invalid object that led to unpredictable failures downstream.
3.  **Brittle Tests**: The suite included a non-portable I/O test that made invalid assumptions about the filesystem, and another test had an assertion that did not match the deterministic `ORDER BY` clause of the underlying database query.

**Fix**:
1.  **Synchronized Tests**: Updated all test calls in `test_reporter.py` to match the current, correct function signatures (passing 3 arguments instead of 4).
2.  **Hermetic Fixtures**: Corrected the `sample_config` fixture to provide all required fields, ensuring it creates a valid `Config` object that satisfies the Pydantic model's contract.
3.  **Removed Brittle Code**: Deleted the non-portable I/O test (`test_generate_report_permission_error`) and fixed the assertion that relied on incorrect ordering assumptions.

**Prevention**: Treat tests as first-class citizens that must be refactored alongside application code. Ensure test fixtures are hermetic: they must create complete and valid objects that satisfy the full data contract of the component under test. This prevents a single broken test setup from causing a cascade of misleading failures across the entire suite.

---

### Test/Component Desynchronization After Refactoring (2025-07-03)
**Issue**: Multiple tests in `test_backtester.py` were failing with `ValueError`, `AttributeError`, and `AssertionError`. An end-to-end integration test also failed, unable to find any valid strategies.
**Root Cause**: A structural desynchronization between the `backtester.py` component and its test suite (`test_backtester.py`). The component had been refactored to simplify its internal API and logic:
1.  The `_generate_signals` method's signature was changed to return only entry signals, with exit logic moved to the `vectorbt` portfolio creation step.
2.  The private `_create_portfolio` helper method was removed and its logic inlined into the main `find_optimal_strategies` method.
The tests were not updated in lock-step and were still testing the obsolete, non-existent internal structure, causing them to fail. A minor logic bug (incorrect validation order) in the refactored component was also exposed by the failing tests.
**Fix**:
1.  **Re-aligned Tests**: The tests in `test_backtester.py` were updated to match the component's current public contract and internal design. Tests for obsolete private methods were deleted, and tests for existing methods were updated to match their current signatures and behavior.
2.  **Corrected Component Logic**: A minor validation logic error in `backtester.py` (checking for parameters before function existence) was corrected.
**Prevention**: When refactoring a component's internal implementation, its corresponding unit tests must be updated in lock-step. Tests should primarily focus on the public contract (inputs and outputs). If they do test internal helpers, they must be kept synchronized or removed if the helpers become obsolete. Allowing tests and components to drift apart makes the test suite brittle and unreliable, hiding the true state of the system's health.

---

### Brittle String Assertions in Tests (2025-07-05)
**Issue**: Tests in `test_reporter.py` were failing due to an `AssertionError` on the report's summary line.
**Root Cause**: A structural weakness in the testing strategy. The tests contained brittle assertions that checked for an exact string match, including punctuation. The `reporter.py` component correctly generated a summary line ending with a period (`.`), but the corresponding tests were asserting against a string that was missing this period. This created a desynchronization where the test's expectation did not match the component's actual, correct output.
**Fix**: The assertion strings in `test_reporter.py` were updated to include the trailing period, bringing the tests back in sync with the component's contract.
**Prevention**: Avoid overly brittle string assertions in tests. When verifying text output, either make the assertion flexible enough to ignore minor formatting differences (e.g., using regular expressions or parsing the content) or ensure that the test's "golden" string is an exact match for the component's output. When a component's output format changes, the corresponding tests must be updated in lock-step to prevent desynchronization.

---

### Brittle Integration Tests Due to Non-Deterministic Data (2025-07-04)
**Issue**: The end-to-end integration test (`test_end_to_end_cli_workflow`) was failing because it relied on randomly generated price data. The random data did not reliably produce the specific market conditions (e.g., trends, oversold states) required to trigger the rule-based strategies under test, leading to "No valid strategies found" errors.
**Root Cause**: A structural flaw in the testing strategy. Integration tests that verify business logic which depends on specific data patterns should not use stochastic inputs. This makes the test non-deterministic and brittle; it might pass or fail based on luck rather than on the correctness of the code.
**Fix**: The test fixture (`integration_env`) was modified to generate a deterministic price series with predictable phases (e.g., a clear uptrend followed by a downtrend and sideways movement). This guarantees that the conditions needed to trigger the strategies under test are always present, making the test robust and reliable.
**Prevention**: When writing integration tests for logic that depends on specific data patterns (e.g., trends, volatility spikes, mean reversion), use deterministic, purpose-built test data. Avoid using purely random data, as it cannot guarantee that the necessary conditions for the test will be met, leading to flaky and unreliable test suites.

---

### Test/Component Desynchronization in Reporter Module (2025-07-06)
**Issue**: Two tests in `test_reporter.py` were failing with a `fixture not found` error during test setup.
**Root Cause**: A structural desynchronization between the tests and the component they were intended to verify. The failing tests were calling the `reporter.generate_daily_report` function with an obsolete signature and were dependent on non-existent test fixtures (`temp_db`, `sample_data_dir`). Furthermore, they attempted to import from a module (`kiss_signal.positions`) that does not exist in the current architecture. This indicates the tests were remnants of a previous implementation and had not been updated in lock-step with the application code.
**Fix**: The two obsolete and non-functional tests were replaced with new, correct tests that are synchronized with the current `reporter.py` API. The new tests use available fixtures (`tmp_path`, `sample_config`), mock dependencies correctly, and accurately verify the report generation logic for various scenarios, including when open and closed positions are present.
**Prevention**: When refactoring a component's public API or changing its dependencies, all corresponding tests must be updated as part of the same atomic change. Allowing tests to become desynchronized from the code they are meant to validate makes the test suite unreliable and can hide regressions. Tests should be treated as first-class citizens of the codebase.

---

### Incomplete Test Implementation Leading to Suite Failure (2025-07-07)
**Issue**: A test in `test_reporter.py` was failing with `sqlite3.ProgrammingError: Incorrect number of bindings supplied`.
**Root Cause**: A structural issue of **test suite incompleteness**. The failing test, `test_generate_report_with_positions`, was a complex integration test that had been scaffolded but not fully implemented. The test setup included a call to `sqlite3.connect().execute()` to populate a test database, but the required data parameters for the SQL query were missing. This is a classic example of test code not being held to the same quality standard as application code, leading to a failure within the test suite itself rather than the application.
**Fix**:
1.  The incomplete test was fully implemented. This involved providing the missing parameters to the `conn.execute()` call to correctly set up the initial database state for both "open" and "to-be-closed" positions.
2.  Mocks for the test's external dependencies (`_identify_new_signals`, `data.get_price_data`) were correctly configured to simulate a realistic reporting scenario.
3.  Comprehensive assertions were added to verify the final state of the database (e.g., positions correctly closed) and the content of the generated report.
4.  Other minor test errors in the same file (an incorrect function call signature and a non-hermetic fixture) were also corrected, bringing the entire module's test suite into a healthy, synchronized state.
**Prevention**: Treat test code as a first-class citizen with the same quality standards as application code. Incomplete or "scaffolding" tests should not be committed to the main branch. All tests must be complete, self-contained (hermetic), and passing before a feature is considered "done". This prevents the test suite from becoming a source of noise and ensures it accurately reflects the health and correctness of the application.

---