"""Data Module - NSE Data Fetching and Caching Functions.

This module provides simple functions for downloading, caching, and serving 
market data for NSE equities without unnecessary abstraction.
"""

import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

__all__ = ["get_price_data", "refresh_market_data", "load_universe"]

logger = logging.getLogger(__name__)


# impure
def load_universe(universe_path: str) -> List[str]:
    """Load universe symbols from CSV file.
    
    Args:
        universe_path: Path to universe CSV file
        
    Returns:
        List of symbols from universe file
        
    Raises:
        FileNotFoundError: If universe file doesn't exist
        ValueError: If universe file is malformed
    """
    try:
        df = pd.read_csv(universe_path)
    except FileNotFoundError:
        logger.error(f"Universe file not found: {universe_path}")
        raise
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to load universe file, malformed CSV: {e}")
        raise ValueError(f"Malformed universe file: {universe_path}") from e

    if 'symbol' not in df.columns:
        raise ValueError("Universe file missing 'symbol' column")

    symbols: List[str] = df['symbol'].astype(str).tolist()
    logger.info(f"Loaded {len(symbols)} symbols from universe")
    return symbols


def get_price_data(
    symbol: str,
    cache_dir: Path,
    refresh_days: int = 30,
    years: int = 1,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    freeze_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get price data from cache with validation.
    
    Args:
        symbol: Stock symbol
        cache_dir: Path to cache directory
        refresh_days: Days before cache refresh
        years: Number of years of data
        start_date: Optional start date filter
        end_date: Optional end date filter
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        Standardized DataFrame with date index and OHLCV columns
        
    Raises:
        ValueError: If data is corrupted or invalid    """
    cache_file = cache_dir / f"{symbol}.NS.csv"
    
    # Check if we need to refresh or download data
    if not cache_file.exists() or _needs_refresh(symbol, cache_dir, refresh_days):
        if freeze_date:
            # In freeze mode, don't download new data
            if not cache_file.exists():
                raise FileNotFoundError(f"Cached data not found for {symbol} (freeze mode)")
            # Use existing cache
            data = _load_symbol_cache(symbol, cache_dir)
        else:
            # Download fresh data
            logger.info(f"Downloading fresh data for {symbol}")
            data = _fetch_symbol_data(symbol, years)
            if data is not None:
                _save_symbol_cache(symbol, data, cache_dir)
            else:
                raise ValueError(f"Failed to fetch data for {symbol}")
    else:
        # Load from cache
        data = _load_symbol_cache(symbol, cache_dir)
    
    # Apply date filtering
    if start_date:
        data = data[data.index >= pd.to_datetime(start_date)]    
    if end_date:
        data = data[data.index <= pd.to_datetime(end_date)]
    
    # Apply freeze date restriction
    if freeze_date:
        data = data[data.index <= pd.to_datetime(freeze_date)]
    
    if data.empty:
        raise ValueError(f"No data available for {symbol} in requested date range")
    
    # Only log in verbose mode for individual symbol data serving
    if len(data) < 50:
        logger.warning(f"Limited data for {symbol}: only {len(data)} rows")
    
    return data


def _needs_refresh(symbol: str, cache_dir: Path, refresh_days: int) -> bool:
    """Check if symbol data needs refresh based on file modification time.
    
    Args:
        symbol: Symbol to check
        cache_dir: Directory containing cached data files
        refresh_days: Days before refresh is needed
        
    Returns:
        True if symbol needs refresh
    """
    cache_file = cache_dir / f"{symbol}.NS.csv"
    
    try:
        if not cache_file.exists():
            return True # Needs refresh if file doesn't exist

        # If exists, check modification time
        file_modified_timestamp = cache_file.stat().st_mtime
        file_modified_date = datetime.fromtimestamp(file_modified_timestamp)
        cutoff_date = datetime.now() - timedelta(days=refresh_days)

        return file_modified_date < cutoff_date # Needs refresh if older than cutoff

    except OSError: # Catch OS errors from .exists() or .stat()
        logger.warning(f"OSError checking cache status for {symbol}, assuming refresh needed.")
        return True # Assume refresh is needed if we can't check
    except ValueError: # Catch potential errors from fromtimestamp
        logger.warning(f"ValueError checking cache status for {symbol}, assuming refresh needed.")
        return True


def _add_ns_suffix(symbol: str) -> str:
    """Add .NS suffix for yfinance compatibility.
    
    Args:
        symbol: NSE symbol
        
    Returns:
        Symbol with .NS suffix
    """
    if symbol.startswith('^'):  # Handle indices like ^NSEI
        return symbol
    return f"{symbol}.NS" if not symbol.endswith('.NS') else symbol


def _fetch_symbol_data(symbol: str, years: int, freeze_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Fetch data for single symbol using yfinance.
    
    Args:
        symbol: Symbol to fetch (with .NS suffix)
        years: Years of historical data to fetch
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """    # Import yfinance here to avoid startup cost
    import yfinance as yf
    
    try:
        end_date = freeze_date or date.today()
        start_date = end_date - timedelta(days=years * 365)
        
        data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)
        
        if data.empty:
            logger.warning(f"No data returned for {symbol}")
            return None
        # Standardize columns: reset index to get 'Date', then lowercase all columns.
        data = data.reset_index()
        # Handle potential MultiIndex or tuple columns from yfinance by checking each column name
        data.columns = [
            col[0].lower() if isinstance(col, tuple) else str(col).lower()
            for col in data.columns
        ]
        
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            logger.error(f"Missing required columns for {symbol}: {data.columns}")
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


