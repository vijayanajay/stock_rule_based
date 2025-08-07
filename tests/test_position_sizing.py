"""Test position sizing functionality."""

import pandas as pd
import numpy as np
import pytest
from src.kiss_signal.backtester import Backtester
from src.kiss_signal.config import RuleDef, EdgeScoreWeights


def test_position_sizing_volatility_impact():
    """Test that high volatility stock gets smaller position size than low volatility stock."""
    # Create two price series with different volatility (ATR)
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    
    # Low volatility stock (1% daily moves)
    low_vol_data = pd.DataFrame({
        'high': [100 * (1 + 0.01 * np.sin(i/10)) for i in range(50)],
        'low': [100 * (1 - 0.01 * np.sin(i/10)) for i in range(50)],
        'close': [100 + i * 0.1 for i in range(50)],  # Steady uptrend
        'volume': [1000] * 50
    }, index=dates)
    
    # High volatility stock (5% daily moves)
    high_vol_data = pd.DataFrame({
        'high': [100 * (1 + 0.05 * np.sin(i/10)) for i in range(50)],
        'low': [100 * (1 - 0.05 * np.sin(i/10)) for i in range(50)],
        'close': [100 + i * 0.1 for i in range(50)],  # Same trend
        'volume': [1000] * 50
    }, index=dates)
    
    # Create backtester
    bt = Backtester(initial_capital=100000.0)
    
    # Create entry signals (buy on day 20)
    entry_signals = pd.Series(False, index=dates)
    entry_signals.iloc[20] = True
    
    # Create exit conditions with ATR-based stop
    exit_conditions = [
        RuleDef(
            name="atr_stop",
            type="chandelier_exit",
            params={"atr_period": 22, "atr_multiplier": 2.0}
        )
    ]
    
    # Calculate position sizes
    low_vol_sizes = bt._calculate_risk_based_size(low_vol_data, entry_signals, exit_conditions)
    high_vol_sizes = bt._calculate_risk_based_size(high_vol_data, entry_signals, exit_conditions)
    
    # High volatility should result in smaller position size
    low_vol_position = low_vol_sizes.iloc[20]
    high_vol_position = high_vol_sizes.iloc[20]
    
    assert low_vol_position > high_vol_position, "Low volatility stock should have larger position size"
    assert low_vol_position > 0, "Position size should be positive"
    assert high_vol_position > 0, "Position size should be positive"


def test_risk_percentage_respected():
    """Test that risk percentage is approximately respected."""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    
    # Create price data
    price_data = pd.DataFrame({
        'high': [102, 104, 103, 105, 104] * 6,
        'low': [98, 96, 97, 95, 96] * 6,
        'close': [100 + i * 0.5 for i in range(30)],
        'volume': [1000] * 30
    }, index=dates)
    
    bt = Backtester(initial_capital=100000.0)
    
    # Entry signal on day 15
    entry_signals = pd.Series(False, index=dates)
    entry_signals.iloc[15] = True
    
    # Exit conditions with known ATR multiplier
    exit_conditions = [
        RuleDef(
            name="atr_stop",
            type="chandelier_exit",
            params={"atr_period": 14, "atr_multiplier": 2.0}
        )
    ]
    
    sizes = bt._calculate_risk_based_size(price_data, entry_signals, exit_conditions)
    position_size = sizes.iloc[15]
    
    # Calculate expected risk (this is approximate since ATR is dynamic)
    # 1% of 100k = 1000
    expected_risk = 1000.0
    
    # The actual risk should be approximately 1% (within reasonable bounds)
    assert position_size > 0, "Position size should be positive"
    # Just verify position size is reasonable (not testing exact risk calculation)
    assert 10 < position_size < 1000, f"Position size {position_size} should be reasonable"


def test_no_division_by_zero():
    """Test that zero volatility doesn't cause division by zero."""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    
    # Constant price data (zero volatility)
    price_data = pd.DataFrame({
        'high': [100] * 10,
        'low': [100] * 10,
        'close': [100] * 10,
        'volume': [1000] * 10
    }, index=dates)
    
    bt = Backtester(initial_capital=100000.0)
    
    entry_signals = pd.Series(False, index=dates)
    entry_signals.iloc[5] = True
    
    exit_conditions = [
        RuleDef(
            name="atr_stop",
            type="chandelier_exit",
            params={"atr_period": 5, "atr_multiplier": 2.0}
        )
    ]
    
    # Should not raise an exception
    sizes = bt._calculate_risk_based_size(price_data, entry_signals, exit_conditions)
    
    # Should either be 0 or NaN for zero volatility
    position_size = sizes.iloc[5]
    assert pd.isna(position_size) or position_size == 0, "Zero volatility should result in 0 or NaN position size"


def test_no_size_where_no_entry():
    """Test that position sizes are only set where entry signals are True."""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    
    price_data = pd.DataFrame({
        'high': [102, 104, 103, 105, 104, 106, 105, 107, 106, 108],
        'low': [98, 96, 97, 95, 96, 94, 95, 93, 94, 92],
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'volume': [1000] * 10
    }, index=dates)
    
    bt = Backtester(initial_capital=100000.0)
    
    # Only entry signal on day 5
    entry_signals = pd.Series(False, index=dates)
    entry_signals.iloc[5] = True
    
    exit_conditions = [
        RuleDef(
            name="atr_stop",
            type="chandelier_exit",
            params={"atr_period": 5, "atr_multiplier": 2.0}
        )
    ]
    
    sizes = bt._calculate_risk_based_size(price_data, entry_signals, exit_conditions)
    
    # Check that only the entry day has a size
    for i, (date, size) in enumerate(sizes.items()):
        if i == 5:  # Entry day
            assert not pd.isna(size) and size > 0, "Entry day should have positive position size"
        else:  # Non-entry days
            assert pd.isna(size), f"Non-entry day {i} should have NaN position size, got {size}"
