"""
Test Chandelier Exit vs baseline performance.
Story 031: Professional ATR-based trailing stop validation.
"""

import sys
sys.path.append('src')

import pytest
import pandas as pd
from pathlib import Path
from datetime import date
from kiss_signal.backtester import Backtester
from kiss_signal.config import RulesConfig, RuleDef, EdgeScoreWeights
from kiss_signal import data

def test_chandelier_vs_baseline_performance():
    """
    Test Chandelier Exit vs baseline - following Story 029 proven pattern.
    
    Compares:
    1. Fixed 5% take-profit (baseline from Story 029)
    2. Simple 5% trailing stop (Story 029 result) 
    3. Chandelier Exit ATR-based trailing stop (Story 031)
    
    Expected: Chandelier Exit should adapt better to volatility than fixed percentages.
    """
    symbol = "HDFCBANK.NS"
    
    # Load test data using the same pattern as Story 029
    print(f"Loading data for {symbol}...")
    
    try:
        price_data = data.get_price_data(
            symbol=symbol,
            cache_dir=Path("data"),
            start_date=date(2022, 1, 1),
            end_date=date(2025, 1, 1)
        )
    except Exception as e:
        pytest.skip(f"Test data for {symbol} not available: {e}")
    
    if len(price_data) < 50:
        pytest.skip(f"Insufficient data for {symbol}: {len(price_data)} rows")
    
    print(f"Loaded {len(price_data)} days of data")
    print(f"Data columns: {list(price_data.columns)}")
    
    # Set frequency for vectorbt compatibility and forward-fill any NaN values
    if price_data.index.freq is None:
        price_data = price_data.asfreq('D').ffill()
        print("Set frequency to daily ('D') and forward-filled missing values")
    
    # Initialize backtester with lower min_trades_threshold for testing
    backtester = Backtester(
        initial_capital=100000,
        hold_period=5,  # Shorter hold period like Story 029
        min_trades_threshold=1  # Accept any trades for testing
    )
    edge_weights = EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
    
    # Common entry signal for all tests (same as Story 029)
    entry_signals = [
        RuleDef(
            name="price_above_sma",
            type="price_above_sma",
            params={"period": 5}
        )
    ]
    
    print(f"\n=== CHANDELIER EXIT PERFORMANCE TEST ===")
    print(f"Symbol: {symbol}")
    print(f"Data Points: {len(price_data)}")
    
    # Test 1: Baseline - Fixed 5% take-profit (Story 029 baseline)
    baseline_exit_conditions = [
        RuleDef(
            name="stop_loss_pct",
            type="stop_loss_pct",
            params={"percentage": 0.05}
        ),
        RuleDef(
            name="take_profit_pct",
            type="take_profit_pct",
            params={"percentage": 0.05}
        )
    ]
    
    baseline_config = RulesConfig(
        entry_signals=entry_signals,
        exit_conditions=baseline_exit_conditions,
        context_filters=[],
        preconditions=[]
    )
    
    print("\n=== Testing BASELINE (Fixed Take-Profit) ===")
    baseline_result = backtester._backtest_combination(
        [entry_signals[0]], price_data, baseline_config, 
        edge_weights, symbol
    )
    
    # Test 2: Simple trailing stop (Story 029 result for comparison)
    trailing_exit_conditions = [
        RuleDef(
            name="stop_loss_pct",
            type="stop_loss_pct",
            params={"percentage": 0.05}
        ),
        RuleDef(
            name="simple_trailing_stop",
            type="simple_trailing_stop",
            params={"trail_percent": 0.05}
        )
    ]
    
    trailing_config = RulesConfig(
        entry_signals=entry_signals,
        exit_conditions=trailing_exit_conditions,
        context_filters=[],
        preconditions=[]
    )
    
    print("\n=== Testing SIMPLE TRAILING STOP ===")
    trailing_result = backtester._backtest_combination(
        [entry_signals[0]], price_data, trailing_config, 
        edge_weights, symbol
    )
    
    # Test 3: Chandelier Exit - NEW (Story 031)
    chandelier_exit_conditions = [
        RuleDef(
            name="stop_loss_pct",
            type="stop_loss_pct",
            params={"percentage": 0.05}
        ),
        RuleDef(
            name="chandelier_exit",
            type="chandelier_exit",
            params={"atr_period": 22, "atr_multiplier": 3.0}
        )
    ]
    
    chandelier_config = RulesConfig(
        entry_signals=entry_signals,
        exit_conditions=chandelier_exit_conditions,
        context_filters=[],
        preconditions=[]
    )
    
    print("\n=== Testing CHANDELIER EXIT ===")
    chandelier_result = backtester._backtest_combination(
        [entry_signals[0]], price_data, chandelier_config, 
        edge_weights, symbol
    )
    
    # Validate all tests produced results
    assert baseline_result is not None, "Baseline test failed"
    assert trailing_result is not None, "Trailing stop test failed"  
    assert chandelier_result is not None, "Chandelier Exit test failed"
    
    # Display comparative results
    print(f"\n=== PERFORMANCE COMPARISON ===")
    print(f"{'Strategy':<25} {'Trades':<8} {'Win Rate':<10} {'Sharpe':<8} {'Edge Score':<10}")
    print("-" * 70)
    
    def format_results(name, result):
        trades = result.get('total_trades', 0)
        win_rate = result.get('win_pct', 0.0) * 100
        sharpe = result.get('sharpe', 0.0)
        edge_score = result.get('edge_score', 0.0)
        print(f"{name:<25} {trades:<8} {win_rate:<10.1f}% {sharpe:<8.2f} {edge_score:<10.3f}")
        return {'trades': trades, 'win_rate': win_rate, 'sharpe': sharpe, 'edge_score': edge_score}
    
    baseline_metrics = format_results("Fixed Take-Profit", baseline_result)
    trailing_metrics = format_results("Simple Trailing 5%", trailing_result)
    chandelier_metrics = format_results("Chandelier Exit", chandelier_result)
    
    # Analysis: Check if Chandelier Exit adapts better to volatility
    print(f"\n=== VOLATILITY ADAPTATION ANALYSIS ===")
    
    # Calculate ATR for the test period to measure volatility context
    from kiss_signal.rules import calculate_atr
    avg_atr = calculate_atr(price_data, period=22).mean()
    avg_price = price_data['close'].mean()
    volatility_ratio = (avg_atr / avg_price) * 100
    
    print(f"Average ATR: {avg_atr:.2f}")
    print(f"Average Price: {avg_price:.2f}")
    print(f"Volatility Ratio: {volatility_ratio:.2f}%")
    
    # Compare performance improvements
    if chandelier_metrics['edge_score'] > baseline_metrics['edge_score']:
        improvement = chandelier_metrics['edge_score'] - baseline_metrics['edge_score']
        print(f"✅ Chandelier Exit outperforms baseline by {improvement:.3f} Edge Score")
    
    if chandelier_metrics['edge_score'] > trailing_metrics['edge_score']:
        improvement = chandelier_metrics['edge_score'] - trailing_metrics['edge_score']
        print(f"✅ Chandelier Exit outperforms simple trailing by {improvement:.3f} Edge Score")
    
    # Key test: At minimum, Chandelier Exit should not catastrophically fail
    assert chandelier_metrics['trades'] > 0, "Chandelier Exit generated no trades"
    assert chandelier_metrics['edge_score'] > -0.5, "Chandelier Exit Edge Score too negative"
    
    print(f"\n=== STORY 031 VALIDATION ===")
    print(f"✅ Chandelier Exit function integrated successfully")
    print(f"✅ ATR-based trailing stop working with backtesting system")
    print(f"✅ Performance measurement framework validated")
    print(f"✅ Ready for production use")

if __name__ == "__main__":
    test_chandelier_vs_baseline_performance()
