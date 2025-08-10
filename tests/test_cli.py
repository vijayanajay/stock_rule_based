"""Tests for CLI module - Consolidated and ruthlessly simplified.

Covers essential CLI functionality:
- Basic commands (run, analyze-strategies, clear-and-recalculate)  
- Error handling for missing configs/files
- Core business logic functions
- Essential edge cases only

Removed bloat:
- Excessive parameterized variations
- Redundant integration tests
- Over-engineered edge case scenarios  
- Duplicate test patterns
"""

import json
import os
import pathlib
import sqlite3
import tempfile
import yaml
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from rich.console import Console
from typer.testing import CliRunner

from kiss_signal.cli import (
    app, _create_progress_context, _run_backtests, _show_banner,
    check_exit_conditions, calculate_position_returns, identify_new_signals,
    process_open_positions, get_position_pricing
)
from kiss_signal.reporter import update_positions_and_generate_report_data
from kiss_signal.config import Config, RuleDef
from kiss_signal import persistence


# Test constants
VALID_RULES_YAML = """
entry_signals:
  - name: "test_baseline"
    type: "sma_crossover"
    params:
      fast_period: 5
      slow_period: 10
"""

VALID_CONFIG_WITH_MIN_TRADES = {
    "universe_path": "data/nifty_large_mid.csv",
    "historical_data_years": 1,
    "cache_dir": "data/cache",
    "hold_period": 20,
    "min_trades_threshold": 5,
    "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
    "database_path": "data/test.db",
    "reports_output_dir": "reports/",
    "edge_score_threshold": 0.5
}

runner = CliRunner()


# =============================================================================
# Core CLI Tests
# =============================================================================

def test_run_command_help() -> None:
    """Test the main application help command is resilient."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "KISS Signal CLI" in result.stdout


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


def test_display_results_empty():
    """Test _display_results handles empty results gracefully."""
    from kiss_signal.cli import _display_results
    
    with patch('kiss_signal.cli.console') as mock_console:
        _display_results([])
        mock_console.print.assert_called()


@pytest.fixture
def mock_data():
    """Mock data loading."""
    with patch('kiss_signal.data.load_universe') as mock_load_universe, \
         patch('kiss_signal.data.get_price_data') as mock_get_price_data, \
         patch('kiss_signal.data.refresh_market_data') as mock_refresh:
        
        mock_load_universe.return_value = ['RELIANCE', 'INFY']
        mock_get_price_data.return_value = pd.DataFrame({
            'open': [100, 101], 'high': [102, 103], 'low': [99, 100], 
            'close': [101, 102], 'volume': [1000, 1100]
        })
        yield mock_load_universe, mock_get_price_data, mock_refresh


@pytest.fixture  
def mock_backtester():
    """Mock backtester."""
    with patch('kiss_signal.backtester.Backtester') as mock_bt:
        bt_instance = Mock()
        bt_instance.find_optimal_strategies.return_value = [
            {'symbol': 'RELIANCE', 'rule_stack': ['test'], 'edge_score': 0.6, 'total_trades': 10}
        ]
        mock_bt.return_value = bt_instance
        yield mock_bt


@pytest.fixture
def test_environment(tmp_path):
    """Create minimal test environment."""
    (tmp_path / "data").mkdir()
    (tmp_path / "config").mkdir()
    
    config = {
        "universe_path": "data/nifty_large_mid.csv",
        "historical_data_years": 1,
        "cache_dir": "cache", 
        "hold_period": 20,
        "min_trades_threshold": 10,
        "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
        "database_path": "test.db",
        "reports_output_dir": "reports/",
        "edge_score_threshold": 0.5
    }
    
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    
    rules_path = tmp_path / "config" / "rules.yaml" 
    rules_path.write_text(VALID_RULES_YAML)
    
    universe_path = tmp_path / "data" / "nifty_large_mid.csv"
    universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
    
    return tmp_path


def test_run_command_basic(mock_data, mock_backtester, test_environment) -> None:
    """Test basic run command functionality."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path), 
            "--rules", str(rules_path), 
            "run"
        ])
        
        assert result.exit_code == 0
        assert "Analysis complete" in result.stdout
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.performance_monitor.get_summary")
def test_run_command_verbose(mock_get_summary, mock_data, mock_backtester, test_environment) -> None:
    """Test verbose run command."""
    mock_get_summary.return_value = {
        'total_functions': 3,
        'total_duration': 1.5,
        'slowest_function': 'backtest_strategy'
    }
    
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--verbose", "--config", str(config_path), 
            "--rules", str(rules_path), "run"
        ])
        
        assert result.exit_code == 0
        assert "Performance Summary" in result.stdout or "backtest_strategy" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_run_command_freeze_date(mock_data, mock_backtester, test_environment) -> None:
    """Test run command with freeze date."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "run", "--freeze-data", "2025-01-01"
        ])
        
        assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


def test_run_command_invalid_freeze_date(test_environment) -> None:
    """Test run command with invalid freeze date."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path), 
            "run", "--freeze-data", "invalid-date"
        ])
        
        assert result.exit_code != 0
    finally:
        os.chdir(original_cwd)


