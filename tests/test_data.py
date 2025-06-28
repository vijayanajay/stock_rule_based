"""Optimized tests for data management functionality."""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from unittest.mock import patch
import tempfile
from pathlib import Path

from kiss_signal import data


@pytest.fixture(scope="session")
def sample_price_data():
    """Session-scoped fixture for sample price data to reduce setup time."""
    dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
    return pd.DataFrame({
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
        'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
        'close': [103, 104, 105, 106, 107, 108, 109, 110, 111, 112],
        'volume': [10000] * 10
    }, index=dates)


@pytest.fixture
def temp_cache_dir():
    """Fast in-memory data manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestDataFunctions:
    """Optimized test suite for data functions."""
    
    def test_load_universe(self, temp_cache_dir):
        universe_path = temp_cache_dir / "universe.csv"
        universe_path.write_text("symbol,name\nRELIANCE,Reliance\nTCS,TCS")
        symbols = data.load_universe(str(universe_path))
        assert symbols == ["RELIANCE", "TCS"]

    def test_load_universe_missing_file(self):
        with pytest.raises(FileNotFoundError):
            data.load_universe("nonexistent.csv")

    def test_load_universe_malformed(self, temp_cache_dir):
        universe_path = temp_cache_dir / "universe.csv"
        universe_path.write_text("header1,header2\nRELIANCE,Reliance")
        with pytest.raises(ValueError, match="Universe file missing 'symbol' column"):
            data.load_universe(str(universe_path))

    def test_add_ns_suffix(self):
        assert data._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert data._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"
        assert data._add_ns_suffix("^NSEI") == "^NSEI"

    def test_needs_refresh_missing_file(self, temp_cache_dir):
        assert data._needs_refresh("TEST", temp_cache_dir, 7) is True

    def test_needs_refresh_fresh_file(self, temp_cache_dir):
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.touch()
        assert data._needs_refresh("TEST", temp_cache_dir, 7) is False

    def test_needs_refresh_stale_file(self, temp_cache_dir):
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.touch()
        # Mock file modification time to be old
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_mtime = (datetime.now() - timedelta(days=8)).timestamp()
            assert data._needs_refresh("TEST", temp_cache_dir, 7) is True

    def test_validate_data_quality_good_data(self):
        """Test data quality validation with good data."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        assert data._validate_data_quality(test_data, "RELIANCE") is True
    
    def test_validate_data_quality_negative_prices(self):
        """Test data quality validation with negative prices."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, -102, 103, 104],  # Negative price
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        assert data._validate_data_quality(test_data, "RELIANCE") is False
    
    def test_save_and_load_symbol_cache(self, temp_cache_dir):
        """Test saving and loading symbol cache."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        })
        data._save_symbol_cache("RELIANCE", test_data, temp_cache_dir)
        loaded_data = data._load_symbol_cache("RELIANCE", temp_cache_dir)
        expected_data = test_data.set_index('date')
        pd.testing.assert_frame_equal(expected_data, loaded_data)
    
    def test_get_price_data_with_date_filtering(self, temp_cache_dir):
        """Test get_price_data with date filtering."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        data._save_symbol_cache("RELIANCE", test_data, temp_cache_dir)
        result = data.get_price_data(
            "RELIANCE",
            temp_cache_dir,
            30,  # refresh_days
            1,   # years
            freeze_date=date(2023, 1, 5)
        )
        assert len(result) == 5  # Data up to 2023-01-05
        assert result.index.max().date() == date(2023, 1, 5)
    
    def test_get_price_data_with_freeze_date(self, temp_cache_dir):
        """Test get_price_data respects freeze_date."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        data._save_symbol_cache("RELIANCE", test_data, temp_cache_dir)
        result = data.get_price_data(
            "RELIANCE",
            temp_cache_dir,
            30,  # refresh_days
            1,   # years
            freeze_date=date(2023, 1, 3)
        )
        assert len(result) == 3
        assert result.index.max().date() == date(2023, 1, 3)

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
        result = data.get_price_data("RELIANCE", temp_cache_dir, 7, 1)
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
            refresh_days=7,
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
            refresh_days=7,
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
