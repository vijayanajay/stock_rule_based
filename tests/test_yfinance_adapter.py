"""Tests for yfinance adapter."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from kiss_signal.adapters import yfinance_adapter


class TestYFinanceAdapter:
    """Test cases for yfinance adapter functions."""

    def test_add_ns_suffix(self):
        """Test NS suffix addition."""
        assert yfinance_adapter._add_ns_suffix("RELIANCE") == "RELIANCE.NS"
        assert yfinance_adapter._add_ns_suffix("RELIANCE.NS") == "RELIANCE.NS"

    @patch('yfinance.download')
    def test_fetch_symbol_data_multiindex_columns(self, mock_download):
        """Test fetch_symbol_data handles MultiIndex columns correctly."""
        # Mock yfinance download with MultiIndex columns (common yfinance behavior)
        mock_data = pd.DataFrame({
            ('Open', 'RELIANCE.NS'): [100, 101, 102],
            ('High', 'RELIANCE.NS'): [105, 106, 107],
            ('Low', 'RELIANCE.NS'): [95, 96, 97],
            ('Close', 'RELIANCE.NS'): [102, 103, 104],
            ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, name='Date'))
        
        # Create MultiIndex columns to simulate yfinance behavior
        mock_data.columns = pd.MultiIndex.from_tuples(mock_data.columns)
        mock_download.return_value = mock_data
        
        result = yfinance_adapter.fetch_symbol_data("RELIANCE", 1)
        
        # Should successfully handle MultiIndex and return standardized data
        assert result is not None
        assert len(result) == 3
        expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        assert all(col in result.columns for col in expected_columns)
        assert result['open'].iloc[0] == 100
        assert result['close'].iloc[2] == 104
        mock_download.assert_called_once()

    @patch('yfinance.download')
    def test_fetch_symbol_data_tuple_columns(self, mock_download):
        """Test fetch_symbol_data handles tuple columns correctly."""
        # Mock yfinance download with tuple columns (edge case)
        mock_data = pd.DataFrame({
            ('Open', 'RELIANCE.NS'): [100, 101, 102],
            ('High', 'RELIANCE.NS'): [105, 106, 107],
            ('Low', 'RELIANCE.NS'): [95, 96, 97],
            ('Close', 'RELIANCE.NS'): [102, 103, 104],
            ('Volume', 'RELIANCE.NS'): [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, name='Date'))
        
        # Force tuple columns (not MultiIndex) to test edge case
        mock_data.columns = [('Open', 'RELIANCE.NS'), ('High', 'RELIANCE.NS'), 
                           ('Low', 'RELIANCE.NS'), ('Close', 'RELIANCE.NS'), 
                           ('Volume', 'RELIANCE.NS')]
        mock_download.return_value = mock_data
        
        result = yfinance_adapter.fetch_symbol_data("RELIANCE", 1)
        
        # Should successfully handle tuple columns and return standardized data
        assert result is not None
        assert len(result) == 3
        expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        assert all(col in result.columns for col in expected_columns)
        mock_download.assert_called_once()
