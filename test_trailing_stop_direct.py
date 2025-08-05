#!/usr/bin/env python3
"""Direct test of trailing stop vs fixed take-profit on a single symbol."""

import sys
sys.path.append('src')

import pandas as pd
from pathlib import Path
from datetime import date
from kiss_signal.backtester import Backtester
from kiss_signal.config import RulesConfig, RuleDef, EdgeScoreWeights
from kiss_signal import data

def test_trailing_stop_directly():
    """Test trailing stop vs fixed take-profit on HDFCBANK."""
    
    # Load data for a single symbol
    symbol = "HDFCBANK.NS"
    print(f"Loading data for {symbol}...")
    
    price_data = data.get_price_data(
        symbol=symbol,
        cache_dir=Path("data"),
        start_date=date(2022, 1, 1),  # Use more recent data that we have
        end_date=date(2025, 1, 1)
    )
    
    print(f"Loaded {len(price_data)} days of data")
    print(f"Data columns: {list(price_data.columns)}")
    
    # Set frequency for vectorbt compatibility and forward-fill any NaN values
    if price_data.index.freq is None:
        price_data = price_data.asfreq('D').ffill()
        print("Set frequency to daily ('D') and forward-filled missing values")
    
    # For testing, use a very simple entry signal that triggers more frequently
    print(f"Data range: {price_data.index[0]} to {price_data.index[-1]}")
    print(f"Close price range: {price_data['close'].min():.2f} to {price_data['close'].max():.2f}")
    
    # Create backtester with very low threshold for testing
    backtester = Backtester(
        initial_capital=100000,
        hold_period=5,  # Shorter hold period
        min_trades_threshold=1  # Accept any trades for testing
    )
    
    # Use a simple price-based entry signal instead of SMA crossover
    entry_signals = [
        RuleDef(
            name="price_above_sma",
            type="price_above_sma",
            params={"period": 5}  # Very short period
        )
    ]
    
    # Test 1: Fixed take-profit (baseline)
    baseline_exit_conditions = [
        RuleDef(
            name="take_profit_pct",
            type="take_profit_pct",
            params={"percentage": 0.05}  # 5% fixed take-profit
        )
    ]
    
    baseline_config = RulesConfig(
        entry_signals=entry_signals,
        exit_conditions=baseline_exit_conditions,
        context_filters=[],
        preconditions=[]
    )
    
    print("\\n=== Testing BASELINE (Fixed Take-Profit) ===")
    baseline_result = backtester._backtest_combination(
        [entry_signals[0]], price_data, baseline_config, 
        EdgeScoreWeights(win_pct=0.6, sharpe=0.4), symbol
    )
    
    if baseline_result:
        print(f"Baseline Results:")
        print(f"  Win Rate: {baseline_result['win_pct']:.1%}")
        print(f"  Sharpe: {baseline_result['sharpe']:.2f}")
        print(f"  Edge Score: {baseline_result['edge_score']:.3f}")
        print(f"  Total Trades: {baseline_result['total_trades']}")
        print(f"  Avg Return: {baseline_result['avg_return']:.4f}")
    else:
        print("❌ Baseline test failed!")
    
    # Test 2: Trailing stop
    trailing_exit_conditions = [
        RuleDef(
            name="trailing_stop_5pct",
            type="simple_trailing_stop",
            params={"trail_percent": 0.05}  # 5% trailing stop
        )
    ]
    
    trailing_config = RulesConfig(
        entry_signals=entry_signals,
        exit_conditions=trailing_exit_conditions,
        context_filters=[],
        preconditions=[]
    )
    
    print("\\n=== Testing TRAILING STOP (5%) ===")
    trailing_result = backtester._backtest_combination(
        [entry_signals[0]], price_data, trailing_config,
        EdgeScoreWeights(win_pct=0.6, sharpe=0.4), symbol
    )
    
    if trailing_result:
        print(f"Trailing Stop Results:")
        print(f"  Win Rate: {trailing_result['win_pct']:.1%}")
        print(f"  Sharpe: {trailing_result['sharpe']:.2f}")
        print(f"  Edge Score: {trailing_result['edge_score']:.3f}")
        print(f"  Total Trades: {trailing_result['total_trades']}")
        print(f"  Avg Return: {trailing_result['avg_return']:.4f}")
    else:
        print("❌ Trailing stop test failed!")
    
    # Compare results
    if baseline_result and trailing_result:
        print("\\n=== COMPARISON ===")
        print(f"Win Rate: Baseline {baseline_result['win_pct']:.1%} vs Trailing {trailing_result['win_pct']:.1%}")
        print(f"Sharpe: Baseline {baseline_result['sharpe']:.2f} vs Trailing {trailing_result['sharpe']:.2f}")
        print(f"Edge Score: Baseline {baseline_result['edge_score']:.3f} vs Trailing {trailing_result['edge_score']:.3f}")
        
        if trailing_result['edge_score'] > baseline_result['edge_score']:
            print("🎉 TRAILING STOP WINS!")
        else:
            print("📊 FIXED TAKE-PROFIT WINS!")
    
    return baseline_result and trailing_result

if __name__ == "__main__":
    success = test_trailing_stop_directly()
    print(f"\\nDirect test: {'PASS' if success else 'FAIL'}")
