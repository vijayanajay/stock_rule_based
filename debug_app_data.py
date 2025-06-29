#!/usr/bin/env python3
"""Debug the exact data being passed to sma_crossover in the application."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from pathlib import Path
from datetime import date
from kiss_signal.rules import sma_crossover
from kiss_signal.data import get_price_data, load_universe

def debug_application_data_flow():
    """Test the exact data flow as the application does it."""
    
    # Load data exactly as the application does
    symbols = load_universe(Path("data/nifty_large_mid.csv"))
    symbol = "RELIANCE"
    
    # Get data through the same path as the application
    cache_dir = Path("data/cache")
    freeze_date = date(2025, 1, 1)
    
    # Load exactly as the application does it
    price_data = get_price_data(symbol, cache_dir, freeze_date=freeze_date)
    print(f"Raw data shape: {price_data.shape}")
    print(f"Raw date range: {price_data.index.min()} to {price_data.index.max()}")
    
    # Apply freeze date filtering exactly as backtester does
    if freeze_date is not None:
        price_data = price_data[price_data.index.date <= freeze_date]
        print(f"After freeze filter: {price_data.shape}")
        print(f"Freeze date range: {price_data.index.min()} to {price_data.index.max()}")
    
    # Apply frequency inference exactly as backtester does
    if price_data.index.freq is None:
        inferred_freq = pd.infer_freq(price_data.index)
        if inferred_freq:
            price_data = price_data.asfreq(inferred_freq)
            print(f"After asfreq('{inferred_freq}'): {price_data.shape}")
        else:
            price_data = price_data.asfreq('D')
            print(f"After asfreq('D'): {price_data.shape}")
        
        # Handle NaN values created by asfreq - forward fill to preserve trading data
        if price_data.isnull().any().any():
            price_data = price_data.ffill()
            print(f"After forward-fill: {price_data.shape}")
    
    print(f"Final data shape: {price_data.shape}")
    print(f"Final columns: {list(price_data.columns)}")
    print(f"Data types: {price_data.dtypes}")
    print(f"Any NaN values: {price_data.isnull().sum()}")
    
    # Test SMA crossover on this exact data
    signals = sma_crossover(price_data, fast_period=10, slow_period=20)
    print(f"\nSMA Crossover signals on processed data: {signals.sum()}")
    
    if signals.sum() == 0:
        print("INVESTIGATING WHY NO SIGNALS...")
        
        # Check the raw calculation
        close = price_data['close']
        print(f"Close price stats: min={close.min():.2f}, max={close.max():.2f}, mean={close.mean():.2f}")
        
        fast_sma = close.rolling(window=10, min_periods=10).mean()
        slow_sma = close.rolling(window=20, min_periods=20).mean()
        
        print(f"Fast SMA stats: min={fast_sma.min():.2f}, max={fast_sma.max():.2f}")
        print(f"Slow SMA stats: min={slow_sma.min():.2f}, max={slow_sma.max():.2f}")
        
        # Check crossover conditions
        fast_above = fast_sma > slow_sma
        prev_fast_below = fast_sma.shift(1) <= slow_sma.shift(1)
        crossover = fast_above & prev_fast_below
        
        print(f"Fast > Slow count: {fast_above.sum()}")
        print(f"Previous fast <= slow count: {prev_fast_below.sum()}")
        print(f"Raw crossover count: {crossover.sum()}")
        print(f"After fillna(False): {crossover.fillna(False).sum()}")
        
        # Check for any issues with the data
        print(f"Fast SMA NaN count: {fast_sma.isnull().sum()}")
        print(f"Slow SMA NaN count: {slow_sma.isnull().sum()}")
        
        # Show sample data
        recent = pd.DataFrame({
            'close': close.tail(10),
            'fast_sma': fast_sma.tail(10),
            'slow_sma': slow_sma.tail(10),
            'fast_above': fast_above.tail(10),
            'crossover': crossover.tail(10)
        })
        print(f"\nRecent 10 days data:")
        print(recent)

if __name__ == "__main__":
    debug_application_data_flow()
