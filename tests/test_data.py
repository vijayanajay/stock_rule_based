"""Consolidated tests for data management functionality.

This module consolidates all data-related tests into a single file following
KISS principles. Tests are organized by functionality area:
- Basic data operations (load, cache, validation)
- Advanced data operations (yfinance, market data refresh)
- Market data alignment fixes
- Timestamp comparison fixes
"""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from unittest.mock import patch
import tempfile
from pathlib import Path
import logging
import numpy as np

from kiss_signal import data
from kiss_signal.data import get_price_data
from kiss_signal.rules import market_above_sma


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
    """Temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


# ================================================================================================
# BASIC DATA OPERATIONS TESTS
# ================================================================================================

class TestDataBasicOperations:
    """Test suite for basic data loading, caching, and validation functions."""
    
    def test_load_universe(self, temp_cache_dir):
        """Test loading universe from CSV file."""
        universe_path = temp_cache_dir / "universe.csv"
        universe_path.write_text("symbol,name\nRELIANCE,Reliance\nTCS,TCS")
        symbols = data.load_universe(str(universe_path))
        assert symbols == ["RELIANCE", "TCS"]

    def test_load_universe_missing_file(self):
        """Test load_universe raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            data.load_universe("nonexistent.csv")

    def test_load_universe_malformed(self, temp_cache_dir):
        """Test load_universe raises error for malformed CSV."""
        universe_path = temp_cache_dir / "universe.csv"
        universe_path.write_text("header1,header2\nRELIANCE,Reliance")
        with pytest.raises(ValueError, match="Universe file missing 'symbol' column"):
            data.load_universe(str(universe_path))

    def test_add_ns_suffix(self):
        """Test _add_ns_suffix function."""
        assert data._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert data._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"
        assert data._add_ns_suffix("^NSEI") == "^NSEI"

    @pytest.mark.parametrize("file_exists,stale", [
        (False, True),   # Missing file needs refresh
        (True, False),   # Fresh file doesn't need refresh  
        (True, True),    # Stale file needs refresh
    ])
    def test_needs_refresh(self, temp_cache_dir, file_exists, stale):
        """Test _needs_refresh function with various scenarios."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        
        if file_exists:
            cache_file.touch()
            if stale:
                # Mock file modification time to be old
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_mtime = (datetime.now() - timedelta(days=8)).timestamp()
                    result = data._needs_refresh(cache_file)
            else:
                result = data._needs_refresh(cache_file)
        else:
            result = data._needs_refresh(cache_file)
        
        expected = True if not file_exists or stale else False
        assert result is expected

    def test_needs_refresh_os_error(self, temp_cache_dir):
        """Test _needs_refresh handles OSError gracefully."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.touch()
        with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
            assert data._needs_refresh(cache_file) is True

    @pytest.mark.parametrize("data_quality,expected", [
        ("good", True),
        ("negative_prices", False),
        ("zero_volume", False),
        ("empty", False),
        ("large_gap", False),
    ])
    def test_validate_data_quality(self, data_quality, expected):
        """Test data quality validation with various data conditions."""
        if data_quality == "good":
            test_data = pd.DataFrame({
                'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
                'open': [100, 101, 102, 103, 104],
                'high': [105, 106, 107, 108, 109],
                'low': [95, 96, 97, 98, 99],
                'close': [102, 103, 104, 105, 106],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })
        elif data_quality == "negative_prices":
            test_data = pd.DataFrame({
                'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
                'open': [100, 101, -102, 103, 104],  # Negative price
                'high': [105, 106, 107, 108, 109],
                'low': [95, 96, 97, 98, 99],
                'close': [102, 103, 104, 105, 106],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })
        elif data_quality == "zero_volume":
            test_data = pd.DataFrame({
                'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
                'open': [100] * 10,
                'high': [105] * 10,
                'low': [95] * 10,
                'close': [102] * 10,
                'volume': [1000, 0, 1200, 0, 1400, 0, 0, 0, 0, 0]  # 60% zero volume
            })
        elif data_quality == "empty":
            test_data = pd.DataFrame()
        elif data_quality == "large_gap":
            test_data = pd.DataFrame({
                'date': pd.to_datetime(['2023-01-01', '2023-01-10']),
                'open': [100, 101], 'high': [100, 101], 'low': [100, 101],
                'close': [100, 101], 'volume': [1000, 1000]
            }).set_index('date')
        
        result = data._validate_data_quality(test_data, "RELIANCE")
        assert result is expected


