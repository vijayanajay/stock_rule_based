"""Tests for CLI module - Basic functionality."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml
from unittest.mock import patch

from kiss_signal.cli import app
import pandas as pd


VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10
"""


# Test imports first
def test_cli_import() -> None:
    """Test that CLI app can be imported without issues."""
    assert app is not None

runner = CliRunner()

def test_app_help() -> None:
    """Test the main app --help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "KISS Signal CLI" in result.stdout
    assert "run" in result.stdout


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

        mock_data.load_universe.return_value = ["RELIANCE"]
        mock_data.get_price_data.return_value = pd.DataFrame(
            {'close': range(101)}, 
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
        )
        mock_bt_instance = mock_backtester.return_value
        mock_bt_instance.find_optimal_strategies.return_value = []

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
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
        rules_path.write_text(VALID_RULES_YAML)

        mock_data.load_universe.return_value = ["RELIANCE"]
        mock_data.get_price_data.return_value = pd.DataFrame(
            {'close': range(101)}, 
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
        )
        mock_bt_instance = mock_backtester.return_value
        mock_bt_instance.find_optimal_strategies.return_value = []

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "--verbose", "run"]
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
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "2025-01-01"]
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
        rules_path.write_text(VALID_RULES_YAML)

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
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
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
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "invalid-date"]
        )
        assert result.exit_code == 1
        assert "Invalid isoformat string" in result.stdout


def test_run_command_no_config() -> None:
    """Test run command with a missing config file."""
    with runner.isolated_filesystem():
        # Create a dummy rules file so only the config is missing
        rules_path = Path("rules.yaml")
        rules_path.write_text("rules: []")
        result = runner.invoke(app, ["--config", "nonexistent.yaml", "--rules", str(rules_path), "run"])
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
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 1
        assert "Rules file not found" in result.stdout
