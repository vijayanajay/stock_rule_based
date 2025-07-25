"""
Test for the ATR exit functions API mismatch fix.

This test ensures that ATR exit functions (stop_loss_atr, take_profit_atr) 
are properly skipped during signal generation since they require entry_price 
parameter which is not available in that context.
"""

import pytest
import pandas as pd
from src.kiss_signal.reporter import _find_signals_in_window


class TestATRExitFunctionsFix:
    """Test the fix for ATR exit functions API mismatch in signal generation."""

    def test_atr_exit_functions_skipped_in_signal_generation(self):
        """Test that ATR exit functions are properly skipped during signal generation."""
        # Create sample price data
        price_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
        
        # Rule stack that includes ATR exit functions (would previously fail)
        rule_stack_defs = [
            {
                'type': 'engulfing_pattern',
                'params': {}
            },
            {
                'type': 'stop_loss_atr',  # Exit function, should be skipped
                'params': {'period': 14, 'multiplier': 2.0}
            },
            {
                'type': 'take_profit_atr',  # Exit function, should be skipped
                'params': {'period': 14, 'multiplier': 4.0}
            }
        ]
        
        # This should not raise an exception (ATR functions are skipped)
        signals = _find_signals_in_window(price_data, rule_stack_defs)
        
        # Should return a valid boolean series
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(price_data)
        assert signals.dtype == bool
        
    def test_only_atr_exit_functions_returns_no_signals(self):
        """Test that a rule stack with only ATR exit functions returns no signals."""
        # Create sample price data
        price_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        # Rule stack with only ATR exit functions
        rule_stack_defs = [
            {
                'type': 'stop_loss_atr',
                'params': {'period': 14, 'multiplier': 2.0}
            },
            {
                'type': 'take_profit_atr',
                'params': {'period': 14, 'multiplier': 4.0}
            }
        ]
        
        # Should return all False signals since all rules are skipped
        signals = _find_signals_in_window(price_data, rule_stack_defs)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(price_data)
        assert signals.dtype == bool
        assert not signals.any()  # All signals should be False
        
    def test_mixed_rule_stack_with_atr_functions(self):
        """Test that mixed rule stacks work correctly when ATR functions are present."""
        # Create sample price data
        price_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        # Mixed rule stack: entry signals + ATR exit functions
        rule_stack_defs = [
            {
                'type': 'engulfing_pattern',  # Entry signal
                'params': {}
            },
            {
                'type': 'stop_loss_atr',  # Exit function, should be skipped
                'params': {'period': 14, 'multiplier': 2.0}
            },
            {
                'type': 'rsi_oversold',  # Entry signal
                'params': {'period': 14, 'threshold': 30}
            },
            {
                'type': 'take_profit_atr',  # Exit function, should be skipped
                'params': {'period': 14, 'multiplier': 4.0}
            }
        ]
        
        # Should work and only process the entry signal functions
        signals = _find_signals_in_window(price_data, rule_stack_defs)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(price_data)
        assert signals.dtype == bool
        # The result should be the AND of engulfing_pattern and rsi_oversold only
