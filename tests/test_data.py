import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import logging

# Suppress pandas_ta related warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API", category=UserWarning)

from src.meqsap.data import fetch_market_data, clear_cache, MAX_ALLOWED_START_DATE_SLIP_DAYS
from src.meqsap.exceptions import DataError

# Mock data for testing
def create_mock_data(start_date, end_date):
    """
    Create mock OHLCV data for testing.
    
    Args:
        start_date: First date to include (inclusive)
        end_date: Last date to include (INCLUSIVE)
    
    Returns:
        DataFrame with mock OHLCV data spanning the full date range
    """
    # Generate date range that includes both start_date and end_date
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create mock OHLCV data
    np.random.seed(42)  # For reproducible test data
    data = {
        'Open': np.random.random(len(date_range)),
        'High': np.random.random(len(date_range)),
        'Low': np.random.random(len(date_range)),
        'Close': np.random.random(len(date_range)),
        'Volume': np.random.randint(1000, 10000, len(date_range))
    }
    
    df = pd.DataFrame(data, index=date_range)
    return df

@pytest.fixture
def mock_yfinance_download():
    with patch('src.meqsap.data.yf.download') as mock_download:  # Adjusted path for consistency
        yield mock_download

@pytest.fixture
def mock_cache():
    with patch('src.meqsap.data.load_from_cache') as mock_load, \
         patch('src.meqsap.data.save_to_cache') as mock_save:  # Adjusted path for consistency
        yield mock_load, mock_save

@pytest.fixture(autouse=True)
def cleanup_cache():
    yield
    # Clear cache after each test
    clear_cache()

def test_cache_miss(mock_yfinance_download, mock_cache):
    mock_load, mock_save = mock_cache
    mock_load.side_effect = FileNotFoundError
    # Create mock data that includes the full requested range (inclusive end_date)
    mock_data = create_mock_data(date(2023, 1, 1), date(2023, 1, 10))  # Include end_date
    mock_yfinance_download.return_value = mock_data

    # Call function
    result = fetch_market_data('AAPL', date(2023, 1, 1), date(2023, 1, 10))

    # Verify
    mock_load.assert_called_once()
    mock_yfinance_download.assert_called_once()
    mock_save.assert_called_once()
    pd.testing.assert_frame_equal(result, mock_data, check_dtype=False) # Allow different dtypes for index after read/write

def test_cache_hit(mock_yfinance_download, mock_cache):
    mock_load, mock_save = mock_cache
    mock_data = create_mock_data(date(2023, 1, 1), date(2023, 1, 10))
    mock_load.return_value = mock_data
    
    # Call function
    result = fetch_market_data('AAPL', date(2023, 1, 1), date(2023, 1, 10))
    
    # Verify
    mock_load.assert_called_once()
    mock_yfinance_download.assert_not_called()
    mock_save.assert_not_called()
    pd.testing.assert_frame_equal(result, mock_data, check_dtype=False)

def test_nan_values_validation(mock_yfinance_download, mock_cache):
    mock_load, _ = mock_cache
    mock_load.side_effect = FileNotFoundError
    mock_data = create_mock_data(date(2023, 1, 1), date(2023, 1, 10))
    mock_data.iloc[2, 3] = np.nan  # Introduce NaN value
    
    mock_yfinance_download.return_value = mock_data
    
    # Test for NaN error
    with pytest.raises(DataError, match="Missing data points"):
        fetch_market_data('AAPL', date(2023, 1, 1), date(2023, 1, 10))

def test_start_date_slip_logic(mock_yfinance_download, mock_cache, caplog):
    mock_load, mock_save = mock_cache
    mock_load.side_effect = FileNotFoundError
    # Create mock data that starts 2 days late
    mock_data = create_mock_data(date(2023, 1, 3), date(2023, 1, 10))  # Starts on Jan 3
    mock_yfinance_download.return_value = mock_data

    caplog.clear()
    # Call function
    result = fetch_market_data('AAPL', date(2023, 1, 1), date(2023, 1, 10))

    # Verify
    mock_load.assert_called_once()
    mock_yfinance_download.assert_called_once()
    mock_save.assert_called_once()
    pd.testing.assert_frame_equal(result, mock_data, check_dtype=False)

    # Expected log based on pytest output:
    # WARNING  src.meqsap.data:data.py:75 Data for AAPL starts on 2023-01-03, which is 2 day(s) after the requested start_date 2023-01-01. This may be due to the requested start date being a non-trading day. Proceeding with analysis using data from 2023-01-03.
    assert "Data for AAPL starts on 2023-01-03, which is 1 trading day(s) after the requested start_date 2023-01-01." in caplog.text
    assert "This may be due to the requested start date being a non-trading day." in caplog.text
    assert "Proceeding with analysis using data from 2023-01-03." in caplog.text
    assert any(record.levelno == logging.WARNING for record in caplog.records), "No WARNING level log found."

def test_invalid_ticker(mock_yfinance_download, mock_cache):
    mock_load, _ = mock_cache
    mock_load.side_effect = FileNotFoundError
    mock_yfinance_download.return_value = pd.DataFrame()  # Empty data
    
    # Test for invalid ticker
    with pytest.raises(DataError, match="No data available"):
        fetch_market_data('INVALID_TICKER', date(2023, 1, 1), date(2023, 1, 10))

def test_clear_cache():
    from src.meqsap.data import CACHE_DIR # Adjusted import for consistency
    
    # Create dummy cache file
    test_file = CACHE_DIR / 'test_cache.parquet'
    test_file.touch()
    
    # Clear cache
    clear_cache()
    
    # Verify the test file was removed
    assert not test_file.exists()

def test_end_date_inclusive_behavior():
    """
    Test that end_date is truly inclusive - data for the specified end_date is present.
    
    This is a mandatory test case per the resolution of RI-20250310-001 (reopen #2)
    to prevent regression of date handling ambiguity.
    """
    # Use a short date range to make verification precise
    start_date = "2022-01-03"  # Monday to avoid weekend issues
    end_date = "2022-01-04"    # Tuesday - should be included in results
    
    # Mock yfinance to return data that includes both days
    with patch('src.meqsap.data.yf.download') as mock_download, \
         patch('src.meqsap.data.load_from_cache') as mock_load, \
         patch('src.meqsap.data.save_to_cache') as mock_save:
        
        # Cache miss
        mock_load.side_effect = FileNotFoundError
        
        # Create mock data that includes both start and end dates
        mock_data = create_mock_data(date(2022, 1, 3), date(2022, 1, 4))
        mock_download.return_value = mock_data
        
        # Call the correct function name
        data = fetch_market_data("AAPL", date(2022, 1, 3), date(2022, 1, 4))
        
        # Verify we have data for both days
        dates = pd.to_datetime(data.index).date
        expected_start = date(2022, 1, 3)
        expected_end = date(2022, 1, 4) 
        
        # Check that we have the start date
        assert expected_start in dates, f"Missing data for start_date {expected_start}"
        
        # Check that we have the end date (this is the critical inclusive behavior)
        assert expected_end in dates, f"Missing data for end_date {expected_end} - end_date should be INCLUSIVE"
        
        # Verify the date range is exactly what we requested
        assert dates.min() == expected_start, f"Data starts at {dates.min()}, expected {expected_start}"
        assert dates.max() == expected_end, f"Data ends at {dates.max()}, expected {expected_end}"
        
        # Verify yfinance was called with adjusted end date (exclusive behavior)
        mock_download.assert_called_once_with(
            "AAPL",
            start=date(2022, 1, 3),
            end="2022-01-05",  # end_date + 1 day for yfinance exclusive behavior
            progress=False
        )