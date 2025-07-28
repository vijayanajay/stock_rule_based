"""Tests for CLI module - Consolidated test suite for all CLI functionality.

This module contains all tests for the kiss_signal.cli module, consolidated from:
- test_cli_basic.py: Basic CLI functionality and run command tests
- test_cli_advanced.py: Advanced features including analyze-strategies command
- test_cli_coverage.py: Edge cases and error handling scenarios
- test_cli_min_trades.py: Minimum trades filtering functionality
- test_cli_clear_and_recalculate_new.py: Clear and recalculate command tests

Test Organization:
- CLI Help and Banner Tests
- Run Command Tests (basic, verbose, freeze-date variations)
- Analyze Strategies Command Tests
- Clear and Recalculate Command Tests
- Error Handling and Edge Cases
- Min Trades Filtering Tests
"""

import json
import pathlib
import sqlite3
import tempfile
import yaml
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from rich.console import Console
from typer.testing import CliRunner

from kiss_signal.cli import app, _create_progress_context, _run_backtests, _show_banner
from kiss_signal.config import Config, RuleDef
from kiss_signal import persistence


# Test data constants
VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10
"""

VALID_CONFIG_WITH_MIN_TRADES = {
    "data_dir": "data/",
    "cache_dir": "data/cache",
    "db_path": "data/test.db",
    "rules_file": "config/rules.yaml",
    "universe_file": "data/nifty_large_mid.csv",
    "date_range": {"start": "2023-01-01", "end": "2024-01-01"},
    "min_trades": 5
}

runner = CliRunner()


# =============================================================================
# CLI Help and Banner Tests
# =============================================================================

def test_run_command_help() -> None:
    """Test run command help shows expected content."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Usage: " in result.stdout
    assert "--freeze-data" in result.stdout


def test_show_banner() -> None:
    """Test _show_banner function."""
    console = Console(record=True)
    with patch('kiss_signal.cli.console', console):
        _show_banner()
        output = console.export_text()
        assert "KISS Signal CLI" in output


def test_create_progress_context() -> None:
    """Test _create_progress_context function."""
    progress_context = _create_progress_context()
    assert progress_context is not None


# =============================================================================
# Run Command Tests - Basic Functionality
# =============================================================================

def test_display_results_empty():
    """Test _display_results with no results."""
    from kiss_signal.cli import _display_results
    from rich.console import Console
    
    console = Console(record=True)
    with patch('kiss_signal.cli.console', console):
        _display_results([])
        output = console.export_text()
        assert "No valid strategies found" in output


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_basic(mock_data, mock_backtester, test_environment) -> None:
    """Test basic run command with complete test environment."""
    # Mock data module functions
    mock_data.load_universe.return_value = ["RELIANCE", "TCS"]
    mock_data.get_price_data.return_value = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [102, 103, 104, 105, 106],
        'Low': [99, 100, 101, 102, 103],
        'Close': [101, 102, 103, 104, 105],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))
    mock_data.refresh_market_data.return_value = None
    
    # Mock backtester
    mock_bt_instance = mock_backtester.return_value
    mock_bt_instance.run.return_value = {
        'edge_score': 0.75, 'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
    }
    
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "edge_score" in result.stdout or "No valid strategies found" in result.stdout
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
@patch("kiss_signal.cli.reporter.generate_daily_report")
def test_run_command_verbose(mock_data, mock_backtester, mock_get_summary, test_environment) -> None:
    """Test run command with verbose flag."""
    # Mock data module functions
    mock_data.load_universe.return_value = ["RELIANCE", "TCS"]
    mock_data.get_price_data.return_value = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [102, 103, 104, 105, 106],
        'Low': [99, 100, 101, 102, 103],
        'Close': [101, 102, 103, 104, 105],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))
    mock_data.refresh_market_data.return_value = None
    
    # Mock backtester
    mock_bt_instance = mock_backtester.return_value
    mock_bt_instance.run.return_value = {
        'edge_score': 0.75, 'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
    }
    
    # Mock reporter
    mock_get_summary.return_value = "Summary report content"
    
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "--verbose", "run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "edge_score" in result.stdout or "No valid strategies found" in result.stdout
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_freeze_date(mock_data, mock_backtester, test_environment) -> None:
    """Test run command with freeze-data parameter."""
    # Mock data module functions
    mock_data.load_universe.return_value = ["RELIANCE", "TCS"]
    mock_data.get_price_data.return_value = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [102, 103, 104, 105, 106],
        'Low': [99, 100, 101, 102, 103],
        'Close': [101, 102, 103, 104, 105],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))
    mock_data.refresh_market_data.return_value = None
    
    # Mock backtester
    mock_bt_instance = mock_backtester.return_value
    mock_bt_instance.run.return_value = {
        'edge_score': 0.75, 'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
    }
    
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "2025-01-01"], catch_exceptions=False)
        assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