# ================================================================================================
# CACHE OPERATIONS TESTS  
# ================================================================================================

class TestCacheOperations:
    """Test suite for cache save/load operations."""

    def test_save_and_load_cache_cycle(self, temp_cache_dir):
        """Test complete save/load cycle preserves data integrity."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        })
        data._save_cache("RELIANCE", test_data, temp_cache_dir)
        loaded_data = data._load_cache("RELIANCE", temp_cache_dir)
        expected_data = test_data.set_index('date')
        pd.testing.assert_frame_equal(expected_data, loaded_data)

    @patch('pandas.DataFrame.to_csv', side_effect=OSError("Disk full"))
    def test_save_cache_exception_handling(self, mock_to_csv, temp_cache_dir):
        """Test _save_cache handles exceptions gracefully."""
        df = pd.DataFrame({'close': [100]})
        assert data._save_cache("TEST", df, temp_cache_dir) is False

    @pytest.mark.parametrize("cache_format", [
        "unnamed_col",     # Cache with 'Unnamed: 0' column
        "date_as_col",     # Cache with date as first column
    ])
    def test_load_cache_format_variations(self, temp_cache_dir, cache_format):
        """Test loading cache files with various formats."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        
        if cache_format == "unnamed_col":
            cache_file.write_text("Unnamed: 0,date,close\n0,2023-01-01,100\n1,2023-01-02,101")
            loaded_data = data._load_cache("TEST", temp_cache_dir)
            assert 'Unnamed: 0' not in loaded_data.columns
            assert 'date' in loaded_data.index.name
            assert len(loaded_data) == 2
        elif cache_format == "date_as_col":
            cache_file.write_text("date,close\n2023-01-01,100\n2023-01-02,101")
            loaded_data = data._load_cache("TEST", temp_cache_dir)
            assert isinstance(loaded_data.index, pd.DatetimeIndex)
            assert len(loaded_data) == 2


# ================================================================================================  
# PRICE DATA RETRIEVAL TESTS
# ================================================================================================

