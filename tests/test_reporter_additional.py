"""Additional comprehensive tests for reporter.py to ensure >88% coverage.

These tests focus on previously uncovered edge cases, error conditions, and
specific code paths in the reporter module.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sqlite3
from pathlib import Path
from datetime import date
import json

from kiss_signal import reporter
from kiss_signal.config import Config


class TestReporterAdditionalCoverage:
    """Additional tests to maximize coverage of reporter.py."""
    
    def test_check_exit_conditions_comprehensive_coverage(self):
        """Comprehensive test of all exit condition code paths."""
        
        # Test 1: Invalid entry price scenarios
        test_cases = [
            {'entry_price': 0},           # Zero price
            {'entry_price': -5.0},        # Negative price  
            {'entry_price': None},        # None price
            {},                           # Missing entry_price
        ]
        
        for position in test_cases:
            position['symbol'] = 'TEST'
            result = reporter.check_exit_conditions(
                position, pd.DataFrame(), 95.0, 105.0, [], 5, 20
            )
            assert result is None, f"Should return None for invalid entry_price: {position}"
        
        # Test 2: All exit condition types with valid position
        position = {'symbol': 'VALID', 'entry_price': 100.0}
        price_data = pd.DataFrame({'close': [95], 'high': [96], 'low': [94]})
        
        # Stop loss percentage
        exit_cond = [{'type': 'stop_loss_pct', 'params': {'percentage': 0.05}}]
        result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, exit_cond, 5, 20)
        assert result is not None and "Stop-loss triggered" in result
        
        # Take profit percentage
        exit_cond = [{'type': 'take_profit_pct', 'params': {'percentage': 0.05}}]
        result = reporter.check_exit_conditions(position, price_data, 104.0, 106.0, exit_cond, 5, 20)
        assert result is not None and "Take-profit triggered" in result
        
        # Test 3: ATR conditions with mocking
        with patch('kiss_signal.reporter.rules.stop_loss_atr', return_value=True):
            exit_cond = [{'type': 'stop_loss_atr', 'params': {'period': 14, 'multiplier': 2.0}}]
            result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, exit_cond, 5, 20)
            assert result is not None and "ATR stop-loss triggered" in result
        
        with patch('kiss_signal.reporter.rules.take_profit_atr', return_value=True):
            exit_cond = [{'type': 'take_profit_atr', 'params': {'period': 14, 'multiplier': 4.0}}]
            result = reporter.check_exit_conditions(position, price_data, 104.0, 106.0, exit_cond, 5, 20)
            assert result is not None and "ATR take-profit triggered" in result
        
        # Test 4: ATR exception handling
        with patch('kiss_signal.reporter.rules.stop_loss_atr', side_effect=Exception("ATR failed")):
            exit_cond = [{'type': 'stop_loss_atr', 'params': {}}]
            result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, exit_cond, 5, 20)
            # Should handle exception gracefully and continue
            assert result is None  # No other exit conditions should trigger
        
        # Test 5: SMA crossover conditions
        mock_signal = pd.Series([False, False, True])
        with patch('kiss_signal.reporter.rules.sma_cross_under', return_value=mock_signal):
            exit_cond = [{'type': 'sma_cross_under', 'params': {'fast_period': 10, 'slow_period': 20}}]
            result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, exit_cond, 5, 20)
            assert result is not None and "sma_cross_under" in result
        
        with patch('kiss_signal.reporter.rules.sma_crossover', return_value=mock_signal):
            exit_cond = [{'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}}]
            result = reporter.check_exit_conditions(position, price_data, 104.0, 106.0, exit_cond, 5, 20)
            assert result is not None and "sma_crossover" in result
        
        # Test 6: SMA exception handling
        with patch('kiss_signal.reporter.rules.sma_cross_under', side_effect=Exception("SMA failed")):
            exit_cond = [{'type': 'sma_cross_under', 'params': {}}]
            result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, exit_cond, 5, 20)
            assert result is None  # Should handle exception
        
        # Test 7: Object-style conditions (not dict)
        condition_obj = Mock()
        condition_obj.type = 'stop_loss_pct'
        condition_obj.params = {'percentage': 0.05}
        result = reporter.check_exit_conditions(position, price_data, 94.0, 96.0, [condition_obj], 5, 20)
        assert result is not None and "Stop-loss triggered" in result
        
        # Test 8: Time-based exit (days held >= hold period)
        result = reporter.check_exit_conditions(position, price_data, 101.0, 102.0, [], 25, 20)
        assert result is not None and "20-day holding period" in result
    
    @patch('kiss_signal.data.get_price_data')
    def test_get_position_pricing_all_scenarios(self, mock_get_price_data, tmp_path):
        """Test all scenarios for get_position_pricing function."""
        
        config = Mock()
        config.cache_dir = str(tmp_path)
        config.freeze_date = None
        
        # Test 1: Successful pricing retrieval
        mock_price_data = pd.DataFrame({
            'close': [105.0], 'high': [106.0], 'low': [104.0]
        }, index=[pd.Timestamp('2023-01-01')])
        mock_get_price_data.return_value = mock_price_data
        
        result = reporter.get_position_pricing('SUCCESS', config)
        assert result is not None
        assert result['current_price'] == 105.0
        assert result['current_high'] == 106.0
        assert result['current_low'] == 104.0
        
        # Test 2: No price data (None)
        mock_get_price_data.return_value = None
        result = reporter.get_position_pricing('NO_DATA', config)
        assert result is None
        
        # Test 3: Empty DataFrame
        mock_get_price_data.return_value = pd.DataFrame()
        result = reporter.get_position_pricing('EMPTY', config)
        assert result is None
        
        # Test 4: Exception during data retrieval
        mock_get_price_data.side_effect = Exception("Data fetch failed")
        result = reporter.get_position_pricing('ERROR', config)
        assert result is None
    
    def test_calculate_position_returns_comprehensive(self):
        """Comprehensive test of position return calculations."""
        
        # Test 1: Valid return calculation
        position = {'entry_price': 100.0, 'symbol': 'VALID'}
        result = reporter.calculate_position_returns(position, 110.0)
        assert result['return_pct'] == 10.0
        assert result['nifty_return_pct'] is None
        
        # Test 2: Invalid entry prices
        invalid_prices = [0, -10, 0.0, -5.5]
        for price in invalid_prices:
            position = {'entry_price': price, 'symbol': 'INVALID'}
            result = reporter.calculate_position_returns(position, 110.0)
            assert result['return_pct'] == 0.0
        
        # Test 3: With valid NIFTY data
        position = {'entry_price': 100.0, 'entry_date': '2023-01-01', 'symbol': 'WITH_NIFTY'}
        nifty_data = pd.DataFrame({
            'close': [18000, 18500, 19000]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        result = reporter.calculate_position_returns(position, 110.0, nifty_data)
        assert result['return_pct'] == 10.0
        assert result['nifty_return_pct'] is not None
        
        # Test 4: NIFTY calculation exception scenarios
        error_scenarios = [
            # Invalid entry date
            {'entry_price': 100.0, 'entry_date': 'invalid-date', 'symbol': 'BAD_DATE'},
            # Missing entry_date
            {'entry_price': 100.0, 'symbol': 'NO_DATE'},
            # Entry date too early (before NIFTY data)
            {'entry_price': 100.0, 'entry_date': '2022-01-01', 'symbol': 'TOO_EARLY'}
        ]
        
        for position in error_scenarios:
            result = reporter.calculate_position_returns(position, 110.0, nifty_data)
            assert result['return_pct'] == 10.0
            assert result['nifty_return_pct'] is None  # Should be None due to error
    
    @patch('kiss_signal.persistence.get_open_positions')
    @patch('kiss_signal.data.get_price_data')
    def test_process_open_positions_edge_cases(self, mock_get_price_data, mock_get_positions, tmp_path):
        """Test edge cases in process_open_positions function."""
        
        config = Mock()
        config.cache_dir = str(tmp_path)
        config.freeze_date = date(2023, 1, 15)
        config.hold_period = 20
        
        # Test 1: No open positions
        mock_get_positions.return_value = []
        positions_to_hold, positions_to_close = reporter.process_open_positions(
            tmp_path / "test.db", config, [], None
        )
        assert len(positions_to_hold) == 0
        assert len(positions_to_close) == 0
        
        # Test 2: Position with no pricing data available
        mock_get_positions.return_value = [
            {'id': 1, 'symbol': 'NO_PRICING', 'entry_date': '2023-01-01', 'entry_price': 100.0}
        ]
        
        def price_side_effect(symbol, **kwargs):
            if symbol == 'NO_PRICING':
                return None  # No pricing data
            return pd.DataFrame({'close': [105], 'high': [106], 'low': [104]})
        
        mock_get_price_data.side_effect = price_side_effect
        
        # Mock get_position_pricing to return None for NO_PRICING
        with patch.object(reporter, 'get_position_pricing', return_value=None):
            positions_to_hold, positions_to_close = reporter.process_open_positions(
                tmp_path / "test.db", config, [], None
            )
        
        assert len(positions_to_hold) == 1  # Should keep position open
        assert len(positions_to_close) == 0
        
        # Test 3: Position that meets exit criteria
        mock_get_positions.return_value = [
            {'id': 1, 'symbol': 'EXIT_ME', 'entry_date': '2023-01-01', 'entry_price': 100.0}
        ]
        
        exit_conditions = [{'type': 'stop_loss_pct', 'params': {'percentage': 0.05}}]
        
        with patch.object(reporter, 'get_position_pricing', 
                         return_value={'current_price': 94.0, 'current_high': 95.0, 'current_low': 93.0}):
            with patch.object(reporter, 'check_exit_conditions', 
                             return_value="Stop-loss triggered"):
                positions_to_hold, positions_to_close = reporter.process_open_positions(
                    tmp_path / "test.db", config, exit_conditions, None
                )
        
        assert len(positions_to_hold) == 0
        assert len(positions_to_close) == 1
        assert positions_to_close[0]['exit_reason'] == "Stop-loss triggered"
    
    def test_identify_new_signals_comprehensive(self, tmp_path):
        """Comprehensive test of identify_new_signals function."""
        
        # Create test database with open positions
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE positions (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                status TEXT DEFAULT 'open'
            )
        """)
        conn.execute("INSERT INTO positions (symbol, status) VALUES ('EXISTING', 'open')")
        conn.commit()
        conn.close()
        
        # Test 1: Empty results
        new_signals = reporter.identify_new_signals([], db_path)
        assert new_signals == []
        
        # Test 2: Mixed results with existing and new signals
        all_results = [
            {
                'symbol': 'EXISTING',  # Should be filtered out
                'rule_stack': [Mock(name='existing_rule', type='existing')],
                'edge_score': 0.8,
                'latest_close': 100.0
            },
            {
                'symbol': 'NEW_SIGNAL1',  # Should be included
                'rule_stack': [Mock(name='new_rule1', type='new1')],
                'edge_score': 0.7,
                'latest_close': 200.0
            },
            {
                'symbol': 'NEW_SIGNAL2',  # Should be included
                'rule_stack': [
                    Mock(name='rule1', type='type1'),
                    Mock(name='rule2', type='type2')
                ],
                'edge_score': 0.9,
                'latest_close': 300.0
            }
        ]
        
        new_signals = reporter.identify_new_signals(all_results, db_path)
        
        assert len(new_signals) == 2
        assert new_signals[0]['ticker'] == 'NEW_SIGNAL1'
        assert new_signals[0]['entry_price'] == 200.0
        assert new_signals[0]['edge_score'] == 0.7
        assert new_signals[1]['ticker'] == 'NEW_SIGNAL2'
        assert new_signals[1]['entry_price'] == 300.0
        assert "rule1 + rule2" in new_signals[1]['rule_stack']
    
    def test_format_strategy_analysis_comprehensive(self):
        """Comprehensive test of format_strategy_analysis_as_csv function."""
        
        # Test 1: Empty data for both aggregated and non-aggregated
        for aggregate in [True, False]:
            result = reporter.format_strategy_analysis_as_csv([], aggregate=aggregate)
            lines = result.strip().split('\n')
            assert len(lines) == 1  # Header only
        
        # Test 2: Non-aggregated format with comprehensive data
        analysis_data = [
            {
                'symbol': 'TEST1',
                'strategy_rule_stack': 'sma_crossover + rsi_oversold',
                'edge_score': 0.75,
                'win_pct': 0.65,
                'sharpe': 1.2,
                'total_return': 0.05,
                'total_trades': 15,
                'config_hash': 'hash123',
                'run_date': '2023-01-01',
                'config_details': '{"param": "value"}'
            },
            {
                'symbol': 'TEST2',
                'strategy_rule_stack': 'test"with"quotes',
                'edge_score': None,  # Test None handling
                'win_pct': float('inf'),  # Test inf handling
                'sharpe': float('-inf'),  # Test -inf handling
                'total_return': float('nan'),  # Test NaN handling
                'total_trades': 0,
                'config_hash': 'hash,with,commas',
                'run_date': '2023-01-02',
                'config_details': '{"key": "value,with,commas"}'
            }
        ]
        
        result = reporter.format_strategy_analysis_as_csv(analysis_data, aggregate=False)
        assert 'TEST1' in result
        assert 'TEST2' in result
        assert '0.7500' in result  # Edge score formatted
        assert '0.0000' in result  # Default for None values
        assert 'test""with""quotes' in result  # Quotes escaped
        
        # Test 3: Aggregated format with comprehensive data
        agg_data = [
            {
                'strategy_rule_stack': 'combined_strategy',
                'frequency': 3,
                'avg_edge_score': 0.8,
                'avg_win_pct': 0.6,
                'avg_sharpe': 1.5,
                'avg_return': 0.04,
                'avg_trades': 20.5,
                'top_symbols': 'SYM1 (2), SYM2 (1)',
                'config_hash': 'agg_hash',
                'run_date': '2023-01-01',
                'config_details': '{}'
            },
            {
                'strategy_rule_stack': 'strategy_with_nones',
                'frequency': 1,
                'avg_edge_score': None,
                'avg_win_pct': None,
                'avg_sharpe': None,
                'avg_return': None,
                'avg_trades': None,
                'top_symbols': '',
                'config_hash': '',
                'run_date': '2023-01-01',
                'config_details': ''
            }
        ]
        
        result = reporter.format_strategy_analysis_as_csv(agg_data, aggregate=True)
        assert 'combined_strategy' in result
        assert 'strategy_with_nones' in result
        assert '0.8000' in result  # Avg edge score formatted
        assert ',0.0,' in result  # Default for None avg_trades
    
    def test_generate_daily_report_error_scenarios(self, tmp_path):
        """Test error scenarios in generate_daily_report function."""
        
        config = Mock()
        config.reports_output_dir = str(tmp_path / "reports")
        config.freeze_date = date(2023, 1, 15)
        
        # Test 1: Permission error when creating directory
        config.reports_output_dir = "/root/cannot_write_here"
        result = reporter.generate_daily_report([], [], [], config)
        # Test 1: Permission error when creating directory (simulate)
        with patch.object(Path, "mkdir", side_effect=PermissionError("Cannot create directory")):
            result = reporter.generate_daily_report([], [], [], config)
            assert result is None  # Should handle error gracefully
        
        # Test 2: Invalid report date handling
        config.reports_output_dir = str(tmp_path / "reports")
        config.freeze_date = "invalid-date"  # Invalid date type
        
        try:
            result = reporter.generate_daily_report([], [], [], config)
            # Should either handle gracefully or raise appropriate error
        except (AttributeError, TypeError):
            pass  # Expected for invalid date
        
        # Test 3: File write permission error (simulate)
        config.freeze_date = date(2023, 1, 15)
        with patch('pathlib.Path.write_text', side_effect=PermissionError("Cannot write")):
            result = reporter.generate_daily_report([], [], [], config)
            assert result is None  # Should handle error gracefully


