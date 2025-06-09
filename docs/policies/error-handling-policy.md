# MEQSAP Error Handling Policy

## Overview
This document provides practical guidelines for implementing consistent error handling throughout the MEQSAP codebase, based on ADR-004.

## Quick Reference

### Exception Mapping
| Error Type | Custom Exception | Use Case |
|------------|------------------|----------|
| Invalid config values | `ConfigurationError` | Pydantic validation failures, missing required settings |
| Data fetch failures | `DataError` | API errors, file not found, invalid data format |
| Backtest execution issues | `BacktestError` | Insufficient data, calculation errors, vectorbt failures |
| Report generation problems | `ReportingError` | Template errors, output file issues |
| CLI usage problems | `CLIError` | Invalid commands, argument parsing issues |
| CLI data acquisition failures | `DataAcquisitionError` | CLI-specific data acquisition failures |
| CLI backtest computation failures | `BacktestExecutionError` | CLI-specific backtest computation failures |
| CLI report generation failures | `ReportGenerationError` | CLI-specific report generation failures |

### CLI Exit Code Reference
```bash
# Success
exit 0

# Configuration errors
exit 1  # ConfigurationError

# Data errors  
exit 2  # DataError

# Backtest errors
exit 3  # BacktestError

# Reporting errors
exit 4  # ReportingError

# CLI errors
exit 5  # CLIError

# Unexpected errors
exit 10  # Unhandled exceptions
```

## Implementation Guidelines

### 1. Exception Creation Checklist
- [ ] Inherits from appropriate MEQSAPError subclass
- [ ] Includes descriptive docstring with usage examples
- [ ] Accepts optional `details` dict for structured context
- [ ] Accepts optional `original_error` for wrapped exceptions
- [ ] Has clear, actionable error message

### 2. Exception Handling Patterns

#### Configuration Validation
```python
from pydantic import ValidationError
from meqsap.exceptions import ConfigurationError

def validate_strategy_params(params: StrategyParams) -> None:
    """Validate strategy parameters with clear error messages."""
    try:
        # Pydantic validation
        validated = StrategyParams.model_validate(params)
    except ValidationError as e:
        raise ConfigurationError(
            f"Invalid strategy configuration: {e}",
            details={"validation_errors": e.errors()},
            original_error=e
        )
    
    # Business logic validation
    if params.ma_short_period >= params.ma_long_period:
        raise ConfigurationError(
            "Short moving average period must be less than long period",
            details={
                "ma_short_period": params.ma_short_period,
                "ma_long_period": params.ma_long_period
            }
        )
```

#### Data Operations
```python
from meqsap.exceptions import DataError

def fetch_price_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch price data with comprehensive error handling."""
    try:
        data = yfinance_download(symbol, start=start_date, end=end_date)
        if data.empty:
            raise DataError(
                f"No price data available for symbol {symbol}",
                details={
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "suggestion": "Check symbol validity and date range"
                }
            )
        return data
    except requests.RequestException as e:
        raise DataError(
            f"Failed to fetch data for {symbol}: Network error",
            details={"symbol": symbol, "error_type": "network"},
            original_error=e
        )
    except Exception as e:
        raise DataError(
            f"Unexpected error fetching data for {symbol}",
            details={"symbol": symbol, "error_type": "unknown"},
            original_error=e
        )
```

#### Backtest Operations
```python
from meqsap.exceptions import BacktestError

def run_backtest(data: pd.DataFrame, strategy: Strategy) -> BacktestResults:
    """Run backtest with proper error handling."""
    if len(data) < strategy.min_periods:
        raise BacktestError(
            f"Insufficient data for {strategy.name} strategy",
            details={
                "data_length": len(data),
                "required_periods": strategy.min_periods,
                "suggestion": "Use longer date range or different strategy"
            }
        )
    
    try:
        # Vectorbt operations
        portfolio = run_vectorbt_backtest(data, strategy)
        return BacktestResults.from_portfolio(portfolio)
    except Exception as e:
        raise BacktestError(
            f"Backtest execution failed for {strategy.name}",
            details={"strategy": strategy.name, "data_shape": data.shape},
            original_error=e
        )
```

### 3. CLI Error Handling
```python
import sys
from meqsap.exceptions import MEQSAPError, ConfigurationError, DataError, BacktestError, ReportingError, CLIError

def handle_cli_error(error: Exception) -> int:
    """Convert exceptions to appropriate CLI exit codes."""
    if isinstance(error, ConfigurationError):
        logger.error("Configuration error: %s", str(error))
        return 1
    elif isinstance(error, DataError):
        logger.error("Data error: %s", str(error))
        return 2
    elif isinstance(error, BacktestError):
        logger.error("Backtest error: %s", str(error))
        return 3
    elif isinstance(error, ReportingError):
        logger.error("Reporting error: %s", str(error))
        return 4
    elif isinstance(error, CLIError):
        logger.error("CLI error: %s", str(error))
        return 5
    else:
        logger.error("Unexpected error: %s", str(error), exc_info=True)
        return 10

# Usage in CLI commands
@app.command()
def backtest_command(config_path: str) -> None:
    """CLI command with proper error handling."""
    try:
        # Command implementation
        config = load_config(config_path)
        results = run_backtest(config)
        print_results(results)
    except MEQSAPError as e:
        sys.exit(handle_cli_error(e))
    except Exception as e:
        sys.exit(handle_cli_error(e))
```

### 4. Logging Standards
```python
import logging

logger = logging.getLogger(__name__)

# Error logging with context
def log_error_with_context(error: MEQSAPError, operation: str, **context):
    """Log errors with structured context information."""
    logger.error(
        "%s failed: %s", 
        operation, 
        str(error),
        extra={
            "error_type": type(error).__name__,
            "operation": operation,
            "details": getattr(error, 'details', {}),
            **context
        }
    )
    
    # Log original error if available
    if hasattr(error, 'original_error') and error.original_error:
        logger.debug(
            "Original error: %s", 
            str(error.original_error), 
            exc_info=error.original_error
        )
```

## Testing Error Handling
```python
import pytest
from meqsap.exceptions import ConfigurationError, DataError

def test_config_validation_error():
    """Test that configuration errors are properly raised and handled."""
    with pytest.raises(ConfigurationError) as exc_info:
        validate_invalid_config()
    
    assert "ma_short_period" in str(exc_info.value)
    assert exc_info.value.details is not None
    assert "ma_short_period" in exc_info.value.details

def test_data_error_with_context():
    """Test that data errors include helpful context."""
    with pytest.raises(DataError) as exc_info:
        fetch_nonexistent_symbol()
    
    error = exc_info.value
    assert error.details["symbol"] == "INVALID"
    assert "suggestion" in error.details
```

## Memory.md Anti-Patterns Prevention
Always check against `docs/memory.md` to avoid:
- Duplicate exception classes across modules
- Incomplete error propagation in CLI commands
- Missing factory methods for error handling
- Inconsistent exit code mappings
- Brittle error message assertions in tests

## Code Review Checklist Integration
- [ ] All custom exceptions follow ADR-004 standards
- [ ] Third-party exceptions properly wrapped
- [ ] CLI commands have proper error handling and exit codes
- [ ] Error messages are user-friendly and actionable
- [ ] Logging includes appropriate context and levels
- [ ] Tests cover error scenarios with proper assertions
- [ ] No anti-patterns from memory.md are introduced
