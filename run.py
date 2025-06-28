#!/usr/bin/env python
# run.py
import sys
from pathlib import Path

# Add src to path so we can import modules directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kiss_signal.cli import app

if __name__ == "__main__":
    app()