class TestPriceDataRetrieval:
    """Test suite for get_price_data function with various scenarios."""

    @pytest.mark.parametrize("scenario", [
        "date_filtering",
        "start_end_date", 
        "freeze_date",
        "freeze_mode_no_cache",
        "no_data_in_range",
    ])
    def test_get_price_data_scenarios(self, temp_cache_dir, scenario):
        """Test get_price_data with various date filtering scenarios."""
        if scenario != "freeze_mode_no_cache":
            # Setup test data for most scenarios
            test_data = pd.DataFrame({
                'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
                'open': range(100, 110),
                'high': range(105, 115),
                'low': range(95, 105),
                'close': range(102, 112),
                'volume': range(1000, 1010)
            })
            data._save_cache("RELIANCE", test_data, temp_cache_dir)
        
        if scenario == "date_filtering":
            result = data.get_price_data(
                "RELIANCE", temp_cache_dir, freeze_date=date(2023, 1, 5)
            )
            assert len(result) == 5
            assert result.index.max().date() == date(2023, 1, 5)
            
        elif scenario == "start_end_date":
            result = data.get_price_data(
                "RELIANCE", temp_cache_dir,
                start_date=date(2023, 1, 3), end_date=date(2023, 1, 7)
            )
            assert len(result) == 5
            assert result.index.min().date() == date(2023, 1, 3)
            assert result.index.max().date() == date(2023, 1, 7)
            
        elif scenario == "freeze_date":
            result = data.get_price_data(
                "RELIANCE", temp_cache_dir, freeze_date=date(2023, 1, 3)
            )
            assert len(result) == 3
            assert result.index.max().date() == date(2023, 1, 3)
            
        elif scenario == "freeze_mode_no_cache":
            with pytest.raises(FileNotFoundError):
                data.get_price_data(
                    "TEST", temp_cache_dir, freeze_date=date(2023, 1, 1)
                )
                
        elif scenario == "no_data_in_range":
            with pytest.raises(ValueError, match="No data available for RELIANCE"):
                data.get_price_data(
                    "RELIANCE", temp_cache_dir, start_date=date(2024, 1, 1)
                )

    @pytest.mark.parametrize("symbol,should_warn", [
        ("RELIANCE", True),    # Regular stock should warn for limited data
        ("^NSEI", False),      # NIFTY should not warn for limited data
    ])
    def test_get_price_data_limited_data_warnings(self, temp_cache_dir, caplog, symbol, should_warn):
        """Test warning behavior for limited data varies by symbol type."""
        # Create limited data that would normally trigger a warning
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [100, 101, 102] if symbol != "^NSEI" else [18000, 18100, 18200],
            'high': [105, 106, 107] if symbol != "^NSEI" else [18200, 18300, 18400],
            'low': [95, 96, 97] if symbol != "^NSEI" else [17800, 17900, 18000],
            'close': [102, 103, 104] if symbol != "^NSEI" else [18050, 18150, 18250],
            'volume': [1000, 1100, 1200] if symbol != "^NSEI" else [1000000, 1100000, 1200000]
        })
        data._save_cache(symbol, test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            result = data.get_price_data(symbol, temp_cache_dir)
            assert len(result) == 3
            
            warning_present = f"Limited data for {symbol}" in caplog.text
            assert warning_present == should_warn

    @pytest.mark.parametrize("date_params,should_warn", [
        ({}, True),                                           # No date filters - should warn
        ({"start_date": date(2023, 1, 2)}, True),            # Only start_date - should warn  
        ({"end_date": date(2023, 1, 3)}, True),              # Only end_date - should warn
        ({"start_date": date(2023, 1, 2), 
          "end_date": date(2023, 1, 3)}, False),             # Position tracking - no warning
    ])
    def test_get_price_data_position_tracking_warnings(self, temp_cache_dir, caplog, date_params, should_warn):
        """Test warning suppression for position tracking (both start_date and end_date specified)."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            data.get_price_data("TESTSTOCK", temp_cache_dir, **date_params)
            warning_present = "Limited data for TESTSTOCK" in caplog.text
            assert warning_present == should_warn

    def test_get_price_data_sufficient_data_no_warning(self, temp_cache_dir, caplog):
        """Test no warning when data is sufficient (>= 50 rows)."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=60)),
            'open': range(100, 160),
            'high': range(105, 165),
            'low': range(95, 155),
            'close': range(102, 162),
            'volume': range(1000, 1060)
        })
        data._save_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            result = data.get_price_data("TESTSTOCK", temp_cache_dir)
            assert len(result) == 60
            assert "Limited data for TESTSTOCK" not in caplog.text

    @pytest.mark.parametrize("symbol,expected_suffix", [
        ("BPCL", "BPCL.NS"),     # Regular stock gets .NS suffix
        ("^NSEI", "^NSEI"),      # Index symbol preserved
    ])
    @patch('kiss_signal.data._fetch_symbol_data')
    def test_get_price_data_symbol_suffix_handling(self, mock_fetch, temp_cache_dir, symbol, expected_suffix):
        """Test symbol suffix handling for different symbol types."""
        mock_fetch.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'open': [100, 101], 'high': [105, 106], 'low': [95, 96],
            'close': [102, 103], 'volume': [1000, 1100]
        })
        
        try:
            data.get_price_data(symbol, temp_cache_dir, years=1)
        except Exception:
            pass  # Expected to fail during save, only care about fetch call
        
        mock_fetch.assert_called_once_with(expected_suffix, 1, None)


# ================================================================================================
# ADVANCED DATA OPERATIONS TESTS  
# ================================================================================================

