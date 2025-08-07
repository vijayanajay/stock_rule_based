"""Comprehensive tests for reporter coverage improvement.

This module focuses on testing previously uncovered paths in reporter.py
to achieve >88% test coverage on reporting functionality.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import sqlite3
from pathlib import Path
import json
from datetime import date
from collections import defaultdict

from src.kiss_signal.reporter import (
    WalkForwardReport, generate_daily_report, analyze_strategy_performance,
    analyze_strategy_performance_aggregated, format_strategy_analysis_as_csv,
    _format_new_buys_table, _format_open_positions_table, _format_sell_positions_table,
    format_walk_forward_results, _fetch_best_strategies
)


class TestReporterCoverageFill:
    """Test class focused on filling coverage gaps in reporter.py."""
    
    def test_walk_forward_report_empty_oos_results(self):
        """Test WalkForwardReport with empty oos_results."""
        report = WalkForwardReport([])
        
        assert report.oos_results == []
        assert report.consolidated_metrics == {}
    
    def test_walk_forward_report_with_nan_values(self):
        """Test WalkForwardReport handling NaN values."""
        oos_results = [
            {
                'avg_return': np.nan,
                'sharpe': np.inf,
                'win_pct': 0.6,
                'total_trades': 10,
                'edge_score': 0.7
            },
            {
                'avg_return': -np.inf,
                'sharpe': np.nan,
                'win_pct': 0.4,
                'total_trades': 8,
                'edge_score': 0.3
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        assert len(report.oos_results) == 2
        assert isinstance(report.consolidated_metrics, dict)
    
    def test_walk_forward_report_single_oos_period(self):
        """Test WalkForwardReport with only one OOS period."""
        oos_results = [
            {
                'avg_return': 50.0,
                'sharpe': 1.2,
                'win_pct': 0.65,
                'total_trades': 15,
                'edge_score': 0.8
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        assert len(report.oos_results) == 1
        assert report.consolidated_metrics['total_trades'] == 15
    
    def test_walk_forward_report_zero_trades_period(self):
        """Test WalkForwardReport with periods containing zero trades."""
        oos_results = [
            {
                'avg_return': 0.0,
                'sharpe': 0.0,
                'win_pct': 0.0,
                'total_trades': 0,  # Zero trades
                'edge_score': 0.0
            },
            {
                'avg_return': 100.0,
                'sharpe': 1.5,
                'win_pct': 0.7,
                'total_trades': 20,
                'edge_score': 0.9
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        assert len(report.oos_results) == 2
        assert report.consolidated_metrics['total_trades'] == 20
    
    def test_format_table_functions_with_none_values(self):
        """Test table formatting functions with None/NaN values."""
        
        # Test with None values that should be handled safely
        strategies_with_none = [
            {'symbol': 'TEST1', 'edge_score': None, 'date': '2023-01-01', 'entry_price': 100.0, 'rule_stack': 'test'},
            {'symbol': 'TEST2', 'edge_score': 0.8, 'date': '2023-01-02', 'entry_price': None, 'rule_stack': 'test'},
            {'symbol': 'TEST3', 'edge_score': 0.7, 'date': '2023-01-03', 'entry_price': 110.0, 'rule_stack': None},
            # Add a dict with missing keys to test .get() with defaults
            {'symbol': 'TEST4'}
        ]
        
        # Should handle None values gracefully with N/A
        table = _format_new_buys_table(strategies_with_none)
        for i in range(1, 5):
            assert f'TEST{i}' in table
        assert 'N/A' in table  # Should have N/A for None values
        
        # Test open positions with None values
        positions_with_none = [
            {'symbol': 'TEST1', 'entry_price': None, 'entry_date': '2023-01-01', 'return_pct': 50.0, 'days_held': 10, 'nifty_return_pct': 10.0, 'current_price': 105.0},
            {'symbol': 'TEST2', 'entry_price': 100.0, 'entry_date': '2023-01-02', 'return_pct': None, 'days_held': 8, 'nifty_return_pct': 8.0, 'current_price': 102.0},
            {'symbol': 'TEST3', 'entry_price': 110.0, 'entry_date': '2023-01-03', 'return_pct': 25.0, 'days_held': 5, 'nifty_return_pct': None, 'current_price': None},
            # Add a dict with missing keys to test .get() with defaults
            {'symbol': 'TEST4'}
        ]
        
        table = _format_open_positions_table(positions_with_none, 30)
        for i in range(1, 5):
            assert f'TEST{i}' in table
        assert 'N/A' in table  # Should have N/A for None values
    
    @patch('sqlite3.connect')
    def test_analyze_strategy_performance_db_error(self, mock_connect):
        """Test analyze_strategy_performance with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")
        
        result = analyze_strategy_performance(Path('test.db'))
        assert result == []
    
    @patch('sqlite3.connect')
    def test_analyze_strategy_performance_aggregated_db_error(self, mock_connect):
        """Test analyze_strategy_performance_aggregated with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")
        
        result = analyze_strategy_performance_aggregated(Path('test.db'))
        assert result == []
    
    def test_format_strategy_analysis_as_csv_empty_data(self):
        """Test format_strategy_analysis_as_csv with empty data."""
        
        # Test with empty list
        csv_content = format_strategy_analysis_as_csv([], aggregate=False)
        lines = csv_content.strip().split('\n')
        
        # Should have header only
        assert len(lines) == 1
        assert 'symbol' in lines[0].lower()
        
        # Test aggregated format with empty data
        csv_content = format_strategy_analysis_as_csv([], aggregate=True)
        lines = csv_content.strip().split('\n')
        
        # Should have header only
        assert len(lines) == 1
        assert 'rule_stack' in lines[0].lower()
    
    def test_analyze_strategy_performance_aggregated_empty_records(self, tmp_path):
        """Test analyze_strategy_performance_aggregated with empty database records."""
        db_path = tmp_path / "empty_test.db"
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
        
        result = analyze_strategy_performance_aggregated(db_path, min_trades=10)
        assert result == []
    
    def test_walk_forward_report_calculation_edge_cases(self):
        """Test WalkForwardReport with edge case calculations."""
        # Test with very small numbers and mixed date formats
        oos_results = [
            {
                'avg_return': 0.001,
                'sharpe': 0.001,
                'win_pct': 0.501,  # Barely profitable
                'total_trades': 1,
                'edge_score': 0.501,
                'oos_test_start': '2023-01-01',  # string date
                'oos_test_end': pd.Timestamp('2023-02-01')  # timestamp date
            },
            {
                'avg_return': 0.002,
                'sharpe': 0.002,
                'win_pct': 0.502,  # Barely profitable
                'total_trades': 1,
                'edge_score': 0.502,
                'oos_test_start': '2023-02-01',  # string date
                'oos_test_end': pd.Timestamp('2023-03-01')  # timestamp date
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        assert len(report.oos_results) == 2
        assert 'total_trades' in report.consolidated_metrics
        assert report.consolidated_metrics['total_trades'] == 2
    
    def test_walk_forward_report_generate_report_method(self):
        """Test WalkForwardReport.generate_report method."""
        oos_results = [
            {
                'avg_return': 50.0,
                'sharpe': 1.2,
                'win_pct': 0.65,
                'total_trades': 15,
                'edge_score': 0.8,
                'rule_stack': [{'name': 'test_rule', 'type': 'test'}],
                'oos_test_start': '2023-01-01',
                'oos_test_end': '2023-02-01'
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        # Test the generate_report method
        report_text = report.generate_report('TEST_SYMBOL')
        
        assert 'TEST_SYMBOL' in report_text
        assert 'WALK-FORWARD ANALYSIS' in report_text  # Match actual output
        assert isinstance(report_text, str)
        assert len(report_text) > 0
    
    def test_format_walk_forward_results_empty(self):
        """Test format_walk_forward_results with empty results."""
        result = format_walk_forward_results([])
        assert "No walk-forward results" in result
    
    def test_format_walk_forward_results_no_oos(self):
        """Test format_walk_forward_results with no OOS results."""
        results = [
            {'symbol': 'TEST', 'is_oos': False, 'edge_score': 0.8}
        ]
        result = format_walk_forward_results(results)
        assert "No out-of-sample results" in result
    
    def test_format_walk_forward_results_with_data(self):
        """Test format_walk_forward_results with valid data."""
        results = [
            {
                'symbol': 'TEST1',
                'is_oos': True,
                'edge_score': 0.8,
                'win_pct': 0.6,
                'sharpe': 1.2,
                'total_trades': 20,
                'avg_return': 15.0,
                'rule_stack': [{'name': 'test_rule', 'type': 'test'}],
                'oos_test_start': '2023-01-01',
                'oos_test_end': '2023-02-01'
            },
            {
                'symbol': 'TEST2',
                'is_oos': True,
                'edge_score': 0.7,
                'win_pct': 0.55,
                'sharpe': 1.0,
                'total_trades': 15,
                'avg_return': 12.0,
                'rule_stack': [{'name': 'test_rule2', 'type': 'test2'}],
                'oos_test_start': '2023-01-01',
                'oos_test_end': '2023-02-01'
            }
        ]
        
        result = format_walk_forward_results(results)
        assert 'TEST1' in result
        assert 'TEST2' in result
        assert 'WALK-FORWARD ANALYSIS SUMMARY' in result
    
    def test_fetch_best_strategies_none_db_path(self):
        """Test _fetch_best_strategies with None database path."""
        result = _fetch_best_strategies(None, 'test_run', 0.5)
        assert result == []
    
    @patch('sqlite3.connect')
    def test_fetch_best_strategies_file_not_found(self, mock_connect):
        """Test _fetch_best_strategies with file not found error."""
        mock_connect.side_effect = FileNotFoundError("No such file")
        
        result = _fetch_best_strategies(Path('nonexistent.db'), 'test_run', 0.5)
        assert result == []
    
    def test_analyze_strategy_performance_malformed_json(self, tmp_path):
        """Test analyze_strategy_performance with malformed JSON data."""
        db_path = tmp_path / "malformed_test.db"
        conn = sqlite3.connect(str(db_path))
        
        # Create table with malformed JSON data
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
        
        # Insert record with malformed rule_stack JSON
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe,
                                  avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'MALFORMED', 'invalid-json', 0.5, 0.5, 1.0, 
            0.02, 15, 'hash123', '2023-01-01 12:00:00', 'invalid-json'
        ))
        
        # Insert valid record
        conn.execute("""
            INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe,
                                  avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'VALID', '[{"type": "sma_crossover"}]', 0.8, 0.6, 1.5,
            0.03, 25, 'hash456', '2023-01-01 12:00:00', '{}'
        ))
        
        conn.commit()
        conn.close()
        
        result = analyze_strategy_performance(db_path, min_trades=10)
        
        # Should skip malformed record and return only valid one
        assert len(result) == 1
        assert result[0]['symbol'] == 'VALID'
    
    def test_analyze_strategy_performance_aggregated_complex(self, tmp_path):
        """Test analyze_strategy_performance_aggregated with complex data."""
        db_path = tmp_path / "complex_test.db"
        conn = sqlite3.connect(str(db_path))
        
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
        
        # Insert multiple records for the same strategy across different symbols
        strategies = [
            ('SYM1', '[{"name": "sma_cross", "type": "sma_crossover"}]', 0.8, 0.6, 1.5, 0.03, 20, 'hash1', '2023-01-01', '{"param": 1}'),
            ('SYM2', '[{"name": "sma_cross", "type": "sma_crossover"}]', 0.7, 0.55, 1.2, 0.025, 18, 'hash1', '2023-01-01', '{"param": 1}'),
            ('SYM3', '[{"name": "rsi_rule", "type": "rsi_oversold"}]', 0.6, 0.5, 1.0, 0.02, 15, 'hash2', '2023-01-01', '{"param": 2}'),
        ]
        
        for strategy in strategies:
            conn.execute("""
                INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe,
                                      avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, strategy)
        
        conn.commit()
        conn.close()
        
        result = analyze_strategy_performance_aggregated(db_path, min_trades=10)
        
        assert len(result) == 2  # Two different strategy groups
        
        # Find the SMA strategy group (should have 2 records)
        sma_group = next((r for r in result if 'sma_cross' in r['strategy_rule_stack']), None)
        assert sma_group is not None
        assert sma_group['frequency'] == 2
        
        # Find the RSI strategy group (should have 1 record)
        rsi_group = next((r for r in result if 'rsi_rule' in r['strategy_rule_stack']), None)
        assert rsi_group is not None
        assert rsi_group['frequency'] == 1
    
    def test_csv_formatting_with_special_characters(self):
        """Test CSV formatting with special characters and edge cases."""
        analysis_data = [
            {
                'symbol': 'TEST"QUOTE',
                'strategy_rule_stack': 'strategy,with,commas',
                'edge_score': float('inf'),
                'win_pct': float('-inf'),
                'sharpe': float('nan'),
                'total_return': None,
                'total_trades': 0,
                'config_hash': 'hash"with"quotes',
                'run_date': '2023-01-01',
                'config_details': '{"key": "value,with,commas"}'
            }
        ]
        
        # Should handle special characters by escaping quotes
        result = format_strategy_analysis_as_csv(analysis_data, aggregate=False)
        assert isinstance(result, str)
        assert 'TEST""QUOTE' in result  # Quotes should be escaped
        assert 'strategy,with,commas' in result  # Commas in quoted field
    
    def test_sell_positions_table_comprehensive(self):
        """Test comprehensive sell positions table formatting."""
        positions = [
            {
                'symbol': 'COMPLETE',
                'entry_date': '2023-01-01',
                'exit_date': '2023-01-15',
                'entry_price': 100.0,
                'exit_price': 110.0,
                'return_pct': 10.0,
                'days_held': 14,
                'exit_reason': 'Take-profit triggered'
            },
            {
                'symbol': 'MISSING_FIELDS',
                # Many fields missing to test defaults
            },
            {
                'symbol': 'NULL_VALUES',
                'entry_date': None,
                'exit_date': None,
                'entry_price': None,
                'exit_price': None,
                'return_pct': None,
                'days_held': None,
                'exit_reason': None
            }
        ]
        
        result = _format_sell_positions_table(positions)
        assert 'COMPLETE' in result
        assert 'Take-profit triggered' in result
        assert 'MISSING_FIELDS' in result
        assert 'NULL_VALUES' in result
        assert 'Unknown' in result  # Default exit reason
        assert 'N/A' in result  # Default for missing values
