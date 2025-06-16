"""Data Manager compatibility shim.

This module provides backwards compatibility for code that still uses
the DataManager class interface. New code should use the data module directly.
"""

import warnings
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from rich.console import Console

from . import data

__all__ = ["DataManager"]


class DataManager:
    """Backwards compatibility wrapper for data module functions.
    
    DEPRECATED: Use kiss_signal.data functions directly instead.
    """
    
    def __init__(
        self,
        universe_path: str,
        cache_dir: str = "data/cache",
        historical_years: int = 3,
        cache_refresh_days: int = 7,
        freeze_date: Optional[date] = None,
        console: Optional[Console] = None
    ) -> None:
        """Initialize data manager.
        
        Args:
            universe_path: Path to universe CSV file
            cache_dir: Directory for cached data files
            historical_years: Years of historical data to fetch
            cache_refresh_days: Days before cache refresh
            freeze_date: Optional freeze date for backtesting
            console: Rich console for progress display (ignored)
        """
        warnings.warn(
            "DataManager class is deprecated. Use kiss_signal.data functions directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.universe_path = Path(universe_path)
        self.cache_dir = Path(cache_dir)
        self.historical_years = historical_years
        self.cache_refresh_days = cache_refresh_days
        self.freeze_date = freeze_date
        self.console = console or Console()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_universe(self) -> List[str]:
        """Load universe symbols from CSV file.
        
        Returns:
            List of symbols from universe file
        """
        return data.load_universe(str(self.universe_path))
    
    def refresh_market_data(self, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """Fetch latest data for symbols with intelligent caching.
        
        Args:
            symbols: Optional list of symbols to refresh. If None, loads from universe.
            
        Returns:
            Dict mapping symbol -> success status
        """
        return data.refresh_market_data(
            universe_path=str(self.universe_path),
            cache_dir=str(self.cache_dir),
            refresh_days=self.cache_refresh_days,
            years=self.historical_years,
            freeze_date=self.freeze_date,
            symbols=symbols
        )
    
    def get_price_data(
        self, 
        symbol: str, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """Serve price data from cache with validation.
        
        Args:
            symbol: Symbol to fetch (without .NS suffix)
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Standardized DataFrame with date index and OHLCV columns
        """
        return data.get_price_data(
            symbol=symbol,
            cache_dir=self.cache_dir,
            start_date=start_date,
            end_date=end_date,
            freeze_date=self.freeze_date
        )
