# KISS Signal CLI - Code Antipatterns to Avoid

This document catalogs antipatterns identified in our codebase to help developers avoid repeating these issues in future development.

## Structural Antipatterns

### 1. Implicit Working Directory Dependency
**Problem**: Code assumes specific working directory without validation
**Impact**: Tests fail when run from different contexts, production deployment issues
**Solution**: 
- Use absolute paths or project-relative path resolution
- Implement dedicated path resolution strategies
- Inject file paths as dependencies rather than hardcoding

```python
# WRONG ❌
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# BETTER ✅
def resolve_config_path(config_name="config.yaml"):
    """Resolves config path from multiple possible locations"""
    # Try current dir
    if Path(config_name).exists():
        return config_name
    # Try project root
    project_root = Path(__file__).parent.parent.parent
    if (project_root / config_name).exists():
        return str(project_root / config_name)
    return config_name  # Return original for error handling

with open(resolve_config_path()) as f:
    config = yaml.safe_load(f)
```

### 2. Exception Swallowing
**Problem**: Converting specific exceptions to generic ones loses context
**Impact**: Makes debugging harder, breaks test expectations
**Solution**: 
- Preserve specific exceptions unless transformation adds value
- Include original exception context when wrapping
- Define custom exception hierarchy for domain-specific errors

```python
# WRONG ❌
try:
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
except Exception as e:
    raise ValueError(f"Failed to load config: {e}")

# BETTER ✅
try:
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
except FileNotFoundError:
    # Let specific exceptions bubble up
    raise
except yaml.YAMLError as e:
    # Only wrap when adding context
    raise ConfigParseError(f"Invalid YAML syntax in {config_path}") from e
```

### 3. Typer's `exists=True` with Test Isolation
**Problem**: Path validation occurs before test isolation filesystem is set up
**Impact**: CLI tests fail with `UsageError` even with valid path setup
**Solution**:
- Avoid using `exists=True` in Typer option definitions
- Perform explicit path validation after directory context is established
- Use dependency injection for file paths in CLI commands

```python
# WRONG ❌
@app.command()
def run(
    config_path: Path = typer.Option("config.yaml", exists=True),
):
    # Command logic

# BETTER ✅
@app.command()
def run(
    config_path: Path = typer.Option("config.yaml"),
):
    if not config_path.exists():
        raise typer.BadParameter(f"Config file not found: {config_path}")
    # Command logic
```

### 4. Unchecked Data Type Assumptions
**Problem**: Code assumes data structures have specific types/properties
**Impact**: Runtime errors in downstream components, silent data issues
**Solution**:
- Validate data at module boundaries
- Use explicit type checking and conversion
- Fail early with clear error messages

```python
# WRONG ❌
def process_price_data(df):
    # Assumes df has DateTimeIndex
    return df.resample('D').mean()

# BETTER ✅
def process_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process price data with daily resampling.
    
    Args:
        df: DataFrame with DateTimeIndex containing price data
        
    Returns:
        DataFrame with daily resampled prices
        
    Raises:
        ValueError: If df doesn't have a DateTimeIndex
    """
    if not isinstance(df.index, pd.DateTimeIndex):
        raise ValueError("DataFrame must have DateTimeIndex")
    return df.resample('D').mean()
```

### 5. Tight Coupling to External Systems
**Problem**: Direct calls to file system, APIs, or databases without abstraction
**Impact**: Hard to test, rigid dependencies, brittle code
**Solution**:
- Use dependency injection for external systems
- Define interfaces/protocols for external dependencies
- Create test doubles (mocks) for external dependencies

