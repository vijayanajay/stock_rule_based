"""Test for index_symbol parameter filtering bug fix in reporter module.

This test validates that the reporter properly filters out the index_symbol parameter
when calling rule functions, preventing the "unexpected keyword argument" error.
"""
import pandas as pd
import pytest
from unittest.mock import patch

from src.kiss_signal import reporter


class TestIndexSymbolParameterFiltering:
    """Test index_symbol parameter filtering in reporter module."""
    
    def test_find_signals_filters_index_symbol_parameter(self):
        """Test that _find_signals_in_window filters out index_symbol parameter."""
        # Create test price data
        price_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1000, 1000]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        # Rule definition with index_symbol parameter (should be filtered out)
        rule_stack_defs = [{
            'type': 'market_above_sma',
            'params': {
                'index_symbol': '^NSEI',  # This should be filtered out
                'period': 20              # This should be passed through
            }
        }]
        
        # Mock the market_above_sma function to verify correct parameters
        with patch('src.kiss_signal.rules.market_above_sma') as mock_market_above_sma:
            mock_market_above_sma.return_value = pd.Series([True, False, True], index=price_data.index)
            
            # Call the function that should filter parameters
            result = reporter._find_signals_in_window(price_data, rule_stack_defs)
            
            # Verify the function was called with correct parameters (index_symbol filtered out)
            mock_market_above_sma.assert_called_once_with(price_data, period=20)
            
            # Verify the result is as expected
            assert isinstance(result, pd.Series)
            assert len(result) == 3
            assert result.dtype == bool
    
    def test_find_signals_preserves_valid_parameters(self):
        """Test that valid parameters are preserved and converted correctly."""
        price_data = pd.DataFrame({
            'close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        # Rule definition with mixed parameter types
        rule_stack_defs = [{
            'type': 'sma_crossover',
            'params': {
                'fast_period': '5',    # String number (should be converted to int)
                'slow_period': 20,     # Already int (should be preserved)
                'threshold': '1.5',    # String float (should be converted to float)
                'name': 'test'         # String non-number (should be preserved as string)
            }
        }]
        
        with patch('src.kiss_signal.rules.sma_crossover') as mock_sma_crossover:
            mock_sma_crossover.return_value = pd.Series([False, True, False], index=price_data.index)
            
            result = reporter._find_signals_in_window(price_data, rule_stack_defs)
            
            # Verify correct parameter conversion and passing
            mock_sma_crossover.assert_called_once_with(
                price_data,
                fast_period=5,      # Converted from string
                slow_period=20,     # Preserved as int
                threshold=1.5,      # Converted from string to float
                name='test'         # Preserved as string
            )
    
    def test_find_signals_handles_multiple_rules_with_index_symbol(self):
        """Test that index_symbol is filtered from multiple rules."""
        price_data = pd.DataFrame({
            'close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        rule_stack_defs = [
            {
                'type': 'market_above_sma',
                'params': {
                    'index_symbol': '^NSEI',  # Should be filtered
                    'period': 50
                }
            },
            {
                'type': 'price_above_sma',
                'params': {
                    'period': 20
                }
            }
        ]
        
        with patch('src.kiss_signal.rules.market_above_sma') as mock_market_sma, \
             patch('src.kiss_signal.rules.price_above_sma') as mock_price_sma:
            
            # Mock return values
            mock_market_sma.return_value = pd.Series([True, True, False], index=price_data.index)
            mock_price_sma.return_value = pd.Series([True, False, True], index=price_data.index)
            
            result = reporter._find_signals_in_window(price_data, rule_stack_defs)
            
            # Verify both functions called with correct parameters
            mock_market_sma.assert_called_once_with(price_data, period=50)
            mock_price_sma.assert_called_once_with(price_data, period=20)
            
            # Result should be AND of both signals: [True & True, True & False, False & True] = [True, False, False]
            expected = pd.Series([True, False, False], index=price_data.index)
            pd.testing.assert_series_equal(result, expected)
    
    def test_find_signals_error_handling_with_invalid_function(self):
        """Test error handling when rule function doesn't exist."""
        price_data = pd.DataFrame({
            'close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        rule_stack_defs = [{
            'type': 'nonexistent_rule',
            'params': {
                'index_symbol': '^NSEI',
                'period': 20
            }
        }]
        
        # Should handle AttributeError gracefully
        result = reporter._find_signals_in_window(price_data, rule_stack_defs)
        
        # Should return all False values
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        assert not result.any()  # All values should be False
