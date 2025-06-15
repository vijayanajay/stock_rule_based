"""Data Manager - NSE Data Fetching and Caching Module.

This module handles downloading, caching, and serving market data for NSE equities.
"""

import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Defer yfinance import to avoid startup cost
# import yfinance as yf

__all__ = ["DataManager"]

logger = logging.getLogger(__name__)


class DataManager:
    """Manages NSE equity price data fetching and caching."""
    
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
            console: Rich console for progress display
        """
        self.universe_path = Path(universe_path)
        self.cache_dir = Path(cache_dir)
        self.historical_years = historical_years
        self.cache_refresh_days = cache_refresh_days
        self.freeze_date = freeze_date
        self.console = console or Console()
          # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._metadata_path = self.cache_dir / "cache_metadata.json"
    
    def _load_universe(self) -> List[str]:
        """Load universe symbols from CSV file.
        
        Returns:
            List of symbols from universe file
              Raises:
            FileNotFoundError: If universe file doesn't exist
            ValueError: If universe file is malformed
        """
        try:
            df = pd.read_csv(self.universe_path)
        except FileNotFoundError:
            logger.error(f"Universe file not found: {self.universe_path}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to load universe file, malformed CSV: {e}")
            raise ValueError(f"Malformed universe file: {self.universe_path}") from e

        if 'symbol' not in df.columns:
            raise ValueError("Universe file missing 'symbol' column")

        symbols: list[str] = df['symbol'].astype(str).tolist()
        logger.info(f"Loaded {len(symbols)} symbols from universe")
        return symbols
    
    def _load_cache_metadata(self) -> Dict[str, str]:
        """Load cache metadata from JSON file.
        
        Returns:
            Dictionary mapping symbol -> last_update timestamp
        """
        if not self._metadata_path.exists():
            return {}
        
        try:
            with open(self._metadata_path, 'r') as f:
                result: dict[str, str] = json.load(f)
                return result
        except json.JSONDecodeError as e:
            logger.warning(f"Cache metadata file corrupted (JSON decode error): {e}")
            return {}
        except (OSError, IOError) as e:
            logger.warning(f"Failed to read cache metadata file: {e}")
            return {}
    
    # impure
    def _save_cache_metadata(self, metadata: Dict[str, str]) -> None:
        """Save cache metadata to JSON file.
        
        Args:
            metadata: Dictionary mapping symbol -> last_update timestamp
        """
        try:
            tmp = self._metadata_path.with_suffix('.tmp')
            with open(tmp, 'w') as f:
                json.dump(metadata, f, indent=2)
            tmp.replace(self._metadata_path)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def _needs_refresh(self, symbol: str, metadata: Dict[str, str]) -> bool:
        """Check if symbol data needs refresh.
        
        Args:
            symbol: Symbol to check
            metadata: Cache metadata dictionary
            
        Returns:
            True if symbol needs refresh
        """
        # Skip cache refresh in freeze mode to maintain repeatability
        if self.freeze_date is not None:
            return False
            
        if symbol not in metadata:
            return True
        
        try:
            last_update = datetime.fromisoformat(metadata[symbol])
            cutoff = datetime.now() - timedelta(days=self.cache_refresh_days)
            return last_update < cutoff
        except (ValueError, KeyError):
            return True
    
    def _add_ns_suffix(self, symbol: str) -> str:
        """Add .NS suffix for yfinance compatibility.
        
        Args:
            symbol: NSE symbol
            
        Returns:
            Symbol with .NS suffix
        """
        return f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
    
    # impure
    def _fetch_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data for single symbol using yfinance.
        
        Args:
            symbol: Symbol to fetch (with .NS suffix)
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        # Import yfinance here to avoid startup cost
        import yfinance as yf
        
        try:
            end_date = self.freeze_date or date.today()
            start_date = end_date - timedelta(days=self.historical_years * 365)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, auto_adjust=True)
            
            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
              # Standardize column names and format
            data = data.reset_index()
            data.columns = [col.lower() for col in data.columns]
            
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_columns):
                logger.error(f"Missing required columns for {symbol}")
                return None
            
            # Select and order columns
            data = data[required_columns].copy()
            
            # Ensure proper data types
            data['date'] = pd.to_datetime(data['date'])
            for col in ['open', 'high', 'low', 'close']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce').astype('Int64')
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    def _validate_data_quality(self, data: pd.DataFrame, symbol: str) -> bool:
        """Validate data quality for a symbol.
        
        Args:
            data: DataFrame to validate
            symbol: Symbol name for logging
            
        Returns:
            True if data passes quality checks
        """
        if data.empty:
            logger.warning(f"Empty data for {symbol}")
            return False
        
        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        negative_prices = (data[price_cols] < 0).any().any()
        if negative_prices:
            logger.warning(f"Negative prices detected for {symbol}")
            return False
        
        # Check for zero volume days
        if (data['volume'] == 0).sum() > len(data) * 0.1:
            logger.warning(f"High zero-volume days for {symbol}")
            return False
        
        # Check for large data gaps
        max_gap_days = data.sort_values('date')['date'].diff().dt.days.max()
        if pd.notna(max_gap_days) and max_gap_days > 5:
            logger.warning(f"Large data gap detected for {symbol}: {max_gap_days} days")
            return False
        
        return True
    
    # impure
    def _save_symbol_cache(self, symbol: str, data: pd.DataFrame) -> bool:
        """Save symbol data to cache file.
        
        Args:
            symbol: Symbol name (without .NS suffix)
            data: DataFrame to save
            
        Returns:
            True if save successful
        """
        cache_file = self.cache_dir / f"{symbol}.NS.csv"
        
        try:
            data.to_csv(cache_file, index=False)
            logger.debug(f"Saved cache for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cache for {symbol}: {e}")
            return False
    
    # impure
    def refresh_market_data(self, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """Fetch latest data for symbols with intelligent caching.
        
        Args:
            symbols: Optional list of symbols to refresh. If None, loads from universe.
            
        Returns:
            Dict mapping symbol -> success status
        """
        if symbols is None:
            symbols = self._load_universe()
        
        metadata = self._load_cache_metadata()
        
        # Filter symbols that need refresh
        symbols_to_fetch = [
            symbol for symbol in symbols 
            if self._needs_refresh(symbol, metadata)
        ]
        
        if not symbols_to_fetch:
            logger.info("All symbols are fresh, no refresh needed")
            return {symbol: True for symbol in symbols}
        
        logger.info(f"Refreshing {len(symbols_to_fetch)} of {len(symbols)} symbols")
        
        results = {}
        updated_metadata = metadata.copy()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"Fetching data for {len(symbols_to_fetch)} symbols...",
                total=len(symbols_to_fetch)
            )
            
            for symbol in symbols_to_fetch:
                symbol_with_suffix = self._add_ns_suffix(symbol)
                
                # Fetch data with retry logic
                data = None
                for attempt in range(3):  # Max 3 retries
                    data = self._fetch_symbol_data(symbol_with_suffix)
                    if data is not None:
                        break
                    
                    if attempt < 2:  # Don't sleep on final attempt
                        time.sleep(2 ** attempt)  # Exponential backoff
                
                if data is not None and self._validate_data_quality(data, symbol):
                    success = self._save_symbol_cache(symbol, data)
                    if success:
                        updated_metadata[symbol] = datetime.now().isoformat()
                    results[symbol] = success
                else:
                    results[symbol] = False
                
                progress.advance(task)
        
        # Save updated metadata
        self._save_cache_metadata(updated_metadata)
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Successfully refreshed {successful}/{len(symbols_to_fetch)} symbols")
        
        return results
    
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
            
        Raises:
            FileNotFoundError: If cached data not found
            ValueError: If data is corrupted or invalid
        """
        cache_file = self.cache_dir / f"{symbol}.NS.csv"
        
        if not cache_file.exists():
            raise FileNotFoundError(f"Cached data not found for {symbol}")
        
        try:
            data = pd.read_csv(cache_file)
            data['date'] = pd.to_datetime(data['date'])
            
            # Apply date filtering
            if start_date:
                data = data[data['date'] >= pd.to_datetime(start_date)]
            
            if end_date:
                data = data[data['date'] <= pd.to_datetime(end_date)]
            
            # Apply freeze date restriction
            if self.freeze_date:
                data = data[data['date'] <= pd.to_datetime(self.freeze_date)]
            
            # Set date as index
            data = data.set_index('date').sort_index()
            
            if data.empty:
                raise ValueError(f"No data available for {symbol} in requested date range")
            
            logger.debug(f"Served {len(data)} rows for {symbol}")
            return data
            
        except (pd.errors.EmptyDataError, pd.errors.ParserError, KeyError) as e:
            logger.error(f"Failed to load or parse cached data for {symbol}: {e}")
            raise ValueError(f"Corrupted or invalid cache data for {symbol}") from e