```python
# WRONG ❌
def get_data():
    import yfinance as yf
    return yf.download("AAPL")

# BETTER ✅
class DataSource:
    """Interface for data sources"""
    def get_data(self, symbol: str) -> pd.DataFrame:
        """Get data for symbol"""
        raise NotImplementedError
        
class YFinanceDataSource(DataSource):
    def get_data(self, symbol: str) -> pd.DataFrame:
        import yfinance as yf
        return yf.download(symbol)
        
# Usage with dependency injection
def backtest(data_source: DataSource, symbol: str):
    data = data_source.get_data(symbol)
    # Rest of backtest logic
```

## CLI and Architecture Antipatterns

### 6. CLI Fat Orchestration
**Problem**: CLI commands contain complex business logic and orchestration
**Impact**: Hard to test business logic, CLI becomes bloated, poor separation of concerns
**Solution**:
- Keep CLI thin - only handle user interface concerns
- Delegate complex logic to dedicated engine/service modules
- Use dependency injection to pass dependencies to business logic

```python
# WRONG ❌
@app.command()
def run(config: str, rules: str):
    # 50+ lines of config loading, data setup, analysis, etc.
    config_path = Path(config)
    app_config = load_config(config_path)
    data_manager = DataManager(...)
    results = data_manager.refresh_market_data()
    # ... more complex logic ...

# BETTER ✅
@app.command()
def run(config: str, rules: str):
    try:
        app_config = load_app_config(Path(config), Path(rules))
        console.print("[1/2] Configuration loaded.")
        
        console.print("[2/2] Running analysis...")
        signals = run_analysis(app_config)
        
        # Simple output formatting only
        console.print("✨ Analysis complete.")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
```

### 7. Inconsistent Test Mocking Strategies
**Problem**: Tests mock at different levels (module vs class vs function) inconsistently
**Impact**: Brittle tests, unclear test boundaries, difficult maintenance
**Solution**:
- Mock at the appropriate boundary - typically the module's public API
- Be consistent with mocking strategy across similar tests
- Update tests when refactoring changes the mocking surface

```python
# WRONG ❌ - Mocking removed dependencies
with patch("kiss_signal.cli.DataManager.refresh_market_data"):
    # This will fail after refactoring removes DataManager from CLI

# BETTER ✅ - Mock the current interface
with patch("kiss_signal.cli.run_analysis") as mock_analysis:
    mock_analysis.return_value = {"refresh_results": {}, "signals": []}
    # Test continues to work after refactoring
```

### 8. Function Signature Changes Without Parameter Updates
**Problem**: Renaming or extending functions without updating all call sites
**Impact**: Breaking changes, undefined behavior, hard-to-trace bugs
**Solution**:
- Use automated refactoring tools when possible
- Maintain backward compatibility with deprecated parameters
- Update all imports and usage consistently

```python
# WRONG ❌ - Breaking change
def load_config(config_path: Path) -> Config:  # Old signature
    # implementation

def load_app_config(config_path: Path, rules_path: Path) -> Config:  # New signature
    # implementation

# BETTER ✅ - Backward compatible transition
def load_app_config(config_path: Path, rules_path: Optional[Path] = None) -> Config:
    """New unified config loader"""
    # implementation

def load_config(config_path: Path) -> Config:
    """Deprecated: Use load_app_config instead"""
    warnings.warn("load_config is deprecated, use load_app_config", DeprecationWarning)
    return load_app_config(config_path)
```

### 9. Missing Freeze Date Propagation
**Problem**: CLI accepts freeze_date parameter but doesn't pass it to engine/config
**Impact**: Feature silently doesn't work, inconsistent behavior
**Solution**:
- Ensure parameters flow through the entire call chain
- Add validation that critical parameters are properly propagated
- Test parameter propagation explicitly

```python
# WRONG ❌ - Parameter not propagated
@app.command()
def run(freeze_data: Optional[str] = None):
    freeze_date = date.fromisoformat(freeze_data) if freeze_data else None
    config = load_app_config(Path(config), Path(rules))
    # freeze_date is lost here!
    signals = run_analysis(config)

# BETTER ✅ - Proper parameter flow
@app.command()
def run(freeze_data: Optional[str] = None):
    freeze_date = date.fromisoformat(freeze_data) if freeze_data else None
    config = load_app_config(Path(config), Path(rules))
    if freeze_date:
        config.freeze_date = freeze_date  # Ensure propagation
    signals = run_analysis(config)
```

