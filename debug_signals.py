#!/usr/bin/env python3
"""Quick test to debug signal generation issues."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from kiss_signal.rules import sma_crossover
from kiss_signal.data import load_universe, get_price_data

def test_sma_crossover_signals():
    """Test if sma_crossover is generating any signals with real data."""
    
    # Load real data
    symbols = load_universe("data/nifty_large_mid.csv")
    print(f"Loaded {len(symbols)} symbols")
    
    # Test with RELIANCE data
    symbol = "RELIANCE"
    from pathlib import Path
    price_data = get_price_data(symbol, Path("data"))
    
    # Apply the same freeze date as the main application
    freeze_date = pd.Timestamp('2025-01-01').date()
    price_data_frozen = price_data[price_data.index.date <= freeze_date]
    
    print(f"\n{symbol} FULL data shape: {price_data.shape}")
    print(f"Full date range: {price_data.index.min()} to {price_data.index.max()}")
    
    print(f"\n{symbol} FROZEN data shape: {price_data_frozen.shape}")
    print(f"Frozen date range: {price_data_frozen.index.min()} to {price_data_frozen.index.max()}")
    print(f"Columns: {list(price_data_frozen.columns)}")
    
    # Test SMA crossover with frozen data
    signals_frozen = sma_crossover(price_data_frozen, fast_period=10, slow_period=20)
    print(f"\nSMA Crossover signals (FROZEN data):")
    print(f"Total signals: {signals_frozen.sum()}")
    print(f"Signal percentage: {(signals_frozen.sum() / len(signals_frozen)) * 100:.2f}%")
    
    # Compare with full data
    signals_full = sma_crossover(price_data, fast_period=10, slow_period=20)
    print(f"\nSMA Crossover signals (FULL data):")
    print(f"Total signals: {signals_full.sum()}")
    print(f"Signal percentage: {(signals_full.sum() / len(signals_full)) * 100:.2f}%")
    
    if signals_frozen.sum() > 0:
        signal_dates = signals_frozen[signals_frozen].index
        print(f"First 5 signal dates: {signal_dates[:5].tolist()}")
        print(f"Last 5 signal dates: {signal_dates[-5:].tolist()}")
    else:
        print("No signals found in frozen data!")
        
        # Debug: check SMA values
        close = price_data_frozen['close']
        fast_sma = close.rolling(window=10).mean()
        slow_sma = close.rolling(window=20).mean()
        
        print(f"\nDebugging SMAs:")
        print(f"Close price range: {close.min():.2f} to {close.max():.2f}")
        print(f"Fast SMA range: {fast_sma.min():.2f} to {fast_sma.max():.2f}")
        print(f"Slow SMA range: {slow_sma.min():.2f} to {slow_sma.max():.2f}")
        
        # Check if fast ever crosses above slow
        crossover_condition = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
        print(f"Raw crossover count: {crossover_condition.sum()}")
        print(f"Fast > Slow count: {(fast_sma > slow_sma).sum()}")
        
        # Show recent data
        recent_data = pd.DataFrame({
            'close': close.tail(10),
            'fast_sma': fast_sma.tail(10),
            'slow_sma': slow_sma.tail(10),
            'fast_above': (fast_sma > slow_sma).tail(10)
        })
        print(f"\nRecent 10 days:")
        print(recent_data)

if __name__ == "__main__":
    test_sma_crossover_signals()
