"""Tests for CLI module."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml
from unittest.mock import patch
import sqlite3

from kiss_signal.cli import app
import pandas as pd


# Test imports first
def test_cli_import() -> None:
    """Test that CLI app can be imported without issues."""
    assert app is not None

runner = CliRunner()

def test_run_command_help() -> None:
    """Test run command help shows expected content."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout.lower()


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_basic(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
    """Test basic run command with isolated filesystem."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        mock_data.load_universe.return_value = ["RELIANCE"]
        mock_data.get_price_data.return_value = pd.DataFrame(
            {'close': range(101)}, 
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
        )
        mock_bt_instance = mock_backtester.return_value
        mock_bt_instance.find_optimal_strategies.return_value = []

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path)]
        )
        assert result.exit_code == 0, result.stdout
        assert "Analysis complete." in result.stdout
        assert "No valid strategies found" in result.stdout


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_verbose(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
    """Test run command with verbose flag and isolated filesystem."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        mock_data.load_universe.return_value = ["RELIANCE"]
        mock_data.get_price_data.return_value = pd.DataFrame(
            {'close': range(101)}, 
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
        )
        mock_bt_instance = mock_backtester.return_value
        mock_bt_instance.find_optimal_strategies.return_value = []

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path), "--verbose"]
        )
        assert result.exit_code == 0, result.stdout


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_freeze_date(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
    """Test run command with freeze date and isolated filesystem."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path), "--freeze-data", "2025-01-01"]
        )
        assert result.exit_code == 0, result.stdout
        assert "skipping data refresh (freeze mode)" in result.stdout.lower()
        mock_data.refresh_market_data.assert_not_called()


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_success(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None:
    """Test a successful run command execution with mocks."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        mock_data.load_universe.return_value = ["RELIANCE"]
        mock_data.get_price_data.return_value = pd.DataFrame(
            {'close': range(101)}, 
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
        )
        mock_bt_instance = mock_backtester.return_value
        mock_bt_instance.find_optimal_strategies.return_value = [{
            'symbol': 'RELIANCE', 
            'rule_stack': [{'type': 'sma_crossover', 'name': 'sma_10_20_crossover', 'params': {'short_window': 10, 'long_window': 20}}], 
            'edge_score': 0.5,
            'win_pct': 0.5, 
            'sharpe': 0.5, 
            'total_trades': 12
        }]

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path)]
        )
        assert result.exit_code == 0, result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "RELIANCE" in result.stdout


def test_run_command_invalid_freeze_date(sample_config: Dict[str, Any]) -> None:
    """Test run command with invalid freeze date."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path), "--freeze-data", "invalid-date"]
        )
        assert result.exit_code == 1
        assert "Invalid isoformat string" in result.stdout


def test_run_command_no_config() -> None:
    """Test run command with a missing config file."""
    with runner.isolated_filesystem():
        # Create a dummy rules file so only the config is missing
        rules_path = Path("rules.yaml")
        rules_path.write_text("rules: []")
        result = runner.invoke(app, ["run", "--config", "nonexistent.yaml", "--rules", str(rules_path)])
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout


def test_run_command_missing_rules(sample_config: Dict[str, Any]) -> None:
    """Test run command with missing rules file."""
    with runner.isolated_filesystem() as fs:
        # Prepare data files for a complete config
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        # Complete config setup using fixture
        complete_config = sample_config.copy()
        complete_config["universe_path"] = str(universe_path)
        complete_config["cache_dir"] = str(cache_dir)
        
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(complete_config))
        rules_path = Path("nonexistent_rules.yaml")
        
        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path)]
        )
        assert result.exit_code == 1
        assert "Rules file not found" in result.stdout


@patch("kiss_signal.cli.persistence.create_database")
@patch("kiss_signal.cli.persistence.save_strategies_batch")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_with_persistence(
    mock_run_backtests, mock_save_batch, mock_create_db, sample_config, tmp_path
):
    """Test that run command integrates with persistence layer."""
    with runner.isolated_filesystem() as fs:
        mock_run_backtests.return_value = [{
            'symbol': 'RELIANCE', 
            'rule_stack': [{'type': 'sma_crossover', 'name': 'sma_10_20_crossover', 'params': {'short_window': 10, 'long_window': 20}}], 
            'edge_score': 0.75,
            'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
        }]

        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))

        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path)]
        )
        assert result.exit_code == 0, result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "RELIANCE" in result.stdout

        mock_create_db.assert_called_once()
        mock_save_batch.assert_called_once()

        call_args = mock_save_batch.call_args
        assert isinstance(call_args.args[0], Path)
        assert call_args.args[1] == mock_run_backtests.return_value


@patch("kiss_signal.cli.persistence.save_strategies_batch")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_persistence_failure_handling(
    mock_run_backtests, mock_save_batch, sample_config, tmp_path
):
    """Test that CLI handles persistence failures gracefully."""
    mock_run_backtests.return_value = [{
        'symbol': 'RELIANCE', 
        'rule_stack': [{'type': 'sma_crossover', 'name': 'sma_10_20_crossover', 'params': {'short_window': 10, 'long_window': 20}}], 
        'edge_score': 0.75,
        'win_pct': 0.65, 'sharpe': 1.2, 'total_trades': 15, 'avg_return': 0.02
    }]

    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))

        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text("rules: []")

        # Mock persistence failure
        mock_save_batch.side_effect = sqlite3.OperationalError("disk I/O error")

        result = runner.invoke(
            app, ["run", "--config", str(config_path), "--rules", str(rules_path)]
        )
        assert result.exit_code == 0, result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "Database error: disk I/O error" in result.stdout
