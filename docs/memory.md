### Brittle CWD Management in CLI Tests (2025-06-15)
**Issue**: CLI tests (`test_cli.py`) were failing with a cryptic `UsageError` (exit code 2) instead of the expected application error (exit code 1).
**Root Cause**: The tests used `os.chdir()` to manually change the current working directory to a temporary location containing config files. This direct manipulation of global state is a brittle pattern that can conflict with the test runner's (`typer.testing.CliRunner`) own environment management, leading to unpredictable behavior. The runner appeared to fail to locate the command correctly, resulting in a `UsageError` before the application's own error handling could be invoked.
**Fix**: Refactored the CLI tests to use the `runner.isolated_filesystem()` context manager. This is the idiomatic and robust method provided by the `click`/`typer` testing framework. It handles creating a temporary directory, changing into it, and cleaning up automatically, without the side effects of manual `os.chdir()`.
**Prevention**: When testing CLI commands that depend on files in the current working directory, always prefer the testing framework's built-in filesystem isolation tools (e.g., `runner.isolated_filesystem()`) over manual state manipulation like `os.chdir()`. This makes tests more robust, self-contained, and less prone to environment-related failures.

---

### Fragile "Magic" Path Resolution in CLI (2025-06-15)
**Issue**: CLI command tests were failing with an unexpected `UsageError` (exit code 2), instead of the application's designed error path (exit code 1).
**Root Cause**: A structural flaw where the CLI used a "magic" path resolution function to find config files in multiple locations (Current Working Directory and a calculated "project root"). This created a fragile, implicit dependency on the file system layout which was not robust, especially under testing conditions using `typer.testing.CliRunner`. The complex interaction caused an internal `typer` error rather than the application's explicit `FileNotFoundError` handling.
**Fix**: 
1. Removed the complex `resolve_path` function from `cli.py`.
2. Modified the `run` command to look for `config.yaml` and `rules.yaml` directly in the current working directory.
**Prevention**: Avoid "magic" file-finding logic in CLI tools. Enforce a simple, explicit convention (e.g., "config files must be in the CWD") or accept configuration paths as explicit command-line arguments. This improves robustness, predictability, and testability.

---

### Inconsistent CLI Application Pattern (2025-06-15)
**Issue**: `ImportError: cannot import name 'app'` during test collection, caused by `__init__.py` attempting to import a CLI application object that was not defined in `cli.py`.
**Root Cause**: A structural mismatch between the CLI implementation and package design. `cli.py` used the simple `typer.run(function)` pattern, suitable for standalone scripts, while `__init__.py` and `pyproject.toml` expected a reusable `typer.Typer` object named `app` for integration into the larger package and for correct script entry point generation.
**Fix**: 
1. Refactored `cli.py` to define a central `app = typer.Typer()` instance and registered the main function as a command using `@app.command()`.
2. Changed the `pyproject.toml` script entry point from `kiss_signal.cli:main` to `kiss_signal.cli:app`.
3. Modified `tests/test_cli.py` to import and use the shared `app` object, making tests more aligned with the actual application structure.
**Prevention**: For CLI tools intended to be part of an importable package, consistently use the `typer.Typer()` application object pattern. This ensures the CLI is a well-defined, importable component, preventing structural conflicts between module implementation and package-level integration.

---

### Unstable CLI Tests Due to Implicit CWD Dependency (2025-06-15)
**Issue**: CLI command tests were failing with a `UsageError` (exit code 2), indicating the test runner could not properly invoke the command. This occurred despite using the recommended `runner.isolated_filesystem()` which is designed to manage test-specific files.
**Root Cause**: The core structural issue was the CLI's implicit dependency on the Current Working Directory (CWD) to find `config.yaml` and `rules.yaml`. Test helpers like `isolated_filesystem` (or manual `os.chdir`) change the CWD, which can interfere with `pytest`'s path resolution mechanisms for the application's source code. This created a fragile state where the test runner could no longer locate the command to execute, causing a failure before the application's own logic and error handling could run. Previous fixes had only swapped one CWD-manipulation technique for another, failing to address the underlying coupling.
**Fix**: The dependency on the CWD was removed by refactoring the `run` command to accept explicit `--config` and `--rules` path arguments using `typer.Option`. This makes the file dependencies explicit and removes the need for tests to manipulate the CWD. Tests were updated to create temporary config files and pass their paths directly to the CLI command.
**Prevention**: Avoid designing CLI commands that rely on implicit CWD conventions for locating critical files. Instead, prefer explicit path arguments. This decouples the application from the execution environment, making it more robust, predictable, and significantly easier to test without resorting to brittle state manipulation like changing the working directory.

---

