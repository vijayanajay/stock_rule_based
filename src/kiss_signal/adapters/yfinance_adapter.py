"""Adapter for fetching data from Yahoo Finance."""

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

__all__ = ["fetch_symbol_data"]

logger = logging.getLogger(__name__)


def _add_ns_suffix(symbol: str) -> str:
    """Add .NS suffix for yfinance compatibility."""
    if symbol.startswith('^'):  # Handle indices like ^NSEI
        return symbol
    return f"{symbol}.NS" if not symbol.endswith('.NS') else symbol


def fetch_symbol_data(symbol: str, years: int, freeze_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Fetch data for single symbol using yfinance."""
    symbol_with_suffix = _add_ns_suffix(symbol)
    try:
        end_date = freeze_date or date.today()
        start_date = end_date - timedelta(days=years * 365)

        data = yf.download(symbol_with_suffix, start=start_date, end=end_date, auto_adjust=True)

        if data.empty:
            logger.warning(f"No data returned for {symbol}")
            return None

        data = data.reset_index()
        data.columns = [
            col[0].lower() if isinstance(col, tuple) else str(col).lower()
            for col in data.columns
        ]

        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            logger.error(f"Missing required columns for {symbol}: {data.columns}")
            return None

        data = data[required_columns].copy()

        data['date'] = pd.to_datetime(data['date'])
        for col in ['open', 'high', 'low', 'close']:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        data['volume'] = pd.to_numeric(data['volume'], errors='coerce').astype('Int64')

        return data

    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return None