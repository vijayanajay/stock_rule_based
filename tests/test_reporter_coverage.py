"""Comprehensive tests for reporter coverage improvement.

This module focuses on testing previously uncovered paths in reporter.py
to achieve >92% test coverage on reporting functionality.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import sqlite3
from pathlib import Path

from src.kiss_signal.reporter import (
    WalkForwardReport, generate_daily_report, analyze_strategy_performance,
    analyze_strategy_performance_aggregated, format_strategy_analysis_as_csv,
    _format_new_buys_table, _format_open_positions_table
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
            {'ticker': 'TEST1', 'edge_score': None, 'date': '2023-01-01', 'entry_price': 100.0, 'rule_stack': 'test'},
            {'ticker': 'TEST2', 'edge_score': 0.8, 'date': '2023-01-02', 'entry_price': None, 'rule_stack': 'test'},
            {'ticker': 'TEST3', 'edge_score': 0.7, 'date': '2023-01-03', 'entry_price': 110.0, 'rule_stack': None},
        ]
        
        # Should handle None values gracefully with N/A
        table = _format_new_buys_table(strategies_with_none)
        assert 'TEST1' in table
        assert 'TEST2' in table
        assert 'TEST3' in table
        assert 'N/A' in table  # Should have N/A for None values
        
        # Test open positions with None values
        positions_with_none = [
            {'symbol': 'TEST1', 'entry_price': None, 'entry_date': '2023-01-01', 'return_pct': 50.0, 'days_held': 10, 'nifty_return_pct': 10.0, 'current_price': 105.0},
            {'symbol': 'TEST2', 'entry_price': 100.0, 'entry_date': '2023-01-02', 'return_pct': None, 'days_held': 8, 'nifty_return_pct': 8.0, 'current_price': 102.0},
            {'symbol': 'TEST3', 'entry_price': 110.0, 'entry_date': '2023-01-03', 'return_pct': 25.0, 'days_held': 5, 'nifty_return_pct': None, 'current_price': None},
        ]
        
        table = _format_open_positions_table(positions_with_none, 30)
        assert 'TEST1' in table
        assert 'TEST2' in table
        assert 'TEST3' in table
        assert 'N/A' in table  # Should have N/A for None values
    
    @patch('src.kiss_signal.persistence.get_connection')
    def test_analyze_strategy_performance_db_error(self, mock_get_connection):
        """Test analyze_strategy_performance with database error."""
        mock_get_connection.side_effect = sqlite3.Error("Database error")
        
        with patch('src.kiss_signal.reporter.logger') as mock_logger:
            result = analyze_strategy_performance(Path('test.db'))
            
        mock_logger.error.assert_called()
        assert result == []
    
    @patch('src.kiss_signal.persistence.get_connection')
    def test_analyze_strategy_performance_aggregated_db_error(self, mock_get_connection):
        """Test analyze_strategy_performance_aggregated with database error."""
        mock_get_connection.side_effect = sqlite3.Error("Database error")
        
        with patch('src.kiss_signal.reporter.logger') as mock_logger:
            result = analyze_strategy_performance_aggregated(Path('test.db'))
            
        mock_logger.error.assert_called()
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
    
    @patch('src.kiss_signal.persistence.get_connection')
    def test_analyze_strategy_performance_aggregated_empty_records(self, mock_get_connection):
        """Test analyze_strategy_performance_aggregated with empty database records."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []  # Empty results
        mock_get_connection.return_value = mock_conn
        
        result = analyze_strategy_performance_aggregated(Path('test.db'))
        
        assert result == []
    
    def test_walk_forward_report_calculation_edge_cases(self):
        """Test WalkForwardReport with edge case calculations."""
        # Test with very small numbers
        oos_results = [
            {
                'avg_return': 0.001,
                'sharpe': 0.001,
                'win_pct': 0.501,  # Barely profitable
                'total_trades': 1,
                'edge_score': 0.501
            },
            {
                'avg_return': -0.001,
                'sharpe': -0.001,
                'win_pct': 0.499,  # Barely unprofitable
                'total_trades': 1,
                'edge_score': 0.499
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
                'edge_score': 0.8
            }
        ]
        
        report = WalkForwardReport(oos_results)
        
        # Test the generate_report method
        report_text = report.generate_report('TEST_SYMBOL')
        
        assert 'TEST_SYMBOL' in report_text
        assert 'WALK-FORWARD ANALYSIS' in report_text  # Match actual output
        assert isinstance(report_text, str)
        assert len(report_text) > 0
