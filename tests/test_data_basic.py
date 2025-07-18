"""Optimized tests for data management functionality - Basic operations."""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from unittest.mock import patch
import tempfile
from pathlib import Path
import logging

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


class TestDataBasicFunctions:
    """Test suite for basic data functions."""
    
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
    
    def test_validate_data_quality_zero_volume(self):
        """Test data quality validation with high zero-volume days."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
            'open': [100] * 10,
            'high': [105] * 10,
            'low': [95] * 10,
            'close': [102] * 10,
            'volume': [1000, 0, 1200, 0, 1400, 0, 0, 0, 0, 0] # 60% zero volume
        })
        assert data._validate_data_quality(test_data, "RELIANCE") is False

    def test_validate_data_quality_empty_df(self):
        """Test _validate_data_quality with an empty DataFrame."""
        assert data._validate_data_quality(pd.DataFrame(), "TEST") is False

    def test_validate_data_quality_large_gap(self):
        """Test _validate_data_quality with a large data gap."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-10']),
            'open': [100, 101], 'high': [100, 101], 'low': [100, 101],
            'close': [100, 101],
            'volume': [1000, 1000]
        })
        test_data = test_data.set_index('date')
        assert data._validate_data_quality(test_data, "TEST") is False

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

    @patch('pandas.DataFrame.to_csv', side_effect=OSError("Disk full"))
    def test_save_symbol_cache_exception(self, mock_to_csv, temp_cache_dir):
        """Test _save_symbol_cache handles exceptions."""
        df = pd.DataFrame({'close': [100]})
        assert data._save_symbol_cache("TEST", df, temp_cache_dir) is False

    def test_load_symbol_cache_with_unnamed_col(self, temp_cache_dir):
        """Test loading cache file with an 'Unnamed: 0' column."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.write_text("Unnamed: 0,date,close\n0,2023-01-01,100\n1,2023-01-02,101")
        
        loaded_data = data._load_symbol_cache("TEST", temp_cache_dir)
        assert 'Unnamed: 0' not in loaded_data.columns
        assert 'date' in loaded_data.index.name
        assert len(loaded_data) == 2

    def test_load_symbol_cache_with_date_as_first_col(self, temp_cache_dir):
        """Test loading cache where date is the first column but not index."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.write_text("date,close\n2023-01-01,100\n2023-01-02,101")
        loaded_data = data._load_symbol_cache("TEST", temp_cache_dir)
        assert isinstance(loaded_data.index, pd.DatetimeIndex)
        assert len(loaded_data) == 2
    
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

    def test_get_price_data_with_start_and_end_date(self, temp_cache_dir):
        """Test get_price_data with start and end date filtering."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
            'open': range(100, 110), 'high': range(105, 115),
            'low': range(95, 105), 'close': range(102, 112),
            'volume': range(1000, 1010)
        })
        data._save_symbol_cache("RELIANCE", test_data, temp_cache_dir)
        result = data.get_price_data(
            "RELIANCE",
            temp_cache_dir,
            start_date=date(2023, 1, 3),
            end_date=date(2023, 1, 7)
        )
        assert len(result) == 5
        assert result.index.min().date() == date(2023, 1, 3)
        assert result.index.max().date() == date(2023, 1, 7)
    
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

    def test_get_price_data_freeze_mode_no_cache(self, temp_cache_dir):
        """Test get_price_data in freeze mode when cache is missing."""
        with pytest.raises(FileNotFoundError):
            data.get_price_data(
                "TEST", temp_cache_dir, freeze_date=date(2023, 1, 1)
            )

    def test_get_price_data_no_data_in_range(self, temp_cache_dir):
        """Test get_price_data when date filtering results in empty DataFrame."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': range(5), 'high': range(5), 'low': range(5), 'volume': range(5),
            'close': range(5)
        })
        data._save_symbol_cache("TEST", test_data, temp_cache_dir)
        with pytest.raises(ValueError, match="No data available for TEST"):
            data.get_price_data("TEST", temp_cache_dir, start_date=date(2024, 1, 1))

    def test_get_price_data_limited_data_warning(self, temp_cache_dir, caplog):
        """Test get_price_data logs a warning for limited data."""
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=10)),
            'open': range(10), 'high': range(10), 'low': range(10), 'volume': range(10),
            'close': range(10)
        })
        data._save_symbol_cache("TEST", test_data, temp_cache_dir)
        with caplog.at_level(logging.WARNING):
            result = data.get_price_data("TEST", temp_cache_dir)
            assert len(result) == 10
            assert "Limited data for TEST" in caplog.text

    def test_get_price_data_nifty_no_warning_for_limited_data(self, temp_cache_dir, caplog):
        """Test get_price_data does NOT log a warning for limited NIFTY data."""
        # Create limited NIFTY data (only 3 rows, which would normally trigger warning)
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [18000, 18100, 18200], 
            'high': [18200, 18300, 18400], 
            'low': [17800, 17900, 18000], 
            'close': [18050, 18150, 18250],
            'volume': [1000000, 1100000, 1200000]
        })
        data._save_symbol_cache("^NSEI", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            result = data.get_price_data("^NSEI", temp_cache_dir)
            assert len(result) == 3
            # Verify NO warning was logged for NIFTY
            assert "Limited data for ^NSEI" not in caplog.text
            
    def test_get_price_data_regular_stock_still_warns_for_limited_data(self, temp_cache_dir, caplog):
        """Test that regular stocks still get warnings for limited data while NIFTY doesn't."""
        # Create limited data for both NIFTY and regular stock
        nifty_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [18000, 18100, 18200], 
            'high': [18200, 18300, 18400], 
            'low': [17800, 17900, 18000], 
            'close': [18050, 18150, 18250],
            'volume': [1000000, 1100000, 1200000]
        })
        
        stock_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=3)),
            'open': [100, 101, 102], 
            'high': [105, 106, 107], 
            'low': [95, 96, 97], 
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        })
        
        data._save_symbol_cache("^NSEI", nifty_data, temp_cache_dir)
        data._save_symbol_cache("RELIANCE", stock_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test NIFTY - should NOT warn
            caplog.clear()
            nifty_result = data.get_price_data("^NSEI", temp_cache_dir)
            assert len(nifty_result) == 3
            assert "Limited data for ^NSEI" not in caplog.text
            
            # Test regular stock - should warn
            caplog.clear()
            stock_result = data.get_price_data("RELIANCE", temp_cache_dir)
            assert len(stock_result) == 3
            assert "Limited data for RELIANCE" in caplog.text

    def test_needs_refresh_os_error(self, temp_cache_dir):
        """Test _needs_refresh handles OSError."""
        cache_file = temp_cache_dir / "TEST.NS.csv"
        cache_file.touch()
        with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
            assert data._needs_refresh("TEST", temp_cache_dir, 7) is True

    @patch('kiss_signal.data._fetch_symbol_data')
    def test_get_price_data_adds_ns_suffix_for_fetch(self, mock_fetch, temp_cache_dir):
        """Test that get_price_data adds .NS suffix when fetching fresh data."""
        # Setup: no cache file exists, so it will try to fetch fresh data
        mock_fetch.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'open': [100, 101],
            'high': [105, 106],
            'low': [95, 96],
            'close': [102, 103],
            'volume': [1000, 1100]
        })
        
        # Call get_price_data with a plain symbol
        try:
            data.get_price_data("BPCL", temp_cache_dir, refresh_days=0, years=1)
        except Exception:
            # We expect this to fail during save, but we only care about the fetch call
            pass
        
        # Verify that _fetch_symbol_data was called with the .NS suffix
        mock_fetch.assert_called_once_with("BPCL.NS", 1)

    @patch('kiss_signal.data._fetch_symbol_data')
    def test_get_price_data_preserves_index_symbols(self, mock_fetch, temp_cache_dir):
        """Test that get_price_data preserves index symbols like ^NSEI without adding .NS suffix."""
        # Setup: no cache file exists, so it will try to fetch fresh data
        mock_fetch.return_value = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'open': [18000, 18100],
            'high': [18200, 18300],
            'low': [17800, 17900],
            'close': [18050, 18150],
            'volume': [1000000, 1100000]
        })
        
        # Call get_price_data with an index symbol
        try:
            data.get_price_data("^NSEI", temp_cache_dir, refresh_days=0, years=1)
        except Exception:
            # We expect this to fail during save, but we only care about the fetch call
            pass
        
        # Verify that _fetch_symbol_data was called with the original symbol (no .NS suffix)
        mock_fetch.assert_called_once_with("^NSEI", 1)

    def test_get_price_data_position_tracking_no_warning(self, temp_cache_dir, caplog):
        """Test that get_price_data does NOT log warning during position tracking (start_date and end_date specified)."""
        # Create limited data that would normally trigger a warning
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),  # Only 5 rows (< 50)
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test position tracking scenario (both start_date and end_date specified)
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 2),  # Filter to even smaller range
                end_date=date(2023, 1, 4)
            )
            
            # Should have 3 rows (2023-01-02, 2023-01-03, 2023-01-04)
            assert len(result) == 3
            
            # Should NOT have WARNING message in logs
            assert "Limited data for TESTSTOCK" not in caplog.text
            
            # Should have DEBUG message instead (though we're testing at WARNING level)
            # Let's test at DEBUG level to verify the DEBUG message exists
            
        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 2),
                end_date=date(2023, 1, 4)
            )
            
            # Should have DEBUG message for position tracking
            assert "Position tracking data for TESTSTOCK: 3 rows from 2023-01-02 to 2023-01-04" in caplog.text

    def test_get_price_data_regular_loading_still_warns(self, temp_cache_dir, caplog):
        """Test that get_price_data still logs warning for limited data during regular loading (no date filters)."""
        # Create limited data that should trigger a warning
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),  # Only 5 rows (< 50)
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test regular loading (no start_date or end_date)
            caplog.clear()
            result = data.get_price_data("TESTSTOCK", temp_cache_dir)
            
            assert len(result) == 5
            # Should have WARNING message for limited data
            assert "Limited data for TESTSTOCK: only 5 rows" in caplog.text

    def test_get_price_data_position_tracking_with_only_start_date_warns(self, temp_cache_dir, caplog):
        """Test that get_price_data warns when only start_date is specified (not position tracking)."""
        # Create limited data that should trigger a warning
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),  # Only 5 rows (< 50)
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test with only start_date (not position tracking)
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 2)  # Only start_date, no end_date
            )
            
            assert len(result) == 4  # 2023-01-02 to 2023-01-05
            # Should have WARNING message since it's not position tracking
            assert "Limited data for TESTSTOCK: only 4 rows" in caplog.text

    def test_get_price_data_position_tracking_with_only_end_date_warns(self, temp_cache_dir, caplog):
        """Test that get_price_data warns when only end_date is specified (not position tracking)."""
        # Create limited data that should trigger a warning
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),  # Only 5 rows (< 50)
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test with only end_date (not position tracking)
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                end_date=date(2023, 1, 3)  # Only end_date, no start_date
            )
            
            assert len(result) == 3  # 2023-01-01 to 2023-01-03
            # Should have WARNING message since it's not position tracking
            assert "Limited data for TESTSTOCK: only 3 rows" in caplog.text

    def test_get_price_data_sufficient_data_no_warning(self, temp_cache_dir, caplog):
        """Test that get_price_data does not warn when there's sufficient data (>= 50 rows)."""
        # Create sufficient data (>= 50 rows)
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=60)),  # 60 rows (>= 50)
            'open': range(100, 160), 
            'high': range(105, 165), 
            'low': range(95, 155), 
            'close': range(102, 162),
            'volume': range(1000, 1060)
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        with caplog.at_level(logging.WARNING):
            # Test regular loading with sufficient data
            caplog.clear()
            result = data.get_price_data("TESTSTOCK", temp_cache_dir)
            
            assert len(result) == 60
            # Should NOT have any warning
            assert "Limited data for TESTSTOCK" not in caplog.text

            # Test position tracking with sufficient data
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 1),
                end_date=date(2023, 2, 28)  # Will get 59 rows (Jan 1-31 + Feb 1-28)
            )
            
            assert len(result) == 59
            # Should NOT have any warning
            assert "Limited data for TESTSTOCK" not in caplog.text

    def test_get_price_data_position_tracking_uses_debug_not_warning(self, temp_cache_dir, caplog):
        """Test that position tracking with limited data shows DEBUG message, not WARNING."""
        # Create test data with only a few rows
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        # Test position tracking scenario (both start_date and end_date specified)
        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 2),  # Will filter to even fewer rows
                end_date=date(2023, 1, 4)
            )
            
            # Should have limited data (3 rows: Jan 2, 3, 4)
            assert len(result) == 3
            
            # Should NOT have WARNING message
            assert "Limited data for TESTSTOCK" not in caplog.text
            
            # Should have DEBUG message for position tracking
            assert "Position tracking data for TESTSTOCK: 3 rows from 2023-01-02 to 2023-01-04" in caplog.text

    def test_get_price_data_limited_data_still_warns_for_regular_loading(self, temp_cache_dir, caplog):
        """Test that regular data loading with limited data still shows WARNING."""
        # Create test data with only a few rows
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        # Test regular loading (no start_date/end_date filters)
        with caplog.at_level(logging.WARNING):
            caplog.clear()
            result = data.get_price_data("TESTSTOCK", temp_cache_dir)
            
            # Should have all 5 rows (which is < 50)
            assert len(result) == 5
            
            # Should have WARNING message for insufficient data
            assert "Limited data for TESTSTOCK: only 5 rows" in caplog.text

    def test_get_price_data_position_tracking_with_start_date_only_still_warns(self, temp_cache_dir, caplog):
        """Test that only specifying start_date (not position tracking) still shows WARNING."""
        # Create test data with only a few rows
        test_data = pd.DataFrame({
            'date': pd.to_datetime(pd.date_range('2023-01-01', periods=5)),
            'open': [100, 101, 102, 103, 104], 
            'high': [105, 106, 107, 108, 109], 
            'low': [95, 96, 97, 98, 99], 
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        data._save_symbol_cache("TESTSTOCK", test_data, temp_cache_dir)
        
        # Test with only start_date (not position tracking)
        with caplog.at_level(logging.WARNING):
            caplog.clear()
            result = data.get_price_data(
                "TESTSTOCK", 
                temp_cache_dir, 
                start_date=date(2023, 1, 3)  # Only start_date, no end_date
            )
            
            # Should have limited data (3 rows: Jan 3, 4, 5)
            assert len(result) == 3
            
            # Should have WARNING message (not position tracking)
            assert "Limited data for TESTSTOCK: only 3 rows" in caplog.text