def _validate_data_quality(data: pd.DataFrame, symbol: str) -> bool:
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
    if 'date' in data.columns:
        date_series = data.sort_values('date')['date']
    elif isinstance(data.index, pd.DatetimeIndex):
        date_series = data.index.to_series().sort_values()
    else:
        # Cannot determine date series for gap check
        logger.warning(f"Could not determine date series for gap check for {symbol}")
        # Assuming True if date series cannot be determined, to not fail valid data.
        # This case should ideally not happen with standardized data.
        date_series = pd.Series(dtype='datetime64[ns]') # Empty series to avoid error, max_gap_days will be NaN

    max_gap_days = date_series.diff().dt.days.max()
    if pd.notna(max_gap_days) and max_gap_days > 5:
        logger.warning(f"Large data gap detected for {symbol}: {max_gap_days} days")
        return False
    
    return True


def _save_symbol_cache(symbol: str, data: pd.DataFrame, cache_dir: Path) -> bool:
    """Save symbol data to cache file.
    
    Args:
        symbol: Symbol name (without .NS suffix)
        data: DataFrame to save (should have 'date' column, not as index)
        cache_dir: Directory to save cached data files
        
    Returns:
        True if save successful
    """
    cache_file = cache_dir / f"{symbol}.NS.csv"
    
    try:
        # Ensure data has 'date' as column, not index
        if data.index.name == 'date' or isinstance(data.index, pd.DatetimeIndex):
            # Reset index to make date a column
            data_to_save = data.reset_index()
            if data_to_save.columns[0] != 'date':
                data_to_save = data_to_save.rename(columns={data_to_save.columns[0]: 'date'})
        else:
            data_to_save = data.copy()
        
        # Save without index to avoid "Unnamed: 0" columns
        data_to_save.to_csv(cache_file, index=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save cache for {symbol}: {e}")
        return False


def _load_symbol_cache(symbol: str, cache_dir: Path) -> pd.DataFrame:
    """Load symbol data from cache file."""
    cache_file = cache_dir / f"{symbol}.NS.csv"
    data = pd.read_csv(cache_file)
    
    # Clean up any unnamed index columns that might have been saved accidentally
    unnamed_cols = [col for col in data.columns if col.startswith('Unnamed:')]
    if unnamed_cols:
        logger.debug(f"Removing unnamed columns from {symbol}: {unnamed_cols}")
        data = data.drop(columns=unnamed_cols)
    
    # Set the date column as index and parse as datetime
    if 'date' in data.columns:
        data['date'] = pd.to_datetime(data['date'])
        data = data.set_index('date')
    else:
        # Fallback to treating first column as date index
        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    
    # Enforce lowercase column names to ensure a consistent data contract
    data.columns = [str(col).lower() for col in data.columns]
    
    return data


def _fetch_and_store_data(
    symbol: str, years: int, freeze_date: Optional[date], cache_path: Path
) -> bool:
    """Fetch, validate, and store data for a single symbol."""
    symbol_with_suffix = _add_ns_suffix(symbol)

    # Fetch data with retry logic
    fetched_data = None
    for attempt in range(3):  # Max 3 retries
        fetched_data = _fetch_symbol_data(symbol_with_suffix, years, freeze_date)
        if fetched_data is not None:
            break

        if attempt < 2:  # Don't sleep on final attempt
            time.sleep(2 ** attempt)  # Exponential backoff

    if fetched_data is not None and _validate_data_quality(fetched_data, symbol):
        success = _save_symbol_cache(symbol, fetched_data, cache_path)
        if not success:
            logger.warning(f"Failed to save cache for {symbol}")
        return success
    
    logger.warning(f"Failed to fetch or validate data for {symbol}")
    return False


def _log_refresh_summary(results: Dict[str, bool], total_to_fetch: int) -> None:
    """Log the summary of the data refresh operation."""
    successful = sum(1 for success in results.values() if success)
    logger.info(f"Successfully refreshed {successful}/{total_to_fetch} symbols")


def refresh_market_data(
    universe_path: Union[str, List[str]],
    cache_dir: str,
    years: int = 3,
    refresh_days: int = 7,
    freeze_date: Optional[date] = None,
) -> Dict[str, bool]:
    """Fetch latest data for symbols with intelligent caching.
    
    Args:
        universe_path: Path to universe CSV file or list of symbols
        cache_dir: Directory for cached data files
        years: Years of historical data to fetch
        refresh_days: Days before cache refresh
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        Dict mapping symbol -> success status
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    # Load symbols from universe_path
    if isinstance(universe_path, list):
        symbols = universe_path
    else:
        symbols = load_universe(universe_path)
    
    # Skip cache refresh in freeze mode to maintain repeatability
    if freeze_date is not None:
        logger.info("Freeze mode active, skipping cache refresh")
        return {symbol: True for symbol in symbols}
    
    # Filter symbols that need refresh
    symbols_to_fetch = [
        symbol for symbol in symbols 
        if _needs_refresh(symbol, cache_path, refresh_days)
    ]
    
    if not symbols_to_fetch:
        logger.info("All symbols are fresh, no refresh needed")
        return {symbol: True for symbol in symbols}
    
    logger.info(f"Refreshing {len(symbols_to_fetch)} of {len(symbols)} symbols")
    
    results = {
        symbol: _fetch_and_store_data(symbol, years, freeze_date, cache_path)
        for symbol in symbols_to_fetch
    }
    
    _log_refresh_summary(results, len(symbols_to_fetch))
    
    return results
