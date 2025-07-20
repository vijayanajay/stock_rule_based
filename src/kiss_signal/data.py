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

__all__ = ["get_price_data", "refresh_market_data", "load_universe", "get_market_data"]

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
            symbol_with_suffix = _add_ns_suffix(symbol)
            data = _fetch_symbol_data(symbol_with_suffix, years)
            if data is not None:
                _save_symbol_cache(symbol, data, cache_dir)
            else:
                raise ValueError(f"Failed to fetch data for {symbol}")
    else:
        # Load from cache
        data = _load_symbol_cache(symbol, cache_dir)
    
    # Apply date filtering with robust index handling
    if start_date:
        start_timestamp = pd.to_datetime(start_date)
        # Ensure index is datetime for proper comparison
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        data = data[data.index >= start_timestamp]    
    if end_date:
        end_timestamp = pd.to_datetime(end_date)
        # Ensure index is datetime for proper comparison
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        data = data[data.index <= end_timestamp]
    
    # Apply freeze date restriction
    if freeze_date:
        # Ensure index is datetime for proper comparison
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        data = data[data.index <= pd.to_datetime(freeze_date)]
    
    if data.empty:
        raise ValueError(f"No data available for {symbol} in requested date range")
    
    # Only log in verbose mode for individual symbol data serving
    # Skip warning for NIFTY index as it's used for benchmark calculations with short date ranges
    # Also skip warning during position tracking (when both start_date and end_date are specified)
    # as limited rows are expected when filtering to position date ranges
    is_position_tracking = start_date is not None and end_date is not None
    if len(data) < 50 and not symbol.startswith('^NSEI') and not is_position_tracking:
        logger.warning(f"Limited data for {symbol}: only {len(data)} rows")
    elif len(data) < 50 and is_position_tracking:
        logger.debug(f"Position tracking data for {symbol}: {len(data)} rows from {start_date} to {end_date}")
    
    return data


