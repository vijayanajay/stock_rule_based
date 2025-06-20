"""Tests for Data Manager module."""

import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from kiss_signal import data


class TestDataManager:
    """Test cases for DataManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test universe file
        self.universe_path = self.temp_path / "test_universe.csv"
        self.universe_path.write_text(
            "symbol,name,sector\n"
            "RELIANCE,Reliance Industries,Energy\n"
            "INFY,Infosys,IT\n"
            "TCS,Tata Consultancy Services,IT\n"
        )
        
        self.cache_dir = self.temp_path / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_universe(self):
        """Test loading universe symbols."""
        symbols = data.load_universe(str(self.universe_path))
        assert symbols == ["RELIANCE", "INFY", "TCS"]
    
    def test_load_universe_missing_file(self):
        """Test loading universe with missing file."""
        with pytest.raises(FileNotFoundError):
            data.load_universe("nonexistent.csv")
    
    def test_load_universe_malformed(self):
        """Test loading malformed universe file."""
        malformed_path = self.temp_path / "malformed.csv"
        malformed_path.write_text("name,sector\nTest,IT\n")  # Missing symbol column
        with pytest.raises(ValueError, match="missing 'symbol' column"):
            data.load_universe(str(malformed_path))
    
    def test_needs_refresh(self):
        """Test cache refresh logic based on file mtime."""
        # Symbol with no cache file should need refresh
        assert data._needs_refresh("RELIANCE", self.cache_dir, 7)

        # Symbol with recent cache file should not need refresh
        cache_file = self.cache_dir / "INFY.NS.csv"
        cache_file.touch()
        assert not data._needs_refresh("INFY", self.cache_dir, 7)

        # Symbol with old cache file should need refresh
        stale_cache_file = self.cache_dir / "TCS.NS.csv"
        stale_cache_file.touch()
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(stale_cache_file, (old_time, old_time))
        assert data._needs_refresh("TCS", self.cache_dir, 7)
    
    def test_add_ns_suffix(self):
        """Test adding .NS suffix for yfinance using data functions directly."""
        assert data._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert data._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"
    
    def test_validate_data_quality(self):
        """Test data quality validation."""
        # Test with good data
        good_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=5),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [105.0, 106.0, 107.0, 108.0, 109.0],
            'low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        assert data._validate_data_quality(good_data, "TEST")
        # Test with empty data
        empty_data = pd.DataFrame()
        assert not data._validate_data_quality(empty_data, "TEST")
    
    @patch('yfinance.download')
    def test_fetch_symbol_data_success(self, mock_download):
        """Test successful symbol data fetching."""
        # Mock yfinance response
        mock_data = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [103.0, 104.0, 105.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [102.0, 103.0, 104.0],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2025-01-01', periods=3, name='Date'))
        mock_download.return_value = mock_data
        result = data._fetch_symbol_data("RELIANCE.NS", years=1)
        assert result is not None
        assert len(result) == 3
        assert list(result.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']
    
    @patch('yfinance.download')
    def test_fetch_symbol_data_failure(self, mock_download):
        """Test failed symbol data fetching."""
        mock_download.side_effect = Exception("Network error")
        result = data._fetch_symbol_data("INVALID.NS", years=1)
        assert result is None
    
    def test_save_and_load_symbol_cache(self):
        """Test saving and loading symbol cache."""
        # Create test data
        test_data_with_col = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2025-01-01', periods=3)),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [102.0, 103.0, 104.0],
            'volume': [1000, 1100, 1200]
        })
        # Save data
        success = data._save_symbol_cache("RELIANCE", test_data_with_col, self.cache_dir)
        assert success
        # Load data
        loaded_data = data.get_price_data("RELIANCE", self.cache_dir, 7, 1)
        assert len(loaded_data) == 3
        assert loaded_data.index.name == 'date'
    
    def test_get_price_data_with_date_filtering(self):
        """Test getting price data with date filtering."""
        # Create and save test data
        test_data_with_col = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2025-01-01', periods=10)),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        data._save_symbol_cache("RELIANCE", test_data_with_col, self.cache_dir)
        # Test date filtering
        filtered_data = data.get_price_data(
            "RELIANCE", 
            self.cache_dir,
            7,
            1,
            start_date=date(2025, 1, 5),
            end_date=date(2025, 1, 8)
        )
        assert len(filtered_data) == 4
        assert filtered_data.index.min() == pd.to_datetime(date(2025, 1, 5))
        assert filtered_data.index.max() == pd.to_datetime(date(2025, 1, 8))
    
    def test_get_price_data_with_freeze_date(self):
        """Test getting price data with freeze date."""
        # Create and save test data
        test_data_with_col = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2025-01-01', periods=10)),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        data._save_symbol_cache("RELIANCE", test_data_with_col, self.cache_dir)
        # Data should be limited to freeze date
        result = data.get_price_data("RELIANCE", self.cache_dir, 7, 1, freeze_date=date(2025, 1, 5))
        assert result.index.max() <= pd.to_datetime(date(2025, 1, 5))
    
    def test_get_price_data_missing_cache(self):
        """Test getting price data for missing cache when download fails."""
        with pytest.raises(ValueError, match="Failed to fetch data for NONEXISTENT"):
            data.get_price_data("NONEXISTENT", self.cache_dir, 7, 1)
    
    @patch('kiss_signal.data._fetch_symbol_data')
    def test_refresh_market_data(self, mock_fetch):
        """Test market data refresh."""
        # Mock fetch to return test data
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2025-01-01', periods=3)),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [102.0, 103.0, 104.0],
            'volume': [1000, 1100, 1200]
        })

        mock_fetch.return_value = test_data
        results = data.refresh_market_data(
            universe_path=["RELIANCE", "INFY"],
            cache_dir=str(self.cache_dir),
            refresh_days=7,
            years=1
        )
        assert results["RELIANCE"] is True
        assert results["INFY"] is True
        assert mock_fetch.call_count == 2


class TestDataConfiguration:
    """Test data functions with different configurations."""
    def test_freeze_date_integration(self):
        """Test freeze date functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            universe_path = temp_path / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            # This test now checks if refresh_market_data respects freeze_date
            with patch('yfinance.download') as mock_download:
                data.refresh_market_data(
                    universe_path=str(universe_path),
                    cache_dir=str(temp_path / "cache"),
                    freeze_date=date(2025, 1, 15)
                )
                mock_download.assert_not_called()
    def test_custom_cache_refresh_days(self):
        """Test custom cache refresh configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Symbol with data from 2 days ago should need refresh
            stale_cache_file = temp_path / "RELIANCE.NS.csv"
            stale_cache_file.touch()
            old_time = (datetime.now() - timedelta(days=2)).timestamp()
            os.utime(stale_cache_file, (old_time, old_time))
            assert data._needs_refresh("RELIANCE", temp_path, 1)
