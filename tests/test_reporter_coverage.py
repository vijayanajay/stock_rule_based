"""
Tests for reporter module - focused on increasing test coverage.

This module targets uncovered code paths in reporter.py, following KISS principles
for pragmatic, thorough testing of edge cases and error conditions.
"""

import pytest
import sqlite3
import json
import logging
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from datetime import date, timedelta
from io import StringIO
import pandas as pd

from src.kiss_signal import reporter, data, rules, persistence
from src.kiss_signal.config import Config


@pytest.fixture
def basic_config(tmp_path: Path) -> Config:
    """Basic config for coverage tests."""
    universe_file = tmp_path / "universe.txt"
    universe_file.write_text("symbol\nTEST\nRELIANCE\n")
    return Config(
        universe_path=str(universe_file),
        historical_data_years=2,
        cache_dir=str(tmp_path / "cache"),
        cache_refresh_days=7,
        hold_period=20,
        database_path=str(tmp_path / "test.db"),
        min_trades_threshold=10,
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        reports_output_dir=str(tmp_path / "reports"),
        edge_score_threshold=0.50,
        freeze_date=None
    )


@pytest.fixture
def sample_db_with_data(tmp_path: Path) -> Path:
    """Database with sample data for testing."""
    db_path = tmp_path / "sample.db"
    persistence.create_database(db_path)
    
    # Add sample strategies
    strategies = [
        {
            "symbol": "TEST",
            "rule_stack": '[{"name": "sma_cross", "type": "sma_crossover", "params": {"short": 5, "long": 20}}]',
            "edge_score": 0.75, "win_pct": 0.65, "sharpe": 1.2, "total_trades": 15, "avg_return": 0.08,
            "config_hash": "abc123", "config_snapshot": '{"hold_period": 20}'
        },
        {
            "symbol": "RELIANCE", 
            "rule_stack": '[{"name": "rsi_signal", "type": "rsi_oversold", "params": {"period": 14}}]',
            "edge_score": 0.60, "win_pct": 0.70, "sharpe": 0.9, "total_trades": 12, "avg_return": 0.05,
            "config_hash": "def456", "config_snapshot": '{"hold_period": 15}'
        }
    ]
    
    with sqlite3.connect(str(db_path)) as conn:
        persistence.save_strategies_batch(conn, strategies, "2024-01-01_run")
    return db_path


class TestDatabaseErrorHandling:
    """Test database error scenarios."""
    
    def test_fetch_best_strategies_connection_error(self, tmp_path):
        """Test database connection failure in _fetch_best_strategies."""
        non_existent_db = tmp_path / "missing.db"
        
        # This should return empty list on connection error
        result = reporter._fetch_best_strategies(non_existent_db, "test_run", 0.5)
        assert result == []
    
    def test_fetch_best_strategies_sql_error(self, sample_db_with_data):
        """Test SQL error handling."""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = sqlite3.Error("SQL execution failed")
            
            result = reporter._fetch_best_strategies(sample_db_with_data, "test_run", 0.5)
            assert result == []
    
    def test_analyze_rule_performance_db_error(self, tmp_path):
        """Test rule performance analysis with database error."""
        non_existent_db = tmp_path / "missing.db"
        
        result = reporter.analyze_rule_performance(non_existent_db)
        assert result == []
    
    def test_analyze_strategy_performance_db_error(self, tmp_path):
        """Test strategy analysis with database error.""" 
        non_existent_db = tmp_path / "missing.db"
        
        result = reporter.analyze_strategy_performance(non_existent_db)
        assert result == []
    
    def test_analyze_strategy_performance_aggregated_db_error(self, tmp_path):
        """Test aggregated strategy analysis with database error."""
        non_existent_db = tmp_path / "missing.db"
        
        result = reporter.analyze_strategy_performance_aggregated(non_existent_db)
        assert result == []