### Brittle CLI Test Architecture for File-Based Commands (2025-06-15)
**Issue**: Multiple CLI tests (`test_run_command_*`) were failing with a `UsageError` (exit code 2), indicating a problem at the `Typer` framework level, not within the application's logic. The tests were passing explicit, absolute paths to temporary configuration files.
**Root Cause**: The structural issue was a brittle test architecture that was not properly isolated. Manually creating files in a global temporary directory and passing absolute paths to `CliRunner` created a fragile dependency on the test runner's ability to correctly interpret those paths within its execution context, which failed `Typer`'s `exists=True` validation. This pattern is prone to subtle environment-specific failures.
**Fix**: The tests were refactored to use the `runner.isolated_filesystem()` context manager. This is the idiomatic pattern for testing file-based CLI commands. It creates a temporary, isolated directory, sets it as the Current Working Directory for the test's scope, and ensures cleanup. The tests now create config files within this controlled environment and invoke the CLI, allowing it to use its default CWD-based file discovery mechanism reliably.
**Prevention**: For CLI commands that read or write files, always use the testing framework's filesystem isolation utilities (like `runner.isolated_filesystem()`). This creates robust, self-contained, and hermetic tests that are decoupled from the host's filesystem state, preventing environment-related test failures.

---

### Premature Path Resolution in CLI Tests (2025-06-15)
**Issue**: CLI tests using `runner.isolated_filesystem()` were failing with a `UsageError` (exit code 2), despite correctly creating config files in the isolated CWD.
**Root Cause**: A structural flaw in the CLI command definition. The `typer.Option` for file paths used `resolve_path=True`. This caused `typer` to resolve the default relative path (e.g., `"config.yaml"`) to an absolute path based on the test runner's *initial* CWD, *before* `isolated_filesystem` could change the CWD for the command's execution context. The subsequent `exists=True` check then failed on this incorrect, prematurely-resolved absolute path.
**Fix**: Removed `resolve_path=True` from the `typer.Option` definitions in `cli.py`. This ensures that path validation (`exists=True`) and usage occurs relative to the CWD established by the test environment (`isolated_filesystem`), making the component compatible with standard, idiomatic testing patterns.
**Prevention**: Avoid using `resolve_path=True` on `typer.Option`s that have relative default paths, especially when testing with tools that manipulate the CWD like `runner.isolated_filesystem()`. Let path resolution occur implicitly within the command's logic, which will respect the runtime CWD.

---

### Path Type Handling in CLI Tests with Typer (2025-06-15)
**Issue**: CLI tests using `runner.isolated_filesystem()` were failing with a `UsageError` (exit code 2), despite correctly creating config files in the isolated filesystem.
**Root Cause**: A structural issue where the CLI command was using `Path` typed parameters directly in `typer.Option()`. This causes Typer to implicitly convert relative paths to absolute paths using the starting CWD, before the isolated filesystem context is properly established. When this happens, the path validation (`Path.exists()`) fails because it's checking against paths resolved from the original CWD rather than the isolated filesystem.
**Fix**: Changed the Typer option parameters from `Path` type to `str` type, and only convert them to `Path` objects inside the command function. This ensures path resolution happens within the command's context after the CWD has been properly set by the test framework.
**Prevention**: When using `typer.testing.CliRunner` with `isolated_filesystem()`, avoid using `Path` typed parameters directly in `typer.Option()`. Instead, use string parameters and convert them to `Path` objects within the command function. This ensures that path resolution happens at runtime in the correct working directory context.

---

### Mismatched Test Patterns for File-Based CLI Commands (2025-06-15)
**Issue**: Multiple CLI tests (`test_run_command_*`) were failing with a `UsageError` (exit code 2), while a configuration test (`test_load_config_missing_file`) failed with an incorrect exception type (`ValueError` instead of `FileNotFoundError`).
**Root Cause**: Two related structural issues were identified:
1.  **Incorrect Test Implementation**: The `test_load_config_missing_file` test violated the `load_config(config_path: Path)` function's type contract by passing a `str` instead of a `pathlib.Path` object. This caused an `AttributeError` which was then improperly masked by a generic `except Exception` block, leading to the wrong exception being raised.
2.  **Non-Idiomatic Test Architecture**: The CLI tests used `pytest`'s `tmp_path` fixture to create config files and passed absolute paths to the test runner. This is a non-standard pattern for `typer`/`click` applications and created a fragile interaction with the framework, resulting in `UsageError`s. The project's established best practice, documented in previous memory entries, is to use `runner.isolated_filesystem()` to create a controlled CWD for the command to run in.
**Fix**:
1.  Corrected `test_load_config_missing_file` to pass a `pathlib.Path` object, adhering to the function's type hint.
2.  Refactored all failing CLI tests in `test_cli.py` to use the `runner.isolated_filesystem()` context manager. This simplifies the tests by allowing them to rely on the CLI's default file discovery in the (now controlled) CWD, and aligns them with the project's canonical testing pattern.
**Prevention**: Always adhere to established testing patterns within a project. For file-based `typer`/`click` CLIs, prefer `runner.isolated_filesystem()` to create hermetic tests that are robust and easy to understand. Ensure tests respect the type contracts of the functions they call.