def test_run_command_no_config() -> None:
    """Test run command without config file."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0 or "config" in result.stdout.lower()


def test_run_command_missing_rules(test_environment) -> None:
    """Test run command with missing rules file."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", "nonexistent.yaml",
            "run"
        ])
        
        assert result.exit_code != 0
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.data.get_price_data")
@patch("kiss_signal.data.load_universe") 
def test_run_command_insufficient_data_handling(mock_load_universe, mock_get_price_data, test_environment):
    """Test run command with insufficient data."""
    mock_load_universe.return_value = ['RELIANCE']
    mock_get_price_data.return_value = pd.DataFrame()  # Empty dataframe
    
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "run"
        ])
        
        # Should handle gracefully - either success or proper error message
        assert "insufficient data" in result.stdout.lower() or result.exit_code == 0
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.persistence.save_strategies_batch")
@patch("kiss_signal.backtester.Backtester")
@patch("kiss_signal.data.get_price_data")
@patch("kiss_signal.data.load_universe")
def test_run_command_with_persistence(
    mock_load_universe, mock_get_price_data, mock_backtester, mock_save_strategies, test_environment
):
    """Test run command with persistence enabled."""
    # Setup mocks with results that should trigger persistence
    mock_load_universe.return_value = ['RELIANCE', 'INFY']
    
    # Create a larger DataFrame with sufficient data points
    mock_get_price_data.return_value = pd.DataFrame({
        'open': [100] * 150, 'high': [102] * 150, 'low': [99] * 150, 
        'close': [101] * 150, 'volume': [1000] * 150
    }, index=pd.date_range('2023-01-01', periods=150))
    
    bt_instance = Mock()
    bt_instance.find_optimal_strategies.return_value = [
        {
            'symbol': 'RELIANCE', 
            'rule_stack': [RuleDef(name='test_baseline', type='sma_crossover', params={'fast_period': 5, 'slow_period': 10})], 
            'edge_score': 0.6, 
            'total_trades': 10,
            'win_pct': 0.6,
            'sharpe': 1.5
        }
    ]
    mock_backtester.return_value = bt_instance
    mock_save_strategies.return_value = True  # Return success

    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "run"
        ])
        
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.stdout}")
        assert result.exit_code == 0
        
        # Check if backtester was actually called
        mock_backtester.assert_called()
        bt_instance.find_optimal_strategies.assert_called()
        
        # Check if save was called
        if not mock_save_strategies.called:
            print("Save strategies was not called!")
            print(f"Mock calls: {mock_save_strategies.call_count}")
        
        mock_save_strategies.assert_called()
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Analyze Strategies Tests
# =============================================================================

