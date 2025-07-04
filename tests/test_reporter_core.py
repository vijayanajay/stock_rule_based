"""
Tests for the reporter module - Core functionality.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import pandas as pd

from src.kiss_signal import reporter
from src.kiss_signal.config import Config


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


@pytest.fixture
def sample_config(tmp_path: Path):
    """Sample config for testing."""
    universe_file = tmp_path / "test_universe.txt"
    universe_file.write_text("symbol\nRELIANCE\n")
    return Config(
        universe_path=str(tmp_path / "test_universe.txt"),
        historical_data_years=3,
        cache_dir=str(tmp_path / "test_cache/"),
        cache_refresh_days=7,
        hold_period=20,
        min_trades_threshold=10,
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        database_path=str(tmp_path / "test.db"),
        reports_output_dir=str(tmp_path / "test_reports/"),
        edge_score_threshold=0.50
    )


@pytest.fixture
def sample_rules_config():
    """Sample rules configuration."""
    return [
        {
            'name': 'sma_10_20_crossover',
            'type': 'sma_crossover',
            'params': {'short_window': 10, 'long_window': 20}
        },
        {
            'name': 'rsi_oversold_30',
            'type': 'rsi_oversold',
            'params': {'period': 14, 'threshold': 30}
        }
    ]


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    dates = pd.date_range('2025-01-01', periods=30, freq='D')
    return pd.DataFrame({
        'open': [100 + i for i in range(30)],
        'high': [105 + i for i in range(30)],
        'low': [95 + i for i in range(30)],
        'close': [102 + i for i in range(30)],
        'volume': [1000000] * 30
    }, index=dates)


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Provides a consistent mock DataFrame for signal testing."""
    dates = pd.to_datetime(pd.date_range(end=date.today(), periods=50, freq='D'))
    return pd.DataFrame({
        'open': [100] * 50, 'high': [100] * 50, 'low': [100] * 50,
        'close': [100 + i for i in range(50)], 'volume': [1000] * 50
    }, index=dates)


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
        db_path = tmp_path / "nonexistent.db"
        
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


class TestReportFormatting:
    """Tests for markdown table formatting functions."""

    def test_format_new_buys_table_empty(self):
        """Test formatting new buys table with no signals."""
        result = reporter._format_new_buys_table([])
        assert result == "*No new buy signals found.*"

    def test_format_open_positions_table_empty(self):
        """Test formatting open positions table with no positions."""
        result = reporter._format_open_positions_table([], 20)
        assert result == "*No open positions.*"

    def test_format_sell_positions_table_empty(self):
        """Test formatting sell positions table with no positions."""
        result = reporter._format_sell_positions_table([], 20)
        assert result == "*No positions to sell.*"

    def test_format_open_positions_table_with_na(self):
        """Test formatting open positions with N/A values."""
        positions = [{
            'symbol': 'TEST', 'entry_date': '2025-01-01', 'entry_price': 100.0,
            'current_price': None, 'return_pct': None, 'nifty_return_pct': None,
            'days_held': 5
        }]
        result = reporter._format_open_positions_table(positions, 20)
        assert "N/A" in result


class TestFindSignalsInWindow:
    """Tests the _find_signals_in_window helper function."""

    def test_single_rule_with_signal(self, mock_price_data):
        """Test that a single rule producing a signal is handled correctly."""
        rule_stack = [{'type': 'sma_crossover', 'params': {}}]
        mock_signals = pd.Series([False] * 49 + [True], index=mock_price_data.index)

        with patch('src.kiss_signal.rules.sma_crossover', return_value=mock_signals) as mock_rule_func:
            result = reporter._find_signals_in_window(mock_price_data, rule_stack)
            mock_rule_func.assert_called_once()
            assert result.sum() == 1
            assert result.iloc[-1]

    def test_multiple_rules_and_logic(self, mock_price_data):
        """Test that multiple rules are correctly combined with AND logic."""
        rule_stack = [
            {'type': 'sma_crossover', 'params': {}},
            {'type': 'rsi_oversold', 'params': {}}
        ]
        signals_a = pd.Series([False, True, True, False], index=mock_price_data.index[:4])
        signals_b = pd.Series([False, True, False, True], index=mock_price_data.index[:4])

        with patch('src.kiss_signal.rules.sma_crossover', return_value=signals_a), \
             patch('src.kiss_signal.rules.rsi_oversold', return_value=signals_b):
            result = reporter._find_signals_in_window(mock_price_data.head(4), rule_stack)
            
            # Expected result is a logical AND of signals_a and signals_b
            expected = pd.Series([False, True, False, False], index=mock_price_data.index[:4])
            pd.testing.assert_series_equal(result, expected)
            assert result.sum() == 1

    def test_no_signals_produced(self, mock_price_data):
        """Test behavior when no rules trigger a signal."""
        rule_stack = [{'type': 'sma_crossover', 'params': {}}]
        mock_signals = pd.Series(False, index=mock_price_data.index)

        with patch('src.kiss_signal.rules.sma_crossover', return_value=mock_signals):
            result = reporter._find_signals_in_window(mock_price_data, rule_stack)
            assert result.sum() == 0

    def test_empty_data_or_rules(self, mock_price_data):
        """Test that empty inputs are handled gracefully."""
        # Empty rule stack
        result_empty_rules = reporter._find_signals_in_window(mock_price_data, [])
        assert result_empty_rules.sum() == 0

        # Empty price data
        result_empty_data = reporter._find_signals_in_window(pd.DataFrame(), [{'type': 'sma', 'params': {}}])
        assert result_empty_data.empty


class TestIdentifyNewSignalsWithWindow:
    """Tests the modified _identify_new_signals function."""

    @pytest.fixture
    def setup_db(self, tmp_path: Path):
        """Creates a temporary database with one optimal strategy."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """
)
            conn.execute(
                "INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('TEST', '[{"name": "test_rule", "type": "sma_crossover", "params": {}}]', 0.8, 'test_run', 0.6, 1.5, 20, 0.02)
            )
        return db_path

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_finds_signal_within_hold_period(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify a signal within the hold_period window is reported."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20 # Explicitly set for clarity
        
        # Mock data and signals
        mock_get_price.return_value = mock_price_data
        
        # Signal is 5 days ago (within 20-day window)
        signal_date = date.today() - timedelta(days=5)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date] = True
        
        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config) # type: ignore

            assert len(result) == 1
            assert result[0]['ticker'] == 'TEST'
            assert result[0]['date'] == signal_date.strftime('%Y-%m-%d')

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_ignores_signal_outside_hold_period(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify a signal outside the hold_period window is ignored."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20

        mock_get_price.return_value = mock_price_data
        
        # Signal is 25 days ago (outside 20-day window)
        signal_date = date.today() - timedelta(days=25)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date] = True

        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config) # type: ignore
            assert len(result) == 0

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_finds_multiple_recent_signals(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify multiple signals within the window are all reported."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20

        mock_get_price.return_value = mock_price_data
        
        # Signals at 3 and 10 days ago
        signal_date_1 = date.today() - timedelta(days=3)
        signal_date_2 = date.today() - timedelta(days=10)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date_1] = True
        signals.loc[signals.index.date == signal_date_2] = True

        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config) # type: ignore
            
            assert len(result) == 2
            dates_found = {r['date'] for r in result}
            assert signal_date_1.strftime('%Y-%m-%d') in dates_found
            assert signal_date_2.strftime('%Y-%m-%d') in dates_found
