#!/usr/bin/env python3
"""Debug hammer pattern detection issue."""

import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kiss_signal.rules import hammer_pattern

def debug_hammer():
    """Debug hammer pattern with test data."""
    
    # Test data from the failing test
    test_data = pd.DataFrame({
        'open': [100.0, 95.0, 99.5, 104.0],
        'high': [101, 96, 100, 105],
        'low': [99, 90, 98, 103],
        'close': [100.5, 94.5, 99.8, 104.2],
        'volume': [1000, 1200, 1100, 1050]
    })
    
    print("Test data:")
    print(test_data)
    print()
    
    # Focus on row 1 (expected hammer)
    row1 = test_data.iloc[1]
    print("Row 1 (expected hammer):")
    print(f"open: {row1['open']}, high: {row1['high']}, low: {row1['low']}, close: {row1['close']}")
    
    # Manual calculations
    body = abs(row1['close'] - row1['open'])
    total_range = row1['high'] - row1['low']
    lower_shadow = min(row1['open'], row1['close']) - row1['low']
    upper_shadow = row1['high'] - max(row1['open'], row1['close'])
    
    print(f"\nManual calculations for row 1:")
    print(f"body = |{row1['close']} - {row1['open']}| = {body}")
    print(f"total_range = {row1['high']} - {row1['low']} = {total_range}")
    print(f"lower_shadow = min({row1['open']}, {row1['close']}) - {row1['low']} = {lower_shadow}")
    print(f"upper_shadow = {row1['high']} - max({row1['open']}, {row1['close']}) = {upper_shadow}")
    
    # Test conditions with body_ratio=0.3, shadow_ratio=2.0
    body_ratio = 0.3
    shadow_ratio = 2.0
    
    print(f"\nHammer conditions (body_ratio={body_ratio}, shadow_ratio={shadow_ratio}):")
    print(f"1. Small body: {body} <= {body_ratio} * {total_range} = {body_ratio * total_range} -> {body <= (body_ratio * total_range)}")
    print(f"2. Long lower shadow: {lower_shadow} >= {shadow_ratio} * {body} = {shadow_ratio * body} -> {lower_shadow >= (shadow_ratio * body)}")
    print(f"3. Small upper shadow: {upper_shadow} <= {lower_shadow}/2.0 = {lower_shadow/2.0} -> {upper_shadow <= (lower_shadow/2.0)}")
    print(f"4. Has body: {body} > 0 -> {body > 0}")
    
    # Run actual function
    print(f"\nRunning hammer_pattern function:")
    signals = hammer_pattern(test_data, body_ratio=0.3, shadow_ratio=2.0)
    print(f"Signals: {signals.tolist()}")
    print(f"Row 1 signal: {signals.iloc[1]}")
    
    # Debug step by step
    print(f"\nStep-by-step debug:")
    
    # Calculate all values
    body_series = (test_data['close'] - test_data['open']).abs()
    total_range_series = test_data['high'] - test_data['low']
    lower_shadow_series = test_data[['open', 'close']].min(axis=1) - test_data['low']
    upper_shadow_series = test_data['high'] - test_data[['open', 'close']].max(axis=1)
    has_body_series = body_series > 0
    
    print(f"body_series: {body_series.tolist()}")
    print(f"total_range_series: {total_range_series.tolist()}")
    print(f"lower_shadow_series: {lower_shadow_series.tolist()}")
    print(f"upper_shadow_series: {upper_shadow_series.tolist()}")
    print(f"has_body_series: {has_body_series.tolist()}")
    
    # Check conditions
    small_body = body_series <= (body_ratio * total_range_series)
    long_lower_shadow = has_body_series & (lower_shadow_series >= (shadow_ratio * body_series))
    small_upper_shadow = upper_shadow_series <= (lower_shadow_series / 2.0)
    
    print(f"small_body: {small_body.tolist()}")
    print(f"long_lower_shadow: {long_lower_shadow.tolist()}")
    print(f"small_upper_shadow: {small_upper_shadow.tolist()}")
    
    final_signals = has_body_series & small_body & long_lower_shadow & small_upper_shadow
    print(f"final_signals: {final_signals.tolist()}")

if __name__ == "__main__":
    debug_hammer()
