"""
Test cases for Story 019: Context Filter Implementation

These tests are designed to integrate with the existing test suite
and verify the context filter functionality works correctly.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

from src.kiss_signal.data import get_price_data


def _save_market_cache_compat(data: pd.DataFrame, cache_file: Path) -> None:
    """Compatibility wrapper for old _save_market_cache function."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure data has 'date' as column, not index
        if data.index.name == 'date' or isinstance(data.index, pd.DatetimeIndex):
            data_to_save = data.reset_index()
            if data_to_save.columns[0] != 'date':
                data_to_save = data_to_save.rename(columns={data_to_save.columns[0]: 'date'})
        else:
            data_to_save = data.copy()
        
        # Remove any unwanted index columns
        if 'index' in data_to_save.columns and 'date' in data_to_save.columns:
            data_to_save = data_to_save.drop(columns=['index'])
            
        data_to_save.to_csv(cache_file, index=False)
    except Exception as e:
        raise RuntimeError(f"Failed to save market cache: {e}")


def _load_market_cache_compat(cache_file: Path) -> pd.DataFrame:
    """Compatibility wrapper for old _load_market_cache function."""
    try:
        data = pd.read_csv(cache_file)
        
        # Standardize to date column + datetime index format
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'], errors='coerce')
            data = data.dropna(subset=['date']).set_index('date')
        elif 'index' in data.columns:
            # Handle case where reset_index created 'index' column
            data['date'] = pd.to_datetime(data['index'], errors='coerce') 
            data = data.drop(columns=['index']).dropna(subset=['date']).set_index('date')
        else:
            # Fallback: try to parse first column as date
            data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Ensure index is properly DatetimeIndex and handle duplicates
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index, errors='coerce')
            data = data.dropna()
        
        # Remove duplicate index entries
        if data.index.duplicated().any():
            data = data[~data.index.duplicated(keep='last')]
        
        # Enforce lowercase column names for consistency
        data.columns = [str(col).lower() for col in data.columns]
        
        if data.empty:
            raise ValueError(f"No valid data found in cache")
            
    except Exception as e:
        raise ValueError(f"Corrupted cache file: {cache_file}") from e
    
    return data
from src.kiss_signal.backtester import Backtester
from src.kiss_signal.config import RuleDef, RulesConfig, EdgeScoreWeights