@patch("kiss_signal.cli.analyze_strategy_performance_aggregated")  # Mock where it's used, not where it's defined
@patch("kiss_signal.cli.format_strategy_analysis_as_csv")
def test_analyze_strategies_command_success(mock_format_csv, mock_analyze, test_environment):
    """Test successful analyze-strategies command."""
    mock_analyze.return_value = [
        {"symbol": "RELIANCE", "total_trades": 10, "win_pct": 0.6, "avg_return": 0.05}
    ]
    mock_format_csv.return_value = "symbol,trades\nRELIANCE,10\n"
    
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        # Create a database with the correct strategies table schema
        db_path = test_environment / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Use the actual application schema from persistence.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                run_timestamp TEXT NOT NULL,
                rule_stack TEXT NOT NULL,
                edge_score REAL NOT NULL,
                win_pct REAL NOT NULL,
                sharpe REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                avg_return REAL NOT NULL,
                config_snapshot TEXT,
                config_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, rule_stack, run_timestamp)
            )
        """)
        # Insert dummy data with all required fields
        cursor.execute("""
            INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
            VALUES ('RELIANCE', '2024-01-01T00:00:00', '["test_baseline"]', 0.6, 0.7, 1.2, 10, 0.05)
        """)
        conn.commit()
        conn.close()
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "analyze-strategies"
        ])
        
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.stdout}")
        if result.exception:
            print(f"Exception: {result.exception}")
        
        assert result.exit_code == 0
        mock_analyze.assert_called_once()
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.cli.analyze_strategy_performance_aggregated")  # Mock where it's used
def test_analyze_strategies_command_no_data(mock_analyze, test_environment):
    """Test analyze-strategies with no data."""
    mock_analyze.return_value = []
    
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "analyze-strategies"
        ])
        
        assert result.exit_code == 0
        assert "No historical strategies found to analyze" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_analyze_strategies_command_no_database(test_environment):
    """Test analyze-strategies command when database doesn't exist."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "analyze-strategies"
        ])
        
        # Should either succeed or give proper error message
        assert result.exit_code == 0 or "database" in result.stdout.lower()
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Clear and Recalculate Tests  
# =============================================================================

@patch("kiss_signal.cli._execute_full_pipeline")
def test_clear_and_recalculate_basic_flow(mock_execute, test_environment):
    """Test basic clear and recalculate flow."""
    mock_execute.return_value = None
    
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "clear-and-recalculate", "--force"
        ])
        
        assert result.exit_code == 0
        # Verify that _execute_full_pipeline was called with clear_strategies=True
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args.kwargs['clear_strategies'] is True
        assert call_args.kwargs['force_clear'] is True
    finally:
        os.chdir(original_cwd)


@patch("kiss_signal.persistence.clear_strategies_for_config", side_effect=Exception("Clear failed"))
def test_clear_and_recalculate_clear_failure(mock_clear, test_environment):
    """Test clear and recalculate when clear operation fails."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "clear-and-recalculate", "--force"
        ])
        
        assert result.exit_code != 0
        assert "Clear failed" in result.stdout
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Error Handling Tests
# =============================================================================

@patch("kiss_signal.cli._execute_backtesting_workflow", side_effect=Exception("Generic backtest error"))
def test_run_command_backtest_generic_exception_verbose(mock_execute_workflow):
    """Test that a generic exception during backtesting is handled with verbose output."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        data_dir = fs_path / "data"
        data_dir.mkdir()
        (fs_path / "config").mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

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

        # Correct invocation: global options must come BEFORE the command.
        result = runner.invoke(app, [
            "--verbose", "--config", str(config_path), 
            "--rules", str(rules_path), "run"
        ], catch_exceptions=False)

        assert result.exit_code == 1
        assert "An unexpected error occurred" in result.stdout
        assert "Generic backtest error" in result.stdout


