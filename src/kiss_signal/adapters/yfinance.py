"""YFinance adapter for fetching market data.

This module isolates the network I/O operations for fetching market data
from yfinance, following H-21 architecture principle.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_symbol_data(symbol: str, years: int, freeze_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Fetch data for single symbol using yfinance.
    
    Args:
        symbol: Symbol to fetch (with .NS suffix)
        years: Years of historical data to fetch
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    # Import yfinance here to avoid startup cost
    import yfinance as yf
    import time
    
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            end_date = freeze_date or date.today()
            start_date = end_date - timedelta(days=years * 365)
            
            # Add session parameter to help with connection issues
            data = yf.download(
                symbol, 
                start=start_date, 
                end=end_date, 
                auto_adjust=True,
                progress=False  # Disable progress bar to reduce noise
            )
            
            if data.empty:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Empty data for {symbol}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.warning(f"No data returned for {symbol} after {max_retries} attempts")
                    return None
                    
            # Standardize columns: reset index to get 'Date', then lowercase all columns.
            data = data.reset_index()
            # Handle potential MultiIndex or tuple columns from yfinance by checking each column name
            new_columns = []
            for col in data.columns:
                if isinstance(col, tuple):
                    # For MultiIndex, take the first level
                    new_columns.append(col[0].lower())
                else:
                    new_columns.append(str(col).lower())
            data.columns = new_columns
            
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
            # Handle volume conversion with consistent NA handling (same as price data)
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce').astype('Int64')
            
            return data
            
        except Exception as e:
            error_msg = str(e)
            
            # Classify error types for better handling
            if "YFTzMissingError" in error_msg or "timezone" in error_msg.lower():
                logger.warning(f"Yahoo Finance timezone error for {symbol}: {error_msg}")
            elif "404" in error_msg or "delisted" in error_msg.lower():
                logger.warning(f"Symbol {symbol} may be delisted or invalid: {error_msg}")
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                logger.warning(f"Network timeout for {symbol}: {error_msg}")
            else:
                logger.error(f"Failed to fetch data for {symbol}: {error_msg}")
            
            # Retry with exponential backoff for retryable errors
            if attempt < max_retries - 1 and ("timeout" in error_msg.lower() or "connection" in error_msg.lower() or "YFTzMissingError" in error_msg):
                delay = base_delay * (2 ** attempt)
                logger.debug(f"Retrying {symbol} in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            else:
                # For non-retryable errors or final attempt, return None
                return None
    
    # This line is unreachable in normal operation since every code path above has a return
    # It serves as a safety fallback and defensive programming practice
    return None  # pragma: no cover