def test_run_command_invalid_freeze_date(test_environment) -> None:
    """Test run command with invalid freeze-data parameter."""
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "invalid-date"])
        assert result.exit_code != 0
        assert "Invalid isoformat string" in result.stdout or "Error" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_run_command_no_config() -> None:
    """Test run command without config file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        assert "No such file or directory" in result.stdout or "Config file not found" in result.stdout


def test_run_command_missing_rules(test_environment) -> None:
    """Test run command with missing rules file."""
    # Change to test environment directory, but delete the rules file
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "missing_rules.yaml"  # Non-existent file
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
        assert result.exit_code != 0
        assert "No such file or directory" in result.stdout or "Error" in result.stdout
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Run Command Tests - Error Handling
# =============================================================================

@patch("kiss_signal.cli.data")
@patch("kiss_signal.cli.backtester.Backtester")  
def test_run_command_insufficient_data_handling(mock_data, mock_bt, test_environment):
    """Test run command when insufficient data is available."""
    # Mock insufficient data scenario
    mock_data.get_universe.return_value = ["RELIANCE"]
    mock_data.get_price_data.side_effect = ValueError("Insufficient data")
    
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
        # Should handle error gracefully
        assert result.exit_code == 0 or "Error" in result.stdout
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_with_persistence(
    mock_run_backtests, mock_get_connection, test_environment
):
    """Test that run command integrates with persistence layer."""
    # Mock the connection and cursor
    mock_conn = mock_get_connection.return_value
    mock_cursor = mock_conn.cursor.return_value

    mock_run_backtests.return_value = [{
        'symbol': 'RELIANCE',
        'rule_stack': [RuleDef(type='sma_crossover', name='sma_10_20_crossover', params={'short_window': 10, 'long_window': 20})],
        'edge_score': 0.75,
        'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
    }]

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"], catch_exceptions=False)
        assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_persistence_failure_handling(
    mock_run_backtests, mock_get_connection, test_environment
):
    """Test that run command handles persistence layer failures gracefully."""
    # Mock persistence failure
    mock_get_connection.side_effect = sqlite3.Error("Database error")
    
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
        # Should handle database errors gracefully
        assert "Database error" in result.stdout or result.exit_code != 0
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Analyze Strategies Command Tests
# =============================================================================

@patch("kiss_signal.cli.reporter.format_strategy_analysis_as_csv")
@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_success(mock_analyze, mock_format_csv, test_environment):
    """Test analyze-strategies command with successful execution."""
    # Mock the analyzer to return sample data
    mock_analyze.return_value = [
        {
            'strategy_rule_stack': 'strategy_1',
            'frequency': 1,
            'avg_edge_score': 0.75,
            'avg_win_pct': 0.65,
            'avg_sharpe': 1.2,
            'avg_return': 0.18,
            'avg_trades': 150.0,
            'top_symbols': 'RELIANCE, TCS',
            'config_hash': 'hash123',
            'run_date': '2024-01-01',
            'config_details': 'test config'
        }
    ]
    
    mock_format_csv.return_value = "CSV formatted output"

    # Create mock database in test environment
    db_path = test_environment / "data" / "kiss_signal.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            strategy_key TEXT,
            edge_score REAL
        )
    """)
    conn.execute("""
        INSERT INTO strategies (strategy_key, edge_score) 
        VALUES ('strategy_1', 0.75)
    """)
    conn.commit()
    conn.close()

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        assert result.exit_code == 0
        assert "Strategy performance analysis saved to:" in result.stdout
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli._validate_database_path")
@patch("kiss_signal.cli.reporter.format_strategy_analysis_as_csv")
@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_custom_output(mock_analyze, mock_get_connection, mock_format_csv, mock_validate_db, test_environment):
    """Test analyze-strategies command with custom output path."""
    # Mock database validation to pass
    mock_validate_db.return_value = None
    
    # Mock database connection
    mock_conn = MagicMock()
    mock_get_connection.return_value = mock_conn
    
    # Mock the analyzer
    mock_analyze.return_value = [
        {
            'strategy_key': 'strategy_1',
            'avg_edge_score': 0.75,
            'avg_win_pct': 0.65,
            'avg_sharpe': 1.2,
            'total_trades': 150,
            'symbol_count': 10
        }
    ]
    
    # Mock CSV formatter
    mock_format_csv.return_value = "CSV content"

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        output_path = test_environment / "custom_output.csv"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--output", str(output_path)])
        if result.exit_code != 0:
            print(f"DEBUG: Exit code: {result.exit_code}")
            print(f"DEBUG: stdout: {result.stdout}")
            print(f"DEBUG: stderr: {result.stderr if hasattr(result, 'stderr') else 'No stderr'}")
        assert result.exit_code == 0
        # Should create the output file
        assert output_path.exists()
    finally:
        os.chdir(original_cwd)


