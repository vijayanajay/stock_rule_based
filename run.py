#!/usr/bin/env python3
"""
MEQSAP Runner - Simple entry point for the Market Equity Quantitative Strategy Analysis Platform

This script provides a convenient way to run MEQSAP from the project root directory.
It automatically handles the Python path and imports to make running the CLI straightforward.

Usage:
    python run.py analyze config.yaml
    python run.py analyze config.yaml --report --verbose
    python run.py version
    python run.py --help

For more detailed usage information, see README.md or run:
    python run.py --help
"""

import sys
from pathlib import Path

# Add the src directory to Python path so we can import meqsap modules
PROJECT_ROOT = Path(__file__).parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Import and run the CLI
try:
    from meqsap.cli import cli_main
    
    if __name__ == "__main__":
        cli_main()
        
except ImportError as e:
    print(f"Error: Failed to import MEQSAP modules: {e}")
    print(f"Make sure you're running this from the project root directory: {PROJECT_ROOT}")
    print("If the error persists, try installing the package in development mode:")
    print("  pip install -e .")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