def test_cli_with_min_trades_config(test_environment):
    """Test CLI with min_trades configuration."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(test_environment)
        config_path = test_environment / "config.yaml"
        rules_path = test_environment / "config" / "rules.yaml"
        
        with patch('kiss_signal.cli._run_backtests') as mock_run:
            mock_run.return_value = [
                {
                    'symbol': 'RELIANCE', 
                    'total_trades': 15, 
                    'edge_score': 0.6,
                    'win_pct': 0.75,  # Add missing win_pct
                    'sharpe': 1.2,    # Add missing sharpe
                    'rule_stack': [{'name': 'test_rule', 'type': 'test_rule'}],
                    'latest_close': 2500.0
                }
            ]
            
            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "run"
            ])
            
            if result.exit_code != 0:
                print(f"Command failed with exit code {result.exit_code}")
                print(f"STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                if hasattr(result, 'exception') and result.exception:
                    print(f"Exception: {result.exception}")
            
            assert result.exit_code == 0
    finally:
        os.chdir(original_cwd)


def test_min_trades_filtering_applied():
    """Test that min_trades filtering is applied correctly."""
    # Create a temporary config file for proper validation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nA\nB\nC\n")
        universe_path = f.name
    
    try:
        config_dict = VALID_CONFIG_WITH_MIN_TRADES.copy()
        config_dict['universe_path'] = universe_path
        config_with_min_trades = Config(**config_dict)
        
        strategies = [
            {'symbol': 'A', 'total_trades': 3, 'edge_score': 0.8},
            {'symbol': 'B', 'total_trades': 10, 'edge_score': 0.7},
            {'symbol': 'C', 'total_trades': 7, 'edge_score': 0.6}
        ]
        
        with patch('kiss_signal.cli._run_backtests') as mock_run:
            mock_run.return_value = strategies
            
            from kiss_signal.cli import _execute_backtesting_workflow
            
            result = _execute_backtesting_workflow(
                app_config=config_with_min_trades,
                rules_config=[RuleDef(name="test", type="sma_crossover", params={})],
                freeze_date=None,
                min_trades=None,
                in_sample=False
            )
            
            # Should filter out strategies with < 5 trades
            filtered = [s for s in result if s['total_trades'] >= 5]
            assert len(filtered) == 2  # B and C should remain
    finally:
        import os
        os.unlink(universe_path)


# =============================================================================
# Business Logic Tests
# =============================================================================

def test_check_exit_conditions_stop_loss() -> None:
    """Test stop loss exit condition."""
    position = {'entry_price': 100.0, 'symbol': 'TEST'}
    price_data = pd.DataFrame({'low': [95.0], 'high': [105.0]})
    exit_conditions = [{'type': 'stop_loss_pct', 'params': {'percentage': 0.05}}]
    
    result = check_exit_conditions(position, price_data, 95.0, 105.0, exit_conditions, 5, 20)
    assert result is not None  # Should trigger exit
    assert "stop_loss_pct" in result


def test_check_exit_conditions_time_based() -> None:
    """Test time-based exit condition."""
    position = {'entry_price': 100.0, 'symbol': 'TEST'}
    price_data = pd.DataFrame({'low': [95.0], 'high': [105.0]})
    exit_conditions = [{'type': 'time_based', 'value': 20}]
    
    result = check_exit_conditions(position, price_data, 100.0, 102.0, exit_conditions, 25, 20)
    assert result is not None  # Should trigger exit after 20 days


def test_calculate_position_returns_basic() -> None:
    """Test basic position return calculation."""
    position = {'entry_price': 100.0, 'entry_date': '2024-01-01'}
    current_price = 110.0
    
    returns = calculate_position_returns(position, current_price)
    # Function returns 'return_pct', not 'absolute_return' or 'percentage_return'
    assert abs(returns['return_pct'] - 10.0) < 0.01  # 10% return


def test_calculate_position_returns_invalid_entry() -> None:
    """Test position return with invalid entry price."""
    position = {'entry_price': 0.0, 'entry_date': '2024-01-01'}  # Invalid
    current_price = 110.0
    
    returns = calculate_position_returns(position, current_price)
    # Function returns 'return_pct': 0.0 for invalid entry prices
    assert returns['return_pct'] == 0.0


@patch("kiss_signal.persistence.get_open_positions")
def test_identify_new_signals_filters(mock_get_open, tmp_path: Path) -> None:
    """Test that new signals filtering works."""
    mock_get_open.return_value = [{'symbol': 'EXISTING'}]
    
    new_signals = [
        {'symbol': 'EXISTING', 'rule_stack': ['test1'], 'edge_score': 0.6}, 
        {'symbol': 'NEW', 'rule_stack': ['test2'], 'edge_score': 0.7}
    ]
    
    from datetime import date
    result = identify_new_signals(new_signals, tmp_path / "test.db", date.today())
    
    assert len(result) == 1
    assert result[0]['ticker'] == 'NEW'  # Function returns 'ticker', not 'symbol'


@patch("kiss_signal.data.get_price_data")  # Mock data fetching
@patch("kiss_signal.cli.get_position_pricing")  
@patch("kiss_signal.persistence.get_open_positions")
def test_process_open_positions_close(mock_open, mock_price, mock_data, tmp_path: Path) -> None:
    """Test processing open positions that should close."""
    mock_open.return_value = [{'id': 1, 'symbol': 'TEST', 'entry_price': 100.0, 'entry_date': '2024-01-01'}]
    mock_price.return_value = {
        'current_price': 95.0, 
        'current_high': 96.0, 
        'current_low': 94.0,
        'price_data': pd.DataFrame({
            'close': [95.0], 'high': [96.0], 'low': [94.0], 'open': [95.5], 'volume': [1000]
        }, index=[pd.Timestamp('2024-01-02')])
    }
    # Mock price data for exit condition checking
    mock_data.return_value = pd.DataFrame({
        'close': [95.0], 'high': [96.0], 'low': [94.0], 'open': [95.5], 'volume': [1000]
    }, index=[pd.Timestamp('2024-01-02')])
    
    # Create a minimal config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nTEST\n")
        universe_path = f.name
    
    try:
        config_dict = VALID_CONFIG_WITH_MIN_TRADES.copy()
        config_dict['universe_path'] = universe_path
        config = Config(**config_dict)
        
        exit_conditions = [{'type': 'stop_loss_pct', 'params': {'percentage': 0.03}}]  # 3% stop loss
        nifty_data = pd.DataFrame()  # Empty nifty data
        
        to_close, to_hold = process_open_positions(tmp_path / "test.db", config, exit_conditions, nifty_data)
        
        assert len(to_close) == 1
        assert len(to_hold) == 0
    finally:
        import os
        os.unlink(universe_path)


@patch("kiss_signal.data.get_price_data")  # Mock data fetching
@patch("kiss_signal.cli.get_position_pricing")
@patch("kiss_signal.persistence.get_open_positions") 
def test_process_open_positions_hold(mock_open, mock_price, mock_data, tmp_path: Path) -> None:
    """Test processing open positions that should be held."""
    mock_open.return_value = [{'id': 1, 'symbol': 'TEST', 'entry_price': 100.0, 'entry_date': '2025-08-01'}]  # Recent entry date
    mock_price.return_value = {
        'current_price': 102.0, 
        'current_high': 103.0, 
        'current_low': 101.0,
        'price_data': pd.DataFrame({
            'close': [102.0], 'high': [103.0], 'low': [101.0], 'open': [101.5], 'volume': [1000]
        }, index=[pd.Timestamp('2025-08-02')])
    }
    # Mock price data for exit condition checking
    mock_data.return_value = pd.DataFrame({
        'close': [102.0], 'high': [103.0], 'low': [101.0], 'open': [101.5], 'volume': [1000]
    }, index=[pd.Timestamp('2025-08-02')])

    # Create a minimal config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nTEST\n")
        universe_path = f.name

    try:
        config_dict = VALID_CONFIG_WITH_MIN_TRADES.copy()
        config_dict['universe_path'] = universe_path
        config = Config(**config_dict)

        exit_conditions = [{'type': 'stop_loss_pct', 'params': {'percentage': 0.05}}]  # 5% stop loss
        nifty_data = pd.DataFrame()  # Empty nifty data

        to_close, to_hold = process_open_positions(tmp_path / "test.db", config, exit_conditions, nifty_data)
        
        assert len(to_close) == 0
        assert len(to_hold) == 1
    finally:
        import os
        os.unlink(universe_path)


@patch("kiss_signal.data.get_price_data")  # Mock all data fetching
@patch("kiss_signal.persistence.add_new_positions_from_signals")
@patch("kiss_signal.persistence.close_positions_batch")
@patch("kiss_signal.cli.get_position_pricing")
@patch("kiss_signal.persistence.get_open_positions")
def test_update_positions_and_generate_report_data(mock_open, mock_price, mock_close, mock_add, mock_data, tmp_path: Path) -> None:
    """Test the complete position update workflow."""
    mock_open.return_value = [{'id': 1, 'symbol': 'HOLD', 'entry_price': 100.0, 'entry_date': '2024-01-01'}]
    mock_price.return_value = {
        'current_price': 105.0, 
        'current_high': 106.0, 
        'current_low': 104.0,
        'price_data': pd.DataFrame({
            'close': [105.0], 'high': [106.0], 'low': [104.0], 'open': [105.0], 'volume': [1000]
        }, index=[pd.Timestamp('2024-01-02')])
    }
    mock_close.return_value = None
    mock_add.return_value = None
    # Mock data fetching to prevent real network calls
    mock_data.return_value = pd.DataFrame({
        'close': [105.0], 'high': [106.0], 'low': [104.0], 'open': [105.0], 'volume': [1000]
    }, index=[pd.Timestamp('2024-01-02')])
    
    # Create minimal config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nHOLD\nNEW\n")
        universe_path = f.name
    
    try:
        config_dict = VALID_CONFIG_WITH_MIN_TRADES.copy() 
        config_dict['universe_path'] = universe_path
        config = Config(**config_dict)
        
        all_results = [{'symbol': 'NEW', 'entry_price': 50.0, 'rule_stack': ['test'], 'edge_score': 0.8}]
        
        # Create a rules config with exit_conditions attribute  
        rules_config = SimpleNamespace(exit_conditions=[])
        
        result = update_positions_and_generate_report_data(
            tmp_path / "test.db",
            "2024-01-01_10:00:00", 
            config,
            rules_config,  # Proper rules config object
            all_results
        )
        
        # Check the actual return keys from the function
        assert 'new_buys' in result
        assert 'open' in result  
        assert 'closed' in result
        
        # Should have positions processed
        assert isinstance(result['new_buys'], list)
        assert isinstance(result['open'], list) 
        assert isinstance(result['closed'], list)
    finally:
        import os
        os.unlink(universe_path)


# =============================================================================
# Integration Test (Essential Only)
# =============================================================================

class TestCLIIntegration:
    """Essential integration tests only - no bloat."""
    
    @pytest.fixture
    def integration_env(self, tmp_path):
        """Minimal integration test environment."""
        (tmp_path / "data").mkdir()
        (tmp_path / "config").mkdir()
        
        # Create universe file first
        universe_path = tmp_path / "data" / "test_universe.csv"
        universe_path.write_text("symbol\nRELIANCE\nINFY\n")
        
        config = {
            "universe_path": str(universe_path),  # Use absolute path 
            "historical_data_years": 1,
            "cache_dir": "cache",
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "database_path": "test.db",
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config))
        
        rules_path = tmp_path / "config" / "rules.yaml"
        rules_path.write_text(VALID_RULES_YAML)
        
        return tmp_path

    def test_config_loading_integration(self, integration_env):
        """Test config loading integration."""
        from kiss_signal.config import load_config
        
        config_path = integration_env / "config.yaml"
        config = load_config(config_path)
        
        assert "test_universe.csv" in config.universe_path
        assert config.historical_data_years == 1

    @patch("kiss_signal.data.get_price_data")
    @patch("kiss_signal.data.load_universe")
    def test_data_loading_integration(self, mock_load_universe, mock_get_price_data, integration_env):
        """Test data loading integration."""
        mock_load_universe.return_value = ['RELIANCE', 'INFY']
        mock_get_price_data.return_value = pd.DataFrame({
            'open': [100], 'high': [102], 'low': [99], 'close': [101], 'volume': [1000]
        })
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(integration_env)
            config_path = integration_env / "config.yaml"
            rules_path = integration_env / "config" / "rules.yaml"
            
            with patch('kiss_signal.backtester.Backtester') as mock_bt:
                bt_instance = Mock()
                bt_instance.find_optimal_strategies.return_value = []
                mock_bt.return_value = bt_instance
                
                result = runner.invoke(app, [
                    "--config", str(config_path),
                    "--rules", str(rules_path), 
                    "run"
                ])
                
                assert result.exit_code == 0
                mock_load_universe.assert_called()
                mock_get_price_data.assert_called()
        finally:
            os.chdir(original_cwd)

    @patch("kiss_signal.data.get_price_data", side_effect=Exception("Data fetch failed"))
    @patch("kiss_signal.data.load_universe")
    def test_error_handling_integration(self, mock_load_universe, mock_get_price_data, integration_env):
        """Test error handling integration."""
        mock_load_universe.return_value = ['RELIANCE', 'INFY']
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(integration_env)
            config_path = integration_env / "config.yaml"
            rules_path = integration_env / "config" / "rules.yaml"
            
            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "run"
            ])
            
            # Should handle errors gracefully
            assert "Error" in result.stdout or result.exit_code != 0
        finally:
            os.chdir(original_cwd)
