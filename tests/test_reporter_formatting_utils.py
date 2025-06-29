"""
Tests for the reporter module - Formatting Utility Functions.
"""

import pytest
# No specific heavy fixtures like sample_config or sample_price_data needed for these simple formatting tests.
# Pandas is not used directly by these formatting functions.
# from unittest.mock import Mock, patch # Not needed
# from pathlib import Path # Not needed
# import sqlite3 # Not needed

from src.kiss_signal import reporter
# from src.kiss_signal.config import Config # Not needed


class TestReportFormatting:
    """Tests for markdown table formatting functions."""

    def test_format_new_buys_table_empty(self):
        """Test formatting new buys table with no signals."""
        result = reporter._format_new_buys_table([])
        assert result == "*No new buy signals found.*"

    def test_format_open_positions_table_empty(self):
        """Test formatting open positions table with no positions."""
        result = reporter._format_open_positions_table([], 20)
        assert result == "*No open positions.*"

    def test_format_sell_positions_table_empty(self):
        """Test formatting sell positions table with no positions."""
        result = reporter._format_sell_positions_table([], 20)
        assert result == "*No positions to sell.*"

    def test_format_open_positions_table_with_na(self):
        """Test formatting open positions with N/A values."""
        positions = [{
            'symbol': 'TEST', 'entry_date': '2025-01-01', 'entry_price': 100.0,
            'current_price': None, 'return_pct': None, 'nifty_return_pct': None,
            'days_held': 5
        }]
        result = reporter._format_open_positions_table(positions, 20)
        assert "N/A" in result
