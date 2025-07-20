"""Simple test to debug the market data alignment issue."""

import pandas as pd
from datetime import date
from pathlib import Path
import tempfile

from src.kiss_signal.data import get_market_data, _load_market_cache, _save_market_cache
from src.kiss_signal.rules import market_above_sma


def debug_market_data_loading():
    """Debug what happens during market data loading."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("=== Creating test market data ===")
        dates = pd.date_range('2023-01-01', '2023-06-30', freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000
        })
        
        # Save to CSV (problematic format)
        cache_file = temp_path / "INDEX_NSEI.csv"
        market_data.to_csv(cache_file, index=False)
        print(f"Saved CSV to: {cache_file}")
        
        # Check what raw CSV looks like
        raw_data = pd.read_csv(cache_file)
        print(f"Raw CSV index type: {type(raw_data.index)}")
        print(f"Raw CSV columns: {list(raw_data.columns)}")
        print(f"Raw CSV shape: {raw_data.shape}")
        
        # Test _load_market_cache directly
        print("\n=== Testing _load_market_cache directly ===")
        try:
            loaded_directly = _load_market_cache(cache_file)
            print(f"Direct load index type: {type(loaded_directly.index)}")
            print(f"Direct load columns: {list(loaded_directly.columns)}")
            print(f"Direct load shape: {loaded_directly.shape}")
        except Exception as e:
            print(f"Direct load failed: {e}")
        
        # Test get_market_data
        print("\n=== Testing get_market_data ===")
        try:
            loaded_via_get = get_market_data("^NSEI", temp_path)
            print(f"get_market_data index type: {type(loaded_via_get.index)}")
            print(f"get_market_data columns: {list(loaded_via_get.columns)}")
            print(f"get_market_data shape: {loaded_via_get.shape}")
        except Exception as e:
            print(f"get_market_data failed: {e}")
        
        # Test market_above_sma with problematic data
        print("\n=== Testing market_above_sma with problematic data ===")
        try:
            signals = market_above_sma(raw_data, period=20)
            print(f"Signals index type: {type(signals.index)}")
            print(f"Signals shape: {signals.shape}")
            print(f"Signal rate: {signals.sum() / len(signals):.1%}")
        except Exception as e:
            print(f"market_above_sma failed: {e}")


if __name__ == "__main__":
    debug_market_data_loading()
