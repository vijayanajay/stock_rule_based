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

## Prevention Strategies

1. **Consistent Code Reviews**: Check for these antipatterns in PR reviews
2. **Static Analysis**: Use mypy, pylint, and other tools to catch issues early
3. **Documentation**: Update this document when new antipatterns are identified
4. **Refactoring**: Prioritize fixing identified antipatterns in existing code
5. **Knowledge Sharing**: Discuss antipatterns in team meetings to build awareness