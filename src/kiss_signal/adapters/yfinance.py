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
