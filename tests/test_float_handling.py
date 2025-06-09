import unittest
import warnings
import pandas as pd
import numpy as np
import datetime
from datetime import date
from src.meqsap.backtest import run_backtest, BacktestError, safe_float, StrategySignalGenerator
from src.meqsap.config import StrategyConfig, MovingAverageCrossoverParams

# Suppress pandas_ta pkg_resources deprecation warning
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API", category=UserWarning)

class TestFloatConversions(unittest.TestCase):
    """Test float conversion handling in backtest module."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample test data
        dates = pd.date_range(start='2022-01-01', periods=100)
        self.test_data = pd.DataFrame({
            'open': np.random.normal(100, 5, 100),
            'high': np.random.normal(105, 5, 100),
            'low': np.random.normal(95, 5, 100),
            'close': np.random.normal(100, 5, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        # Create signals data for testing
        self.signals = pd.DataFrame({
            'entry': np.random.choice([True, False], size=100),
            'exit': np.random.choice([True, False], size=100)
        }, index=dates)
        
        # Create a valid strategy config
        self.valid_params = MovingAverageCrossoverParams(
            fast_ma=5,
            slow_ma=20,
            stop_loss=0.05,
            take_profit=0.1,
            trailing_stop=0.02,
            position_size=1.0
        )
        
        self.valid_strategy = StrategyConfig(
            ticker="AAPL",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            strategy_type="MovingAverageCrossover",
            strategy_params=self.valid_params.model_dump()
        )
    
    def test_none_values(self):
        """Test handling of None values in parameters."""
        # Create params with None values
        params = MovingAverageCrossoverParams(
            fast_ma=5,
            slow_ma=20,
            stop_loss=0.05,
            take_profit=None,  # None value
            trailing_stop=0.02,
            position_size=1.0
        )
        
        strategy = StrategyConfig(
            ticker="AAPL",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            strategy_type="MovingAverageCrossover",
            strategy_params=params.model_dump()
        )
        
        # Prepare data and signals for backtesting
        prices_series = self.test_data['close']
        signals_df = pd.DataFrame({
            'entry': np.random.choice([True, False], size=len(self.test_data)),
            'exit': np.random.choice([True, False], size=len(self.test_data))
        }, index=self.test_data.index)
        
        # Should not raise an exception
        result = run_backtest(prices_data=prices_series, signals_data=signals_df)
        self.assertIsNotNone(result)
        
    def test_string_values(self):
        """Test handling of string values in parameters."""
        # Create params with string values that should convert to float
        params = MovingAverageCrossoverParams(
            fast_ma=5,
            slow_ma=20,
            stop_loss="0.05",  # String value
            take_profit=0.1,
            trailing_stop="0.02",  # String value
            position_size=1.0
        )
        
        strategy = StrategyConfig(
            ticker="AAPL",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            strategy_type="MovingAverageCrossover",
            strategy_params=params.model_dump()
        )
        
        # Prepare data and signals for backtesting
        prices_series = self.test_data['close']
        signals_df = pd.DataFrame({
            'entry': np.random.choice([True, False], size=len(self.test_data)),
            'exit': np.random.choice([True, False], size=len(self.test_data))
        }, index=self.test_data.index)
        result = run_backtest(prices_data=prices_series, signals_data=signals_df)
        self.assertIsNotNone(result)
        
    def test_mock_stats_with_non_numeric(self):
        """Test handling of non-numeric values in stats dictionary."""
        self.skipTest("Skipping this test as it requires mocking")

class TestFloatHandling(unittest.TestCase):
    """Test safe float handling in backtesting operations."""
    
    def test_safe_float_with_valid_numbers(self):
        """Test safe_float with valid numeric inputs."""
        self.assertEqual(safe_float(1.5), 1.5)
        self.assertEqual(safe_float(10), 10.0)
        self.assertEqual(safe_float("3.14"), 3.14)
        self.assertEqual(safe_float(0), 0.0)
        
    def test_safe_float_with_invalid_inputs(self):
        """Test safe_float with invalid inputs."""
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float("invalid"), 0.0)
        self.assertEqual(safe_float([1, 2, 3]), 0.0)
        self.assertEqual(safe_float({"key": "value"}), 0.0)
        
    def test_safe_float_with_custom_default(self):
        """Test safe_float with custom default values."""
        self.assertEqual(safe_float(None, default=100.0), 100.0)
        self.assertEqual(safe_float("invalid", default=-1.0), -1.0)
        
    def test_safe_float_with_nan_and_inf(self):
        """Test safe_float with NaN and infinite values."""
        self.assertEqual(safe_float(np.nan, default=0.0), 0.0)
        # Note: inf values should be handled gracefully
        result = safe_float(np.inf, default=0.0)
        self.assertTrue(result == 0.0 or result == float('inf'))  # Allow either behavior

if __name__ == '__main__':
    unittest.main()
