"""Debug ATR calculation issue."""

import pandas as pd
import numpy as np
from src.kiss_signal import rules
from src.kiss_signal.backtester import Backtester
from src.kiss_signal.config import RuleDef


def debug_atr_calculation():
    """Debug why ATR calculation returns NaN."""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    
    # Create simple price data
    price_data = pd.DataFrame({
        'high': [102, 104, 103, 105, 104] * 6,
        'low': [98, 96, 97, 95, 96] * 6,
        'close': [100 + i * 0.5 for i in range(30)],
        'volume': [1000] * 30
    }, index=dates)
    
    print("Price data columns:", price_data.columns.tolist())
    print("Price data head:")
    print(price_data.head())
    
    # Try calculating ATR directly
    try:
        atr_values = rules.calculate_atr(price_data, period=14)
        print("\nATR calculation successful!")
        print("ATR values (first 20):")
        print(atr_values.head(20))
        print(f"ATR non-null count: {atr_values.notna().sum()}")
        print(f"ATR mean: {atr_values.mean()}")
        
        # Test position sizing
        bt = Backtester(initial_capital=100000.0)
        entry_signals = pd.Series(False, index=dates)
        entry_signals.iloc[15] = True
        
        exit_conditions = [
            RuleDef(
                name="atr_stop",
                type="chandelier_atr_exit",
                params={"multiplier": 2.0}
            )
        ]
        
        print(f"\nATR at entry day (15): {atr_values.iloc[15]}")
        print(f"Entry signal at day 15: {entry_signals.iloc[15]}")
        
        # Check the risk calculation step by step
        atr_multiplier = bt._get_atr_multiplier(exit_conditions)
        print(f"ATR multiplier: {atr_multiplier}")
        
        risk_per_share = atr_values * atr_multiplier
        print(f"Risk per share at entry day: {risk_per_share.iloc[15]}")
        
        risk_amount = bt.initial_capital * 0.01
        print(f"Risk amount (1%): {risk_amount}")
        
        if risk_per_share.iloc[15] > 0:
            calculated_size = risk_amount / risk_per_share.iloc[15]
            print(f"Calculated position size: {calculated_size}")
        else:
            print("Risk per share is 0 or NaN!")
            
        # Test the full method
        sizes = bt._calculate_risk_based_size(price_data, entry_signals, exit_conditions)
        print(f"\nFull method result at entry day: {sizes.iloc[15]}")
        print(f"Sizes series type: {type(sizes.iloc[15])}")
        print(f"Non-null sizes count: {sizes.notna().sum()}")
        
        # Let's also check our boolean logic
        valid_entries = entry_signals & risk_per_share.notna() & (risk_per_share > 0)
        print(f"Valid entries at day 15: {valid_entries.iloc[15]}")
        print(f"Total valid entries: {valid_entries.sum()}")
        
        # Debug the assignment step by step
        print(f"\nDebug assignment:")
        print(f"risk_per_share.loc[valid_entries]: {risk_per_share.loc[valid_entries]}")
        print(f"risk_amount / risk_per_share.loc[valid_entries]: {risk_amount / risk_per_share.loc[valid_entries]}")
        
        # Manual test of the assignment
        test_sizes = pd.Series(index=price_data.index, dtype=float)
        test_sizes[:] = np.nan
        print(f"Initial test_sizes: {test_sizes.iloc[15]}")
        
        # Direct assignment
        test_sizes.iloc[15] = 71.55
        print(f"After direct assignment: {test_sizes.iloc[15]}")
        
        # Try the vectorized assignment
        test_sizes2 = pd.Series(index=price_data.index, dtype=float)
        test_sizes2[:] = np.nan
        test_sizes2.loc[valid_entries] = risk_amount / risk_per_share.loc[valid_entries]
        print(f"After vectorized assignment: {test_sizes2.iloc[15]}")
        
    except Exception as e:
        print(f"Error calculating ATR: {e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    debug_atr_calculation()
