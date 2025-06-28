#!/usr/bin/env python3
"""
Temporary debug script to test signal generation issue.
This script will isolate and test the signal generation logic.
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kiss_signal.data import get_price_data
from kiss_signal.rules import sma_crossover
from kiss_signal.backtester import Backtester

def debug_signal_generation():
    """Debug why signals are not being generated."""
    
    print("=== DEBUGGING SIGNAL GENERATION ===")
    
    # Test 1: Load sample data
    print("\n1. Loading sample data for RELIANCE...")
    try:
        # Use correct signature with cache_dir
        cache_dir = Path(__file__).parent / "data" / "cache"
        data = get_price_data("RELIANCE", str(cache_dir), freeze_date=None)
        print(f"   Data shape: {data.shape}")
        print(f"   Date range: {data.index.min()} to {data.index.max()}")
        print(f"   Columns: {list(data.columns)}")
        print("   Last 5 rows:")
        print(data.tail())
    except Exception as e:
        print(f"   ERROR loading data: {e}")
        print("   Trying alternative method...")
        try:
            # Try loading directly from CSV
            csv_path = Path(__file__).parent / "data" / "RELIANCE.NS.csv"
            data = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            print(f"   Data shape (from CSV): {data.shape}")
            print(f"   Date range: {data.index.min()} to {data.index.max()}")
            print(f"   Columns: {list(data.columns)}")
            print("   Last 5 rows:")
            print(data.tail())
        except Exception as e2:
            print(f"   ERROR loading CSV: {e2}")
            return
    
    # Test 2: Test individual rule function
    print("\n2. Testing SMA crossover rule directly...")
    try:
        # Test with sample parameters - using correct parameter names
        signals = sma_crossover(data, fast_period=10, slow_period=20)
        print(f"   Signals shape: {signals.shape}")
        print(f"   Signal count: {signals.sum()}")
        print("   Signals (last 20):")
        print(signals.tail(20))
        
        if signals.sum() > 0:
            print("   Signal dates:")
            signal_dates = data[signals].index
            for date in signal_dates[-5:]:  # Last 5 signals
                print(f"     {date}")
    except Exception as e:
        print(f"   ERROR testing rule: {e}")
        return
    
    # Test 3: Test backtester signal generation
    print("\n3. Testing backtester signal generation...")
    try:
        backtester = Backtester(hold_period=20, min_trades_threshold=10)
        
        # Test single rule using correct format
        rule_def = {"name": "sma_10_20_crossover", "type": "sma_crossover", "params": {"fast_period": 10, "slow_period": 20}}
        signals = backtester._generate_signals(rule_def, data)
        
        print(f"   Backtester signals shape: {signals.shape}")
        print(f"   Backtester signal count: {signals.sum()}")
        print("   Backtester signals (last 20):")
        print(signals.tail(20))
        
    except Exception as e:
        print(f"   ERROR testing backtester: {e}")
        return
    
    # Test 4: Check data quality
    print("\n4. Checking data quality...")
    try:
        print(f"   Null values: {data.isnull().sum().sum()}")
        print(f"   Infinite values: {pd.isinf(data.select_dtypes(include=[float, int])).sum().sum()}")
        print("   Close price stats:")
        if 'Close' in data.columns:
            print(f"     Min: {data['Close'].min()}")
            print(f"     Max: {data['Close'].max()}")
            print(f"     Mean: {data['Close'].mean():.2f}")
        elif 'close' in data.columns:
            print(f"     Min: {data['close'].min()}")
            print(f"     Max: {data['close'].max()}")
            print(f"     Mean: {data['close'].mean():.2f}")
        else:
            print("     No 'Close' or 'close' column found!")
            
    except Exception as e:
        print(f"   ERROR checking data quality: {e}")
    
    # Test 5: Manual SMA calculation
    print("\n5. Manual SMA calculation test...")
    try:
        # Use the correct column name
        price_col = 'Close' if 'Close' in data.columns else 'close'
        if price_col not in data.columns:
            print("   ERROR: No price column found!")
            return
            
        sma_10 = data[price_col].rolling(window=10).mean()
        sma_20 = data[price_col].rolling(window=20).mean()
        
        print("   SMA 10 last 5 values:")
        print(sma_10.tail())
        print("   SMA 20 last 5 values:")
        print(sma_20.tail())
        
        # Manual crossover detection
        crossover = (sma_10 > sma_20) & (sma_10.shift(1) <= sma_20.shift(1))
        print(f"   Manual crossover signals: {crossover.sum()}")
        
        if crossover.sum() > 0:
            print("   Manual crossover dates (last 5):")
            crossover_dates = data[crossover].index
            for date in crossover_dates[-5:]:
                print(f"     {date}")
                
    except Exception as e:
        print(f"   ERROR in manual calculation: {e}")

    # Test 6: Test VectorBT portfolio creation
    print("\n6. Testing VectorBT portfolio creation...")
    try:
        import vectorbt as vbt
        import numpy as np
        
        # Get the entry signals we generated
        entry_signals = sma_crossover(data, fast_period=10, slow_period=20)
        print(f"   Entry signals: {entry_signals.sum()}")
        
        # Test exit signal generation
        backtester = Backtester(hold_period=20, min_trades_threshold=10)
        exit_signals = backtester._generate_time_based_exits(entry_signals, 20)
        print(f"   Exit signals: {exit_signals.sum()}")
        print("   Exit signals (where True):")
        print(exit_signals[exit_signals].head(10))
        
        # Set frequency for VectorBT
        if data.index.freq is None:
            data = data.asfreq('D')
            entry_signals = entry_signals.asfreq('D').fillna(False)
            exit_signals = exit_signals.asfreq('D').fillna(False)
            print("   Set frequency to daily for VectorBT")
        
        # Test VectorBT portfolio creation
        print("   Creating VectorBT portfolio...")
        portfolio = vbt.Portfolio.from_signals(
            close=data['close'],
            entries=entry_signals,
            exits=exit_signals,
            fees=0.001,
            slippage=0.0005,
            init_cash=100000,
            size=np.inf
        )
        
        total_trades = portfolio.trades.count()
        print(f"   VectorBT Portfolio trades: {total_trades}")
        
        if total_trades > 0:
            print("   Trade details:")
            print(portfolio.trades.records)
        else:
            print("   No trades created!")
            print("   Portfolio stats:")
            print(f"     Total return: {portfolio.total_return()}")
            print(f"     Entry signals sum: {entry_signals.sum()}")
            print(f"     Exit signals sum: {exit_signals.sum()}")
            
    except Exception as e:
        print(f"   ERROR testing VectorBT: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_signal_generation()
