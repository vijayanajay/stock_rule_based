"""Test to ensure pandas downcasting FutureWarning is fixed.

This test verifies that the backtester module properly handles pandas downcasting
without generating FutureWarnings for fillna, ffill, and bfill operations.
"""

import warnings
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kiss_signal.backtester import Backtester
from kiss_signal.config import RulesConfig, RuleDef


class TestPandasDowncastingFix:
    """Test class for pandas downcasting fix."""

    def test_no_future_warnings_on_import(self):
        """Test that importing backtester module doesn't generate FutureWarnings."""
        # Capture all warnings during import
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Re-import the module to test warning behavior
            import importlib
            from kiss_signal import backtester
            importlib.reload(backtester)
            
            # Check that no FutureWarnings related to downcasting were raised
            future_warnings = [warning for warning in w 
                             if issubclass(warning.category, FutureWarning) 
                             and "downcasting" in str(warning.message).lower()]
            
            assert len(future_warnings) == 0, f"Found unexpected FutureWarnings: {future_warnings}"

    def test_apply_context_filters_no_warnings(self):
        """Test that _apply_context_filters method doesn't generate FutureWarnings."""
        # Create test data
        stock_data = pd.DataFrame({
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100 + 5,
            'low': np.random.rand(100) * 100 - 5,
            'close': np.random.rand(100) * 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=pd.date_range('2023-01-01', periods=100))
        
        # Mock context filter definition
        filter_def = Mock()
        filter_def.type = "market_above_sma"
        filter_def.name = "test_filter"
        filter_def.params = {"index_symbol": "^NSEI", "period": 20}
        
        # Create backtester instance
        backtester = Backtester()
        
        # Mock the market data cache method to return test data
        backtester._market_cache = {
            "^NSEI": pd.DataFrame({
                'close': np.random.rand(120) * 100
            }, index=pd.date_range('2022-12-01', periods=120))
        }
        
        # Mock the rules module function
        import kiss_signal.rules as rules
        original_market_above_sma = getattr(rules, 'market_above_sma', None)
        
        def mock_market_above_sma(data, period=20):
            # Return a boolean series with some random pattern
            return pd.Series(np.random.choice([True, False], len(data)), index=data.index)
        
        rules.market_above_sma = mock_market_above_sma
        
        try:
            # Capture warnings during the actual method call
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Call the method that previously generated warnings
                result = backtester._apply_context_filters(
                    stock_data, [filter_def], "TEST"
                )
                
                # Check that no FutureWarnings about downcasting were raised
                future_warnings = [warning for warning in w 
                                 if issubclass(warning.category, FutureWarning) 
                                 and ("downcasting" in str(warning.message).lower() 
                                     or "fillna" in str(warning.message).lower()
                                     or "ffill" in str(warning.message).lower())]
                
                assert len(future_warnings) == 0, f"Found unexpected FutureWarnings: {future_warnings}"
                
                # Verify the method still works correctly
                assert isinstance(result, pd.Series)
                assert len(result) == len(stock_data)
                assert result.dtype == bool
        
        finally:
            # Restore original function if it existed
            if original_market_above_sma is not None:
                rules.market_above_sma = original_market_above_sma
            elif hasattr(rules, 'market_above_sma'):
                delattr(rules, 'market_above_sma')

    def test_pandas_option_is_set(self):
        """Test that the pandas option for future downcasting behavior is enabled."""
        # Check that the pandas option was set correctly
        option_value = pd.get_option('future.no_silent_downcasting')
        assert option_value is True, "pandas option 'future.no_silent_downcasting' should be True"

    def test_fillna_operations_no_warnings(self):
        """Test specific fillna operations that previously caused warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Create test series that would trigger the warning
            test_series = pd.Series([True, False, np.nan, True, False])
            
            # Perform operations that previously caused warnings
            result1 = test_series.ffill().fillna(False).infer_objects(copy=False)
            result2 = test_series.reindex(range(10)).ffill().fillna(False).infer_objects(copy=False)
            
            # Check for FutureWarnings
            future_warnings = [warning for warning in w 
                             if issubclass(warning.category, FutureWarning) 
                             and "downcasting" in str(warning.message).lower()]
            
            assert len(future_warnings) == 0, f"Found unexpected FutureWarnings: {future_warnings}"
            
            # Verify results are correct
            assert isinstance(result1, pd.Series)
            assert isinstance(result2, pd.Series)

    def test_backtester_integration_no_warnings(self):
        """Integration test to ensure full backtester workflow doesn't generate warnings."""
        # Create minimal test configuration
        baseline = RuleDef(name="test_rule", type="sma_crossover", params={"fast_period": 5, "slow_period": 10})
        rules_config = RulesConfig(
            baseline=baseline,
            layers=[],
            context_filters=[
                RuleDef(name="market_filter", type="market_above_sma", 
                       params={"index_symbol": "^NSEI", "period": 20})
            ],
            sell_conditions=[]
        )
        
        # Create test price data
        price_data = pd.DataFrame({
            'open': np.random.rand(50) * 100,
            'high': np.random.rand(50) * 100 + 5,
            'low': np.random.rand(50) * 100 - 5,
            'close': np.random.rand(50) * 100,
            'volume': np.random.randint(1000, 10000, 50)
        }, index=pd.date_range('2023-01-01', periods=50, freq='D'))
        
        backtester = Backtester(min_trades_threshold=1)  # Lower threshold for test
        
        # Mock market data
        backtester._market_cache = {
            "^NSEI": pd.DataFrame({
                'close': np.random.rand(60) * 100
            }, index=pd.date_range('2022-12-01', periods=60, freq='D'))
        }
        
        # Mock rules functions to avoid import issues
        import kiss_signal.rules as rules
        original_functions = {}
        
        def mock_sma_crossover(data, fast_period=5, slow_period=10):
            return pd.Series(np.random.choice([True, False], len(data), p=[0.1, 0.9]), index=data.index)
        
        def mock_market_above_sma(data, period=20):
            return pd.Series(np.random.choice([True, False], len(data), p=[0.5, 0.5]), index=data.index)
        
        # Store and replace functions
        for func_name in ['sma_crossover', 'market_above_sma']:
            if hasattr(rules, func_name):
                original_functions[func_name] = getattr(rules, func_name)
        
        rules.sma_crossover = mock_sma_crossover
        rules.market_above_sma = mock_market_above_sma
        
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Run the backtester - this calls _apply_context_filters internally
                strategies = backtester.find_optimal_strategies(
                    price_data=price_data,
                    rules_config=rules_config,
                    symbol="TEST"
                )
                
                # Check for FutureWarnings about downcasting
                future_warnings = [warning for warning in w 
                                 if issubclass(warning.category, FutureWarning) 
                                 and ("downcasting" in str(warning.message).lower()
                                     or "fillna" in str(warning.message).lower()
                                     or "ffill" in str(warning.message).lower())]
                
                assert len(future_warnings) == 0, f"Found unexpected FutureWarnings: {future_warnings}"
                
                # Verify backtester still works
                assert isinstance(strategies, list)
        
        finally:
            # Restore original functions
            for func_name, original_func in original_functions.items():
                setattr(rules, func_name, original_func)
            
            # Clean up mock functions
            for func_name in ['sma_crossover', 'market_above_sma']:
                if func_name not in original_functions and hasattr(rules, func_name):
                    delattr(rules, func_name)
