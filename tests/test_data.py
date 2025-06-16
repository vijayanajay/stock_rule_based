"""Tests for Data module functions."""

import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from kiss_signal import data


class TestDataFunctions:
    """Test cases for data module functions."""
    
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
        """Test loading universe from CSV file."""
        symbols = data.load_universe(str(self.universe_path))
        
        assert symbols == ["RELIANCE", "INFY", "TCS"]
    
    def test_load_universe_missing_file(self):
        """Test error handling for missing universe file."""
        with pytest.raises(FileNotFoundError):
            data.load_universe("nonexistent.csv")
    
    def test_load_universe_malformed(self):
        """Test error handling for malformed universe file."""
        bad_file = self.temp_path / "bad_universe.csv"
        bad_file.write_text("name,sector\nReliance,Energy")  # Missing symbol column
        
        with pytest.raises(ValueError, match="missing 'symbol' column"):
            data.load_universe(str(bad_file))
    
    def test_add_ns_suffix(self):
        """Test NS suffix addition."""
        assert data._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert data._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"
    
    def test_needs_refresh_missing_file(self):
        """Test refresh check for missing cache file."""
        assert data._needs_refresh("NONEXISTENT", self.cache_dir, 7) is True
    
    def test_needs_refresh_fresh_file(self):
        """Test refresh check for fresh cache file."""
        cache_file = self.cache_dir / "RELIANCE.NS.csv"
        cache_file.write_text("date,open,high,low,close,volume\n")
        
        assert data._needs_refresh("RELIANCE", self.cache_dir, 7) is False

    def test_needs_refresh_stale_file(self):
        """Test refresh check for stale cache file."""
        cache_file = self.cache_dir / "RELIANCE.NS.csv"
        cache_file.write_text("date,open,high,low,close,volume\n")
        
        # Modify file timestamp to make it old
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(cache_file, (old_time, old_time))
        
        assert data._needs_refresh("RELIANCE", self.cache_dir, 7) is True
    
    def test_validate_data_quality_good_data(self):
        """Test data quality validation with good data."""
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=5),
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
            'date': pd.date_range('2023-01-01', periods=5),
            'open': [100, 101, -102, 103, 104],  # Negative price
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        assert data._validate_data_quality(test_data, "RELIANCE") is False
    
    def test_save_and_load_symbol_cache(self):
        """Test saving and loading symbol cache."""
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=3),
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        })
        test_data.set_index('date', inplace=True)
        
        # Save data
        data._save_symbol_cache("RELIANCE", test_data, self.cache_dir)
        
        # Load and verify
        loaded_data = data._load_symbol_cache("RELIANCE", self.cache_dir)
        pd.testing.assert_frame_equal(test_data, loaded_data)
    
    def test_get_price_data_with_date_filtering(self):
        """Test get_price_data with date filtering."""
        # Create cached data
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=10),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        test_data.set_index('date', inplace=True)
        data._save_symbol_cache("RELIANCE", test_data, self.cache_dir)        # Test filtering
        result = data.get_price_data(
            "RELIANCE",
            self.cache_dir,
            30,  # refresh_days
            1,   # years
            freeze_date=date(2023, 1, 5),
            max_age_days=365
        )
        
        assert len(result) == 5  # Data up to 2023-01-05
        assert result.index.max().date() == date(2023, 1, 5)
    
    def test_get_price_data_with_freeze_date(self):
        """Test get_price_data respects freeze_date."""
        # Create cached data 
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=10),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        test_data.set_index('date', inplace=True)
        data._save_symbol_cache("RELIANCE", test_data, self.cache_dir)
          # Test with freeze date
        result = data.get_price_data(
            "RELIANCE",
            self.cache_dir,
            30,  # refresh_days
            1,   # years
            freeze_date=date(2023, 1, 3)        )
        
        assert len(result) == 3
        assert result.index.max().date() == date(2023, 1, 3)

    @patch('yfinance.download')
    def test_get_price_data_missing_cache(self, mock_download):
        """Test get_price_data when cache is missing."""
        # Mock yfinance download - this should match what yfinance actually returns
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [102, 103, 104],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, name='Date'))
        mock_download.return_value = mock_data
        
        result = data.get_price_data("RELIANCE", self.cache_dir, 7, 1)
        
        assert len(result) == 3
        assert 'open' in result.columns
        mock_download.assert_called_once()
    
    @patch('yfinance.download')
    def test_refresh_market_data_freeze_mode(self, mock_download):
        """Test refresh_market_data in freeze mode."""
        # Create existing cache
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=5),
            'open': range(100, 105),
            'high': range(105, 110),
            'low': range(95, 100),
            'close': range(102, 107),
            'volume': range(1000, 1005)
        })
        test_data.set_index('date', inplace=True)
        data._save_symbol_cache("RELIANCE", test_data, self.cache_dir)
          # Should not download in freeze mode
        data.refresh_market_data(
            ["RELIANCE"],  # Pass list directly
            self.cache_dir,
            refresh_days=7,
            years=1,
            freeze_date=date(2023, 1, 10)
        )
        
        mock_download.assert_not_called()
    
    @patch('yfinance.download')  
    def test_refresh_market_data_success(self, mock_download):
        """Test successful market data refresh."""        # Mock yfinance download - this should match what yfinance actually returns
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [102, 103, 104],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, name='Date'))
        mock_download.return_value = mock_data

        data.refresh_market_data(
            ["RELIANCE"],  # Pass list directly
            self.cache_dir,
            refresh_days=7,
            years=1
        )
        
        mock_download.assert_called_once()
        
        # Verify cache was created
        cache_file = self.cache_dir / "RELIANCE.NS.csv"
        assert cache_file.exists()
