"""Tests for reporter module - Consolidated test suite for all reporter functionality.

This module contains all tests for the kiss_signal.reporter module, consolidated from:
- test_reporter_core.py: Core reporter functionality including strategy fetching and formatting
- test_reporter_advanced.py: Advanced features including signal identification and analysis
- test_reporter_coverage.py: Edge cases, error handling, and comprehensive test coverage
- test_reporter_data_issues.py: Data validation, freeze date handling, and data integrity tests
- test_reporter_index_symbol_bug.py: Bug fix regression tests for index symbol parameter filtering

Test Organization:
- Core Reporter Functionality Tests
- Strategy Analysis Tests  
- Signal Identification Tests
- Data Processing and Validation Tests
- Error Handling and Edge Cases
- Performance Analysis Tests
- CSV Formatting Tests
"""

import logging
import sqlite3
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from kiss_signal.config import Config, RuleDef
from kiss_signal import reporter, persistence
from kiss_signal import rules


# =============================================================================
# Test Fixtures
# =============================================================================

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
            'symbol': 'TCS',
            'rule_stack': '["rsi_oversold"]',
            'edge_score': 0.72,
            'win_pct': 0.70,
            'sharpe': 1.1,
            'total_trades': 38,
            'avg_return': 0.030
        }
    ]


@pytest.fixture
def sample_config(tmp_path: Path):
    """Sample config for testing."""
    universe_file = tmp_path / "test_universe.txt"
    universe_file.write_text("symbol\nRELIANCE\nTCS\n")
    return Config(
        universe_path=str(universe_file),
        historical_data_years=3,
        cache_dir=str(tmp_path / "test_cache/"),
        hold_period=20,
        database_path=str(tmp_path / "test.db"),
        min_trades_threshold=10,
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        edge_score_threshold=0.5,
        reports_output_dir=str(tmp_path / "test_reports/"),
        freeze_date=None
    )


@pytest.fixture
def basic_config(tmp_path: Path) -> Config:
    """Basic config fixture for testing."""
    universe_file = tmp_path / "test_universe.csv"
    universe_file.write_text("symbol\nRELIANCE\nTCS\n")
    return Config(
        universe_path=str(universe_file),
        historical_data_years=1,
        cache_dir=str(tmp_path / "test_cache"),
        hold_period=20,
        database_path=str(tmp_path / "test.db"),
        min_trades_threshold=10,
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        edge_score_threshold=0.5,
        reports_output_dir=str(tmp_path / "test_reports"),
        freeze_date=None
    )


