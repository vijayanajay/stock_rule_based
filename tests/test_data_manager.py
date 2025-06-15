"""Tests for Data Manager module."""

import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from rich.console import Console

from kiss_signal.data_manager import DataManager


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
        self.console = Console(file=Mock())  # Mock console for testing
    
    def test_init(self):
        """Test DataManager initialization."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        assert dm.universe_path == self.universe_path
        assert dm.cache_dir == self.cache_dir
        assert dm.historical_years == 3
        assert dm.cache_refresh_days == 7
        assert dm.freeze_date is None
        assert dm.cache_dir.exists()
    
    def test_load_universe(self):
        """Test loading universe symbols."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        symbols = dm._load_universe()
        assert symbols == ["RELIANCE", "INFY", "TCS"]
    
    def test_load_universe_missing_file(self):
        """Test loading universe with missing file."""
        dm = DataManager(
            universe_path="nonexistent.csv",
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        with pytest.raises(FileNotFoundError):
            dm._load_universe()
    
    def test_load_universe_malformed(self):
        """Test loading malformed universe file."""
        malformed_path = self.temp_path / "malformed.csv"
        malformed_path.write_text("name,sector\nTest,IT\n")  # Missing symbol column
        
        dm = DataManager(
            universe_path=str(malformed_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        with pytest.raises(ValueError, match="missing 'symbol' column"):
            dm._load_universe()
    
    def test_cache_metadata_operations(self):
        """Test cache metadata loading and saving."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Test loading empty metadata
        metadata = dm._load_cache_metadata()
        assert metadata == {}
        
        # Test saving and loading metadata
        test_metadata = {"RELIANCE": "2025-01-01T00:00:00"}
        dm._save_cache_metadata(test_metadata)
        
        loaded_metadata = dm._load_cache_metadata()
        assert loaded_metadata == test_metadata
    
    def test_needs_refresh(self):
        """Test cache refresh logic."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            cache_refresh_days=7,
            console=self.console
        )
        
        # Symbol not in metadata should need refresh
        assert dm._needs_refresh("RELIANCE", {})
        
        # Recent update should not need refresh
        recent_time = datetime.now() - timedelta(days=1)
        metadata = {"RELIANCE": recent_time.isoformat()}
        assert not dm._needs_refresh("RELIANCE", metadata)
        
        # Old update should need refresh
        old_time = datetime.now() - timedelta(days=10)
        metadata = {"RELIANCE": old_time.isoformat()}
        assert dm._needs_refresh("RELIANCE", metadata)
    
    def test_add_ns_suffix(self):
        """Test adding .NS suffix for yfinance."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        assert dm._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert dm._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"
    
    def test_validate_data_quality(self):
        """Test data quality validation."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Test with good data
        good_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=5),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [105.0, 106.0, 107.0, 108.0, 109.0],
            'low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        assert dm._validate_data_quality(good_data, "TEST")
        
        # Test with empty data
        empty_data = pd.DataFrame()
        assert not dm._validate_data_quality(empty_data, "TEST")
    
    @patch('yfinance.Ticker')
    def test_fetch_symbol_data_success(self, mock_yf_ticker):
        """Test successful symbol data fetching."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Mock yfinance response
        mock_ticker_instance = Mock()
        mock_data = pd.DataFrame({
            'Date': pd.date_range('2025-01-01', periods=3),
            'Open': [100.0, 101.0, 102.0],
            'High': [103.0, 104.0, 105.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [102.0, 103.0, 104.0],
            'Volume': [1000, 1100, 1200]
        })
        mock_ticker_instance.history.return_value = mock_data
        mock_yf_ticker.return_value = mock_ticker_instance
        
        result = dm._fetch_symbol_data("RELIANCE.NS")
        
        assert result is not None
        assert len(result) == 3
        assert list(result.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']
    
    @patch('yfinance.Ticker')
    def test_fetch_symbol_data_failure(self, mock_yf_ticker):
        """Test failed symbol data fetching."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Mock yfinance to raise exception
        mock_yf_ticker.side_effect = Exception("Network error")
        
        result = dm._fetch_symbol_data("INVALID.NS")
        assert result is None
    
    def test_save_and_load_symbol_cache(self):
        """Test saving and loading symbol cache."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Create test data
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=3),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [102.0, 103.0, 104.0],
            'volume': [1000, 1100, 1200]
        })
        
        # Save data
        success = dm._save_symbol_cache("RELIANCE", test_data)
        assert success
        
        # Load data
        loaded_data = dm.get_price_data("RELIANCE")
        assert len(loaded_data) == 3
        assert loaded_data.index.name == 'date'
    
    def test_get_price_data_with_date_filtering(self):
        """Test getting price data with date filtering."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Create and save test data
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        dm._save_symbol_cache("RELIANCE", test_data)
        
        # Test date filtering
        filtered_data = dm.get_price_data(
            "RELIANCE", 
            start_date=date(2025, 1, 5),
            end_date=date(2025, 1, 8)
        )
        
        assert len(filtered_data) == 4  # 5th, 6th, 7th, 8th
    
    def test_get_price_data_with_freeze_date(self):
        """Test getting price data with freeze date."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            freeze_date=date(2025, 1, 5),
            console=self.console
        )
        
        # Create and save test data
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            'open': range(100, 110),
            'high': range(105, 115),
            'low': range(95, 105),
            'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        dm._save_symbol_cache("RELIANCE", test_data)
        
        # Data should be limited to freeze date
        data = dm.get_price_data("RELIANCE")
        assert data.index.max() <= pd.to_datetime(date(2025, 1, 5))
    
    def test_get_price_data_missing_cache(self):
        """Test getting price data for missing cache."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        with pytest.raises(FileNotFoundError):
            dm.get_price_data("NONEXISTENT")
    
    @patch('kiss_signal.data_manager.DataManager._fetch_symbol_data')
    def test_refresh_market_data(self, mock_fetch):
        """Test market data refresh."""
        dm = DataManager(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            console=self.console
        )
        
        # Mock fetch to return test data
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=3),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [102.0, 103.0, 104.0],
            'volume': [1000, 1100, 1200]
        })
        mock_fetch.return_value = test_data
        
        results = dm.refresh_market_data(["RELIANCE", "INFY"])
        
        assert results["RELIANCE"] is True
        assert results["INFY"] is True
        assert mock_fetch.call_count == 2


class TestDataManagerConfiguration:
    """Test DataManager with different configurations."""
    
    def test_freeze_date_integration(self):
        """Test freeze date functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            universe_path = temp_path / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            dm = DataManager(
                universe_path=str(universe_path),
                cache_dir=str(temp_path / "cache"),
                freeze_date=date(2025, 1, 15),
                console=Console(file=Mock())
            )
            
            assert dm.freeze_date == date(2025, 1, 15)
    
    def test_custom_cache_refresh_days(self):
        """Test custom cache refresh configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            universe_path = temp_path / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            dm = DataManager(
                universe_path=str(universe_path),
                cache_dir=str(temp_path / "cache"),
                cache_refresh_days=1,
                console=Console(file=Mock())
            )
            
            # Symbol with data from 2 days ago should need refresh
            old_time = datetime.now() - timedelta(days=2)
            metadata = {"RELIANCE": old_time.isoformat()}
            assert dm._needs_refresh("RELIANCE", metadata)
