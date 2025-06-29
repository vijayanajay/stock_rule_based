"""Tests for CLI module - Advanced functionality."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml
from unittest.mock import patch
import sqlite3

from kiss_signal.cli import app
from kiss_signal.config import RuleDef


VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10
"""

runner = CliRunner()


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
            'rule_stack': [RuleDef(type='sma_crossover', name='sma_10_20_crossover', params={'short_window': 10, 'long_window': 20})],
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
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
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
        'rule_stack': [RuleDef(type='sma_crossover', name='sma_10_20_crossover', params={'short_window': 10, 'long_window': 20})],
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
        rules_path.write_text(VALID_RULES_YAML)

        # Mock persistence failure
        mock_save_batch.side_effect = sqlite3.OperationalError("disk I/O error")

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 0, result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "Database error: disk I/O error" in result.stdout


@patch("kiss_signal.cli._run_backtests", side_effect=ValueError("Backtest failed!"))
@patch("kiss_signal.cli.data")
def test_run_command_backtest_value_error(
    mock_data, mock_run_backtests, sample_config: Dict[str, Any]
) -> None:
    """Test that a ValueError during backtesting is handled gracefully."""
    with runner.isolated_filesystem() as fs:
        # Create dummy universe file to pass config validation
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.touch()

        sample_config["universe_path"] = str(universe_path)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))

        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])

        assert result.exit_code == 1
        assert "Error: Backtest failed!" in result.stdout


@patch("kiss_signal.cli._run_backtests", side_effect=FileNotFoundError("Universe file not found"))
@patch("kiss_signal.cli.data.load_universe")
def test_run_command_file_not_found_in_backtest(
    mock_load_universe, mock_run_backtests, sample_config: Dict[str, Any]
) -> None:
    """Test that a FileNotFoundError during backtesting is handled."""
    with runner.isolated_filesystem() as fs:
        # Setup a valid config so the app starts
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.touch()
        sample_config["universe_path"] = str(universe_path)

        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        rules_path.write_text(VALID_RULES_YAML)
    
        # The universe file is checked inside _run_backtests which we are mocking
        # to raise the error.
        mock_load_universe.return_value = ["RELIANCE"]
    
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
    
        assert result.exit_code == 1
        assert "Error: Universe file not found" in result.stdout


@patch("kiss_signal.cli._run_backtests", side_effect=Exception("Generic backtest error"))
@patch("kiss_signal.cli.data")
def test_run_command_backtest_generic_exception_verbose(
    mock_data, mock_run_backtests, sample_config: Dict[str, Any]
) -> None:
    """Test that a generic exception during backtesting is handled with verbose output."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        rules_path.write_text(VALID_RULES_YAML)

        # Corrected order: global options like --verbose must come before the command
        result = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "run"])

        assert result.exit_code == 1
        assert "An unexpected error occurred: Generic backtest error" in result.stdout
        assert "Traceback (most recent call last)" in result.stdout  # Match Rich's traceback format


@patch("rich.console.Console.export_text", side_effect=Exception("Cannot export"))
@patch("kiss_signal.cli._run_backtests")
def test_run_command_log_save_failure(
    mock_run_backtests, mock_export_text, sample_config, tmp_path
):
    """Test that CLI handles log saving failures in finally block."""
    mock_run_backtests.return_value = []
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))
        rules_path = Path(fs) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "run"])
        assert result.exit_code == 0, result.stdout
        assert "Critical error: Could not save log file" in result.stderr
