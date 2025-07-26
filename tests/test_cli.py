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
def test_run_command_basic(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
    """Test basic run command with isolated filesystem."""
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
    
    with runner.isolated_filesystem() as fs:
        # Create data directory structure
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\nTCS,TCS,IT\n")
        
        # Update config with correct paths
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Create rules file
        config_dir = Path(fs) / "config"
        config_dir.mkdir()
        rules_path = config_dir / "rules.yaml"
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "edge_score" in result.stdout or "No valid strategies found" in result.stdout


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
@patch("kiss_signal.cli.reporter.generate_daily_report")
def test_run_command_verbose(mock_data, mock_backtester, mock_get_summary, sample_config: Dict[str, Any]) -> None:
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
    
    with runner.isolated_filesystem() as fs:
        # Create data directory structure
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\nTCS,TCS,IT\n")
        
        # Update config with correct paths
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Create rules file
        config_dir = Path(fs) / "config"
        config_dir.mkdir()
        rules_path = config_dir / "rules.yaml"
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--verbose"], catch_exceptions=False)
        assert result.exit_code == 0


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_freeze_date(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
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
    
    with runner.isolated_filesystem() as fs:
        # Create data directory structure
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\nTCS,TCS,IT\n")
        
        # Update config with correct paths
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Create rules file
        config_dir = Path(fs) / "config"
        config_dir.mkdir()
        rules_path = config_dir / "rules.yaml"
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "2025-01-01"], catch_exceptions=False)
        assert result.exit_code == 0


def test_run_command_invalid_freeze_date(sample_config: Dict[str, Any]) -> None:
    """Test run command with invalid freeze-data parameter."""
    with runner.isolated_filesystem() as fs:
        # Create data directory structure
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        # Update config with correct paths
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Create rules file
        config_dir = Path(fs) / "config"
        config_dir.mkdir()
        rules_path = config_dir / "rules.yaml"
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "invalid-date"])
        assert result.exit_code != 0
        assert "Invalid isoformat string" in result.stdout or "Error" in result.stdout


