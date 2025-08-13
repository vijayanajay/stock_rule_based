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


def _get_cache_filepath(symbol: str, cache_dir: Path) -> Path:
    """Generate cache file path for stock or index symbol."""
    if symbol.startswith("^"):
        return cache_dir / f"{symbol.replace('^', 'INDEX_')}.csv"
    return cache_dir / f"{symbol}.NS.csv"


def get_price_data(
    symbol: str,
    cache_dir: Path,
    years: int = 1,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    freeze_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get price data for a stock or index from cache or by fetching.
    
    Args:
        symbol: Stock symbol or index (e.g., 'RELIANCE' or '^NSEI')
        cache_dir: Path to cache directory
        years: Number of years of data
        start_date: Optional start date filter
        end_date: Optional end date filter
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        Standardized DataFrame with date index and OHLCV columns
        
    Raises:
        ValueError: If data is corrupted or invalid
        FileNotFoundError: If cache doesn't exist in freeze mode
    """
    cache_file = _get_cache_filepath(symbol, cache_dir)
    data = None
    should_fetch = True

    if not _needs_refresh(cache_file):
        try:
            data = _load_cache(symbol, cache_dir)
            
            # In freeze mode, use cached data if it exists and is valid
            if freeze_date:
                should_fetch = False  # Use whatever cache we have in freeze mode
            else:
                # NEW: In normal mode, validate if cached data is sufficient for requested history
                temp_data = data.copy()
                
                # Apply same datetime index logic as below to check coverage
                if "date" in temp_data.columns:
                    temp_data["date"] = pd.to_datetime(temp_data["date"], errors="coerce", format="mixed")
                    temp_data = temp_data.dropna(subset=["date"]).set_index("date")
                elif not isinstance(temp_data.index, pd.DatetimeIndex):
                    temp_data.index = pd.to_datetime(temp_data.index, errors="coerce", format="mixed")
                    temp_data = temp_data.dropna()
                
                if not temp_data.empty and isinstance(temp_data.index, pd.DatetimeIndex):
                    end_date_ref = date.today()
                    required_start_date = end_date_ref - timedelta(days=years * 365)

                    # Add a 7-day buffer for weekends/holidays
                    if temp_data.index.min().date() <= (required_start_date + timedelta(days=7)):
                        should_fetch = False  # Cache is valid and sufficient
                    else:
                        logger.info(f"Cache for {symbol} is insufficient. Re-fetching.")
                else:
                    logger.info(f"Cache for {symbol} has invalid date format. Re-fetching.")
        except (FileNotFoundError, ValueError, AttributeError):
            logger.warning(f"Could not load or validate cache for {symbol}. Re-fetching.")

    if should_fetch:
        if freeze_date:
            raise FileNotFoundError(f"Cached data not found for {symbol} (freeze mode)")

        logger.info(f"Downloading fresh data for {symbol}")
        symbol_with_suffix = _add_ns_suffix(symbol)
        fetched_data = _fetch_symbol_data(symbol_with_suffix, years, freeze_date)
        if fetched_data is not None and _validate_data_quality(fetched_data, symbol):
            _save_cache(symbol, fetched_data, cache_dir)
            data = fetched_data
        else:
            raise ValueError(f"Failed to fetch or validate data for {symbol}")
    
    # At this point, data should never be None
    if data is None:
        raise ValueError(f"No data available for {symbol}")
    
    # Ensure proper datetime index
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce", format="mixed")
        data = data.dropna(subset=["date"]).set_index("date")
    elif not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index, errors="coerce", format="mixed")
        data = data.dropna()
    
    # Apply date filters
    if freeze_date:
        data = data[data.index.date <= freeze_date]
    if start_date:
        data = data[data.index.date >= start_date]
    if end_date:
        data = data[data.index.date <= end_date]
    
    if data.empty:
        raise ValueError(f"No data available for {symbol} in requested date range")
    
    # Try to infer and set frequency for vectorbt compatibility
    if len(data) > 1:
        try:
            inferred_freq = pd.infer_freq(data.index)
            if inferred_freq:
                data.index.freq = inferred_freq
                logger.debug(f"Inferred frequency '{inferred_freq}' for {symbol}")
            else:
                # For irregular data (missing weekends/holidays), vectorbt needs frequency hint
                # Try business daily frequency for stock data
                logger.debug(f"Could not infer frequency for {symbol}. Forcing business day frequency ('B').")
                try:
                    # Business day frequency accounts for weekends being missing
                    data.index.freq = 'B'
                except ValueError:
                    # If business day doesn't work, leave as None and let vectorbt handle it
                    logger.debug(f"Business day frequency doesn't fit {symbol} data. Using irregular frequency.")
        except Exception as e:
            # If frequency setting fails, continue without it
            logger.debug(f"Frequency inference failed for {symbol}: {e}. Continuing with irregular frequency.")
    
    # Log warnings for limited data (with same logic as before)
    is_position_tracking = start_date is not None and end_date is not None
    if len(data) < 50 and not symbol.startswith('^NSEI') and not is_position_tracking:
        logger.warning(f"Limited data for {symbol}: only {len(data)} rows")
    elif len(data) < 50 and is_position_tracking:
        logger.debug(f"Position tracking data for {symbol}: {len(data)} rows from {start_date} to {end_date}")
    
    return data


def _needs_refresh(cache_file: Path) -> bool:
    """Check if symbol data needs refresh - refreshes once per day.
    
    Args:
        cache_file: Path to the cache file to check.
        
    Returns:
        True if symbol needs refresh (file doesn't exist or wasn't modified today)
    """
    try:
        if not cache_file.exists():
            return True # Needs refresh if file doesn't exist

        # Check if file was modified today
        file_modified_timestamp = cache_file.stat().st_mtime
        file_modified_date = datetime.fromtimestamp(file_modified_timestamp).date()
        today = datetime.now().date()

        return file_modified_date < today # Needs refresh if not modified today

    except OSError: # Catch OS errors from .exists() or .stat()
        logger.warning(f"OSError checking cache status for {cache_file.name}, assuming refresh needed.")
        return True # Assume refresh is needed if we can't check
    except ValueError: # Catch potential errors from fromtimestamp
        logger.warning(f"ValueError checking cache status for {cache_file.name}, assuming refresh needed.")
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


def _save_cache(symbol: str, data: pd.DataFrame, cache_dir: Path) -> bool:
    """Save standardized symbol data to a cache file."""
    cache_file = _get_cache_filepath(symbol, cache_dir)
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle DataFrame with DatetimeIndex - convert to 'date' column for CSV storage
        if isinstance(data.index, pd.DatetimeIndex):
            data_to_save = data.reset_index()
            if data_to_save.columns[0] != 'date':
                data_to_save = data_to_save.rename(columns={data_to_save.columns[0]: 'date'})
        else:
            # Data already has 'date' column, save as-is
            data_to_save = data.copy()
        
        data_to_save.to_csv(cache_file, index=False)
        logger.debug(f"Saved cache to {cache_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cache for {symbol}: {e}")
        return False


def _load_cache(symbol: str, cache_dir: Path) -> pd.DataFrame:
    """Load symbol data from a cache file, setting 'date' as the index."""
    cache_file = _get_cache_filepath(symbol, cache_dir)
    try:
        # Load the CSV file first
        df = pd.read_csv(cache_file)
        
        # Clean up any unnamed index columns
        unnamed_cols = [col for col in df.columns if col.startswith('Unnamed:')]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)
        
        # Handle date column and set as index
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')
            # Drop rows with invalid dates
            df = df.dropna(subset=['date'])
            df = df.set_index('date')
        else:
            # Fallback: try to parse first column as date
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Ensure index is DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, errors='coerce', format='mixed')
            df = df.dropna()
        
        if df.empty:
            raise ValueError(f"No valid data found in cache for {symbol}")
        return df
    except ValueError:
        # Re-raise ValueError exceptions (business logic errors) without masking
        raise
    except Exception as e:
        logger.error(f"Failed to load cache for {symbol}: {e}")
        raise ValueError(f"Corrupted cache file: {cache_file}") from e


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
        success = _save_cache(symbol, fetched_data, cache_path)
        if not success:
            logger.warning(f"Failed to save cache for {symbol}")
        return success
    
    # Log more informative warnings
    if fetched_data is None:
        logger.warning(f"Failed to fetch data for {symbol} after {max_retries} attempts")
    else:
        logger.warning(f"Data validation failed for {symbol}")
    
    return False


def refresh_market_data(
    universe_path: Union[str, List[str]],
    cache_dir: str,
    years: int = 3,
    freeze_date: Optional[date] = None,
) -> Dict[str, bool]:
    """Refresh market data for all symbols in the universe."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    symbols = universe_path if isinstance(universe_path, list) else load_universe(universe_path)
    
    if freeze_date is not None:
        logger.info("Freeze mode active, skipping cache refresh")
        return {symbol: True for symbol in symbols}
    
    # Filter symbols that need refresh
    symbols_to_fetch = [symbol for symbol in symbols if _needs_refresh(cache_path / f"{symbol}.NS.csv")]
    
    if not symbols_to_fetch:
        logger.info("All symbols are fresh, no refresh needed")
        return {symbol: True for symbol in symbols}

    logger.info(f"Refreshing {len(symbols_to_fetch)} symbols")
    
    # Fetch data for each symbol
    results = {}
    for i, symbol in enumerate(symbols_to_fetch):
        # Add rate limiting between requests
        if i > 0:
            time.sleep(0.5)  # 500ms delay between requests to avoid rate limiting
            
        logger.debug(f"Fetching {symbol} ({i+1}/{len(symbols_to_fetch)})")
        results[symbol] = _fetch_and_store_data(symbol, years, freeze_date, cache_path)
    
    # Log summary
    successful = sum(1 for success in results.values() if success)
    logger.info(f"Successfully refreshed {successful}/{len(symbols_to_fetch)} symbols")
    
    return {symbol: results.get(symbol, True) for symbol in symbols}