class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling in reporter functions."""
    
    def test_analysis_functions_with_malformed_data(self, tmp_path):
        """Test analysis functions with malformed database data."""
        
        db_path = tmp_path / "malformed.db"
        conn = sqlite3.connect(str(db_path))
        
        # Create table with various malformed data scenarios
        conn.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                rule_stack TEXT,
                edge_score REAL,
                win_pct REAL,
                sharpe REAL,
                avg_return REAL,
                total_trades INTEGER,
                config_hash TEXT,
                run_timestamp TEXT,
                config_snapshot TEXT
            )
        """)
        
        # Insert various malformed records
        test_records = [
            # Invalid JSON in rule_stack
            ('SYM1', 'not-valid-json', 0.5, 0.5, 1.0, 0.02, 10, 'hash1', '2023-01-01', '{}'),
            # Empty rule_stack
            ('SYM2', '', 0.6, 0.6, 1.1, 0.03, 12, 'hash2', '2023-01-01', '{}'),
            # None values
            ('SYM3', None, 0.7, 0.7, 1.2, 0.04, 15, 'hash3', '2023-01-01', None),
            # Valid record for comparison
            ('SYM4', '[{"name": "valid", "type": "sma_crossover"}]', 0.8, 0.8, 1.3, 0.05, 20, 'hash4', '2023-01-01', '{"valid": true}')
        ]
        
        for record in test_records:
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe,
                                      avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, record)
        
        conn.commit()
        conn.close()
        
        # Test analyze_strategy_performance with malformed data
        result = reporter.analyze_strategy_performance(db_path, min_trades=5)
        
        # Should handle malformed records gracefully and return valid ones
        valid_records = [r for r in result if r['symbol'] == 'SYM4']
        assert len(valid_records) > 0  # Valid record should be included
        
        # Test analyze_strategy_performance_aggregated with same data
        agg_result = reporter.analyze_strategy_performance_aggregated(db_path, min_trades=5)
        
        # Should handle malformed data and still process what it can
        assert isinstance(agg_result, list)  # Should return list even with errors
    
    def test_database_connection_errors(self):
        """Test various database connection error scenarios."""
        
        # Test with non-existent database file
        nonexistent_db = Path("/nonexistent/path/to/database.db")
        
        result1 = reporter.analyze_strategy_performance(nonexistent_db)
        assert result1 == []
        
        result2 = reporter.analyze_strategy_performance_aggregated(nonexistent_db)
        assert result2 == []
        
        result3 = reporter._fetch_best_strategies(nonexistent_db, "test_run", 0.5)
        assert result3 == []
        
        # Test with None database path
        result4 = reporter._fetch_best_strategies(None, "test_run", 0.5)
        assert result4 == []