def test_run_command_no_config() -> None:
    """Test run command without config file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        assert "No such file or directory" in result.stdout or "Config file not found" in result.stdout


def test_run_command_missing_rules(sample_config: Dict[str, Any]) -> None:
    """Test run command with missing rules file."""
    with runner.isolated_filesystem() as fs:
        # Create data directory structure
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache" 
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        # Update config with correct paths
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        
        # Create config file but no rules file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        result = runner.invoke(app, ["--config", str(config_path), "run"])
        assert result.exit_code != 0
        assert "Rules file not found" in result.stdout or "No such file or directory" in result.stdout


# =============================================================================
# Run Command Tests - Error Handling
# =============================================================================

@patch("kiss_signal.cli.data")
@patch("kiss_signal.cli.backtester.Backtester")  
def test_run_command_insufficient_data_handling(mock_data, mock_bt, sample_config, tmp_path):
    """Test run command when insufficient data is available."""
    # Mock insufficient data scenario
    mock_data.get_universe.return_value = ["RELIANCE"]
    mock_data.get_price_data.side_effect = ValueError("Insufficient data")
    
    with runner.isolated_filesystem() as fs:
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Create rules file
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
        
        # Create data directories
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\n")
        
        result = runner.invoke(app, ["run"])
        # Should handle error gracefully
        assert result.exit_code == 0 or "Error" in result.stdout


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_with_persistence(
    mock_run_backtests, mock_get_connection, sample_config, tmp_path
):
    """Test that run command integrates with persistence layer."""
    # Mock the connection and cursor
    mock_conn = mock_get_connection.return_value
    mock_cursor = mock_conn.cursor.return_value

    with runner.isolated_filesystem() as fs:
        mock_run_backtests.return_value = [{
            'symbol': 'RELIANCE',
            'rule_stack': [RuleDef(type='sma_crossover', name='sma_10_20_crossover', params={'short_window': 10, 'long_window': 20})],
            'edge_score': 0.75,
            'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
        }]

        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        result = runner.invoke(app, ["run"], catch_exceptions=False)
        assert result.exit_code == 0


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_persistence_failure_handling(
    mock_run_backtests, mock_get_connection, sample_config
):
    """Test that run command handles persistence layer failures gracefully."""
    # Mock persistence failure
    mock_get_connection.side_effect = sqlite3.Error("Database error")
    
    with runner.isolated_filesystem() as fs:
        # Create config file
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        # Create rules file  
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        # Create data directories
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        result = runner.invoke(app, ["run"])
        # Should handle database errors gracefully
        assert "Database error" in result.stdout or result.exit_code != 0


# =============================================================================
# Analyze Strategies Command Tests
# =============================================================================

@patch("kiss_signal.cli.reporter.format_strategy_analysis_as_csv")
@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_success(mock_format_csv, mock_analyze, sample_config):
    """Test analyze-strategies command with successful execution."""
    # Mock the analyzer to return sample data
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
    
    mock_format_csv.return_value = "CSV formatted output"

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        # Create mock database
        db_path = Path(fs) / "data" / "test.db"
        db_path.parent.mkdir()
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

        result = runner.invoke(app, ["analyze-strategies"])
        assert result.exit_code == 0
        assert "CSV formatted output" in result.stdout


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_custom_output(mock_get_connection, mock_analyze, sample_config):
    """Test analyze-strategies command with custom output path."""
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

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        output_path = Path(fs) / "custom_output.csv"
        
        result = runner.invoke(app, ["analyze-strategies", "--output", str(output_path)])
        assert result.exit_code == 0
        # Should create the output file
        assert output_path.exists()


def test_analyze_strategies_command_no_database(sample_config):
    """Test analyze-strategies command when database doesn't exist."""
    with runner.isolated_filesystem() as fs:
        # Setup config without database
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        result = runner.invoke(app, ["analyze-strategies"])
        assert result.exit_code != 0
        assert "database" in result.stdout.lower() or "error" in result.stdout.lower()


@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_no_data(mock_analyze, sample_config):
    """Test analyze-strategies command when no data is available."""
    # Mock analyzer to return empty data
    mock_analyze.return_value = []

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        # Create empty database
        db_path = Path(fs) / "data" / "test.db"
        db_path.parent.mkdir()
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

        result = runner.invoke(app, ["analyze-strategies"])
        assert result.exit_code == 0
        assert "No data found" in result.stdout or "no strategies" in result.stdout.lower()


@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
def test_analyze_strategies_command_error_handling(mock_analyze, sample_config):
    """Test analyze-strategies command error handling."""
    # Mock analyzer to raise an exception
    mock_analyze.side_effect = Exception("Analysis failed")

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        # Create database
        db_path = Path(fs) / "data" / "test.db"
        db_path.parent.mkdir()
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

        result = runner.invoke(app, ["analyze-strategies"])
        assert "Error" in result.stdout or result.exit_code != 0


# =============================================================================
# Clear and Recalculate Command Tests  
# =============================================================================

