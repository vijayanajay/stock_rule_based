"""Tests for timestamp comparison fix in data.py.

This test suite verifies that the fix for the '>=' not supported between instances
of 'numpy.ndarray' and 'Timestamp' error is working correctly.
"""

__all__ = [
    "TestTimestampComparisonFix",
]

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
from pathlib import Path
import tempfile
from unittest.mock import patch

from kiss_signal import data


@pytest.fixture
def temp_cache_dir():
    """Temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_data_with_problematic_index():
    """Create sample data with different index types that can cause comparison issues."""
    dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
    return pd.DataFrame({
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
        'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
        'close': [103, 104, 105, 106, 107, 108, 109, 110, 111, 112],
        'volume': [10000] * 10
    }, index=dates)


class TestTimestampComparisonFix:
    """Test cases specifically for the timestamp comparison fix."""

    def test_get_price_data_with_string_index(self, temp_cache_dir):
        """Test that get_price_data handles string-based index properly."""
        # Create cache file with string dates that could cause comparison issues
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000"""
        cache_file.write_text(cache_data)
        
        # This should not raise the '>=' not supported error
        result = data.get_price_data(
            symbol="TEST",
            cache_dir=temp_cache_dir,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4)
        )
        
        assert len(result) == 3
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index[0] == pd.to_datetime('2024-01-02')
        assert result.index[-1] == pd.to_datetime('2024-01-04')

    def test_get_price_data_with_numeric_index(self, temp_cache_dir):
        """Test that get_price_data handles numeric index properly."""
        # Create a problematic cache file with numeric index
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """Unnamed: 0,date,open,high,low,close,volume
0,2024-01-01,100,105,95,103,10000
1,2024-01-02,101,106,96,104,10000
2,2024-01-03,102,107,97,105,10000
3,2024-01-04,103,108,98,106,10000
4,2024-01-05,104,109,99,107,10000"""
        cache_file.write_text(cache_data)
        
        # This should not raise the '>=' not supported error
        result = data.get_price_data(
            symbol="TEST",
            cache_dir=temp_cache_dir,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4)
        )
        
        assert len(result) == 3
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_load_symbol_cache_converts_index_to_datetime(self, temp_cache_dir):
        """Test that _load_cache properly converts index to DatetimeIndex."""
        # Create cache file with potential index issues
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000"""
        cache_file.write_text(cache_data)
        
        result = data._load_cache("TEST", temp_cache_dir)
        
        # Verify the index is properly converted
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3

    def test_load_symbol_cache_handles_invalid_dates(self, temp_cache_dir):
        """Test that _load_cache handles invalid dates gracefully."""
        # Create cache file with some invalid dates
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
invalid-date,101,106,96,104,10000
2024-01-03,102,107,97,105,10000"""
        cache_file.write_text(cache_data)
        
        result = data._load_cache("TEST", temp_cache_dir)
        
        # Should drop invalid dates and keep valid ones
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 2  # One invalid date should be dropped

    def test_load_symbol_cache_empty_after_cleanup_raises_error(self, temp_cache_dir):
        """Test that _load_cache raises error if no valid dates remain."""
        # Create cache file with only invalid dates
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
invalid-date1,100,105,95,103,10000
invalid-date2,101,106,96,104,10000
not-a-date,102,107,97,105,10000"""
        cache_file.write_text(cache_data)
        
        with pytest.raises(ValueError, match="No valid data found in cache for TEST"):
            data._load_cache("TEST", temp_cache_dir)

    def test_get_price_data_with_freeze_date_index_conversion(self, temp_cache_dir):
        """Test that freeze_date filtering works with index conversion."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000"""
        cache_file.write_text(cache_data)
        
        # Test with freeze_date that should trigger index conversion
        result = data.get_price_data(
            symbol="TEST",
            cache_dir=temp_cache_dir,
            freeze_date=date(2024, 1, 3)
        )
        
        assert len(result) == 3  # Should only include dates up to freeze_date
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index[-1] <= pd.to_datetime('2024-01-03')

    @patch('kiss_signal.data._load_cache')
    def test_get_price_data_handles_non_datetime_index(self, mock_load_cache, temp_cache_dir):
        """Test that get_price_data converts non-DatetimeIndex properly."""
        # Create mock data with RangeIndex (problematic type)
        mock_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [103, 104, 105],
            'volume': [10000, 10000, 10000]
        })
        # Simulate the problematic case with non-DatetimeIndex
        mock_data.index = pd.RangeIndex(start=0, stop=3)
        mock_data.index.name = None
        mock_load_cache.return_value = mock_data
        
        # Create dummy cache file
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.write_text("dummy")
        
        # This should handle the index conversion without error
        with pytest.raises(ValueError, match="No data available for TEST"):
            data.get_price_data(
                symbol="TEST",
                cache_dir=temp_cache_dir,
                start_date=date(2024, 1, 1)
            )

    def test_get_price_data_all_filtering_with_index_conversion(self, temp_cache_dir):
        """Test all date filtering scenarios work with index conversion."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000
2024-01-06,105,110,100,108,10000"""
        cache_file.write_text(cache_data)
        
        # Test with start_date, end_date, and freeze_date all applied
        result = data.get_price_data(
            symbol="TEST",
            cache_dir=temp_cache_dir,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 5),
            freeze_date=date(2024, 1, 4)
        )
        
        # Should get data from Jan 2 to Jan 4 (freeze_date takes precedence over end_date)
        assert len(result) == 3
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index[0] == pd.to_datetime('2024-01-02')
        assert result.index[-1] == pd.to_datetime('2024-01-04')

    def test_regression_nifty_data_comparison_error(self, temp_cache_dir):
        """Regression test for the specific NIFTY data comparison error from the log."""
        # Simulate the exact scenario that was failing
        cache_file = temp_cache_dir / "^NSEI.NS.csv"
        cache_data = """date,open,high,low,close,volume
2025-07-01,25453.40,25500.00,25400.00,25453.40,1000000
2025-07-02,25454.00,25550.00,25430.00,25480.00,1100000
2025-07-17,25000.00,25100.00,24900.00,25050.00,1200000
2025-07-18,25050.00,25150.00,24950.00,24968.40,1300000"""
        cache_file.write_text(cache_data)
        
        # This was the exact call that was failing in reporter.py
        nifty_data = data.get_price_data(
            symbol="^NSEI", 
            cache_dir=temp_cache_dir, 
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 18)
        )
        
        assert len(nifty_data) == 14
        assert isinstance(nifty_data.index, pd.DatetimeIndex)
        # Verify the filtering worked correctly
        assert nifty_data.index[0] == pd.to_datetime('2025-07-01')
        assert nifty_data.index[-1] == pd.to_datetime('2025-07-18')