## Code Quality Antipatterns

### 1. Missing Type Annotations
**Problem**: Code without type hints is harder to understand and maintain
**Impact**: More runtime errors, harder refactoring, poorer IDE support
**Solution**:
- Add full type hints to all function signatures
- Use type hints for complex data structures
- Leverage mypy for static type checking

### 2. Inconsistent Logging
**Problem**: Ad-hoc logging approaches across modules
**Impact**: Difficult to trace issues, inconsistent verbosity control
**Solution**:
- Use `logging.getLogger(__name__)` consistently
- Respect verbosity levels
- Use structured logging where appropriate

### 3. Monolithic Functions
**Problem**: Large functions handling multiple concerns
**Impact**: Hard to test, understand, and maintain
**Solution**:
- Break into smaller, focused functions
- Separate concerns (data loading, processing, reporting)
- Stay under 25 lines per function when possible

### 4. Variable Name Shadowing
**Problem**: Using parameter names that conflict with local variables
**Impact**: Confusing code, potential bugs, poor readability
**Solution**:
- Use distinct names for parameters vs local variables
- Consider prefixing parameters (e.g., `config_path` vs `config`)
- Use descriptive variable names that indicate scope

```python
# WRONG ❌ - Parameter shadows local variable
def run(config: str):
    config = load_app_config(Path(config))  # Shadows parameter
    # Now 'config' refers to different things!

# BETTER ✅ - Clear naming
def run(config_path: str):
    app_config = load_app_config(Path(config_path))
    # Clear distinction between path and loaded config
```

## Testing Antipatterns

### 1. Environment-dependent Tests
**Problem**: Tests depend on specific environment state
**Impact**: Flaky tests, different results on different machines
**Solution**:
- Use fixtures to create controlled test environments
- Mock external dependencies
- Use temporary directories or in-memory databases

### 2. Inadequate Test Coverage
**Problem**: Critical paths or edge cases not tested
**Impact**: Regressions, unexpected behavior in production
**Solution**:
- Test happy path, edge cases, and error conditions
- Add regression tests for bug fixes
- Use parametrized tests for similar scenarios

### 3. Test Data Leakage
**Problem**: Tests affecting each other through shared state
**Impact**: Order-dependent tests, flaky results
**Solution**:
- Use isolated fixtures for each test
- Reset shared resources between tests
- Avoid persistent state in test modules

### 4. Syntax Errors in String Replacements
**Problem**: Text editing creates malformed code (missing newlines, etc.)
**Impact**: Tests fail to run, syntax errors in code
**Solution**:
- Always verify syntax after string replacements
- Use proper code formatting tools
- Include sufficient context in replacements to avoid ambiguity

```python
# WRONG ❌ - Missing newline creates syntax error
(config_dir / "rules.yaml").write_text("rules: []")        with patch(...):

# BETTER ✅ - Proper line separation
(config_dir / "rules.yaml").write_text("rules: []")

        with patch(...):
```

## Prevention Strategies

1. **Consistent Code Reviews**: Check for these antipatterns in PR reviews
2. **Static Analysis**: Use mypy, pylint, and other tools to catch issues early
3. **Documentation**: Update this document when new antipatterns are identified
4. **Refactoring**: Prioritize fixing identified antipatterns in existing code
5. **Knowledge Sharing**: Discuss antipatterns in team meetings to build awareness
6. **Automated Testing**: Write tests that catch common antipatterns
7. **Incremental Refactoring**: Make small, focused changes to avoid introducing new antipatterns
8. **Parameter Flow Validation**: Explicitly test that parameters propagate correctly through call chains