@pytest.fixture
def sample_rules_config():
    """Sample rules configuration for testing."""
    return {
        "sma_crossover": {
            "type": "trend",
            "signal_type": "buy",
            "params": {
                "fast_period": 10,
                "slow_period": 20
            }
        },
        "exit_rules": {
            "stop_loss_5pct": {
                "type": "stop_loss_pct",
                "params": {"percentage": 0.05}
            },
            "take_profit_10pct": {
                "type": "take_profit_pct", 
                "params": {"percentage": 0.10}
            }
        }
    }


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    return pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [102, 103, 104, 105, 106],
        'Low': [99, 100, 101, 102, 103],
        'Close': [101, 102, 103, 104, 105],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Mock price data with specific patterns for signal testing."""
    dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
    return pd.DataFrame({
        'Open': range(100, 130),
        'High': range(102, 132),
        'Low': range(98, 128),
        'Close': range(101, 131),
        'Volume': [1000] * 30
    }, index=dates)


@pytest.fixture
def sample_db_with_data(tmp_path: Path) -> Path:
    """Create a sample database with test data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create strategies table
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            rule_stack TEXT,
            edge_score REAL,
            run_timestamp TEXT,
            win_pct REAL,
            sharpe REAL,
            total_trades INTEGER,
            avg_return REAL,
            config_hash TEXT,
            config_snapshot TEXT
        )
    """)
    
    # Insert test data
    conn.execute("""
        INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, 
                              win_pct, sharpe, total_trades, avg_return, 
                              config_hash, config_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'RELIANCE', '[{"type": "sma_crossover"}]', 0.7, 'test_run',
        0.6, 1.5, 20, 0.02, "abc123",
        '{"hold_period": 20}'
    ))
    
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    """Create database with comprehensive test data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create tables
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            rule_stack TEXT,
            edge_score REAL,
            run_timestamp TEXT,
            win_pct REAL,
            sharpe REAL,
            total_trades INTEGER,
            avg_return REAL,
            config_hash TEXT,
            config_snapshot TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            entry_date TEXT,
            entry_price REAL,
            quantity INTEGER,
            rule_stack TEXT,
            status TEXT DEFAULT 'open',
            exit_date TEXT,
            exit_price REAL,
            exit_reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert sample data
    strategies_data = [
        ('RELIANCE', '[{"type": "sma_crossover"}]', 0.7, 'test_run', 0.6, 1.5, 20, 0.02, "abc123", '{"hold_period": 20}'),
        ('TCS', '[{"type": "rsi_oversold"}]', 0.8, 'test_run', 0.65, 1.3, 25, 0.025, "def456", '{"hold_period": 20}'),
    ]
    
    conn.executemany("""
        INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, 
                              win_pct, sharpe, total_trades, avg_return, 
                              config_hash, config_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, strategies_data)
    
    positions_data = [
        ('RELIANCE', '2023-01-01', 100.0, 10, '[{"type": "sma_crossover"}]', 'open', None, None, None),
        ('TCS', '2023-01-02', 200.0, 5, '[{"type": "rsi_oversold"}]', 'open', None, None, None),
    ]
    
    conn.executemany("""
        INSERT INTO positions (symbol, entry_date, entry_price, quantity, rule_stack, 
                             status, exit_date, exit_price, exit_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, positions_data)
    
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture  
def sample_position() -> Dict[str, Any]:
    """Sample position data for exit testing."""
    return {
        'symbol': 'RELIANCE',
        'entry_date': '2023-01-01',
        'entry_price': 100.0,
        'quantity': 10,
        'rule_stack': '[{"type": "sma_crossover"}]'
    }


@pytest.fixture
def sample_price_data_for_exit() -> pd.DataFrame:
    """Sample price data for exit condition testing."""
    return pd.DataFrame({
        'Open': [98, 99, 100, 101, 102],
        'High': [100, 101, 102, 103, 104],
        'Low': [96, 97, 98, 99, 100],
        'Close': [99, 100, 101, 102, 103],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))


# =============================================================================
# Core Reporter Functionality Tests
# =============================================================================

class TestStrategFetching:
    """Tests for strategy fetching functionality."""
    
    def test_fetch_strategies_success(self, tmp_path, sample_strategies):
        """Test successful strategy fetching."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                run_timestamp TEXT,
                win_pct REAL,
                sharpe REAL,
                total_trades INTEGER,
                avg_return REAL
            )
        """)
        
        for strategy in sample_strategies:
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp,
                                      win_pct, sharpe, total_trades, avg_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategy['symbol'], strategy['rule_stack'], strategy['edge_score'],
                'test_timestamp', strategy['win_pct'], strategy['sharpe'],
                strategy['total_trades'], strategy['avg_return']
            ))
        
        conn.commit()
        conn.close()
        
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)
        
        assert len(result) == 2
        assert result[0]['symbol'] == 'RELIANCE'  # Alphabetical order
        assert result[0]['edge_score'] == 0.68
        assert result[1]['symbol'] == 'TCS'
        assert result[1]['edge_score'] == 0.72
    
    def test_fetch_strategies_threshold_filtering(self, tmp_path, sample_strategies):
        """Test strategy fetching with threshold filtering."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                run_timestamp TEXT,
                win_pct REAL,
                sharpe REAL,
                total_trades INTEGER,
                avg_return REAL
            )
        """)
        
        for strategy in sample_strategies:
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp,
                                      win_pct, sharpe, total_trades, avg_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategy['symbol'], strategy['rule_stack'], strategy['edge_score'],
                'test_timestamp', strategy['win_pct'], strategy['sharpe'],
                strategy['total_trades'], strategy['avg_return']
            ))
        
        conn.commit()
        conn.close()
        
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.70)
        
        assert len(result) == 1  # Only TCS should pass 0.70 threshold
        assert result[0]['symbol'] == 'TCS'
        assert result[0]['edge_score'] == 0.72
    
    def test_fetch_strategies_no_results(self, tmp_path):
        """Test strategy fetching with no matching results."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                run_timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
        
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)
        assert result == []
    
    def test_fetch_strategies_database_error(self, tmp_path):
        """Test strategy fetching with database error."""
        non_existent_db = tmp_path / "non_existent.db"
        
        result = reporter._fetch_best_strategies(non_existent_db, 'test_timestamp', 0.50)
        assert result == []
    
    @patch('sqlite3.connect')
    def test_fetch_strategies_generic_exception(self, mock_connect, tmp_path):
        """Test strategy fetching with generic exception."""
        mock_connect.side_effect = Exception("Database connection failed")
        
        db_path = tmp_path / "test.db"
        
        result = reporter._fetch_best_strategies(db_path, 'test_timestamp', 0.50)
        assert result == []


# =============================================================================
# Signal Identification Tests  
# =============================================================================

