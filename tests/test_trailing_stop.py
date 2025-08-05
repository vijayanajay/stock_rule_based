#!/usr/bin/env python3
"""Test script to verify simple_trailing_stop function works."""

import sys
sys.path.append('src')

from kiss_signal import rules
import pandas as pd

def test_simple_trailing_stop():
    """Test the simple_trailing_stop function implementation."""
    # Test data - price goes up then comes down
    test_data = pd.DataFrame({
        'close': [100, 105, 110, 115, 120, 115, 110, 105, 100, 95],
        'high': [101, 106, 111, 116, 121, 116, 111, 106, 101, 96],
        'low': [99, 104, 109, 114, 119, 114, 109, 104, 99, 94],
        'open': [100, 105, 110, 115, 120, 115, 110, 105, 100, 95],
        'volume': [1000] * 10
    })

    print('Testing simple_trailing_stop function...')
    print(f'Test data shape: {test_data.shape}')
    print(f'Close prices: {list(test_data["close"])}')
    
    # Test the function
    result = rules.simple_trailing_stop(test_data, trail_percent=0.05)
    print(f'✅ Function exists and works: {type(result)}, length: {len(result)}')
    print(f'Exit signals: {result.sum()} out of {len(result)} bars')
    print(f'Exit signal locations: {list(result[result].index)}')
    print(f'Exit signals by bar: {list(result)}')
    
    # Calculate what the trailing stop should be
    high_water_mark = test_data['close'].expanding().max()
    trailing_stop_price = high_water_mark * (1 - 0.05)
    print(f'High water marks: {list(high_water_mark)}')
    print(f'Trailing stop prices: {list(trailing_stop_price.round(2))}')
    
    # Assertions for proper testing
    assert isinstance(result, pd.Series), "Result should be a pandas Series"
    assert len(result) == len(test_data), "Result should have same length as input data"
    assert result.sum() > 0, "Should generate some exit signals for this test data"
    
    # Test that exit signals are properly triggered when price drops below trailing stop
    # At index 6 (price=110), trailing stop is 114, so 110 < 114 = True (exit signal)
    assert result.iloc[6] == True, "Should trigger exit signal when price drops below trailing stop"

if __name__ == "__main__":
    test_simple_trailing_stop()
    print(f'\nTest completed successfully!')
