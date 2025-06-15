"""KISS Signal CLI - Keep-It-Simple Signal Generation for NSE Equities."""

__version__ = "1.4.0"
__author__ = "KISS Signal Team"

# Re-export main classes for convenience
from .config import Config

__all__ = ["Config", "__version__"]
