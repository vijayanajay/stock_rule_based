# MEQSAP Code Review Checklist

## Overview
This checklist ensures all code changes meet MEQSAP's quality standards and architectural requirements. Each item must be verified before approving any pull request.

## Mandatory Items

### 1. Error Handling Policy Compliance ⚠️ **CRITICAL**
- [ ] **Exception Usage**: All custom exceptions inherit from appropriate MEQSAPError subclasses
- [ ] **Third-Party Wrapping**: External library exceptions are properly wrapped in MEQSAP exceptions
- [ ] **Error Messages**: User-facing error messages follow the `[Category] Brief: Details` format
- [ ] **CLI Exit Codes**: CLI commands return correct exit codes per ADR-004 policy
- [ ] **Context Information**: Exceptions include helpful `details` dict when applicable
- [ ] **Logging Standards**: Error logging includes appropriate level and context
- [ ] **Memory.md Compliance**: No anti-patterns from `docs/memory.md` are introduced

### 2. Code Structure & Architecture
- [ ] **Module Boundaries**: Changes respect existing modular structure (`config`, `data`, `backtest`, `reporting`, `cli`)
- [ ] **Coupling**: No unnecessary coupling between modules introduced
- [ ] **Dependencies**: No new dependencies added without architectural discussion
- [ ] **Package Structure**: Complete `__init__.py` files for all packages
- [ ] **Import Verification**: All imports work correctly (`python -c "from module import function"`)

### 3. Type Safety & Validation
- [ ] **Type Hints**: All new functions, methods, and variables have type hints
- [ ] **Pydantic Models**: Data structures use Pydantic models where appropriate
- [ ] **MyPy Compliance**: Code passes `mypy` type checking without errors
- [ ] **Runtime Validation**: Input validation is implemented for public APIs

### 4. Testing Requirements
- [ ] **Test Coverage**: New code is covered by tests (aim for >90%)
- [ ] **Test Structure**: Tests match actual implementation structure
- [ ] **Mock Specifications**: Mock objects match actual return types and interfaces
- [ ] **Error Testing**: Error scenarios are tested with proper exception assertions
- [ ] **Integration Testing**: CLI commands tested end-to-end where applicable
- [ ] **Test Independence**: Tests don't depend on external resources or specific execution order

### 5. Documentation Standards
- [ ] **Docstrings**: All public functions and classes have clear docstrings
- [ ] **Type Documentation**: Parameters and return values documented with types
- [ ] **Usage Examples**: Complex functions include usage examples in docstrings
- [ ] **README Updates**: Changes that affect usage update relevant documentation
- [ ] **ADR Updates**: Architectural changes reference or update relevant ADRs

### 6. CLI-Specific Requirements (if applicable)
- [ ] **Command Structure**: Proper Typer subcommand structure
- [ ] **Help Text**: Commands and options have clear help text
- [ ] **Error Handling**: CLI exceptions use return codes, not raised exceptions
- [ ] **User Experience**: Error messages are actionable and user-friendly
- [ ] **Testing**: CLI help is accessible (`python -m module --help`)

### 7. Performance & Security
- [ ] **Resource Management**: Proper cleanup of resources (files, connections, etc.)
- [ ] **Input Sanitization**: User inputs are validated and sanitized
- [ ] **Error Information**: Error messages don't leak sensitive information
- [ ] **Performance Impact**: Changes don't introduce obvious performance regressions

## Error Handling Deep Dive

### Exception Definition Review
For any new custom exceptions:
```python
# ✅ Good: Follows ADR-004 standards
class SpecificDataError(DataError):
    """Raised when specific data validation fails.
    
    Args:
        message: Human-readable error description
        details: Dict with validation context
        original_error: Optional wrapped exception
    """
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.details = details or {}
        self.original_error = original_error

# ❌ Bad: Doesn't follow standards
class DataIssue(Exception):
    pass
```

### Error Wrapping Review
```python
# ✅ Good: Proper exception wrapping
try:
    data = external_api_call()
except requests.RequestException as e:
    raise DataError(
        f"Failed to fetch data: {str(e)}",
        details={"api_endpoint": endpoint, "error_type": "network"},
        original_error=e
    )

# ❌ Bad: Silent failure or bare exception
try:
    data = external_api_call()
except:
    return None  # Silent failure
```

### CLI Error Handling Review
```python
# ✅ Good: Proper CLI error handling
@app.command()
def process_data(file_path: str) -> None:
    try:
        result = process_file(file_path)
        print(f"Success: {result}")
    except ConfigError as e:
        logger.error("Configuration error: %s", str(e))
        sys.exit(1)
    except DataError as e:
        logger.error("Data processing error: %s", str(e))
        sys.exit(2)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        sys.exit(10)

# ❌ Bad: Exceptions propagate to CLI framework
@app.command()
def process_data(file_path: str) -> None:
    result = process_file(file_path)  # May raise exceptions
    print(f"Success: {result}")
```

## Review Process

### 1. Automated Checks
Before manual review, ensure all automated checks pass:
```bash
# Type checking
mypy src/

# Code formatting
black --check src/ tests/

# Linting
flake8 src/ tests/

# Testing
pytest tests/ -v

# Import verification
python -c "import src.meqsap"
```

### 2. Manual Review Priority
1. **Error Handling Compliance** (highest priority)
2. **Architectural Adherence** 
3. **Type Safety**
4. **Test Coverage**
5. **Documentation Quality**
6. **Performance & Security**

### 3. Common Red Flags
- Functions without type hints
- Missing error handling in CLI commands
- New exceptions that don't inherit from MEQSAPError
- Tests that don't cover error scenarios
- Silent failures or generic exception catching
- Missing docstrings on public APIs
- Import errors or incomplete package structure

## Sign-Off Requirements

### For Regular Changes
- [ ] All checklist items verified
- [ ] Automated checks pass
- [ ] At least one other team member reviewed

### For Architectural Changes
- [ ] All checklist items verified
- [ ] ADR created or updated
- [ ] Memory.md updated if new anti-patterns discovered
- [ ] Team discussion completed
- [ ] Documentation updated

## Anti-Pattern Prevention
Reference `docs/memory.md` during review to prevent known issues:
- Import & Package Structure problems
- CLI Testing fragility
- Configuration & Schema Evolution issues
- Exception Handling duplications
- Testing brittleness

Remember: **Quality is non-negotiable.** It's better to request changes than to approve code that doesn't meet our standards.