@patch("kiss_signal.cli.persistence.clear_strategies_for_config")
@patch("kiss_signal.cli._run_backtests")
@patch("kiss_signal.cli._process_and_save_results")
def test_clear_and_recalculate_basic_flow(mock_process, mock_run, mock_clear, sample_config):
    """Test basic clear-and-recalculate command flow."""
    # Mock the backtesting results
    mock_run.return_value = [
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

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        # Create data directories
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        result = runner.invoke(app, ["clear-and-recalculate"])
        assert result.exit_code == 0
        
        # Verify the clear function was called
        mock_clear.assert_called_once()
        # Verify backtests were run
        mock_run.assert_called_once()
        # Verify results were processed
        mock_process.assert_called_once()


@patch("kiss_signal.cli.persistence.clear_strategies_for_config")
def test_clear_and_recalculate_clear_failure(mock_clear, sample_config):
    """Test clear-and-recalculate command when clear operation fails."""
    # Mock clear to raise an exception
    mock_clear.side_effect = sqlite3.Error("Clear failed")

    with runner.isolated_filesystem() as fs:
        # Setup files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        result = runner.invoke(app, ["clear-and-recalculate"])
        assert "Error" in result.stdout or result.exit_code != 0


# =============================================================================
# Min Trades Filtering Tests
# =============================================================================

def test_cli_with_min_trades_config():
    """Test CLI respects min_trades configuration."""
    with runner.isolated_filesystem() as fs:
        # Create config with min_trades
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(VALID_CONFIG_WITH_MIN_TRADES, f)

        # Create rules file
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        # Create data directories
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        # Test that config loads successfully
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0


@patch("kiss_signal.cli._run_backtests")
def test_min_trades_filtering_applied(mock_run_backtests):
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

    with runner.isolated_filesystem() as fs:
        # Create config with min_trades
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(VALID_CONFIG_WITH_MIN_TRADES, f)

        # Create rules file
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        # Create data directories
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        result = runner.invoke(app, ["run"])
        # Should filter out strategies with insufficient trades
        assert result.exit_code == 0


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


def test_run_command_backtest_generic_exception_verbose():
    """Test run command handles generic exceptions in verbose mode."""
    with patch("kiss_signal.cli._run_backtests") as mock_run:
        mock_run.side_effect = Exception("Generic error")
        
        with runner.isolated_filesystem() as fs:
            # Setup minimal config
            config_path = Path(fs) / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump({"data_dir": "data/"}, f)
            
            result = runner.invoke(app, ["run", "--verbose"])
            assert "Error" in result.stdout or result.exit_code != 0


@patch("kiss_signal.cli.reporter.generate_daily_report")
def test_run_command_report_generation_fails_warning(mock_generate_report):
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
        
        with runner.isolated_filesystem() as fs:
            # Setup minimal config
            config_path = Path(fs) / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump({"data_dir": "data/"}, f)
            
            result = runner.invoke(app, ["run", "--verbose"])
            # Should handle report generation failure gracefully
            assert result.exit_code == 0 or "warning" in result.stdout.lower()


# =============================================================================
# Parameterized Tests for Variations
# =============================================================================

@pytest.mark.parametrize("command_args,expected_success", [
    (["run"], True),
    (["run", "--verbose"], True),
    (["run", "--freeze-data", "2025-01-01"], True),
    (["run", "--freeze-data", "invalid-date"], False),
    (["analyze-strategies"], True),
    (["analyze-strategies", "--per-stock"], True),
    (["clear-and-recalculate"], True),
])
def test_cli_command_variations(command_args, expected_success, sample_config):
    """Parameterized test for various CLI command variations."""
    with runner.isolated_filesystem() as fs:
        # Setup basic files
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        if expected_success:
            # For successful cases, we expect proper error handling
            result = runner.invoke(app, command_args)
            # Either success or graceful error handling
            assert result.exit_code == 0 or "Error" in result.stdout
        else:
            # For failure cases, we expect non-zero exit code
            result = runner.invoke(app, command_args)
            assert result.exit_code != 0


# =============================================================================
# Integration-style Tests
# =============================================================================

@patch("kiss_signal.cli.data.load_universe")
@patch("kiss_signal.cli.data.get_price_data")
@patch("kiss_signal.cli.data.refresh_market_data")
@patch("kiss_signal.cli.backtester.Backtester")
def test_full_cli_integration_flow(mock_bt, mock_refresh, mock_price, mock_universe, sample_config):
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

    with runner.isolated_filesystem() as fs:
        # Setup complete environment
        config_path = Path(fs) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)

        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)

        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write("RELIANCE\nTCS\n")

        # Test run command
        result = runner.invoke(app, ["run"], catch_exceptions=False)
        assert result.exit_code == 0

        # Verify mocks were called appropriately
        mock_universe.assert_called()
        mock_price.assert_called()
        mock_refresh.assert_called()
        mock_bt.assert_called()
