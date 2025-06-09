# ADR-004: System-Wide Error Handling and Exception Policy

## Status
Accepted

## Context
Analysis from AR-20250515-001 and ongoing maintenance revealed inconsistencies in error handling across the MEQSAP codebase. While `exceptions.py` provides a solid foundation and CLI error handling has been improved (per stories/05-cli-integration-and-error-handling.md), we need a formalized, system-wide policy to ensure:

- Consistent error propagation and handling
- Predictable user experience with clear error messages
- Simplified debugging and maintenance
- Prevention of error-related regressions
- Proper handling of edge cases like date validation (RI-20250310-001)

## Decision

### Exception Hierarchy
We establish the following custom exception hierarchy based on `exceptions.py`:

```
MEQSAPError (base)
├── ConfigError (configuration issues)
├── DataError (data retrieval/processing issues)  
├── BacktestError (backtesting execution issues)
├── ReportingError (report generation issues)
└── CLIError (CLI-specific issues)
    ├── DataAcquisitionError (CLI-specific data acquisition failures)
    ├── BacktestExecutionError (CLI-specific backtest computation failures)
    └── ReportGenerationError (CLI-specific report generation failures)
```

### Exception Usage Guidelines

#### When to Define New Custom Exceptions
- **DO**: Create new exceptions for distinct error categories that require different handling
- **DO**: Extend existing categories when the error semantics fit (e.g., `DataValidationError(DataError)`)
- **DON'T**: Create exceptions for every possible error scenario
- **DON'T**: Use custom exceptions for standard library errors that should propagate normally

#### Third-Party Library Exception Wrapping
- **pandas/numpy errors**: Wrap in `DataError` when data-specific, otherwise let propagate
- **requests/HTTP errors**: Wrap in `DataError` for data source issues
- **pydantic ValidationError**: Wrap in `ConfigError` for configuration validation
- **filesystem errors**: Wrap in `DataError` for data file issues, `ConfigError` for config file issues
- **vectorbt errors**: Wrap in `BacktestError` for backtesting issues

### Logging Policy
- **ERROR level**: All custom MEQSAPError exceptions with full stack trace
- **WARNING level**: Wrapped third-party exceptions with context
- **INFO level**: Expected error conditions (e.g., missing optional data)
- **DEBUG level**: Error recovery attempts and detailed diagnostic info

### User-Facing Error Messages
- **Structure**: `[Category] Brief description: Specific details`
- **Examples**:
  - `[Config] Invalid strategy parameter: ma_short_period must be less than ma_long_period`
  - `[Data] Failed to fetch price data: Symbol 'INVALID' not found`
  - `[Backtest] Insufficient data: Need at least 100 periods for analysis`

### CLI Exit Codes
- `0`: Success
- `1`: ConfigError (configuration issues)
- `2`: DataError (data-related failures)  
- `3`: BacktestError (backtesting failures)
- `4`: ReportingError (report generation failures)
- `5`: CLIError (CLI usage issues)
- `10`: Unexpected/unhandled errors

## Implementation Requirements

### Exception Definition Standards
```python
class SpecificError(ParentError):
    """Brief description of when this exception occurs.
    
    Args:
        message: Human-readable error description
        details: Optional dict with additional context
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
```

### Error Handling Patterns
```python
# Wrapping third-party exceptions
try:
    result = third_party_operation()
except ThirdPartyError as e:
    raise DataError(
        f"Data operation failed: {str(e)}",
        details={"operation": "fetch_prices", "symbol": symbol},
        original_error=e
    )

# Logging with context
logger.error(
    "Backtest failed for strategy %s: %s", 
    strategy_name, 
    str(error),
    extra={"strategy": strategy_name, "params": params}
)
```

## Consequences

### Positive
- Standardized error handling across all modules
- Consistent user experience with predictable error messages
- Simplified debugging with structured error information
- Clear separation of error categories for targeted handling
- Reduced maintenance burden through established patterns

### Negative
- Additional development overhead for exception handling
- Potential performance impact from extensive error wrapping
- Risk of over-engineering simple error scenarios

## Compliance

All new code must adhere to this policy. Existing code should be gradually refactored to comply during maintenance cycles. The code review checklist includes mandatory error handling policy compliance verification.