def _needs_refresh(symbol: str, cache_dir: Path, refresh_days: int) -> bool:
    """Check if symbol data needs refresh - refreshes once per day.
    
    Args:
        symbol: Symbol to check
        cache_dir: Directory containing cached data files
        refresh_days: DEPRECATED - kept for compatibility, always uses daily refresh
        
    Returns:
        True if symbol needs refresh (file doesn't exist or wasn't modified today)
    """
    cache_file = cache_dir / f"{symbol}.NS.csv"
    
    try:
        if not cache_file.exists():
            return True # Needs refresh if file doesn't exist

        # Check if file was modified today
        file_modified_timestamp = cache_file.stat().st_mtime
        file_modified_date = datetime.fromtimestamp(file_modified_timestamp).date()
        today = datetime.now().date()

        return file_modified_date < today # Needs refresh if not modified today

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
    """Fetch data for single symbol using yfinance adapter.
    
    Args:
        symbol: Symbol to fetch (with .NS suffix)
        years: Years of historical data to fetch
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    from .adapters.yfinance import fetch_symbol_data
    return fetch_symbol_data(symbol, years, freeze_date)


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
    negative_prices = (data[price_cols] < 0).any(axis=None)
    if negative_prices:
        logger.warning(f"Negative prices detected for {symbol}")
        return False
    
    # Check for zero volume days - handle potential nullable integers
    try:
        volume_column = data['volume']
        # Handle both regular and nullable integer columns
        if hasattr(volume_column, 'isna'):
            # For nullable integer columns, handle NA values
            zero_volume_mask = (volume_column == 0) & (~volume_column.isna())
            zero_volume_count = int(zero_volume_mask.sum())
        else:
            # For regular columns
            zero_volume_count = int((volume_column == 0).sum())
        
        if zero_volume_count > len(data) * 0.1:
            logger.warning(f"High zero-volume days for {symbol}")
            return False
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not validate volume data for {symbol}: {e}")
        # Continue validation even if volume check fails
        pass
    
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
        
        # Convert nullable Int64 volume to regular int to avoid CSV save issues
        if 'volume' in data_to_save.columns:
            volume_col = data_to_save['volume']
            if hasattr(volume_col, 'dtype') and str(volume_col.dtype) == 'Int64':
                data_to_save['volume'] = volume_col.fillna(0).astype(int)
            elif hasattr(volume_col, 'isna') and volume_col.isna().any(axis=None):
                # Handle any nullable columns that might have NA values
                data_to_save['volume'] = volume_col.fillna(0).astype(int)
        
        # Also ensure all numeric columns are regular types for CSV compatibility
        for col in ['open', 'high', 'low', 'close']:
            if col in data_to_save.columns:
                col_data = data_to_save[col]
                if hasattr(col_data, 'isna') and col_data.isna().any(axis=None):
                    data_to_save[col] = col_data.fillna(0).astype(float)
        
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
        # Handle potentially invalid dates gracefully
        data['date'] = pd.to_datetime(data['date'], format='%Y-%m-%d', errors='coerce')
        # Drop rows with invalid dates (NaT values)
        data = data.dropna(subset=['date'])
        if data.empty:
            raise ValueError(f"No valid date data found for {symbol}")
        data = data.set_index('date')
    else:
        # Fallback to treating first column as date index
        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    
    # Ensure index is properly converted to DatetimeIndex
    # This fixes the '>=' not supported between instances of 'numpy.ndarray' and 'Timestamp' error
    if not isinstance(data.index, pd.DatetimeIndex):
        try:
            data.index = pd.to_datetime(data.index)
        except Exception as e:
            logger.warning(f"Failed to convert index to datetime for {symbol}: {e}")
            # If conversion fails, try to parse the index as strings with error handling
            data.index = pd.to_datetime(data.index, errors='coerce')
            # Drop any rows with invalid dates
            data = data.dropna()
            if data.empty:
                raise ValueError(f"No valid date data found for {symbol}")
    
    # Enforce lowercase column names to ensure a consistent data contract
    data.columns = [str(col).lower() for col in data.columns]
    
    # Ensure numeric columns are properly typed (fix for string division errors)
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Drop any rows where all numeric columns are NaN (invalid data)
    data = data.dropna(subset=[col for col in numeric_columns if col in data.columns], how='all')
    
    if data.empty:
        raise ValueError(f"No valid numeric data found for {symbol}")
    
    return data


def _fetch_and_store_data(
    symbol: str, years: int, freeze_date: Optional[date], cache_path: Path
) -> bool:
    """Fetch, validate, and store data for a single symbol."""
    symbol_with_suffix = _add_ns_suffix(symbol)

    # Fetch data with improved retry logic
    fetched_data = None
    max_retries = 3
    
    for attempt in range(max_retries):
        fetched_data = _fetch_symbol_data(symbol_with_suffix, years, freeze_date)
        if fetched_data is not None:
            break

        if attempt < max_retries - 1:  # Don't sleep on final attempt
            delay = 1 + (attempt * 0.5)  # Progressive delay: 1s, 1.5s, 2s
            logger.debug(f"Retrying {symbol} in {delay}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)

    if fetched_data is not None and _validate_data_quality(fetched_data, symbol):
        success = _save_symbol_cache(symbol, fetched_data, cache_path)
        if not success:
            logger.warning(f"Failed to save cache for {symbol}")
        return success
    
    # Log more informative warnings
    if fetched_data is None:
        logger.warning(f"Failed to fetch data for {symbol} after {max_retries} attempts")
    else:
        logger.warning(f"Data validation failed for {symbol}")
    
    return False


def _log_refresh_summary(results: Dict[str, bool], total_to_fetch: int) -> None:
    """Log the summary of the data refresh operation."""
    successful = sum(1 for success in results.values() if success)
    logger.info(f"Successfully refreshed {successful}/{total_to_fetch} symbols")


def _get_symbols_to_fetch(symbols: List[str], cache_path: Path, refresh_days: int) -> List[str]:
    """Filter a list of symbols to only those that need a data refresh."""
    return [
        symbol for symbol in symbols
        if _needs_refresh(symbol, cache_path, refresh_days)
    ]


def _fetch_data_for_symbols(
    symbols_to_fetch: List[str], years: int, freeze_date: Optional[date], cache_path: Path
) -> Dict[str, bool]:
    """Fetch and store data for a list of symbols, returning the results."""
    if not symbols_to_fetch:
        logger.info("All symbols are fresh, no refresh needed")
        return {}

    logger.info(f"Refreshing {len(symbols_to_fetch)} symbols")
    
    results = {}
    for i, symbol in enumerate(symbols_to_fetch):
        # Add rate limiting between requests
        if i > 0:
            time.sleep(0.5)  # 500ms delay between requests to avoid rate limiting
            
        logger.debug(f"Fetching {symbol} ({i+1}/{len(symbols_to_fetch)})")
        results[symbol] = _fetch_and_store_data(symbol, years, freeze_date, cache_path)
    
    return results


def refresh_market_data(
    universe_path: Union[str, List[str]],
    cache_dir: str,
    years: int = 3,
    refresh_days: int = 2,
    freeze_date: Optional[date] = None,
) -> Dict[str, bool]:
    """Refresh market data for all symbols in the universe."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    symbols = universe_path if isinstance(universe_path, list) else load_universe(universe_path)
    
    if freeze_date is not None:
        logger.info("Freeze mode active, skipping cache refresh")
        return {symbol: True for symbol in symbols}
    
    symbols_to_fetch = _get_symbols_to_fetch(symbols, cache_path, refresh_days)
    results = _fetch_data_for_symbols(symbols_to_fetch, years, freeze_date, cache_path)
    _log_refresh_summary(results, len(symbols_to_fetch))
    return {symbol: results.get(symbol, True) for symbol in symbols}