---

### Cascading Failures from Brittle Config and Flawed Test Architecture (2025-06-16)
**Issue**: Widespread, cascading test failures across `test_cli.py`, `test_config.py`, and `test_data_manager.py`. The root causes were interconnected structural issues, not simple logic errors.
**Root Cause**:
1.  **Brittle Pydantic Model**: The `Config` model in `config.py` was not synchronized with `config.yaml` (it was missing fields like `hold_period`) and had mandatory nested fields (`EdgeScoreWeights`) without defaults. This made it intolerant to partial configs and difficult to instantiate in tests, causing validation errors.
2.  **Incorrect Mocking Strategy**: `test_data_manager.py` tried to patch a deferred (in-function) import (`yfinance`) at the module level. This is structurally incorrect as the name doesn't exist in the module's namespace, causing `AttributeError` during test collection.
3.  **Non-Hermetic CLI Tests**: `test_cli.py` tests were not properly isolated. They failed to create all necessary file dependencies (like the universe CSV) within the `isolated_filesystem`, and they attempted to make real network calls via the `DataManager`, violating the principle of hermetic testing.
**Fix**:
1.  **Robust Config Model**: The `Config` model was updated to include all fields from the YAML file and provided a `default_factory` for the nested `EdgeScoreWeights`. This makes the model resilient and easier to work with. The `load_config` function was also hardened to explicitly reject empty files.
2.  **Correct Mocking**: The data manager tests were fixed to patch the `yfinance.Ticker` class directly, which is the correct pattern for mocking a dependency that is imported inside a function.
3.  **Hermetic CLI Tests**: The CLI tests were refactored to be fully hermetic. The `DataManager` is now mocked to prevent network calls, and the tests create a complete, self-contained file environment (`config.yaml`, `rules.yaml`, universe file) for the CLI to run against.
**Prevention**:
1.  Design Pydantic models to be robust by providing sensible defaults, especially for nested models, to simplify testing and instantiation.
2.  When mocking, always target the object where it is looked up. For deferred imports, this usually means patching the source library (e.g., `yfinance.Ticker`) rather than a local alias.
3.  Integration tests for CLI commands must be hermetic. Mock all external interactions (network, databases) and use filesystem fixtures to create a fully controlled environment.

---

### Non-Hermetic Tests Causing Prerequisite Failures (2025-06-16)
**Issue**: Multiple CLI tests in `test_cli.py` were failing with `ValidationError` on `universe_path`, even when the test was intended to check for a different condition (e.g., a missing `rules.yaml`).
**Root Cause**: A structural flaw in the test design. The tests used `runner.isolated_filesystem()` but failed to create a *hermetic* (self-contained) environment. They created a `config.yaml` but neglected to also create the `universe.csv` file that the config pointed to. This caused Pydantic's validation to fail on the missing universe file *before* the CLI could proceed to the logic the test was actually trying to validate (like checking for `rules.yaml`).
**Fix**: Refactored all failing CLI tests to be fully hermetic. Each test now creates all necessary file dependencies (e.g., `config.yaml`, `rules.yaml`, and a dummy `universe.csv`) within the `isolated_filesystem` context. This ensures that prerequisite checks pass, allowing the test to correctly target and validate its intended behavior. External network calls from `DataManager` were also mocked to ensure tests are fast and reliable.
**Prevention**: When testing components that interact with the filesystem, especially within an isolated context, ensure the test setup is hermetic. Create *all* file dependencies that the code under test will access during its execution path. This prevents unrelated, prerequisite errors from masking the true test condition and creates more robust, reliable, and easier-to-debug tests.

---

### Cascading Failures from Inconsistent Configuration and Error Handling (2025-06-16)
**Issue**: Widespread test failures, primarily `AttributeError: 'Config' object has no attribute 'cache_dir'` in `test_cli.py` and an `AssertionError` on an incorrect exception message in `test_data_manager.py`.
**Root Cause**: A set of interconnected structural issues:
1.  **Data Contract Mismatch**: The `Config` Pydantic model (`config.py`) had fallen out of sync with its consumer, `DataManager` (`data_manager.py`). The `DataManager` required a `cache_dir` parameter, but the `Config` model did not define it. The `cli.py` orchestrator failed when it tried to wire them together.
2.  **Error Obscuration**: In `data_manager.py`, a specific `ValueError` (e.g., "missing 'symbol' column") was being caught by a broad `except (ValueError, KeyError)` block and re-raised with a generic message. This broke a test that was correctly asserting on the specific, more informative error.
**Fix**:
1.  **Synchronized Config**: The `Config` model in `config.py` was updated to include the missing `cache_dir` field. The `DataManager` instantiation in `cli.py` was also updated to pass all required parameters, restoring the data contract.
2.  **Preserved Error Details**: The error handling in `data_manager.py`'s `_load_universe` method was refactored. The check for the specific `ValueError` was moved outside the `try...except` block that was incorrectly catching it, allowing the specific error to propagate.
**Prevention**:
1.  Treat configuration models as strict, shared interfaces. When a component's dependencies change, update the configuration schema and any orchestrator code in lockstep.
2.  When handling exceptions, be specific. Avoid broad `except` clauses that can accidentally swallow and re-wrap more specific, informative exceptions raised within the `try` block. This preserves error details, making tests more precise and debugging easier.