class TestAdvancedDataOperations:
    """Test suite for advanced data operations involving yfinance integration."""

    @patch('yfinance.download')
    def test_get_price_data_missing_cache_fetches_new_data(self, mock_download, temp_cache_dir):
        """Test get_price_data fetches new data when cache is missing."""
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
    def test_refresh_market_data_freeze_mode_skips_download(self, mock_download, temp_cache_dir):
        """Test refresh_market_data skips download in freeze mode."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': range(100, 105), 'high': range(105, 110),
            'low': range(95, 100), 'close': range(102, 107),
            'volume': range(1000, 1005)
        })
        data._save_cache("RELIANCE", test_data, temp_cache_dir)
        
        data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir),
            years=1,
            freeze_date=date(2023, 1, 10)
        )
        mock_download.assert_not_called()

    @patch('yfinance.download')
    def test_refresh_market_data_success_creates_cache(self, mock_download, temp_cache_dir):
        """Test successful market data refresh creates cache file."""
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102], 'High': [105, 106, 107],
            'Low': [95, 96, 97], 'Close': [102, 103, 104],
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

    @pytest.mark.parametrize("column_type,expected_success", [
        ("multiindex", True),    # MultiIndex columns should be handled
        ("tuple", True),         # Tuple columns should be handled  
        ("missing", False),      # Missing required columns should fail
    ])
    @patch('yfinance.download')
    def test_fetch_symbol_data_column_handling(self, mock_download, column_type, expected_success):
        """Test _fetch_symbol_data handles various column formats."""
        if column_type == "multiindex":
            mock_data = pd.DataFrame({
                ('Open', 'RELIANCE.NS'): [100, 101, 102],
                ('High', 'RELIANCE.NS'): [105, 106, 107],
                ('Low', 'RELIANCE.NS'): [95, 96, 97],
                ('Close', 'RELIANCE.NS'): [102, 103, 104],
                ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
            }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
            mock_data.columns = pd.MultiIndex.from_tuples(mock_data.columns)
        elif column_type == "tuple":
            mock_data = pd.DataFrame({
                ('Open', 'RELIANCE.NS'): [100, 101, 102],
                ('High', 'RELIANCE.NS'): [105, 106, 107],
                ('Low', 'RELIANCE.NS'): [95, 96, 97],
                ('Close', 'RELIANCE.NS'): [102, 103, 104],
                ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
            }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=3, name='Date')))
        elif column_type == "missing":
            mock_data = pd.DataFrame({'Open': [100]}, 
                                   index=pd.to_datetime(['2023-01-01']))
        
        mock_download.return_value = mock_data
        result = data._fetch_symbol_data("RELIANCE.NS", 1)
        
        if expected_success:
            assert result is not None
            assert len(result) == 3 if column_type != "missing" else None
            if column_type in ["multiindex", "tuple"]:
                expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                assert all(col in result.columns for col in expected_columns)
        else:
            assert result is None

    @pytest.mark.parametrize("failure_type", [
        "download_failure",      # yfinance returns None
        "validation_failure",    # Data fails validation  
        "api_exception",         # yfinance raises exception
        "empty_dataframe",       # yfinance returns empty DataFrame
    ])
    @patch('yfinance.download')
    def test_refresh_market_data_failure_scenarios(self, mock_download, temp_cache_dir, failure_type):
        """Test refresh_market_data handles various failure scenarios."""
        if failure_type == "download_failure":
            mock_download.return_value = None
        elif failure_type == "validation_failure":
            mock_data = pd.DataFrame({
                'Open': [-100], 'High': [105], 'Low': [95], 
                'Close': [102], 'Volume': [1000]
            }, index=pd.to_datetime(['2023-01-01']))
            mock_download.return_value = mock_data
        elif failure_type == "api_exception":
            mock_download.side_effect = Exception("API Error")
        elif failure_type == "empty_dataframe":
            mock_download.return_value = pd.DataFrame()
        
        results = data.refresh_market_data(
            universe_path=["RELIANCE"],
            cache_dir=str(temp_cache_dir)
        )
        
        assert results["RELIANCE"] is False
        if failure_type != "api_exception":  # API exception is caught earlier
            cache_file = temp_cache_dir / "RELIANCE.NS.csv"
            assert not cache_file.exists()

    @patch('kiss_signal.data._fetch_and_store_data', return_value=True)
    def test_refresh_market_data_with_symbol_list(self, mock_fetch_store, temp_cache_dir):
        """Test refresh_market_data processes list of symbols."""
        results = data.refresh_market_data(
            universe_path=["RELIANCE", "TCS"],
            cache_dir=str(temp_cache_dir)
        )
        
        assert mock_fetch_store.call_count == 2
        assert results["RELIANCE"] is True
        assert results["TCS"] is True


# ================================================================================================
# MARKET DATA ALIGNMENT TESTS
# ================================================================================================

class TestMarketDataAlignment:
    """Test suite for market data alignment fixes preventing 0% pass rates."""

    def setup_method(self):
        """Set up test fixtures for alignment tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample market data with proper structure
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        self.sample_market_data = pd.DataFrame({
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000 + (dates.dayofyear % 100000)
        }, index=dates)
        
        # Create sample stock data with overlapping dates
        stock_dates = pd.date_range('2023-06-01', '2023-12-31', freq='D')
        self.sample_stock_data = pd.DataFrame({
            'open': 50 + (stock_dates.dayofyear % 25),
            'high': 55 + (stock_dates.dayofyear % 25),
            'low': 45 + (stock_dates.dayofyear % 25),
            'close': 50 + (stock_dates.dayofyear % 25) + (stock_dates.dayofyear % 5),
            'volume': 500000 + (stock_dates.dayofyear % 50000)
        }, index=stock_dates)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _save_market_cache_compat(self, data_df: pd.DataFrame, cache_file: Path) -> None:
        """Compatibility wrapper for market cache operations."""
        filename = cache_file.name
        if filename.startswith("INDEX_"):
            symbol = "^" + filename.replace("INDEX_", "").replace(".csv", "")
        else:
            symbol = filename.replace(".NS.csv", "")
        
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        data._save_cache(symbol, data_df, cache_file.parent)

    def _load_market_cache_compat(self, cache_file: Path) -> pd.DataFrame:
        """Compatibility wrapper for market cache operations."""
        filename = cache_file.name
        if filename.startswith("INDEX_"):
            symbol = "^" + filename.replace("INDEX_", "").replace(".csv", "")
        else:
            symbol = filename.replace(".NS.csv", "")
        return data._load_cache(symbol, cache_file.parent)

    def test_market_cache_preserves_datetime_index(self):
        """Test market cache save/load preserves DatetimeIndex."""
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        
        self._save_market_cache_compat(self.sample_market_data, cache_file)
        loaded_data = self._load_market_cache_compat(cache_file)
        
        assert isinstance(loaded_data.index, pd.DatetimeIndex)
        assert len(loaded_data) == len(self.sample_market_data)
        assert loaded_data.columns.tolist() == ['open', 'high', 'low', 'close', 'volume']

    @pytest.mark.parametrize("input_index_type", ["range", "datetime"])
    def test_market_above_sma_handles_index_types(self, input_index_type):
        """Test market_above_sma handles different index types correctly."""
        if input_index_type == "range":
            # Create problematic data with RangeIndex (realistic issue)
            problematic_data = self.sample_market_data.reset_index()
            assert isinstance(problematic_data.index, pd.RangeIndex)
            test_data = problematic_data
        else:
            # Data with proper DatetimeIndex
            test_data = self.sample_market_data
        
        signals = market_above_sma(test_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert isinstance(signals.index, pd.DatetimeIndex)
        assert len(signals) > 0
        assert signals.dtype == bool

    def test_market_data_alignment_integration(self):
        """Test end-to-end alignment works in backtester context."""
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        self._save_market_cache_compat(self.sample_market_data, cache_file)
        
        market_data = get_price_data("^NSEI", self.temp_dir)
        market_signals = market_above_sma(market_data, period=20)
        
        # Simulate backtester alignment process
        aligned_signals = market_signals.reindex(self.sample_stock_data.index)
        filled_signals = aligned_signals.ffill().fillna(False)
        
        assert len(filled_signals) == len(self.sample_stock_data)
        assert filled_signals.sum() > 0
        assert not (filled_signals == False).all()

    def test_freeze_date_preserves_datetime_index(self):
        """Test freeze date filtering maintains DatetimeIndex."""
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        self._save_market_cache_compat(self.sample_market_data, cache_file)
        
        freeze_date = date(2023, 6, 30)
        market_data = get_price_data("^NSEI", self.temp_dir, freeze_date=freeze_date)
        
        assert market_data.index.max().date() <= freeze_date
        assert len(market_data) < len(self.sample_market_data)
        assert isinstance(market_data.index, pd.DatetimeIndex)

    def test_alignment_signal_preservation(self):
        """Test signal counts remain reasonable after alignment."""
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        close_prices = []
        
        # Create pattern where ~60% of days will be above 20-day SMA
        for i, dt in enumerate(dates):
            base_price = 100
            trend = i * 0.01
            noise = (i % 10) - 5
            close_prices.append(base_price + trend + noise)
        
        market_data = pd.DataFrame({
            'open': close_prices, 'high': [p + 2 for p in close_prices],
            'low': [p - 2 for p in close_prices], 'close': close_prices,
            'volume': [1000000] * len(dates)
        }, index=dates)
        
        signals = market_above_sma(market_data, period=20)
        original_signal_rate = signals.sum() / len(signals)
        
        # Test alignment with subset
        stock_dates = dates[180:300]
        aligned_signals = signals.reindex(stock_dates)
        filled_signals = aligned_signals.ffill().fillna(False)
        aligned_signal_rate = filled_signals.sum() / len(filled_signals)
        
        assert aligned_signal_rate > 0.1  # Should not be 0%
        assert abs(aligned_signal_rate - original_signal_rate) < 0.5

    def test_problematic_csv_format_handling(self):
        """Test handling CSV files that caused original alignment issues."""
        csv_content = """date,open,high,low,close,volume
2023-01-01,100,105,95,102,1000000
2023-01-02,102,107,97,104,1100000
2023-01-03,104,109,99,106,1200000
2023-01-04,106,111,101,108,1300000
2023-01-05,108,113,103,110,1400000"""
        
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        with open(cache_file, 'w') as f:
            f.write(csv_content)
        
        loaded_data = self._load_market_cache_compat(cache_file)
        
        assert isinstance(loaded_data.index, pd.DatetimeIndex)
        assert 'date' not in loaded_data.columns
        assert len(loaded_data) == 5
        
        signals = market_above_sma(loaded_data, period=3)
        assert isinstance(signals.index, pd.DatetimeIndex)
        assert len(signals) == 5


# ================================================================================================
# TIMESTAMP COMPARISON TESTS
# ================================================================================================

class TestTimestampComparison:
    """Test suite for timestamp comparison fixes preventing numpy array errors."""

    @pytest.mark.parametrize("index_format", [
        "string_dates",       # String-based dates in CSV
        "numeric_index",      # Numeric index with date column
        "invalid_dates",      # Some invalid date entries
    ])
    def test_get_price_data_index_conversion(self, temp_cache_dir, index_format):
        """Test get_price_data handles various index formats without comparison errors."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        
        if index_format == "string_dates":
            cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000"""
        elif index_format == "numeric_index":
            cache_data = """Unnamed: 0,date,open,high,low,close,volume
0,2024-01-01,100,105,95,103,10000
1,2024-01-02,101,106,96,104,10000
2,2024-01-03,102,107,97,105,10000
3,2024-01-04,103,108,98,106,10000
4,2024-01-05,104,109,99,107,10000"""
        elif index_format == "invalid_dates":
            cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
invalid-date,101,106,96,104,10000
2024-01-03,102,107,97,105,10000"""
        
        cache_file.write_text(cache_data)
        
        if index_format == "invalid_dates":
            result = data._load_cache("TEST", temp_cache_dir)
            assert isinstance(result.index, pd.DatetimeIndex)
            assert len(result) == 2  # Invalid date dropped
        else:
            result = data.get_price_data(
                symbol="TEST", cache_dir=temp_cache_dir,
                start_date=date(2024, 1, 2), end_date=date(2024, 1, 4)
            )
            assert len(result) == 3
            assert isinstance(result.index, pd.DatetimeIndex)

    def test_load_cache_invalid_dates_error_handling(self, temp_cache_dir):
        """Test _load_cache raises error when no valid dates remain."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
invalid-date1,100,105,95,103,10000
invalid-date2,101,106,96,104,10000
not-a-date,102,107,97,105,10000"""
        cache_file.write_text(cache_data)
        
        with pytest.raises(ValueError, match="No valid data found in cache for TEST"):
            data._load_cache("TEST", temp_cache_dir)

    def test_get_price_data_freeze_date_index_conversion(self, temp_cache_dir):
        """Test freeze_date filtering works correctly with index conversion."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000"""
        cache_file.write_text(cache_data)
        
        result = data.get_price_data(
            symbol="TEST", cache_dir=temp_cache_dir,
            freeze_date=date(2024, 1, 3)
        )
        
        assert len(result) == 3
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index[-1] <= pd.to_datetime('2024-01-03')

    @patch('kiss_signal.data._load_cache')
    def test_get_price_data_non_datetime_index_handling(self, mock_load_cache, temp_cache_dir):
        """Test get_price_data converts non-DatetimeIndex properly."""
        # Create mock data with problematic RangeIndex
        mock_data = pd.DataFrame({
            'open': [100, 101, 102], 'high': [105, 106, 107],
            'low': [95, 96, 97], 'close': [103, 104, 105],
            'volume': [10000, 10000, 10000]
        })
        mock_data.index = pd.RangeIndex(start=0, stop=3)
        mock_load_cache.return_value = mock_data
        
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.write_text("dummy")
        
        with pytest.raises(ValueError, match="No data available for TEST"):
            data.get_price_data(
                symbol="TEST", cache_dir=temp_cache_dir,
                start_date=date(2024, 1, 1)
            )

    def test_get_price_data_complex_filtering_with_conversion(self, temp_cache_dir):
        """Test complex date filtering works with index conversion."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_data = """date,open,high,low,close,volume
2024-01-01,100,105,95,103,10000
2024-01-02,101,106,96,104,10000
2024-01-03,102,107,97,105,10000
2024-01-04,103,108,98,106,10000
2024-01-05,104,109,99,107,10000
2024-01-06,105,110,100,108,10000"""
        cache_file.write_text(cache_data)
        
        result = data.get_price_data(
            symbol="TEST", cache_dir=temp_cache_dir,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 5),
            freeze_date=date(2024, 1, 4)
        )
        
        assert len(result) == 3  # Jan 2-4 (freeze_date takes precedence)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index[0] == pd.to_datetime('2024-01-02')
        assert result.index[-1] == pd.to_datetime('2024-01-04')

    def test_regression_nifty_comparison_error(self, temp_cache_dir):
        """Regression test for specific NIFTY comparison error from logs."""
        cache_file = temp_cache_dir / "^NSEI.NS.csv"
        cache_data = """date,open,high,low,close,volume
2025-07-01,25453.40,25500.00,25400.00,25453.40,1000000
2025-07-02,25454.00,25550.00,25430.00,25480.00,1100000
2025-07-17,25000.00,25100.00,24900.00,25050.00,1200000
2025-07-18,25050.00,25150.00,24950.00,24968.40,1300000"""
        cache_file.write_text(cache_data)
        
        nifty_data = data.get_price_data(
            symbol="^NSEI", cache_dir=temp_cache_dir,
            start_date=date(2025, 7, 1), end_date=date(2025, 7, 18)
        )
        
        # Should include trading days in range (weekends excluded)
        # July 1-18, 2025: 14 trading days (excludes weekends)
        assert len(nifty_data) == 14  
        assert isinstance(nifty_data.index, pd.DatetimeIndex)
        assert nifty_data.index[0] == pd.to_datetime('2025-07-01')
        assert nifty_data.index[-1] == pd.to_datetime('2025-07-18')


# ================================================================================================
# END-TO-END INTEGRATION TESTS
# ================================================================================================

def test_end_to_end_alignment_regression():
    """End-to-end test simulating original alignment problem and verifying fix."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create market data with problematic format
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000
        })
        
        # Save to CSV (creates problematic format)
        cache_file = temp_path / "INDEX_NSEI.csv"
        market_data.to_csv(cache_file, index=False)
        
        # Verify problematic format exists
        raw_data = pd.read_csv(cache_file)
        assert isinstance(raw_data.index, pd.RangeIndex)
        assert 'date' in raw_data.columns
        
        # Load and verify fix
        loaded_market = get_price_data("^NSEI", temp_path)
        assert isinstance(loaded_market.index, pd.DatetimeIndex)
        
        # Create overlapping stock data
        stock_dates = pd.date_range('2023-06-01', '2023-10-31', freq='D')
        stock_data = pd.DataFrame({
            'close': 50 + (stock_dates.dayofyear % 25)
        }, index=stock_dates)
        
        # Test signal generation and alignment
        market_signals = market_above_sma(loaded_market, period=50)
        assert isinstance(market_signals.index, pd.DatetimeIndex)
        
        # Test backtester-style alignment
        aligned_signals = market_signals.reindex(stock_data.index)
        final_signals = aligned_signals.ffill().fillna(False)
        
        signal_rate = final_signals.sum() / len(final_signals)
        assert signal_rate > 0, f"Signal rate should be > 0%, got {signal_rate:.1%}"


if __name__ == "__main__":
    # Run key regression tests
    test_end_to_end_alignment_regression()
    print("✅ All data tests consolidated successfully")
