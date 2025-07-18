"""KISS Signal CLI - Keep-It-Simple Signal Generation for NSE Equities."""

__version__ = "1.4.0"
__author__ = "KISS Signal Team"

# Re-export main classes and modules for convenience
from .config import Config
from . import data, backtester, persistence, reporter

__all__ = ["Config", "data", "backtester", "persistence", "reporter", "__version__"]