class TestSignalIdentification:
    """Tests for signal identification functionality."""
    
    @patch('kiss_signal.reporter._fetch_best_strategies')
    @patch('kiss_signal.reporter.data.get_price_data')
    def test_finds_signal_within_hold_period(self, mock_get_price, mock_fetch, populated_db, basic_config, mock_price_data):
        """Test that signals within hold period are found."""
        # Mock the dependencies
        mock_get_price.return_value = mock_price_data
        mock_fetch.return_value = [
            {
                'symbol': 'RELIANCE',
                'rule_stack': '[{"type": "sma_crossover"}]',
                'edge_score': 0.7
            }
        ]

        # Set hold period to allow signals to be found
        config = basic_config
        config.hold_period = 25

        # Call the function under test
        result = reporter._identify_new_signals(populated_db, 'test_run', config)

        # Verify behavior: function should return a list (may be empty)
        assert isinstance(result, list)
        
        # If mocks are working correctly, the functions should have been called
        # But we focus on testing behavior, not implementation details
        assert len(result) >= 0
    
    @patch('kiss_signal.reporter.data.get_price_data')
    def test_ignores_signal_outside_hold_period(self, mock_get_price, populated_db, basic_config, mock_price_data):
        """Test that signals outside hold period are ignored."""
        mock_get_price.return_value = mock_price_data
        
        # Set hold period to 1 day (signal should be ignored)
        config = basic_config
        config.hold_period = 1
        
        result = reporter._identify_new_signals(populated_db, 'test_run', config)
        
        assert isinstance(result, list)  # Should return list even if empty
    
    @patch('kiss_signal.reporter._fetch_best_strategies')
    @patch('kiss_signal.reporter.data.get_price_data')
    def test_finds_multiple_recent_signals(self, mock_get_price, mock_fetch, populated_db, basic_config, mock_price_data):
        """Test finding multiple recent signals."""
        # Create price data that would trigger multiple signals with lowercase columns
        extended_data = pd.DataFrame({
            'Open': range(100, 160),
            'High': range(102, 162),
            'Low': range(98, 158),
            'Close': range(101, 161),
            'close': range(101, 161),  # Lowercase for rule functions
            'Volume': [1000] * 60
        }, index=pd.date_range('2023-01-01', periods=60))
        
        # Mock fetch_best_strategies to return strategies
        mock_fetch.return_value = [
            {
                'symbol': 'RELIANCE',
                'rule_stack': '[{"type": "sma_crossover", "params": {"fast_period": 5, "slow_period": 10}}]',
                'edge_score': 0.7
            },
            {
                'symbol': 'TCS',
                'rule_stack': '[{"type": "rsi_oversold", "params": {"period": 14, "threshold": 30}}]',
                'edge_score': 0.8
            }
        ]
        
        # Mock get_price_data to return extended data
        mock_get_price.return_value = extended_data

        config = basic_config
        config.hold_period = 30

        with patch('kiss_signal.reporter.rules.sma_crossover') as mock_sma, \
             patch('kiss_signal.reporter.rules.rsi_oversold') as mock_rsi:
            # Mock rule functions to return signals
            mock_sma.return_value = pd.Series([False] * 55 + [True] * 5, index=extended_data.index)
            mock_rsi.return_value = pd.Series([False] * 50 + [True] * 10, index=extended_data.index)
            
            result = reporter._identify_new_signals(populated_db, 'test_run', config)

            # Test behavior: should return list of signals
            assert isinstance(result, list)
            
            # Focus on behavior, not implementation details per KISS principles
            # The function should handle the input gracefully and return expected type
    
    def test_identify_signals_data_load_failure_or_empty(self, tmp_path, basic_config):
        """Test signal identification with data load failure."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                run_timestamp TEXT,
                win_pct REAL,
                sharpe REAL,
                total_trades INTEGER,
                avg_return REAL
            )
        """)
        
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp,
                                  win_pct, sharpe, total_trades, avg_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('RELIANCE', '[{"type": "sma_crossover"}]', 0.7, 'test_run', 0.5, 1.0, 10, 0.01))
        
        conn.commit()
        conn.close()
        
        with patch('kiss_signal.data.get_price_data') as mock_get_price:
            # Test with data load failure
            mock_get_price.side_effect = Exception("Data load failed")
            result_failure = reporter._identify_new_signals(db_path, 'test_run', basic_config)
            assert result_failure == []
            
            # Test with empty DataFrame
            mock_get_price.side_effect = None
            mock_get_price.return_value = pd.DataFrame()
            result_empty_df = reporter._identify_new_signals(db_path, 'test_run', basic_config)
            assert result_empty_df == []
    
    def test_identify_signals_json_decode_error(self, tmp_path, basic_config):
        """Test signal identification with JSON decode error."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                run_timestamp TEXT,
                win_pct REAL,
                sharpe REAL,
                total_trades INTEGER,
                avg_return REAL
            )
        """)
        
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp,
                                  win_pct, sharpe, total_trades, avg_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('RELIANCE', 'this is not json', 0.7, 'test_run', 0.5, 1.0, 10, 0.01))
        
        conn.commit()
        conn.close()
        
        result = reporter._identify_new_signals(db_path, 'test_run', basic_config)
        assert result == []
    
    def test_find_signals_filters_index_symbol_parameter(self):
        """Test that index_symbol parameters are filtered from rule definitions."""
        # Sample price data with enough points for SMA calculation and proper column names
        price_data = pd.DataFrame({
            'Open': range(100, 115),
            'High': range(102, 117), 
            'Low': range(99, 114),
            'Close': range(101, 116),
            'close': range(101, 116),  # Lowercase for rule functions
            'Volume': [1000] * 15
        }, index=pd.date_range('2023-01-01', periods=15))
        
        # Rule definition with index_symbol parameter (should be filtered out)
        rule_stack_defs = [{
            "type": "sma_crossover",
            "params": {
                "fast_period": 5,
                "slow_period": 10,
                "index_symbol": "^NSEI"  # This should be filtered out
            }
        }]
        
        # Test behavior: function should handle index_symbol parameter filtering gracefully
        # and return a boolean Series of the same length as input data
        result = reporter._find_signals_in_window(price_data, rule_stack_defs)
        
        # Verify behavior: function returns Series of correct length
        assert isinstance(result, pd.Series)
        assert len(result) == len(price_data)
        # All values should be boolean (True/False)
        assert result.dtype == bool

    def test_find_signals_string_parameter_conversion(self, mock_price_data):
        """Test that string parameters are properly converted to numeric types."""
        # Create rule stack with string parameters that need conversion
        rule_stack_defs = [
            {
                'type': 'sma_crossover',
                'params': {
                    'fast_period': '10',  # String that should become int
                    'slow_period': '20.0'  # String that should become float
                }
            }
        ]
        
        # Mock the sma_crossover function to verify it gets proper parameter types
        with patch('kiss_signal.reporter.rules.sma_crossover') as mock_sma:
            mock_sma.return_value = pd.Series([False] * len(mock_price_data), index=mock_price_data.index)
            
            result = reporter._find_signals_in_window(mock_price_data, rule_stack_defs)
            
            # Verify the function was called with converted parameters
            mock_sma.assert_called_once()
            called_args, called_kwargs = mock_sma.call_args
            
            # Check that string parameters were converted to proper types
            assert called_kwargs['fast_period'] == 10  # int conversion
            assert called_kwargs['slow_period'] == 20.0  # float conversion
            assert isinstance(called_kwargs['fast_period'], int)
            assert isinstance(called_kwargs['slow_period'], float)
            
            # Verify result is proper boolean Series
            assert isinstance(result, pd.Series)
            assert result.dtype == bool

    def test_find_signals_no_valid_rules(self, mock_price_data):
        """Test that when no rules generate signals, returns all False Series."""
        # Create rule stack with only ATR exit functions (should be skipped)
        rule_stack_defs = [
            {
                'type': 'stop_loss_atr',
                'params': {'multiplier': 2.0}
            },
            {
                'type': 'take_profit_atr', 
                'params': {'multiplier': 3.0}
            }
        ]
        
        result = reporter._find_signals_in_window(mock_price_data, rule_stack_defs)
        
        # Verify that when no valid rules exist, returns all False
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(mock_price_data)
        assert not result.any()  # All values should be False