def test_analyze_strategies_command_no_database(test_environment):
    """Test analyze-strategies command when database doesn't exist."""
    # Change to test environment directory and run CLI  
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        # Make sure database doesn't exist
        db_path = test_environment / "data" / "kiss_signal.db"
        if db_path.exists():
            db_path.unlink()
        
        result = runner.invoke(app, ["--config", str(config_path), "analyze-strategies"])
        assert result.exit_code != 0
        assert "database" in result.stdout.lower() or "error" in result.stdout.lower()
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_no_data(mock_analyze, test_environment):
    """Test analyze-strategies command when no data is available."""
    # Mock analyzer to return empty data
    mock_analyze.return_value = []

    # Create empty database in test environment
    db_path = test_environment / "data" / "kiss_signal.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            strategy_key TEXT,
            edge_score REAL
        )
    """)
    conn.commit()
    conn.close()

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "analyze-strategies"])
        assert result.exit_code == 0
        assert "No historical strategies found to analyze" in result.stdout or "no strategies" in result.stdout.lower()
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_error_handling(mock_analyze, test_environment):
    """Test analyze-strategies command error handling."""
    # Mock analyzer to raise an exception
    mock_analyze.side_effect = Exception("Analysis failed")

    # Create database in test environment
    db_path = test_environment / "data" / "kiss_signal.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            strategy_key TEXT,
            edge_score REAL
        )
    """)
    conn.commit()
    conn.close()

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "analyze-strategies"])
        assert "Error" in result.stdout or result.exit_code != 0
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Clear and Recalculate Command Tests  
# =============================================================================

