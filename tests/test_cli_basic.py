"""Tests for CLI module - Basic functionality."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml
from unittest.mock import patch

from kiss_signal.cli import app
from kiss_signal.config import RuleDef
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

def test_run_command_help() -> None:
    """Test the main app --help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "analyze-rules" in result.stdout


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
        mock_bt_instance.find_optimal_strategies.return_value = [] # Ensure no results

        # Mock persistence methods that would be called if results were present
        mock_save_batch = patch("kiss_signal.cli.persistence.save_strategies_batch").start()
        mock_create_db = patch("kiss_signal.cli.persistence.create_database").start()


        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 0, result.stdout
        assert "Analysis complete." in result.stdout
        assert "No valid strategies found" in result.stdout
        mock_backtester.assert_called_with(
            hold_period=sample_config["hold_period"],
            min_trades_threshold=sample_config["min_trades_threshold"]
        )

        # Verify that save_results was effectively skipped
        mock_create_db.assert_not_called()
        mock_save_batch.assert_not_called()
        patch.stopall() # Stop patches started in this test


@patch("kiss_signal.cli.performance_monitor.get_summary")
@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_verbose(mock_data, mock_backtester, mock_get_summary, sample_config: Dict[str, Any]) -> None:
    """Test run command with verbose flag and isolated filesystem."""
    mock_get_summary.return_value = {
        "total_duration": 12.34,
        "slowest_function": "test_func (5.67s)"
    }
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
            app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 0, result.stdout
        assert "Performance Summary:" in result.stdout
        assert "Total Duration: 12.34s" in result.stdout
        assert "Slowest Function: test_func (5.67s)" in result.stdout
        mock_get_summary.assert_called_once()


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
            app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "run", "--freeze-data", "2025-01-01"]
        )
        assert result.exit_code == 0, result.stdout
        assert "skipping data refresh (freeze mode)" in result.stdout.lower()
        assert "Freeze mode active: 2025-01-01" in result.stdout # Check for verbose log
        mock_data.refresh_market_data.assert_not_called()


@patch("kiss_signal.cli.backtester.Backtester")
@patch("kiss_signal.cli.data")
def test_run_command_success(mock_data, mock_backtester, sample_config: Dict[str, Any]) -> None: # Removed mock_get_summary from params
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
            'rule_stack': [RuleDef(type='sma_crossover', name='sma_10_20_crossover', params={'short_window': 10, 'long_window': 20})],
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
        assert "Error loading configuration" in result.stdout


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


@patch("kiss_signal.cli.backtester.Backtester") # Mock backtester to prevent actual runs
@patch("kiss_signal.cli.data") # Mock data module
def test_run_command_insufficient_data_handling(mock_data, mock_bt, sample_config, tmp_path):
    """Test that CLI handles insufficient data for symbols gracefully."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        cache_dir = data_dir / "cache"
        cache_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        # Universe with two symbols
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\nINFY,Infosys,IT\n")

        sample_config["universe_path"] = str(universe_path)
        sample_config["cache_dir"] = str(cache_dir)
        config_path = Path("config.yaml")
        config_path.write_text(yaml.dump(sample_config))

        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text(VALID_RULES_YAML)

        # Mock load_universe to return the two symbols
        mock_data.load_universe.return_value = ["RELIANCE", "INFY"]

        # Mock get_price_data:
        # - RELIANCE: returns None (simulating no data)
        # - INFY: returns short DataFrame (less than 100 rows)
        short_df = pd.DataFrame(
            {'close': range(50)},
            index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=50))
        )
        mock_data.get_price_data.side_effect = [None, short_df]

        # Mock the backtester instance's find_optimal_strategies to return empty list
        # as it shouldn't be called if data is insufficient.
        mock_bt_instance = mock_bt.return_value
        mock_bt_instance.find_optimal_strategies.return_value = []

        result = runner.invoke(
            app, ["--config", str(Path(fs) / "config.yaml"), "--rules", str(Path(fs) / "config" / "rules.yaml"), "run"] # Temporarily remove --verbose
        )

        assert result.exit_code == 0, result.stdout

        # Check that warnings for insufficient data were logged
        assert "Insufficient data for RELIANCE, skipping" in result.stdout
        assert "Insufficient data for INFY, skipping" in result.stdout

        # Ensure find_optimal_strategies was not called for these symbols
        mock_bt_instance.find_optimal_strategies.assert_not_called()

        # Ensure it still says "No valid strategies found" if all were skipped
        assert "No valid strategies found" in result.stdout