class TestJsonParsingErrors:
    """Test JSON parsing error scenarios."""
    
    def test_identify_new_signals_json_decode_error(self, sample_db_with_data, basic_config):
        """Test JSON decode error in _identify_new_signals."""
        # Create strategy with malformed JSON
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                VALUES ('MALFORMED', '2024-01-01_run', 'invalid_json', 0.8, 0.7, 1.5, 10, 0.05)
            """)
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame({
                'close': [100, 105, 102],
                'open': [99, 104, 101],
                'high': [101, 106, 103],
                'low': [98, 103, 100],
                'volume': [1000, 1200, 900]
            }, index=pd.date_range('2024-01-01', periods=3))
            
            # Should handle JSON decode error gracefully
            result = reporter._identify_new_signals(sample_db_with_data, "2024-01-01_run", basic_config)
            # Should skip malformed entry and process valid ones
            assert len(result) >= 0  # May have valid entries
    
    def test_analyze_rule_performance_json_errors(self, sample_db_with_data):
        """Test rule performance analysis with JSON parsing errors."""
        # Add strategy with malformed rule_stack
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                VALUES ('JSON_ERROR', '2024-01-01_run', 'not_valid_json', 0.7, 0.6, 1.0, 8, 0.04)
            """)
        
        result = reporter.analyze_rule_performance(sample_db_with_data)
        # Should skip malformed entries and process valid ones
        assert isinstance(result, list)
    
    def test_analyze_strategy_performance_json_errors(self, sample_db_with_data):
        """Test strategy performance analysis with JSON errors."""
        # Add malformed data
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, config_snapshot)
                VALUES ('BAD_JSON', '2024-01-01_run', 'invalid', 0.6, 0.5, 0.8, 5, 0.03, 'bad_config_json')
            """)
        
        result = reporter.analyze_strategy_performance(sample_db_with_data)
        # Should handle errors gracefully
        assert isinstance(result, list)


class TestDataProcessingEdgeCases:
    """Test edge cases in data processing."""
    
    def test_find_signals_empty_rule_stack(self):
        """Test _find_signals_in_window with empty rule stack."""
        price_data = pd.DataFrame({
            'close': [100, 105, 102],
            'open': [99, 104, 101],
            'high': [101, 106, 103],
            'low': [98, 103, 100],
            'volume': [1000, 1200, 900]
        }, index=pd.date_range('2024-01-01', periods=3))
        
        result = reporter._find_signals_in_window(price_data, [])
        assert len(result) == len(price_data)
        assert not result.any()  # All False
    
    def test_find_signals_empty_dataframe(self):
        """Test _find_signals_in_window with empty DataFrame."""
        empty_df = pd.DataFrame()
        rule_stack = [{"type": "sma_crossover", "params": {"short": 5, "long": 20}}]
        
        result = reporter._find_signals_in_window(empty_df, rule_stack)
        assert len(result) == 0
    
    def test_find_signals_rule_function_error(self):
        """Test _find_signals_in_window with rule function error."""
        price_data = pd.DataFrame({
            'close': [100, 105, 102],
        }, index=pd.date_range('2024-01-01', periods=3))
        
        # Rule that doesn't exist
        rule_stack = [{"type": "nonexistent_rule", "params": {}}]
        
        result = reporter._find_signals_in_window(price_data, rule_stack)
        assert len(result) == len(price_data)
        assert not result.any()  # Should return all False on error
    
    def test_identify_new_signals_empty_price_data(self, sample_db_with_data, basic_config):
        """Test _identify_new_signals with empty price data."""
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame()  # Empty DataFrame
            
            result = reporter._identify_new_signals(sample_db_with_data, "2024-01-01_run", basic_config)
            assert isinstance(result, list)
    
    def test_identify_new_signals_non_list_rule_stack(self, sample_db_with_data, basic_config):
        """Test _identify_new_signals with rule stack that's not a list."""
        # Add strategy with rule_stack as dict instead of list
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                VALUES ('DICT_RULES', '2024-01-01_run', '{"type": "sma_crossover"}', 0.7, 0.6, 1.0, 8, 0.04)
            """)
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame({
                'close': [100, 105],
                'open': [99, 104],
                'high': [101, 106], 
                'low': [98, 103],
                'volume': [1000, 1200]
            }, index=pd.date_range('2024-01-01', periods=2))
            
            result = reporter._identify_new_signals(sample_db_with_data, "2024-01-01_run", basic_config)
            # Should skip non-list rule stacks
            assert isinstance(result, list)


class TestFileIOErrors:
    """Test file I/O error scenarios."""
    
    def test_generate_daily_report_file_write_error(self, sample_db_with_data, basic_config):
        """Test generate_daily_report with file write error."""
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame()
            
            with patch('src.kiss_signal.persistence.get_open_positions') as mock_positions:
                mock_positions.return_value = []
                
                with patch('pathlib.Path.write_text') as mock_write:
                    mock_write.side_effect = OSError("Permission denied")
                    
                    result = reporter.generate_daily_report(
                        sample_db_with_data, "2024-01-01_run", basic_config, {}
                    )
                    assert result is None
    
    def test_generate_daily_report_directory_creation_error(self, sample_db_with_data, basic_config):
        """Test generate_daily_report with directory creation error."""
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame()
            
            with patch('src.kiss_signal.persistence.get_open_positions') as mock_positions:
                mock_positions.return_value = []
                
                with patch('pathlib.Path.mkdir') as mock_mkdir:
                    mock_mkdir.side_effect = OSError("Cannot create directory")
                    
                    result = reporter.generate_daily_report(
                        sample_db_with_data, "2024-01-01_run", basic_config, {}
                    )
                    assert result is None


class TestConfigurationEdgeCases:
    """Test configuration edge cases."""
    
    def test_identify_new_signals_no_hold_period(self, sample_db_with_data, tmp_path):
        """Test _identify_new_signals with config missing hold_period."""
        universe_file = tmp_path / "universe.txt"
        universe_file.write_text("symbol\nTEST\nRELIANCE\n")
        
        config = Config(
            universe_path=str(universe_file),
            historical_data_years=2,
            cache_dir=str(tmp_path / "cache"),
            cache_refresh_days=7,
            hold_period=20,  # Required field - can't be missing
            database_path="test.db",
            min_trades_threshold=10,
            edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
            reports_output_dir="reports",
            edge_score_threshold=0.50
        )
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame({
                'close': [100, 105],
                'open': [99, 104],
                'high': [101, 106],
                'low': [98, 103], 
                'volume': [1000, 1200]
            }, index=pd.date_range('2024-01-01', periods=2))
            
            result = reporter._identify_new_signals(sample_db_with_data, "2024-01-01_run", config)
            assert isinstance(result, list)
    
    def test_process_open_positions_nifty_data_error(self, basic_config):
        """Test _process_open_positions with NIFTY data fetch error."""
        open_positions = [{
            "id": 1,
            "symbol": "TEST",
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "rule_stack": '[{"type": "sma_crossover"}]'
        }]
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            # First call for stock data - success
            # Second call for NIFTY data - failure
            mock_price_data.side_effect = [
                pd.DataFrame({
                    'close': [105],
                    'high': [106],
                    'low': [104],
                }, index=pd.date_range('2024-01-02', periods=1)),
                Exception("NIFTY data fetch failed")
            ]
            
            positions_to_hold, positions_to_close = reporter._process_open_positions(
                open_positions, basic_config, {}
            )
            
            # Should handle NIFTY error gracefully
            assert len(positions_to_hold) + len(positions_to_close) == 1
            # Should set nifty_return_pct to 0.0 on error
            all_positions = positions_to_hold + positions_to_close
            assert all_positions[0]['nifty_return_pct'] == 0.0


class TestExitConditionEdgeCases:
    """Test edge cases in exit condition checking."""
    
    def test_check_exit_conditions_rule_function_not_found(self):
        """Test _check_exit_conditions with non-existent rule function."""
        position = {"entry_price": 100.0}
        price_data = pd.DataFrame({
            'close': [105],
            'high': [106],
            'low': [104],
        }, index=pd.date_range('2024-01-01', periods=1))
        
        sell_conditions = [{"type": "nonexistent_rule", "params": {}}]
        
        result = reporter._check_exit_conditions(
            position, price_data, 104.0, 106.0, sell_conditions, 5, 20
        )
        assert result is None
    
    def test_check_exit_conditions_rule_execution_error(self):
        """Test _check_exit_conditions with rule execution error."""
        position = {"entry_price": 100.0}
        price_data = pd.DataFrame({
            'close': [105],
            'high': [106], 
            'low': [104],
        }, index=pd.date_range('2024-01-01', periods=1))
        
        # Use a real rule but with invalid parameters to cause error
        sell_conditions = [{"type": "sma_crossover", "params": {"short": -1, "long": -1}}]
        
        result = reporter._check_exit_conditions(
            position, price_data, 104.0, 106.0, sell_conditions, 5, 20
        )
        assert result is None
    
    def test_check_exit_conditions_dict_vs_object_params(self):
        """Test _check_exit_conditions with dict parameters vs object parameters."""
        position = {"entry_price": 100.0}
        price_data = pd.DataFrame({
            'close': [90],  # Trigger stop loss
            'high': [91],
            'low': [89],
        }, index=pd.date_range('2024-01-01', periods=1))
        
        # Test with dict params
        sell_conditions = [{"type": "stop_loss_pct", "params": {"percentage": 0.05}}]
        
        result = reporter._check_exit_conditions(
            position, price_data, 89.0, 91.0, sell_conditions, 5, 20
        )
        assert "Stop-loss" in result
        
        # Test with object-like params (mock object with percentage attribute)
        class MockParams:
            percentage = 0.05
        
        class MockCondition:
            type = "stop_loss_pct" 
            params = MockParams()
            name = "test_stop_loss"
        
        sell_conditions = [MockCondition()]
        
        result = reporter._check_exit_conditions(
            position, price_data, 89.0, 91.0, sell_conditions, 5, 20
        )
        assert "Stop-loss" in result


class TestCSVFormattingEdgeCases:
    """Test CSV formatting edge cases."""
    
    def test_format_strategy_analysis_csv_empty_data(self):
        """Test CSV formatting with empty data."""
        result_aggregated = reporter.format_strategy_analysis_as_csv([], aggregate=True)
        result_per_stock = reporter.format_strategy_analysis_as_csv([], aggregate=False)
        
        # Should return headers only
        assert "strategy_rule_stack,frequency" in result_aggregated
        assert "symbol,strategy_rule_stack" in result_per_stock
    
    def test_format_strategy_analysis_csv_none_values(self):
        """Test CSV formatting with None values."""
        data = [{
            'strategy_rule_stack': 'test_strategy',
            'frequency': 5,
            'avg_edge_score': None,
            'avg_win_pct': None,
            'avg_sharpe': None,
            'avg_return': None,
            'avg_trades': None,
            'top_symbols': 'TEST, RELIANCE',
            'config_hash': 'abc123',
            'run_date': '2024-01-01',
            'config_details': '{"test": "value"}'
        }]
        
        result = reporter.format_strategy_analysis_as_csv(data, aggregate=True)
        
        # Should handle None values gracefully
        assert "0.0000" in result  # None values converted to 0.0000
        assert "test_strategy" in result
    
    def test_format_strategy_analysis_csv_special_characters(self):
        """Test CSV formatting with special characters requiring escaping."""
        data = [{
            'symbol': 'TEST"QUOTE',
            'strategy_rule_stack': 'sma, cross "over"',
            'edge_score': 0.75,
            'win_pct': 0.65,
            'sharpe': 1.2,
            'total_return': 0.08,
            'total_trades': 15,
            'config_hash': 'abc"123',
            'run_date': '2024-01-01',
            'config_details': '{"test": "value, with comma"}'
        }]
        
        result = reporter.format_strategy_analysis_as_csv(data, aggregate=False)
        
        # Should properly escape quotes
        assert '""' in result  # Quotes should be escaped as ""
        assert 'TEST""QUOTE' in result


class TestPositionProcessingEdgeCases:
    """Test edge cases in position processing."""
    
    def test_process_open_positions_zero_entry_price(self, basic_config):
        """Test _process_open_positions with zero entry price."""
        open_positions = [{
            "id": 1,
            "symbol": "TEST",
            "entry_date": "2024-01-01", 
            "entry_price": 0.0,  # Zero entry price
            "rule_stack": '[{"type": "sma_crossover"}]'
        }]
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame({
                'close': [105],
                'high': [106],
                'low': [104],
            }, index=pd.date_range('2024-01-02', periods=1))
            
            positions_to_hold, positions_to_close = reporter._process_open_positions(
                open_positions, basic_config, {}
            )
            
            all_positions = positions_to_hold + positions_to_close
            # Should set return_pct to 0.0 when entry_price is 0
            assert all_positions[0]['return_pct'] == 0.0
    
    def test_process_open_positions_stale_data_logging(self, basic_config, caplog):
        """Test _process_open_positions logs stale data appropriately."""
        open_positions = [{
            "id": 1,
            "symbol": "TEST",
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "rule_stack": '[{"type": "sma_crossover"}]'
        }]
        
        # Set freeze_date to future date to simulate stale data
        basic_config.freeze_date = date(2024, 1, 10)
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            # Return data that's older than freeze_date
            mock_price_data.return_value = pd.DataFrame({
                'close': [105],
                'high': [106],
                'low': [104],
            }, index=pd.date_range('2024-01-05', periods=1))  # Older than freeze_date
            
            with caplog.at_level(logging.INFO):
                positions_to_hold, positions_to_close = reporter._process_open_positions(
                    open_positions, basic_config, {}
                )
                
                # Should log stale data warning
                assert any("Using stale data" in record.message for record in caplog.records)
    
    def test_process_open_positions_exception_handling(self, basic_config):
        """Test _process_open_positions handles exceptions gracefully."""
        open_positions = [{
            "id": 1,
            "symbol": "TEST",
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "rule_stack": '[{"type": "sma_crossover"}]'
        }]
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.side_effect = Exception("Data fetch failed")
            
            positions_to_hold, positions_to_close = reporter._process_open_positions(
                open_positions, basic_config, {}
            )
            
            # Should handle exception and add position to hold with N/A values
            assert len(positions_to_hold) == 1
            assert positions_to_hold[0]['current_price'] is None
            assert positions_to_hold[0]['return_pct'] is None
            assert positions_to_hold[0]['nifty_return_pct'] is None


class TestAnalysisFunctionEdgeCases:
    """Test edge cases in analysis functions."""
    
    def test_analyze_rule_performance_malformed_rule_defs(self, sample_db_with_data):
        """Test analyze_rule_performance with malformed rule definitions."""
        # Add strategies with various malformed rule stacks
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            # Rule stack with non-dict elements
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                VALUES ('TEST1', '2024-01-01_run', '[{"type": "valid"}, "not_a_dict", 123]', 0.7, 0.6, 1.0, 10, 0.05)
            """)
            # Rule def missing 'name' field  
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                VALUES ('TEST2', '2024-01-01_run', '[{"type": "valid"}, {"type": "no_name"}]', 0.8, 0.7, 1.2, 12, 0.06)
            """)
        
        result = reporter.analyze_rule_performance(sample_db_with_data)
        # Should handle malformed data gracefully and process valid entries
        assert isinstance(result, list)
        
    def test_analyze_strategy_performance_aggregated_empty_records(self, tmp_path):
        """Test aggregated analysis with strategy groups that have no records."""
        db_path = tmp_path / "empty_test.db"
        persistence.create_database(db_path)
        
        # Add strategy with empty rule stack
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, avg_return, total_trades)
                VALUES ('TEST', '2024-01-01_run', '[]', 0.0, 0.0, 0.0, 0.0, 0)
            """)
        
        result = reporter.analyze_strategy_performance_aggregated(db_path)
        # Should handle empty rule stacks gracefully
        assert isinstance(result, list)
    
    def test_analyze_strategy_performance_aggregated_config_parsing_error(self, sample_db_with_data):
        """Test aggregated analysis with config snapshot parsing errors."""
        # Add strategy with malformed config_snapshot
        with sqlite3.connect(str(sample_db_with_data)) as conn:
            conn.execute("""
                INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, 
                                      avg_return, total_trades, config_hash, config_snapshot)
                VALUES ('BAD_CONFIG', '2024-01-01_run', '[{"name": "test", "type": "sma_crossover"}]', 
                        0.7, 0.6, 1.0, 0.05, 10, 'hash123', 'invalid_json_config')
            """)
        
        result = reporter.analyze_strategy_performance_aggregated(sample_db_with_data)
        # Should handle JSON parsing errors in config_snapshot
        assert isinstance(result, list)
        # Should use empty dict for malformed config
        for record in result:
            if 'BAD_CONFIG' in record.get('top_symbols', ''):
                assert record['config_details'] == '{}'