---

### Duplicate Rule Configuration Files (2025-06-16)
**Issue**: Duplicate rule configuration files existed at root level (`rules.yaml`) and in config directory (`config/rules.yaml`) with conflicting validation ranges, causing non-deterministic behavior and potential configuration drift.
**Root Cause**: Multiple rule definition files were created during development iterations without consolidating them. The files had different validation constraints (e.g., `fast_period` min values: root had `min: 5`, config had `min: 2`) and different structures (embedded vs. centralized validation), leading to inconsistent rule behavior depending on which file was loaded.
**Fix**: 
1. Consolidated into single canonical file: `config/rules.yaml` with consistent validation ranges
2. Removed root-level `rules.yaml` file to eliminate duplication
3. Updated CLI default from `"rules.yaml"` to `"config/rules.yaml"`
4. Created CI check script (`scripts/check_duplicate_rules.py`) and batch file (`check_rules.bat`) to prevent future duplicates
5. Updated all test files to use config directory structure
**Prevention**: 
- Always run `check_rules.bat` before committing changes to verify single canonical rules file
- Keep rule configuration files only in `config/` directory
- Use consistent validation ranges across all rule definitions
- CI checks will fail if multiple rule configuration files are detected

---

### Misaligned Tests After Refactoring (2025-06-17)
**Issue**: Widespread `AttributeError` failures in `test_data_manager.py` after a major refactoring of the data layer.
**Root Cause**: A structural mismatch between the code and its tests. The core data logic was refactored from a `DataManager` class into a module of pure functions (`kiss_signal/data.py`). The `DataManager` class was kept as a thin, deprecated compatibility shim. However, the test suite (`test_data_manager.py`) was not updated and continued to test the old class structure, including private methods that no longer existed on the shim. This created a fragile state where the tests were validating an obsolete and incomplete interface.
**Fix**: The test suite was refactored to align with the new architecture.
1. All tests in `test_data_manager.py` were modified to import and call functions directly from the `kiss_signal.data` module.
2. Calls to non-existent methods like `dm._fetch_symbol_data()` were replaced with calls to the actual implementation, e.g., `data._fetch_symbol_data()`.

---

### Cascading Test Failures from Inconsistent Test Fixtures and Mock Contracts (2025-06-17)
**Issue**: Widespread test failures in `test_data_manager.py` caused by multiple related structural issues, not a single bug in application code.
**Root Cause**:
1.  **Inconsistent Test Setup**: The `setup_method` for the test class defined a path for a cache directory but never created it on disk. This caused any test that attempted to write to the cache (`touch`, `to_csv`) to fail with `FileNotFoundError`.
2.  **Incorrect Mock Contracts**: Mocks used in tests for `_fetch_symbol_data` and `refresh_market_data` did not return data in the same format (schema) as the real functions. For example, a mock returned a DataFrame with a named index instead of a `date` column, causing `KeyError` downstream when the code under test tried to access the column.
3.  **Brittle Test Code**: A test used a `datetime` object with `os.utime`, which expects a numerical timestamp, causing a `TypeError`.
**Fix**:
1.  **Robust Test Setup**: Modified the `setup_method` to always create the cache directory (`mkdir(parents=True, exist_ok=True)`), ensuring a valid environment for all tests in the class.
2.  **Corrected Mocks**: Updated the mock DataFrames to exactly match the schema (column names, types, and structure) of the data returned by the real functions they were replacing.
3.  **Hardened Test Code**: Corrected the `os.utime` call to use `.timestamp()` to convert the `datetime` object to the required float.
**Prevention**:
1.  **Hermetic Test Fixtures**: Test setup fixtures (like `setup_method` or `pytest` fixtures) must create a complete and valid environment for the code under test. If a test needs a directory, the fixture must create it.
2.  **Strict Mock Contracts**: Mocks must be treated as drop-in replacements that respect the data contract (return type and schema) of the original function. Always validate that mock data structure matches the real data structure.
3.  **Type-Aware Testing**: Write test code that is aware of the types required by underlying libraries and functions (e.g., `os.utime` expecting a timestamp, not a `datetime` object).