@pytest.fixture
def comprehensive_test_db(tmp_path):
    """Create a comprehensive test database with various data scenarios."""
    db_path = tmp_path / "comprehensive.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create all necessary tables
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            rule_stack TEXT,
            edge_score REAL,
            win_pct REAL,
            sharpe REAL,
            avg_return REAL,
            total_trades INTEGER,
            config_hash TEXT,
            run_timestamp TEXT,
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
            exit_reason TEXT
        )
    """)
    
    # Insert comprehensive test data
    strategy_data = [
        ('GOOD_STRAT', '[{"name": "good_rule", "type": "sma_crossover"}]', 0.85, 0.75, 1.8, 0.06, 30, 'good_hash', 'test_run', '{"good": true}'),
        ('POOR_STRAT', '[{"name": "poor_rule", "type": "rsi_oversold"}]', 0.45, 0.40, 0.8, -0.01, 25, 'poor_hash', 'test_run', '{"poor": true}'),
        ('MALFORMED', 'invalid-json', 0.60, 0.55, 1.0, 0.02, 20, 'mal_hash', 'test_run', 'also-invalid'),
    ]
    
    for strategy in strategy_data:
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe,
                                  avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, strategy)
    
    position_data = [
        ('OPEN_POS', '2023-01-01', 100.0, 10, '[{"name": "test", "type": "test"}]', 'open', None, None, None),
        ('CLOSED_POS', '2022-12-01', 90.0, 15, '[{"name": "closed", "type": "closed"}]', 'closed', '2023-01-01', 99.0, 'Take profit'),
    ]
    
    for position in position_data:
        conn.execute("""
            INSERT INTO positions (symbol, entry_date, entry_price, quantity, rule_stack, status, exit_date, exit_price, exit_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, position)
    
    conn.commit()
    conn.close()
    
    return db_path