def get_market_data(
    index_symbol: str,
    cache_dir: Path,
    years: int = 1,
    freeze_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get market index data for context filtering.
    
    Simplified version of get_price_data specifically for market indices.
    
    Args:
        index_symbol: Market index symbol (e.g., '^NSEI')
        cache_dir: Path to cache directory
        years: Number of years of data
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with market index OHLCV data
        
    Raises:
        ValueError: If market data cannot be fetched
        FileNotFoundError: If cache doesn't exist in freeze mode
    """
    # Use different cache filename pattern for indices
    cache_file = cache_dir / f"{index_symbol.replace('^', 'INDEX_')}.csv"
    
    # Same logic as get_price_data but for market indices
    if freeze_date or not _needs_refresh(index_symbol, cache_dir, 30):
        if cache_file.exists():
            return _load_market_cache(cache_file)
    
    if freeze_date:
        # In freeze mode, don't download new data
        if not cache_file.exists():
            raise FileNotFoundError(f"Cached market data not found for {index_symbol} (freeze mode)")
    
    # Download fresh data
    logger.info(f"Downloading market index data for {index_symbol}")
    data = _fetch_symbol_data(index_symbol, years)
    if data is not None:
        _save_market_cache(data, cache_file)
        return data
    else:
        raise ValueError(f"Failed to fetch market data for {index_symbol}")


def _load_market_cache(cache_file: Path) -> pd.DataFrame:
    """Load market index data from cache."""
    try:
        data = pd.read_csv(cache_file)
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'], errors='coerce')
            data = data.dropna(subset=['date']).set_index('date')
        else:
            # Fallback for old format where date was the index
            data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    except Exception as e:
        logger.error(f"Failed to load market cache from {cache_file}: {e}")
        raise ValueError(f"Corrupted market cache file: {cache_file}") from e
    if data.empty:
        raise ValueError(f"Empty or invalid cache file: {cache_file}")
    return data


def _save_market_cache(data: pd.DataFrame, cache_file: Path) -> None:
    """Save market index data to cache."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        # Reset index to save datetime index as 'date' column to match load expectations
        data_to_save = data.reset_index()
        if data_to_save.index.name or 'date' not in data_to_save.columns:
            data_to_save = data_to_save.rename(columns={data_to_save.columns[0]: 'date'})
        data_to_save.to_csv(cache_file, index=False)
        logger.debug(f"Saved market cache to {cache_file}")
    except Exception as e:
        logger.error(f"Failed to save market cache to {cache_file}: {e}")
        raise