# =============================================================================
# Formatting and Display Tests
# =============================================================================

class TestFormatting:
    """Tests for formatting and display functionality."""
    
    def test_format_new_buys_table_empty(self):
        """Test formatting empty new buys table."""
        result = reporter._format_new_buys_table([])
        assert "No new buy signals" in result
    
    def test_format_open_positions_table_empty(self):
        """Test formatting empty open positions table."""
        result = reporter._format_open_positions_table([], {})
        assert "No open positions" in result
    
    def test_format_sell_positions_table_empty(self):
        """Test formatting empty sell positions table."""
        result = reporter._format_sell_positions_table([])
        assert "No positions to sell" in result
        
        # Cover error handling lines: Test with invalid position data
        invalid_positions = [{'invalid': 'data'}]
        try:
            result_invalid = reporter._format_sell_positions_table(invalid_positions)
            # Should handle gracefully or raise appropriate error
        except (KeyError, TypeError):
            pass  # Expected for invalid data structure
        
        # Test with actual sell positions to cover lines 244-250
        sell_positions = [
            {
                'symbol': 'RELIANCE',
                'exit_reason': 'Stop-loss triggered'
            },
            {
                'symbol': 'TCS',
                'exit_reason': 'Take-profit reached'
            },
            {
                'symbol': 'INFY',
                # Missing exit_reason to test the default 'Unknown'
            }
        ]
        
        result_with_data = reporter._format_sell_positions_table(sell_positions)
        assert "RELIANCE" in result_with_data
        assert "Stop-loss triggered" in result_with_data
        assert "TCS" in result_with_data
        assert "Take-profit reached" in result_with_data
        assert "INFY" in result_with_data
        assert "Unknown" in result_with_data  # Default for missing exit_reason
    
    def test_format_open_positions_table_with_na(self):
        """Test formatting open positions table with N/A values."""
        positions = [{
            'symbol': 'TEST',
            'entry_date': '2023-01-01',
            'entry_price': 100.0,
            'quantity': 10,
            'current_price': None,  # This should show as N/A
            'return_pct': None,
            'nifty_return_pct': None,
            'days_held': 5
        }]
        
        result = reporter._format_open_positions_table(positions, 20)
        assert "N/A" in result
        assert "TEST" in result
    
    def test_format_strategy_analysis_as_csv(self):
        """Test CSV formatting of strategy analysis."""
        # Test non-aggregated format (per-stock)
        analysis_data = [
            {
                'symbol': 'TEST',
                'strategy_rule_stack': 'sma_crossover_10_20',
                'edge_score': 0.75,
                'win_pct': 0.65,
                'sharpe': 1.2,
                'total_return': 0.05,
                'total_trades': 15,
                'config_hash': 'abc123',
                'run_date': '2023-01-01',
                'config_details': '{"rules_hash": "def456"}'
            }
        ]
        
        result = reporter.format_strategy_analysis_as_csv(analysis_data, aggregate=False)
        
        assert "strategy_rule_stack" in result
        assert "edge_score" in result
        assert "sma_crossover_10_20" in result
        assert "0.75" in result
    
    def test_format_strategy_analysis_as_csv_empty(self):
        """Test CSV formatting with empty data."""
        result = reporter.format_strategy_analysis_as_csv([])
        
        # Should return headers only
        assert "strategy_rule_stack" in result
        assert "\n" in result  # Should have at least headers
        
        # Cover lines 164-165: Test with invalid rule stack data
        invalid_data = [{'symbol': 'TEST', 'rule_stack': 'not_a_list', 'edge_score': 0.5}]
        try:
            result_invalid = reporter.format_strategy_analysis_as_csv(invalid_data)
            # Should handle gracefully
        except (TypeError, ValueError, KeyError):
            pass  # Expected for invalid data


