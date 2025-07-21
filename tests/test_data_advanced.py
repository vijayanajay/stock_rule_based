"""Optimized tests for data management functionality - Advanced operations."""

import pytest
import pandas as pd
from datetime import date
from unittest.mock import patch
import tempfile
from pathlib import Path

from kiss_signal import data


@pytest.fixture
def temp_cache_dir():
    """Fast in-memory data manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestDataAdvancedFunctions:
    """Test suite for advanced data functions."""

    @patch('yfinance.download')
    def test_get_price_data_missing_cache(self, mock_download, temp_cache_dir):
        """Test get_price_data when cache is missing."""
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [102, 103, 104],
            'Volume': [1000, 1100, 1200]
        }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
        mock_download.return_value = mock_data
        result = data.get_price_data("RELIANCE", temp_cache_dir, years=1)
        assert len(result) == 3
        assert 'open' in result.columns
        mock_download.assert_called_once()
    
    @patch('yfinance.download')
    def test_refresh_market_data_freeze_mode(self, mock_download, temp_cache_dir):
        """Test refresh_market_data in freeze mode."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': range(100, 105),
            'high': range(105, 110),
            'low': range(95, 100),
            'close': range(102, 107),
            'volume': range(1000, 1005)
        })
        data._save_symbol_cache("RELIANCE", test_data, temp_cache_dir)
        data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir),
            years=1,
            freeze_date=date(2023, 1, 10)
        )
        mock_download.assert_not_called()
    
    @patch('yfinance.download')  
    def test_refresh_market_data_success(self, mock_download, temp_cache_dir):
        """Test successful market data refresh."""
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [102, 103, 104],
            'Volume': [1000, 1100, 1200]
        }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
        mock_download.return_value = mock_data
        data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir),
            years=1
        )
        mock_download.assert_called_once()
        cache_file = temp_cache_dir / "RELIANCE.NS.csv"
        assert cache_file.exists()

    @patch('yfinance.download')
    def test_fetch_symbol_data_multiindex_columns(self, mock_download):
        """Test _fetch_symbol_data handles MultiIndex columns correctly."""
        mock_data = pd.DataFrame({
            ('Open', 'RELIANCE.NS'): [100, 101, 102],
            ('High', 'RELIANCE.NS'): [105, 106, 107],
            ('Low', 'RELIANCE.NS'): [95, 96, 97],
            ('Close', 'RELIANCE.NS'): [102, 103, 104],
            ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
        }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
        mock_data.columns = pd.MultiIndex.from_tuples(mock_data.columns)
        mock_download.return_value = mock_data
        result = data._fetch_symbol_data("RELIANCE.NS", 1)
        assert result is not None
        assert len(result) == 3
        mock_download.assert_called_once()
    
    @patch('yfinance.download')
    def test_fetch_symbol_data_tuple_columns(self, mock_download):
        """Test _fetch_symbol_data handles tuple columns correctly."""
        mock_data = pd.DataFrame({
            ('Open', 'RELIANCE.NS'): [100, 101, 102],
            ('High', 'RELIANCE.NS'): [105, 106, 107],
            ('Low', 'RELIANCE.NS'): [95, 96, 97],
            ('Close', 'RELIANCE.NS'): [102, 103, 104],
            ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
        }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
        mock_data.columns = [('Open', 'RELIANCE.NS'), ('High', 'RELIANCE.NS'), 
                           ('Low', 'RELIANCE.NS'), ('Close', 'RELIANCE.NS'), 
                           ('Volume', 'RELIANCE.NS')]
        mock_download.return_value = mock_data
        result = data._fetch_symbol_data("RELIANCE.NS", 1)
        assert result is not None
        assert len(result) == 3
        expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        assert all(col in result.columns for col in expected_columns)
        mock_download.assert_called_once()

    @patch('yfinance.download')
    def test_refresh_market_data_fetch_failure(self, mock_download, temp_cache_dir):
        """Test refresh_market_data when yfinance download fails."""
        mock_download.return_value = None  # Simulate download failure
        
        results = data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir)
        )
        
        assert results["RELIANCE"] is False
        cache_file = temp_cache_dir / "RELIANCE.NS.csv"
        assert not cache_file.exists()

    @patch('yfinance.download')
    def test_refresh_market_data_validation_failure(self, mock_download, temp_cache_dir):
        """Test refresh_market_data when data validation fails."""
        # Return data with negative prices, which should fail validation
        mock_data = pd.DataFrame({
            'Open': [-100], 'High': [105], 'Low': [95], 'Close': [102], 'Volume': [1000]
        }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=1, name='Date')))
        mock_download.return_value = mock_data
        
        results = data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir)
        )
        
        assert results["RELIANCE"] is False

    @patch('kiss_signal.data._fetch_symbol_data', return_value=None)
    def test_get_price_data_fetch_fails(self, mock_fetch, temp_cache_dir):
        """Test get_price_data when fetching fails."""
        with pytest.raises(ValueError, match="Failed to fetch data for TEST"):
            data.get_price_data("TEST", temp_cache_dir)

    @patch('yfinance.download', return_value=pd.DataFrame())
    def test_fetch_symbol_data_empty_df(self, mock_download):
        """Test _fetch_symbol_data when yfinance returns an empty DataFrame."""
        result = data._fetch_symbol_data("TEST.NS", 1)
        assert result is None

    @patch('yfinance.download')
    def test_fetch_symbol_data_missing_columns(self, mock_download):
        """Test _fetch_symbol_data with missing required columns."""
        mock_df = pd.DataFrame({'Open': [100]}, index=pd.to_datetime(['2023-01-01']))
        mock_download.return_value = mock_df
        result = data._fetch_symbol_data("TEST.NS", 1)
        assert result is None

    @patch('yfinance.download', side_effect=Exception("API Error"))
    def test_fetch_symbol_data_api_exception(self, mock_download):
        """Test _fetch_symbol_data when yfinance raises an exception."""
        result = data._fetch_symbol_data("TEST.NS", 1)
        assert result is None

    @patch('kiss_signal.data._fetch_symbol_data', return_value=None)
    def test_fetch_and_store_data_fetch_fails(self, mock_fetch, temp_cache_dir):
        """Test _fetch_and_store_data when fetching fails."""
        result = data._fetch_and_store_data("TEST", 1, None, temp_cache_dir)
        assert result is False

    @patch('kiss_signal.data._fetch_symbol_data')
    @patch('kiss_signal.data._validate_data_quality', return_value=False)
    def test_fetch_and_store_data_validation_fails(self, mock_validate, mock_fetch, temp_cache_dir):
        """Test _fetch_and_store_data when validation fails."""
        mock_fetch.return_value = pd.DataFrame({'close': [100]})
        result = data._fetch_and_store_data("TEST", 1, None, temp_cache_dir)
        assert result is False

    @patch('kiss_signal.data._fetch_symbol_data')
    @patch('kiss_signal.data._validate_data_quality', return_value=True)
    @patch('kiss_signal.data._save_symbol_cache', return_value=False)
    def test_fetch_and_store_data_save_fails(self, mock_save, mock_validate, mock_fetch, temp_cache_dir):
        """Test _fetch_and_store_data when saving fails."""
        mock_fetch.return_value = pd.DataFrame({'close': [100]})
        result = data._fetch_and_store_data("TEST", 1, None, temp_cache_dir)
        assert result is False

    @patch('kiss_signal.data._fetch_and_store_data', return_value=True)
    def test_refresh_market_data_with_list(self, mock_fetch_store, temp_cache_dir):
        """Test refresh_market_data with a list of symbols."""
        results = data.refresh_market_data(
            universe_path=["RELIANCE", "TCS"],
            cache_dir=str(temp_cache_dir)
        )
        assert mock_fetch_store.call_count == 2
        assert results["RELIANCE"] is True
        assert results["TCS"] is True