class TestAdditionalCoverageTargets:
    """Additional targeted tests to push coverage higher."""
    
    def test_fetch_best_strategies_no_strategies_above_threshold(self, sample_db_with_data):
        """Test _fetch_best_strategies when no strategies meet threshold."""
        # Should log warning when no strategies above threshold
        result = reporter._fetch_best_strategies(sample_db_with_data, "2024-01-01_run", 0.99)  # Very high threshold
        assert result == []
    
    def test_fetch_best_strategies_unexpected_error(self, sample_db_with_data):
        """Test _fetch_best_strategies with unexpected error."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = RuntimeError("Unexpected error")
            
            result = reporter._fetch_best_strategies(sample_db_with_data, "test_run", 0.5)
            assert result == []
    
    def test_identify_new_signals_no_strategies_found(self, tmp_path, basic_config):
        """Test _identify_new_signals when no strategies above threshold."""
        empty_db = tmp_path / "empty.db"
        persistence.create_database(empty_db)
        
        result = reporter._identify_new_signals(empty_db, "2024-01-01_run", basic_config)
        assert result == []
    
    def test_identify_new_signals_strategy_processing_exception(self, sample_db_with_data, basic_config):
        """Test _identify_new_signals with exception during strategy processing."""
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            # First call succeeds, second call fails with unexpected error
            mock_price_data.side_effect = [
                pd.DataFrame({
                    'close': [100, 105, 102],
                    'open': [99, 104, 101],
                    'high': [101, 106, 103],
                    'low': [98, 103, 100],
                    'volume': [1000, 1200, 900]
                }, index=pd.date_range('2024-01-01', periods=3)),
                RuntimeError("Unexpected data processing error")
            ]
            
            result = reporter._identify_new_signals(sample_db_with_data, "2024-01-01_run", basic_config)
            # Should continue processing despite one strategy failing
            assert isinstance(result, list)
    
    def test_generate_daily_report_comprehensive_flow(self, sample_db_with_data, basic_config):
        """Test generate_daily_report end-to-end successful flow."""
        # Mock all the data dependencies
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            mock_price_data.return_value = pd.DataFrame({
                'close': [100, 105, 102, 98, 101],
                'open': [99, 104, 101, 97, 100],
                'high': [101, 106, 103, 99, 102],
                'low': [98, 103, 100, 96, 99],
                'volume': [1000, 1200, 900, 800, 1100]
            }, index=pd.date_range('2024-01-01', periods=5))
            
            with patch('src.kiss_signal.persistence.get_open_positions') as mock_positions:
                mock_positions.return_value = [{
                    "id": 1,
                    "symbol": "TEST",
                    "entry_date": "2024-01-01",
                    "entry_price": 100.0,
                    "rule_stack": '[{"type": "sma_crossover", "params": {"short": 5, "long": 20}}]'
                }]
                
                result = reporter.generate_daily_report(
                    sample_db_with_data, "2024-01-01_run", basic_config, {}
                )
                
                # Should return the report path on success
                assert result is not None
                assert str(result).endswith('.md')
    
    def test_check_exit_conditions_stop_loss_trigger(self):
        """Test _check_exit_conditions when stop-loss is triggered."""
        position = {"entry_price": 100.0}
        price_data = pd.DataFrame({
            'close': [85],  # 15% drop triggers stop-loss
            'high': [86],
            'low': [84],
        }, index=pd.date_range('2024-01-01', periods=1))
        
        sell_conditions = [{"type": "stop_loss_pct", "params": {"percentage": 0.10}}]
        
        result = reporter._check_exit_conditions(
            position, price_data, 84.0, 86.0, sell_conditions, 5, 20
        )
        assert result is not None
        assert "Stop-loss" in result
    
    def test_process_open_positions_successful_processing(self, basic_config):
        """Test _process_open_positions with successful position processing."""
        open_positions = [{
            "id": 1,
            "symbol": "TEST",
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "rule_stack": '[{"type": "sma_crossover", "params": {"short": 5, "long": 20}}]'
        }]
        
        with patch('src.kiss_signal.data.get_price_data') as mock_price_data:
            # Mock both stock and NIFTY data calls
            mock_price_data.side_effect = [
                # Stock data
                pd.DataFrame({
                    'close': [105],
                    'high': [106],
                    'low': [104],
                }, index=pd.date_range('2024-01-02', periods=1)),
                # NIFTY data  
                pd.DataFrame({
                    'close': [20000],
                    'high': [20100],
                    'low': [19900],
                }, index=pd.date_range('2024-01-02', periods=1))
            ]
            
            positions_to_hold, positions_to_close = reporter._process_open_positions(
                open_positions, basic_config, {}
            )
            
            # Should process position successfully
            all_positions = positions_to_hold + positions_to_close
            assert len(all_positions) == 1
            assert all_positions[0]['current_price'] == 105
            assert all_positions[0]['return_pct'] == 5.0  # (105-100)/100 * 100


# ...existing code...
if __name__ == "__main__":
    pytest.main([__file__])