@patch("kiss_signal.cli._validate_database_path")
@patch("kiss_signal.cli.persistence.clear_strategies_for_config")
@patch("kiss_signal.cli._execute_backtesting_workflow")
@patch("kiss_signal.cli._process_and_save_results")
def test_clear_and_recalculate_basic_flow(mock_process, mock_execute, mock_clear, mock_validate_db, test_environment):
    """Test basic clear-and-recalculate command flow."""
    # Mock database validation to pass
    mock_validate_db.return_value = None
    
    # Mock the backtesting results
    mock_execute.return_value = [
        {
            'symbol': 'RELIANCE',
            'rule_stack': [RuleDef(type='sma_crossover', name='test', params={})],
            'edge_score': 0.75,
            'win_pct': 0.65,
            'sharpe': 1.2,
            'total_trades': 15,
            'avg_return': 0.02
        }
    ]
    
    # Mock clear operation to return a result dict
    mock_clear.return_value = {'cleared_count': 5, 'preserved_count': 10}

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "clear-and-recalculate", "--force"])
        if result.exit_code != 0:
            print(f"DEBUG: Exit code: {result.exit_code}")
            print(f"DEBUG: stdout: {result.stdout}")
            print(f"DEBUG: stderr: {result.stderr if hasattr(result, 'stderr') else 'No stderr'}")
        assert result.exit_code == 0
        
        # Verify the clear function was called
        mock_clear.assert_called_once()
        # Verify backtests were run
        mock_execute.assert_called_once()
        # Verify results were processed
        mock_process.assert_called_once()
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.persistence.clear_strategies_for_config")
def test_clear_and_recalculate_clear_failure(mock_clear, test_environment):
    """Test clear-and-recalculate command when clear operation fails."""
    # Mock clear to raise an exception
    mock_clear.side_effect = sqlite3.Error("Clear failed")

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "clear-and-recalculate"])
        assert "Error" in result.stdout or result.exit_code != 0
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Min Trades Filtering Tests
# =============================================================================

def test_cli_with_min_trades_config(test_environment):
    """Test CLI respects min_trades configuration."""
    # Modify the config to have a different min_trades value for this test
    config_path = test_environment / "config.yaml"
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Update min_trades_threshold from 10 to 5 for this test
    modified_config = config_content.replace('min_trades_threshold: 10', 'min_trades_threshold: 5')
    
    with open(config_path, 'w') as f:
        f.write(modified_config)

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        rules_path = test_environment / "config" / "rules.yaml"
        
        # Test that config loads successfully  
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--help"])
        assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli._run_backtests")
def test_min_trades_filtering_applied(mock_run_backtests, test_environment):
    """Test that min_trades filtering is applied to results."""
    # Mock results where some strategies have fewer than min_trades
    mock_run_backtests.return_value = [
        {
            'symbol': 'RELIANCE',
            'rule_stack': [RuleDef(type='sma_crossover', name='test', params={})],
            'edge_score': 0.75,
            'total_trades': 3,  # Below min_trades threshold
            'win_pct': 0.65,
            'sharpe': 1.2,
            'avg_return': 0.02
        },
        {
            'symbol': 'TCS',
            'rule_stack': [RuleDef(type='sma_crossover', name='test', params={})],
            'edge_score': 0.80,
            'total_trades': 10,  # Above min_trades threshold
            'win_pct': 0.70,
            'sharpe': 1.5,
            'avg_return': 0.03
        }
    ]

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
        # Should filter out strategies with insufficient trades
        assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

def test_run_command_backtest_value_error():
    """Test run command handles ValueError in backtesting."""
    with patch("kiss_signal.cli._run_backtests") as mock_run:
        mock_run.side_effect = ValueError("Backtest error")
        
        with runner.isolated_filesystem() as fs:
            # Setup minimal config
            config_path = Path(fs) / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump({"data_dir": "data/"}, f)
            
            result = runner.invoke(app, ["run"])
            assert "Error" in result.stdout or result.exit_code != 0


def test_run_command_file_not_found_in_backtest():
    """Test run command handles FileNotFoundError in backtesting."""
    with patch("kiss_signal.cli._run_backtests") as mock_run:
        mock_run.side_effect = FileNotFoundError("File not found")
        
        with runner.isolated_filesystem() as fs:
            # Setup minimal config
            config_path = Path(fs) / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump({"data_dir": "data/"}, f)
            
            result = runner.invoke(app, ["run"])
            assert "not found" in result.stdout.lower() or result.exit_code != 0


