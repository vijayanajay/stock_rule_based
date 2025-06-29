"""
Tests for the reporter module - Fetching Best Strategies.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sqlite3
# pandas is not directly used in TestFetchBestStrategies but _fetch_best_strategies returns list of dicts
# from pandas data, so it's indirectly related. Keeping it for now.
import pandas as pd

from src.kiss_signal import reporter
# Config is not directly used by TestFetchBestStrategies, can be removed if not needed by fixtures later
# from src.kiss_signal.config import Config


@pytest.fixture
def sample_strategies():
    """Sample strategy data for testing."""
    return [
        {
            'symbol': 'RELIANCE',
            'rule_stack': '["sma_10_20_crossover"]',
            'edge_score': 0.68,
            'win_pct': 0.65,
            'sharpe': 1.2,
            'total_trades': 45,
            'avg_return': 0.025
        },
        {
            'symbol': 'INFY',
            'rule_stack': '["rsi_oversold_30"]',
            'edge_score': 0.55,
            'win_pct': 0.60,
            'sharpe': 1.0,
            'total_trades': 38,
            'avg_return': 0.020
        }
    ]

# sample_config fixture might not be needed here if TestFetchBestStrategies doesn't use it.
# For now, I'll keep it minimal. If tests break, I'll add it back or move to conftest.

class TestFetchBestStrategies:
    """Test _fetch_best_strategies private function."""

    def test_fetch_strategies_success(self, tmp_path, sample_strategies):
        """Test successful strategy fetching."""
        db_path = tmp_path / "test.db"

        # Create test database
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT,
                    rule_stack TEXT,
                    edge_score REAL,
                    win_pct REAL,
                    sharpe REAL,
                    total_trades INTEGER,
                    avg_return REAL,
                    run_timestamp TEXT
                )
            """)

            # Insert test data
            for strategy in sample_strategies:
                conn.execute("""
                    INSERT INTO strategies
                    (symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, run_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy['symbol'],
                    strategy['rule_stack'],
                    strategy['edge_score'],
                    strategy['win_pct'],
                    strategy['sharpe'],
                    strategy['total_trades'],
                    strategy['avg_return'],
                    'test_timestamp'
                ))

        # Test fetch
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)

        assert len(result) == 2
        # The query orders by symbol, so INFY comes before RELIANCE
        assert result[0]['symbol'] == 'INFY'
        assert result[1]['symbol'] == 'RELIANCE'

    def test_fetch_strategies_threshold_filtering(self, tmp_path, sample_strategies):
        """Test threshold filtering."""
        db_path = tmp_path / "test.db"

        # Create test database with one strategy below threshold
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT,
                    rule_stack TEXT,
                    edge_score REAL,
                    win_pct REAL,
                    sharpe REAL,
                    total_trades INTEGER,
                    avg_return REAL,
                    run_timestamp TEXT
                )
            """)

            for strategy in sample_strategies:
                conn.execute("""
                    INSERT INTO strategies
                    (symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, run_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy['symbol'],
                    strategy['rule_stack'],
                    strategy['edge_score'],
                    strategy['win_pct'],
                    strategy['sharpe'],
                    strategy['total_trades'],
                    strategy['avg_return'],
                    'test_timestamp'
                ))

        # Test with higher threshold
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.60)

        assert len(result) == 1
        assert result[0]['symbol'] == 'RELIANCE'

    def test_fetch_strategies_no_results(self, tmp_path):
        """Test when no strategies are found."""
        db_path = tmp_path / "test.db"

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT,
                    rule_stack TEXT,
                    edge_score REAL,
                    win_pct REAL,
                    sharpe REAL,
                    total_trades INTEGER,
                    avg_return REAL,
                    run_timestamp TEXT
                )
            """)

        result = reporter._fetch_best_strategies(db_path, 'nonexistent_timestamp', 0.50)
        assert len(result) == 0

    def test_fetch_strategies_database_error(self, tmp_path):
        """Test database error handling."""
        db_path = tmp_path / "nonexistent.db" # File that cannot be opened as sqlite db

        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)
        assert len(result) == 0

    @patch('sqlite3.connect')
    def test_fetch_strategies_generic_exception(self, mock_connect, tmp_path):
        """Test generic exception handling during strategy fetching."""
        db_path = tmp_path / "test.db"
        db_path.touch() # Ensure file exists

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchall.side_effect = Exception("Generic fetch error")
        mock_connect.return_value.__enter__.return_value = mock_conn # For context manager

        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)
        assert len(result) == 0
        mock_connect.assert_called_once_with(str(db_path))
