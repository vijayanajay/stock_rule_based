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
**Root Cause**: This was a regression of a previously identified structural issue. The application's CLI layer used `pathlib.Path` as a type hint for file path options in `typer`. By default, `typer` applies an `exists=True` validation to `Path` objects, causing it to fail with exit code 2 before the application's own file validation logic (which is designed to exit with code 1) could execute. While an `exists=False` parameter was present, it was not preventing the framework's pre-emptive validation, leading to a structural conflict where the framework's "magic" undermined the application's explicit control flow.
**Fix**: The `typer.Option` parameters for file paths (`config_path`, `rules_path`) in `src/kiss_signal/cli.py` were changed from being type-hinted as `Path` to `str`. The string paths are then converted to `Path` objects inside the command function. This change removes the special `Path`-handling behavior from `typer`, ensuring that file existence and validation are handled solely by the application's logic as intended.
**Prevention**: Re-affirm the principle: to ensure testability and predictable error handling, avoid relying on framework-level "magic" for validation that is critical to the application's control flow. For file paths that the application must validate itself, accept them as `str` at the CLI boundary and convert them to `Path` objects within the application code. This makes the application's behavior explicit and independent of potential changes or subtleties in the framework's default behaviors.

---