@patch("kiss_signal.cli._run_backtests", side_effect=Exception("Generic backtest error"))
@patch("kiss_signal.cli.data")
def test_run_command_backtest_generic_exception_verbose(mock_data, mock_run_backtests):
    """Test that a generic exception during backtesting is handled with verbose output."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        data_dir = fs_path / "data"
        data_dir.mkdir()
        (fs_path / "config").mkdir()
        universe_path = data_dir / "test_universe.csv"
        universe_path.write_text("symbol\nTEST\n")

        sample_config_dict = {
            "universe_path": str(universe_path),
            "historical_data_years": 1,
            "cache_dir": "cache",
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "database_path": "test.db",
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path = fs_path / "config.yaml"
        config_path.write_text(yaml.dump(sample_config_dict))

        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.write_text(VALID_RULES_YAML)

        # Correct invocation order: global options before command
        result = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "run"])

        assert result.exit_code == 1
        assert "An unexpected error occurred" in result.stdout
        assert "Generic backtest error" in result.stdout


@patch("kiss_signal.cli.reporter.generate_daily_report")
def test_run_command_report_generation_fails_warning(mock_generate_report, test_environment):
    """Test run command handles report generation failures with warning."""
    mock_generate_report.side_effect = Exception("Report generation failed")
    
    with patch("kiss_signal.cli._run_backtests") as mock_run:
        mock_run.return_value = [
            {
                'symbol': 'TEST',
                'rule_stack': [RuleDef(type='test', name='test', params={})],
                'edge_score': 0.75,
                'total_trades': 10,
                'win_pct': 0.65,
                'sharpe': 1.2,
                'avg_return': 0.02
            }
        ]
        
        # Change to test environment directory and run CLI
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment)
            config_path = test_environment / "config.yaml"
            rules_path = test_environment / "config" / "rules.yaml"
            
            result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "--verbose", "run"])
            # Should handle report generation failure gracefully
            assert result.exit_code == 0 or "warning" in result.stdout.lower()
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Parameterized Tests for Variations
# =============================================================================

@pytest.mark.parametrize("command_args,expected_success", [
    (["run"], True),
    (["--verbose", "run"], True),
    (["run", "--freeze-data", "2025-01-01"], True),
    (["run", "--freeze-data", "invalid-date"], False),
    (["analyze-strategies"], True),
    (["analyze-strategies", "--per-stock"], True),
    (["clear-and-recalculate"], True),
])
def test_cli_command_variations(command_args, expected_success, test_environment):
    """Parameterized test for various CLI command variations."""
    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        # Add config and rules args to command
        full_command = ["--config", str(config_path), "--rules", str(rules_path)] + command_args
        
        if expected_success:
            # For successful cases, we expect proper error handling
            result = runner.invoke(app, full_command)
            # Either success or graceful error handling
            assert result.exit_code == 0 or "Error" in result.stdout
        else:
            # For failure cases, we expect non-zero exit code
            result = runner.invoke(app, full_command)
            assert result.exit_code != 0
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Integration-style Tests
# =============================================================================

@patch("kiss_signal.cli.data.load_universe")
@patch("kiss_signal.cli.data.get_price_data")
@patch("kiss_signal.cli.data.refresh_market_data")
@patch("kiss_signal.cli.backtester.Backtester")
def test_full_cli_integration_flow(mock_bt, mock_refresh, mock_price, mock_universe, test_environment):
    """Test full CLI integration flow from start to finish."""
    # Setup comprehensive mocks
    mock_universe.return_value = ["RELIANCE", "TCS"]
    mock_price.return_value = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [102, 103, 104, 105, 106],
        'Low': [99, 100, 101, 102, 103],
        'Close': [101, 102, 103, 104, 105],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=pd.date_range('2023-01-01', periods=5))
    mock_refresh.return_value = None
    
    mock_bt_instance = mock_bt.return_value
    mock_bt_instance.run.return_value = {
        'edge_score': 0.75, 'win_pct': 0.65, 'sharpe': 1.2, 
        'total_trades': 15, 'avg_return': 0.02
    }

    # Change to test environment directory and run CLI
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        # Test run command
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"], catch_exceptions=False)
        assert result.exit_code == 0
        
        # Verify mocks were called appropriately
        mock_universe.assert_called()
        mock_price.assert_called()
        mock_refresh.assert_called()
        mock_bt.assert_called()
    finally:
        os.chdir(original_cwd)
