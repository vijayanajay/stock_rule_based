"""Custom exceptions for the KISS Signal system."""


class DataMismatchError(ValueError):
    """Raised when market data doesn't cover the full history needed for analysis."""
    pass


class InsufficientDataError(ValueError):
    """Raised when there isn't enough data for proper backtesting."""
    pass


class ConfigurationError(ValueError):
    """Raised when configuration is invalid or incomplete."""
    pass
