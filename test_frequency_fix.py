#!/usr/bin/env python3
"""Quick test script to verify frequency fix."""

import pandas as pd
from src.kiss_signal.data import get_price_data
from pathlib import Path

def test_frequency_fix():
    """Test that frequency is properly set after data loading."""
    # Test frequency setting
    data = get_price_data('RELIANCE', Path('cache'))
    print(f'Index type: {type(data.index)}')
    print(f'Frequency: {data.index.freq}')
    print(f'Data shape: {data.shape}')
    print(f'First 3 dates: {data.index[:3].tolist()}')
    print(f'Last 3 dates: {data.index[-3:].tolist()}')
    
    # Test slicing (this should maintain frequency with our fix)
    sliced = data[-100:]
    print(f'\nAfter slicing:')
    print(f'Sliced frequency: {sliced.index.freq}')
    print(f'Sliced shape: {sliced.shape}')

if __name__ == "__main__":
    test_frequency_fix()
