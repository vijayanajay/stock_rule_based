"""
Tests for the reporter module.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
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
        universe_path=str(universe_file),
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


class TestCheckForSignal:
    """Test _check_for_signal private function."""
    
    def test_check_signal_with_valid_rule(self, sample_price_data):
        """Test signal checking with valid rule."""
        rule_def = {
            'type': 'sma_crossover',
            'params': {'short_window': 5, 'long_window': 10}
        }
        
        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            # Mock rule function that returns signals
            mock_func = Mock()
            mock_signals = pd.Series([False] * 29 + [True], index=sample_price_data.index)
            mock_func.return_value = mock_signals
            mock_rules.sma_crossover = mock_func
            
            result = reporter._check_for_signal(sample_price_data, rule_def)
            
            assert result is True
            mock_func.assert_called_once_with(sample_price_data, short_window=5, long_window=10)
    
    def test_check_signal_no_signal(self, sample_price_data):
        """Test when rule returns no signal."""
        rule_def = {
            'type': 'sma_crossover',
            'params': {'short_window': 5, 'long_window': 10}
        }
        
        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_func = Mock()
            mock_signals = pd.Series([False] * 30, index=sample_price_data.index)
            mock_func.return_value = mock_signals
            mock_rules.sma_crossover = mock_func
            
            result = reporter._check_for_signal(sample_price_data, rule_def)
            
            assert result is False
    
    def test_check_signal_empty_data(self):
        """Test with empty price data."""
        empty_data = pd.DataFrame()
        rule_def = {'type': 'sma_crossover', 'params': {}}
        
        result = reporter._check_for_signal(empty_data, rule_def)
        assert result is False
    
    def test_check_signal_unknown_rule(self, sample_price_data):
        """Test with unknown rule type."""
        rule_def = {'type': 'unknown_rule', 'params': {}}
        
        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_rules.unknown_rule = None
            del mock_rules.unknown_rule  # Simulate missing attribute
            
            result = reporter._check_for_signal(sample_price_data, rule_def)
            assert result is False
    
    def test_check_signal_rule_exception(self, sample_price_data):
        """Test when rule function raises exception."""
        rule_def = {'type': 'sma_crossover', 'params': {}}
        
        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_func = Mock(side_effect=Exception("Rule error"))
            mock_rules.sma_crossover = mock_func
            
            result = reporter._check_for_signal(sample_price_data, rule_def)
            assert result is False


class TestIdentifyNewSignals:
    """Test _identify_new_signals function."""
    
    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_identify_signals_success(self, mock_get_price_data, tmp_path, sample_config, sample_price_data):
        """Test successful signal identification."""
        db_path = tmp_path / "test.db"
        
        # Setup database
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT,
                    rule_stack TEXT,
                    edge_score REAL,
                    win_pct REAL,
                    sharpe REAL,
                    total_trades INTEGER,
                    avg_return REAL,                    run_timestamp TEXT
                )
            """)
            
            conn.execute("""
                INSERT INTO strategies 
                (symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, run_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('RELIANCE', '[{"type": "sma_crossover", "name": "sma_10_20_crossover", "params": {"short_window": 10, "long_window": 20}}]', 0.68, 0.65, 1.2, 45, 0.025, 'test_timestamp'))
        
        # Mock price data and signal check
        mock_get_price_data.return_value = sample_price_data
        
        with patch('src.kiss_signal.reporter._check_for_signal') as mock_check:
            mock_check.return_value = True
            
            result = reporter._identify_new_signals(db_path, 'test_timestamp', sample_config)
            
            assert len(result) == 1
            assert result[0]['ticker'] == 'RELIANCE'
            assert result[0]['rule_stack'] == 'sma_10_20_crossover'
            assert result[0]['edge_score'] == 0.68
            assert 'date' in result[0]
            assert 'entry_price' in result[0]
    
    def test_identify_signals_no_strategies(self, tmp_path, sample_config):
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
        
        # The function only takes 3 arguments now.
        result = reporter._identify_new_signals(db_path, 'nonexistent_timestamp', sample_config)
        
        assert len(result) == 0


class TestGenerateDailyReport:
    """Test daily report generation."""
    
    def test_generate_report_structure_with_positions(self, temp_db: str, sample_data_dir: str) -> None:
        """Test report structure includes positions when enabled."""
        # Add some test trades
        from kiss_signal.positions import save_trade, Trade
        from decimal import Decimal
        from datetime import date
        
        trade = Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY")
        save_trade(temp_db, trade)
        
        universe_file = Path(sample_data_dir) / "universe.txt"
        universe_file.write_text("TEST\n")
        
        report = reporter.generate_daily_report(
            temp_db, 
            sample_data_dir, 
            str(universe_file),
            include_positions=True
        )
        
        assert "positions" in report
        assert "portfolio_summary" in report
        assert isinstance(report["positions"], dict)
        assert isinstance(report["portfolio_summary"], dict)
    
    def test_generate_report_without_positions(self, temp_db: str, sample_data_dir: str) -> None:
        """Test report generation without position tracking."""
        universe_file = Path(sample_data_dir) / "universe.txt"
        universe_file.write_text("TEST\n")
        
        report = reporter.generate_daily_report(
            temp_db, 
            sample_data_dir, 
            str(universe_file),
            include_positions=False
        )
        
        assert "positions" in report
        assert "portfolio_summary" in report
        assert report["positions"] == {}
        assert report["portfolio_summary"] == {}