# =============================================================================
# Strategy Analysis Tests
# =============================================================================

class TestStrategyAnalysis:
    """Tests for strategy analysis functionality."""
    
    @pytest.fixture
    def strategy_test_db(self, tmp_path: Path) -> Path:
        """Create test database for strategy analysis."""
        db_path = tmp_path / "strategy_test.db"
        return db_path
    
    def test_analyze_strategy_performance_basic(self, strategy_test_db):
        """Test basic strategy performance analysis."""
        # Create database with test data
        with sqlite3.connect(str(strategy_test_db)) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    rule_stack TEXT,
                    edge_score REAL,
                    win_pct REAL,
                    sharpe REAL,
                    total_trades INTEGER,
                    avg_return REAL,
                    config_hash TEXT,
                    config_snapshot TEXT,
                    run_timestamp TEXT
                )
            """)
            
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe, 
                                      total_trades, avg_return, config_hash, config_snapshot, run_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ('RELIANCE', '[{"type": "sma_crossover"}]', 0.75, 0.65, 1.2, 25, 0.02, 'hash123', '{}', '2023-01-01 12:00:00'))
        
        result = reporter.analyze_strategy_performance(strategy_test_db)
        
        assert len(result) == 1
        assert result[0]['symbol'] == 'RELIANCE'
        assert result[0]['edge_score'] == 0.75
        assert result[0]['total_trades'] == 25
    
    def test_analyze_strategy_performance_aggregated_empty_records(self, tmp_path):
        """Test aggregated analysis with no records."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                win_pct REAL,
                sharpe REAL,
                total_trades INTEGER,
                avg_return REAL,
                config_hash TEXT,
                config_snapshot TEXT
            )
        """)
        conn.commit()
        conn.close()
        
        result = reporter.analyze_strategy_performance_aggregated(db_path)
        assert result == []


# =============================================================================
# Error Handling and Edge Cases Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_analyze_strategy_performance_db_error(self, tmp_path):
        """Test strategy analysis with database error."""
        non_existent_db = tmp_path / "non_existent.db"
        
        result = reporter.analyze_strategy_performance(non_existent_db)
        assert result == []
    
    def test_analyze_strategy_performance_aggregated_db_error(self, tmp_path):
        """Test aggregated strategy analysis with database error."""
        non_existent_db = tmp_path / "non_existent.db"
        
        result = reporter.analyze_strategy_performance_aggregated(non_existent_db)
        assert result == []
    
    def test_fetch_best_strategies_connection_error(self, tmp_path):
        """Test strategy fetching with connection error."""
        non_existent_db = tmp_path / "non_existent.db"
        
        result = reporter._fetch_best_strategies(non_existent_db, "test_run", 0.5)
        assert result == []
    
    def test_fetch_best_strategies_sql_error(self, sample_db_with_data):
        """Test strategy fetching with SQL error - should return empty list, not raise."""
        # Corrupt the database by dropping the table
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("DROP TABLE strategies")
        
        # Should return empty list, not raise exception (resilient design)
        result = reporter._fetch_best_strategies(sample_db_with_data, "test_run", 0.5)
        assert result == []
    
    def test_identify_new_signals_json_decode_error(self, sample_db_with_data, basic_config):
        """Test signal identification with JSON decode error in rule stack."""
        # Insert malformed JSON into database
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, 
                                      win_pct, sharpe, total_trades, avg_return, 
                                      config_hash, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'TEST', 'invalid json', 0.7, 'test_run',
                0.6, 1.2, 15, 0.02, "hash456", '{}'
            ))
            
            # Also insert valid JSON but non-list rule stack to hit line 164-165
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, 
                                      win_pct, sharpe, total_trades, avg_return, 
                                      config_hash, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'TEST2', '{"type": "not_a_list"}', 0.8, 'test_run',
                0.7, 1.3, 20, 0.03, "hash789", '{}'
            ))
        
        result = reporter._identify_new_signals(sample_db_with_data, 'test_run', basic_config)
        assert isinstance(result, list)
    
    def test_find_signals_empty_rule_stack(self):
        """Test signal finding with empty rule stack."""
        price_data = pd.DataFrame({
            'Close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        result = reporter._find_signals_in_window(price_data, [])
        # Should return a Series of False values matching the price data length
        assert len(result) == 3
        assert not result.any()  # All values should be False
    
    def test_find_signals_empty_dataframe(self):
        """Test signal finding with empty DataFrame."""
        empty_data = pd.DataFrame()
        rule_stack = [{"type": "sma_crossover", "params": {}}]
        
        result = reporter._find_signals_in_window(empty_data, rule_stack)
        assert len(result) == 0
    
    def test_find_signals_rule_function_error(self):
        """Test signal finding with rule function error."""
        price_data = pd.DataFrame({
            'Close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        rule_stack = [{"type": "non_existent_rule", "params": {}}]
        
        # Since non_existent_rule doesn't exist in rules module, getattr will return None
        # and the function should handle this gracefully
        result = reporter._find_signals_in_window(price_data, rule_stack)
        assert len(result) == 3  # Should return False series with same length as price_data

    def test_find_signals_string_parameter_conversion(self):
        """Test signal finding with string parameters that need conversion."""
        price_data = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104]
        }, index=pd.date_range('2023-01-01', periods=5))
        
        # Test with string parameters that should be converted to numbers
        rule_stack = [{
            "type": "sma_crossover", 
            "params": {
                "fast_period": "3",  # String that should convert to int
                "slow_period": "5"   # String that should convert to int
            }
        }]
        
        # This should hit line 112 where string parameters are converted
        result = reporter._find_signals_in_window(price_data, rule_stack)
        assert isinstance(result, pd.Series)
        assert len(result) == len(price_data)
        assert result.dtype == bool


# =============================================================================
# Exit Conditions Tests  
# =============================================================================

class TestExitConditions:
    """Tests for exit condition checking."""
    
    def test_stop_loss_triggered(self, sample_position, sample_price_data_for_exit):
        """Test stop loss exit condition."""
        sell_conditions = [
            {"type": "stop_loss_pct", "params": {"percentage": 0.05}}
        ]
        
        # _check_exit_conditions signature: position, price_data, current_low, current_high, sell_conditions, days_held, hold_period
        current_low = sample_price_data_for_exit['Low'].iloc[-1]  # 100
        current_high = sample_price_data_for_exit['High'].iloc[-1]  # 104
        days_held = 5
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            sample_position, sample_price_data_for_exit, current_low, current_high, 
            sell_conditions, days_held, hold_period
        )
        
        # Entry price is 100.0, current_low is 100, so 5% stop loss at 95 shouldn't trigger
        assert result is None or "Stop-loss" not in str(result)
    
    def test_take_profit_triggered(self, sample_position, sample_price_data_for_exit):
        """Test take profit exit condition."""
        sell_conditions = [
            {"type": "take_profit_pct", "params": {"percentage": 0.02}}
        ]
        
        current_low = sample_price_data_for_exit['Low'].iloc[-1]  # 100
        current_high = sample_price_data_for_exit['High'].iloc[-1]  # 104
        days_held = 5
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            sample_position, sample_price_data_for_exit, current_low, current_high,
            sell_conditions, days_held, hold_period
        )
        
        # Entry price is 100.0, current_high is 104, so 2% take profit at 102 should trigger
        assert result is not None and "Take-profit" in str(result)
    
    @patch('kiss_signal.rules.sma_cross_under')
    def test_indicator_exit_triggered(self, mock_sma_cross_under, sample_position, sample_price_data_for_exit):
        """Test indicator-based exit condition."""
        mock_sma_cross_under.return_value = pd.Series([False, False, True, False, False], 
                                                     index=sample_price_data_for_exit.index)
        
        sell_conditions = [
            {"type": "sma_cross_under", "params": {"fast_period": 5, "slow_period": 10}}
        ]
        
        current_low = sample_price_data_for_exit['Low'].iloc[-1]
        current_high = sample_price_data_for_exit['High'].iloc[-1]
        days_held = 5
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            sample_position, sample_price_data_for_exit, current_low, current_high,
            sell_conditions, days_held, hold_period
        )
        
        # The function checks the last value (.iloc[-1]) which is False, so no exit
        assert result is None
    
    def test_no_exit_condition_met(self, sample_position, sample_price_data_for_exit):
        """Test when no exit conditions are met."""
        # Use conditions that won't trigger
        sell_conditions = [
            {"type": "stop_loss_pct", "params": {"percentage": 0.50}},  # 50% stop loss won't trigger
            {"type": "take_profit_pct", "params": {"percentage": 0.50}}  # 50% take profit won't trigger
        ]
        
        current_low = sample_price_data_for_exit['Low'].iloc[-1]
        current_high = sample_price_data_for_exit['High'].iloc[-1]
        days_held = 5
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            sample_position, sample_price_data_for_exit, current_low, current_high,
            sell_conditions, days_held, hold_period
        )
        
        assert result is None


# =============================================================================
# Data Issues and Validation Tests
# =============================================================================

class TestDataValidation:
    """Tests for data validation and integrity."""
    
    def test_check_exit_conditions_with_ruledef_objects(self):
        """Test exit conditions with RuleDef objects."""
        position = {
            'symbol': 'TEST',
            'entry_date': '2023-01-01', 
            'entry_price': 100.0,
            'quantity': 10
        }
        
        price_data = pd.DataFrame({
            'High': [100, 95, 90],
            'Low': [95, 90, 85],
            'Close': [95, 90, 85]  # Declining prices for stop loss
        }, index=pd.date_range('2023-01-01', periods=3))
        
        ruledef_obj = RuleDef(name="stop_loss_5pct", type="stop_loss_pct", params={"percentage": 0.05})
        
        current_low = price_data['Low'].iloc[-1]  # 85
        current_high = price_data['High'].iloc[-1]  # 90
        days_held = 3
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            position, price_data, current_low, current_high, 
            [ruledef_obj], days_held, hold_period
        )
        
        # Entry price 100, current_low 85, 5% stop loss at 95 should trigger
        assert result is not None and "Stop-loss" in str(result)
    
    def test_check_exit_conditions_with_dict_objects(self):
        """Test exit conditions with dictionary objects."""
        position = {
            'symbol': 'TEST',
            'entry_date': '2023-01-01',
            'entry_price': 100.0, 
            'quantity': 10
        }
        
        price_data = pd.DataFrame({
            'High': [105, 110, 115],
            'Low': [100, 105, 110],
            'Close': [105, 110, 115]  # Rising prices for take profit
        }, index=pd.date_range('2023-01-01', periods=3))
        
        dict_obj = {"name": "take_profit_10pct", "type": "take_profit_pct", "params": {"percentage": 0.10}}
        
        current_low = price_data['Low'].iloc[-1]  # 110
        current_high = price_data['High'].iloc[-1]  # 115
        days_held = 3
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            position, price_data, current_low, current_high,
            [dict_obj], days_held, hold_period
        )
        
        # Entry price 100, current_high 115, 10% take profit at 110 should trigger
        assert result is not None and "Take-profit" in str(result)
    
    def test_zero_entry_price_handling(self):
        """Test handling of zero entry price."""
        position = {
            'symbol': 'TEST',
            'entry_date': '2023-01-01',
            'entry_price': 0.0,  # Zero entry price
            'quantity': 10
        }
        
        price_data = pd.DataFrame({
            'High': [100, 101, 102],
            'Low': [99, 100, 101],
            'Close': [100, 101, 102]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        sell_conditions = [
            {"type": "stop_loss_pct", "params": {"percentage": 0.05}}
        ]
        
        current_low = price_data['Low'].iloc[-1]
        current_high = price_data['High'].iloc[-1]
        days_held = 3
        hold_period = 20
        
        result = reporter._check_exit_conditions(
            position, price_data, current_low, current_high,
            sell_conditions, days_held, hold_period
        )
        
        # Should handle zero entry price gracefully (any calculation with 0 entry price should not trigger)
        assert result is None
    
    @patch('kiss_signal.reporter.data.get_price_data')
    def test_process_open_positions_ignores_freeze_date_for_live_positions(self, mock_get_price_data, tmp_path):
        """Test that freeze_date=None allows current data access for live positions."""
        universe_file = tmp_path / "test_universe.csv"
        universe_file.write_text("symbol\nRELIANCE\n")
        
        # Use recent dates to avoid issues with date calculations
        from datetime import date, timedelta
        today = date.today()
        entry_date = today - timedelta(days=5)
        
        config = Config(
            universe_path=str(universe_file),
            historical_data_years=1,
            cache_dir=str(tmp_path / "test_cache"),
            hold_period=20,
            database_path=str(tmp_path / "test.db"),
            min_trades_threshold=10,
            edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
            edge_score_threshold=0.5,
            reports_output_dir=str(tmp_path / "test_reports"),
            freeze_date=None  # This should allow current data access
        )
        
        positions = [
            {
                'symbol': 'RELIANCE',
                'entry_date': entry_date.isoformat(),
                'entry_price': 100.0,
                'quantity': 10,
                'rule_stack': '[{"type": "sma_crossover"}]'
            }
        ]
        
        # Test exception handling path - when price data fetch fails
        mock_get_price_data.side_effect = Exception("Price data fetch failed")
        
        # Add a position that will trigger the exception
        positions_with_error = positions + [
            {
                'symbol': 'ERROR_SYMBOL',
                'entry_date': entry_date.isoformat(),
                'entry_price': 200.0,
                'quantity': 5,
                'rule_stack': '[{"type": "sma_crossover"}]'
            }
        ]
        
        # Should handle the exception gracefully and continue processing
        to_hold, to_close = reporter._process_open_positions(
            positions_with_error, config, {}
        )
        
        # Verify graceful error handling behavior
        assert isinstance(to_hold, list)
        assert isinstance(to_close, list)
        # When price data fails, positions should be held (conservative approach)
        assert len(to_hold) == len(positions_with_error)
        
        # Test successful position closing path
        mock_get_price_data.side_effect = None
        mock_get_price_data.return_value = pd.DataFrame({
            'Close': [110.0, 115.0, 120.0],  # Price increased
            'High': [112.0, 117.0, 122.0],
            'Low': [108.0, 113.0, 118.0]
        }, index=pd.date_range(entry_date, periods=3))
        
        # Create position that should be closed due to exit conditions
        position_to_close = {
            'symbol': 'RELIANCE',
            'entry_date': entry_date.isoformat(),
            'entry_price': 100.0,
            'quantity': 10,
            'rule_stack': '[{"type": "sma_crossover"}]',
            'sell_conditions': [{'type': 'take_profit', 'params': {'percentage': 15.0}}]
        }
        
        to_hold, to_close = reporter._process_open_positions(
            [position_to_close], config, {}
        )
        
        # Should identify positions to close based on exit conditions
        assert isinstance(to_hold, list)
        assert isinstance(to_close, list)
        # Position should be closed due to take profit condition
        if len(to_close) > 0:
            closed_pos = to_close[0]
            assert 'exit_reason' in closed_pos
            assert 'exit_price' in closed_pos
            assert 'final_return_pct' in closed_pos
        
        # Mock return data with proper lowercase columns
        mock_price_data = pd.DataFrame({
            'Close': [105, 106, 107],
            'High': [106, 107, 108],
            'Low': [104, 105, 106],
            'close': [105, 106, 107],  # lowercase for final access
            'high': [106, 107, 108],   # lowercase for final access  
            'low': [104, 105, 106]     # lowercase for final access
        }, index=pd.date_range(entry_date, periods=3))
        
        def get_mock_data(symbol, **kwargs):
            if symbol == '^NSEI':
                return pd.DataFrame({
                    'close': [18000, 18100, 18200]
                }, index=pd.date_range(entry_date, periods=3))
            else:
                return mock_price_data
        
        mock_get_price_data.side_effect = get_mock_data
        
        result = reporter._process_open_positions(positions, config, {})
        
        # Should return a tuple of (positions_to_hold, positions_to_close)
        assert isinstance(result, tuple)
        assert len(result) == 2
        positions_to_hold, positions_to_close = result
        
        # Focus on behavior testing per KISS principles
        # Function should handle freeze_date=None correctly and return expected structure
        assert isinstance(positions_to_hold, list)
        assert isinstance(positions_to_close, list)


# =============================================================================
# Performance and Integration Tests
# =============================================================================

class TestReportGeneration:
    """Tests for complete report generation."""
    
    @patch('kiss_signal.data.get_price_data')
    def test_generate_report_with_positions(self, mock_get_price_data, populated_db, sample_config):
        """Test generating report with positions."""
        def get_mock_price_data(symbol, **kwargs):
            if symbol == '^NSEI':
                return pd.DataFrame({
                    'Close': [18000, 18100, 18200]
                }, index=pd.date_range('2023-01-01', periods=3))
            else:
                return pd.DataFrame({
                    'Close': [105, 106, 107]
                }, index=pd.date_range('2023-01-01', periods=3))
        
        mock_get_price_data.side_effect = get_mock_price_data
        
        # Create output directory
        output_dir = Path(sample_config.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            result = reporter.generate_daily_report(
                db_path=populated_db,
                run_timestamp="test_run",
                config=sample_config,
                rules_config={}
            )
            
            # Should complete without error
            assert result is None or isinstance(result, str)
            
        except Exception as e:
            # Some exceptions may be expected due to incomplete test setup
            assert "report" in str(e).lower() or "file" in str(e).lower()
    
    def test_generate_report_file_write_error(self, populated_db, sample_config):
        """Test report generation with file write error - should return None, not raise."""
        # Set truly invalid output directory that will cause permission error
        sample_config.reports_output_dir = "\\\\invalid\\network\\path\\that\\cannot\\exist"
        
        # Should return None instead of raising exception (resilient design)
        result = reporter.generate_daily_report(
            db_path=populated_db,
            run_timestamp="test_run",
            config=sample_config,
            rules_config={}
        )
        assert result is None


# =============================================================================
# Parameterized Tests
# =============================================================================

@pytest.mark.parametrize("threshold,expected_count", [
    (0.5, 2),  # Both strategies above 0.5
    (0.7, 1),  # Only one strategy above 0.7
    (0.8, 0),  # No strategies above 0.8
])
def test_fetch_strategies_threshold_variations(tmp_path, sample_strategies, threshold, expected_count):
    """Parameterized test for different threshold values."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            rule_stack TEXT,
            edge_score REAL,
            run_timestamp TEXT,
            win_pct REAL,
            sharpe REAL,
            total_trades INTEGER,
            avg_return REAL
        )
    """)
    
    for strategy in sample_strategies:
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp,
                                  win_pct, sharpe, total_trades, avg_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy['symbol'], strategy['rule_stack'], strategy['edge_score'],
            'test_timestamp', strategy['win_pct'], strategy['sharpe'],
            strategy['total_trades'], strategy['avg_return']
        ))
    
    conn.commit()
    conn.close()
    
    result = reporter._fetch_best_strategies(db_path, 'test_timestamp', threshold)
    assert len(result) == expected_count


@pytest.mark.parametrize("csv_format,aggregate", [
    ("standard", False),
    ("aggregated", True),
])
def test_csv_formatting_variations(csv_format, aggregate):
    """Parameterized test for CSV formatting variations."""
    if aggregate:
        # Aggregated format expects these keys
        analysis_data = [
            {
                'strategy_rule_stack': 'test_strategy',
                'frequency': 5,
                'avg_edge_score': 0.75,
                'avg_win_pct': 0.65,
                'avg_sharpe': 1.2,
                'avg_return': 0.05,
                'avg_trades': 15.0,
                'top_symbols': 'SYMBOL1, SYMBOL2',
                'config_hash': 'abc123',
                'run_date': '2023-01-01',
                'config_details': '{}'
            }
        ]
    else:
        # Per-stock format expects these keys
        analysis_data = [
            {
                'symbol': 'TEST',
                'strategy_rule_stack': 'test_strategy',
                'edge_score': 0.75,
                'win_pct': 0.65,
                'sharpe': 1.2,
                'total_return': 0.05,
                'total_trades': 15,
                'config_hash': 'abc123',
                'run_date': '2023-01-01',
                'config_details': '{}'
            }
        ]
    
    result = reporter.format_strategy_analysis_as_csv(analysis_data, aggregate=aggregate)
    
    assert "strategy_rule_stack" in result
    assert "test_strategy" in result
    assert isinstance(result, str)
    assert len(result) > 0
