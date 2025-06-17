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