class TestContextFilterIntegration(unittest.TestCase):
    """Test context filter integration with the existing system."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache_dir = Path("test_cache")
        
        # Create realistic test data
        self.stock_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000]
        }, index=pd.date_range('2024-01-01', periods=5, freq='D'))

        # Create uptrending market data
        self.market_data = pd.DataFrame({
            'open': [1000, 1010, 1020, 1030, 1040],
            'high': [1050, 1060, 1070, 1080, 1090],
            'low': [950, 960, 970, 980, 990],
            'close': [1040, 1050, 1060, 1070, 1080],
            'volume': [10000, 20000, 30000, 40000, 50000]
        }, index=pd.date_range('2024-01-01', periods=5, freq='D'))

    def test_get_price_data_basic_functionality(self):
        """Test basic get_price_data functionality for market indices."""
        with patch('src.kiss_signal.data._needs_refresh', return_value=True), \
             patch('src.kiss_signal.data._fetch_symbol_data', return_value=self.market_data) as mock_fetch, \
             patch('src.kiss_signal.data._save_cache') as mock_save, \
             patch.object(Path, 'exists', return_value=False):
            
            result = get_price_data("^NSEI", self.cache_dir, years=1)
            
            # Verify correct symbol passed to fetch
            mock_fetch.assert_called_once_with("^NSEI", 1, None)
            mock_save.assert_called_once()
            
            # Verify data structure
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 5)
            self.assertIn('close', result.columns)

    def test_market_cache_filename_pattern(self):
        """Test that market indices use INDEX_ prefix in cache files."""
        with patch('src.kiss_signal.data._needs_refresh', return_value=False), \
             patch('src.kiss_signal.data._load_cache', return_value=self.market_data) as mock_load, \
             patch.object(Path, 'exists', return_value=True):
            
            get_price_data("^NSEI", self.cache_dir)
            
            # Verify correct cache function called with symbol and cache_dir
            mock_load.assert_called_once_with("^NSEI", self.cache_dir)

    def test_backtester_apply_context_filters_integration(self):
        """Test backtester _apply_context_filters method integration."""
        backtester = Backtester()
        
        # Test with no context filters (backward compatibility)
        result = backtester._apply_context_filters(self.stock_data, [], "TEST")
        expected = pd.Series(True, index=self.stock_data.index)
        pd.testing.assert_series_equal(result, expected)

    def test_backtester_market_data_caching(self):
        """Test backtester market data caching mechanism."""
        backtester = Backtester()
        
        with patch('src.kiss_signal.data.get_price_data', return_value=self.market_data) as mock_get_data:
            
            # First call should fetch data
            result1 = backtester._get_market_data_cached("^NSEI")
            
            # Second call should use cache
            result2 = backtester._get_market_data_cached("^NSEI")
            
            # Verify data is same
            pd.testing.assert_frame_equal(result1, self.market_data)
            pd.testing.assert_frame_equal(result2, self.market_data)
            
            # Should only call get_price_data once
            self.assertEqual(mock_get_data.call_count, 1)

    def test_context_filter_with_market_above_sma(self):
        """Test context filter with market_above_sma rule type."""
        backtester = Backtester()
        
        context_filter = RuleDef(
            name="market_bullish",
            type="market_above_sma",
            params={"index_symbol": "^NSEI", "period": 3}
        )
        
        with patch.object(backtester, '_get_market_data_cached', return_value=self.market_data), \
             patch('src.kiss_signal.rules.market_above_sma') as mock_market_filter:
            
            # Mock market filter to return mixed results
            mock_filter_result = pd.Series([True, False, True, True, False], index=self.market_data.index)
            mock_market_filter.return_value = mock_filter_result
            
            result = backtester._apply_context_filters(
                self.stock_data, [context_filter], "TEST"
            )
            
            # Verify market_above_sma was called correctly
            mock_market_filter.assert_called_once_with(self.market_data, period=3)
            
            # Result should match the filter output
            expected = pd.Series([True, False, True, True, False], index=self.stock_data.index)
            pd.testing.assert_series_equal(result, expected)

    def test_context_filter_error_handling(self):
        """Test context filter error handling (fail-safe behavior)."""
        backtester = Backtester()
        
        context_filter = RuleDef(
            name="error_filter",
            type="market_above_sma",
            params={"index_symbol": "^NSEI", "period": 3}
        )
        
        with patch.object(backtester, '_get_market_data_cached', side_effect=Exception("Data error")):
            
            result = backtester._apply_context_filters(
                self.stock_data, [context_filter], "TEST"
            )
            
            # Should return all False on error (fail-safe)
            expected = pd.Series(False, index=self.stock_data.index)
            pd.testing.assert_series_equal(result, expected)

    def test_unknown_context_filter_type(self):
        """Test handling of unknown context filter types."""
        backtester = Backtester()
        
        unknown_filter = RuleDef(
            name="unknown_filter",
            type="unknown_type",
            params={"some_param": "value"}
        )
        
        result = backtester._apply_context_filters(
            self.stock_data, [unknown_filter], "TEST"
        )
        
        # Should return all False for unknown filter type (fail-safe)
        expected = pd.Series(False, index=self.stock_data.index)
        pd.testing.assert_series_equal(result, expected)

    def test_market_cache_save_load_cycle(self):
        """Test complete save/load cycle for market cache."""
        cache_file = Path("test_market_cache.csv")
        
        try:
            # Save test data
            _save_market_cache_compat(self.market_data, cache_file)
            self.assertTrue(cache_file.exists())
            
            # Load data back
            loaded_data = _load_market_cache_compat(cache_file)
            
            # Verify data integrity (allowing for index frequency differences)
            self.assertEqual(loaded_data.shape, self.market_data.shape)
            self.assertListEqual(list(loaded_data.columns), list(self.market_data.columns))
            
            # Check values are approximately equal (handle floating point precision and index frequency)
            for col in self.market_data.columns:
                pd.testing.assert_series_equal(
                    loaded_data[col], 
                    self.market_data[col], 
                    check_names=False,
                    check_index=False,
                    check_freq=False
                )
                
        finally:
            # Cleanup
            if cache_file.exists():
                cache_file.unlink()

    def test_freeze_mode_behavior(self):
        """Test get_price_data behavior in freeze mode for indices."""
        freeze_date = date(2024, 6, 1)
        
        # Test with existing cache
        with patch('src.kiss_signal.data._load_cache', return_value=self.market_data) as mock_load, \
             patch.object(Path, 'exists', return_value=True):
            
            result = get_price_data("^NSEI", self.cache_dir, freeze_date=freeze_date)
            mock_load.assert_called_once()
            pd.testing.assert_frame_equal(result, self.market_data)
        
        # Test without cache (should raise error)
        with patch.object(Path, 'exists', return_value=False):
            with self.assertRaises(FileNotFoundError) as context:
                get_price_data("^NSEI", self.cache_dir, freeze_date=freeze_date)
            
            self.assertIn("freeze mode", str(context.exception))

    def test_context_filter_parameter_extraction(self):
        """Test that context filter parameters are correctly extracted."""
        backtester = Backtester()
        
        context_filter = RuleDef(
            name="market_filter",
            type="market_above_sma",
            params={"index_symbol": "^NSEI", "period": 20, "extra_param": "ignored"}
        )
        
        with patch.object(backtester, '_get_market_data_cached', return_value=self.market_data), \
             patch('src.kiss_signal.rules.market_above_sma') as mock_market_filter:
            
            mock_market_filter.return_value = pd.Series(True, index=self.market_data.index)
            
            backtester._apply_context_filters(self.stock_data, [context_filter], "TEST")
            
            # Verify only valid parameters were passed (index_symbol excluded, extra_param ignored)
            call_args = mock_market_filter.call_args
            self.assertEqual(call_args[0][0].equals(self.market_data), True)  # market_data
            self.assertEqual(call_args[1], {"period": 20})  # Only period param


class TestRulesConfigContextFilters(unittest.TestCase):
    """Test RulesConfig integration with context filters."""

    def test_rules_config_loads_context_filters(self):
        """Test that RulesConfig can load context filters from YAML."""
        # This test assumes the rules.yaml has been updated with context filters
        from src.kiss_signal.config import load_rules
        
        try:
            rules = load_rules(Path('config/rules.yaml'))
            
            # Should load without error
            self.assertIsInstance(rules, RulesConfig)
            self.assertIsInstance(rules.context_filters, list)
            
            # If context filters are enabled, verify structure
            if rules.context_filters:
                first_filter = rules.context_filters[0]
                self.assertIsInstance(first_filter, RuleDef)
                self.assertIn('name', first_filter.model_dump())
                self.assertIn('type', first_filter.model_dump())
                self.assertIn('params', first_filter.model_dump())
                
        except Exception as e:
            self.fail(f"Failed to load rules with context filters: {e}")

    def test_backward_compatibility_empty_context_filters(self):
        """Test backward compatibility when context_filters is empty."""
        # Create minimal rules config
        baseline = RuleDef(name="test", type="sma_crossover", params={"fast_period": 5, "slow_period": 10})
        rules_config = RulesConfig(baseline=baseline)
        
        # Should have empty context_filters by default
        self.assertEqual(len(rules_config.context_filters), 0)
        self.assertIsInstance(rules_config.context_filters, list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
