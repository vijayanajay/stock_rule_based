"""Debug script to understand test failure."""

import pandas as pd
from pathlib import Path
import tempfile
from src.kiss_signal.data import get_market_data, _load_market_cache, _save_market_cache

def debug_market_data_loading():
    """Debug why test is failing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create market data with the problematic format (date as column, RangeIndex)
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000
        })
        
        print("Original market data:")
        print(f"  Index type: {type(market_data.index)}")
        print(f"  Columns: {market_data.columns.tolist()}")
        print(f"  Shape: {market_data.shape}")
        
        # Save to CSV (this creates the problematic format)
        cache_file = temp_path / "INDEX_NSEI.csv"
        market_data.to_csv(cache_file, index=False)
        print(f"\nSaved to: {cache_file}")
        
        # Check what's in the CSV
        raw_data = pd.read_csv(cache_file)
        print(f"\nRaw CSV data:")
        print(f"  Index type: {type(raw_data.index)}")
        print(f"  Columns: {raw_data.columns.tolist()}")
        print(f"  Shape: {raw_data.shape}")
        print(f"  First few rows:\n{raw_data.head()}")
        
        # Test _load_market_cache directly
        print(f"\nTesting _load_market_cache directly:")
        try:
            loaded_direct = _load_market_cache(cache_file)
            print(f"  Index type: {type(loaded_direct.index)}")
            print(f"  Columns: {loaded_direct.columns.tolist()}")
            print(f"  Shape: {loaded_direct.shape}")
            print(f"  SUCCESS: _load_market_cache works")
        except Exception as e:
            print(f"  ERROR in _load_market_cache: {e}")
            
        # Test get_market_data
        print(f"\nTesting get_market_data:")
        try:
            loaded_market = get_market_data("^NSEI", temp_path)
            print(f"  Index type: {type(loaded_market.index)}")
            print(f"  Columns: {loaded_market.columns.tolist()}")
            print(f"  Shape: {loaded_market.shape}")
            if isinstance(loaded_market.index, pd.DatetimeIndex):
                print(f"  SUCCESS: DatetimeIndex as expected")
            else:
                print(f"  FAILURE: Expected DatetimeIndex, got {type(loaded_market.index)}")
        except Exception as e:
            print(f"  ERROR in get_market_data: {e}")

if __name__ == "__main__":
    debug_market_data_loading()
