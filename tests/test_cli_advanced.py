"""Tests for CLI module - Advanced functionality."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml, pathlib
from unittest.mock import patch, MagicMock
import sqlite3
import json

from kiss_signal.cli import app
from kiss_signal.config import RuleDef
from kiss_signal import persistence


VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10
"""

runner = CliRunner()


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

        mock_get_connection.assert_called_once()
        mock_conn.cursor.assert_called()
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called_once()


@patch("kiss_signal.cli.persistence.get_connection")
@patch("kiss_signal.cli._run_backtests")
def test_run_command_persistence_failure_handling(
    mock_run_backtests, mock_get_connection, sample_config, tmp_path
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
        mock_conn = mock_get_connection.return_value
        mock_conn.commit.side_effect = sqlite3.OperationalError("disk I/O error")

        result = runner.invoke(
            app, ["--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 0, result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "Failed to save results to database" in result.stdout
        mock_conn.close.assert_called_once()


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
        universe_path = data_dir / "universe.csv"
        universe_path.write_text("symbol\nTEST\n")

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
        universe_path = data_dir / "universe.csv"
        universe_path.write_text("symbol\nTEST\n")
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
    with runner.isolated_filesystem() as fs_path:
        data_dir = Path(fs_path) / "data"; data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"; universe_path.write_text("symbol\nRELIANCE\n")
        sample_config["universe_path"] = str(universe_path)
        config_path = Path(fs_path) / "config.yaml"
        config_path.write_text(yaml.dump(sample_config))
        rules_path = Path(fs_path) / "config" / "rules.yaml"
        rules_path.parent.mkdir()
        rules_path.write_text(VALID_RULES_YAML)

        # Global options like --verbose must come BEFORE the command.
        result = runner.invoke(
            app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "run"]
        )
        assert result.exit_code == 1, result.stdout
        assert "An unexpected error occurred: Generic backtest error" in result.stdout
        assert "Traceback (most recent call last)" in result.stdout


@patch("kiss_signal.cli.reporter.generate_daily_report", return_value=None)
@patch("kiss_signal.cli._run_backtests") # Mock to prevent actual backtesting
@patch("kiss_signal.cli.persistence") # Mock persistence to avoid DB operations
def test_run_command_report_generation_fails_warning(
    mock_persistence, mock_run_backtests, mock_generate_report, sample_config, tmp_path
):
    """Test CLI shows warning if report generation returns None."""
    mock_run_backtests.return_value = [{ # Need some results to proceed to report generation
        'symbol': 'RELIANCE',
        'rule_stack': [RuleDef(type='sma_crossover', name='sma_test', params={'fast_period':5, 'slow_period':10})],
        'edge_score': 0.1, 'win_pct': 0.1, 'sharpe': 0.1, 'total_trades': 1, 'avg_return': 0.01
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
        sample_config["database_path"] = str(Path(fs) / "test.db") # Ensure db path is in temp
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
        assert "(WARN) Report generation failed" in result.stdout
        mock_generate_report.assert_called_once()


def test_analyze_rules_command(tmp_path: Path):
    """Test the 'analyze-rules' CLI command."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        db_path = fs_path / "test.db"
        config_path = fs_path / "config.yaml"
        output_path = fs_path / "analysis.md"

        # 1. Create a populated database
        persistence.create_database(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', 'run1', json.dumps([{'name': 'rule_A'}]), 0.8, 0.7, 1.5, 10, 0.05)
            )

        # Create a basic config.yaml that passes validation
        dummy_universe_file = fs_path / "dummy_universe.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")
        dummy_cache_dir = fs_path / "dummy_cache"
        dummy_cache_dir.mkdir()

        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": str(dummy_cache_dir),
            "cache_refresh_days": 7,
            "historical_data_years": 5,
            "hold_period": 20, # Add other required fields by Config model
            "min_trades_threshold": 5,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
            # "freeze_date": null, # Optional
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml" # Dummy, not used by analyze-rules
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)


        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-rules", "-o", str(output_path)])
        assert result.exit_code == 0, result.stdout
        assert "Rule performance analysis saved" in result.stdout
        assert output_path.exists()


def test_analyze_rules_db_not_found(tmp_path: Path):
    """Test 'analyze-rules' when the database file does not exist."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        config_path = fs_path / "config.yaml"

        dummy_universe_file = fs_path / "dummy_universe.csv"; dummy_universe_file.write_text("symbol\nTEST\n")
        dummy_cache_dir = fs_path / "dummy_cache"; dummy_cache_dir.mkdir()
        sample_config_dict = {
            "database_path": str(fs_path / "nonexistent.db"),
            "universe_path": str(dummy_universe_file), "cache_dir": str(dummy_cache_dir),
            "cache_refresh_days": 7, "historical_data_years": 5, "hold_period": 20,
            "min_trades_threshold": 5, "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/", # Added missing field
            "edge_score_threshold": 0.5, # Added missing field
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml" # Dummy, not used by analyze-rules
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result.exit_code == 1
        assert "Error: Database file not found" in result.stdout


@patch("kiss_signal.cli.reporter.analyze_rule_performance", return_value={})
def test_analyze_rules_no_strategies_found(mock_analyze, tmp_path: Path):
    """Test 'analyze-rules' when no strategies are found in the DB."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        db_path = fs_path / "test.db" # DB will exist but mock will return no data
        config_path = fs_path / "config.yaml"

        # Create empty DB
        persistence.create_database(db_path)

        dummy_universe_file = fs_path / "dummy_universe.csv"; dummy_universe_file.write_text("symbol\nTEST\n")
        dummy_cache_dir = fs_path / "dummy_cache"; dummy_cache_dir.mkdir()
        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file), "cache_dir": str(dummy_cache_dir),
            "cache_refresh_days": 7, "historical_data_years": 5, "hold_period": 20,
            "min_trades_threshold": 5, "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/", # Added missing field
            "edge_score_threshold": 0.5, # Added missing field
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)

        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result.exit_code == 0, result.stdout
        assert "No historical strategies found in the database to analyze." in result.stdout
        mock_analyze.assert_called_once_with(db_path)


@patch("kiss_signal.cli.reporter.analyze_rule_performance", side_effect=Exception("Analysis boom!"))
@patch("kiss_signal.cli.persistence.get_connection")
def test_analyze_rules_exception_handling(mock_get_connection, mock_analyze, tmp_path: Path):
    """Test 'analyze-rules' general exception handling."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        persistence.create_database(db_path)
        dummy_universe_file = fs_path / "dummy_universe.csv"
        dummy_universe_file.write_text("symbol\nTEST\n") # Add header and content
        dummy_cache_dir = fs_path / "dummy_cache"
        dummy_cache_dir.mkdir()
        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": str(dummy_cache_dir),
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        result = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result.exit_code == 1
        assert "An unexpected error occurred during analysis: Analysis boom!" in result.stdout
        result_verbose = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result_verbose.exit_code == 1
        assert "An unexpected error occurred during analysis: Analysis boom!" in result_verbose.stdout
        assert "Traceback (most recent call last)" in result_verbose.stdout


@patch("kiss_signal.cli.reporter.analyze_strategy_performance")
@patch("kiss_signal.cli.reporter.format_strategy_analysis_as_csv")
def test_analyze_strategies_command_success(mock_format_csv, mock_analyze, sample_config):
    """Test analyze-strategies command with successful execution."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        # Setup mock data - Story 16: Use aggregated strategy format
        mock_analyze.return_value = [
            {
                'strategy_rule_stack': 'test_strategy',
                'frequency': 5,
                'avg_edge_score': 0.5,
                'avg_win_pct': 0.6,
                'avg_sharpe': 1.0,
                'avg_return': 0.1,
                'avg_trades': 10.0,
                'top_symbols': 'RELIANCE (2), INFY (2), TCS (1)'
            }
        ]
        mock_format_csv.return_value = "strategy_rule_stack,frequency,avg_edge_score\ntest_strategy,5,0.5000"
        
        # Setup config and database
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        persistence.create_database(db_path)
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")
        
        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": "cache/",
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        
        # Test default output file
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        
        assert result.exit_code == 0
        assert "Analyzing per-stock strategy performance" in result.stdout
        assert "Strategy performance analysis saved to:" in result.stdout  # Story 17 change: Updated text
        assert "strategy_performance_report.csv" in result.stdout
        # Check that file was created
        output_file = fs_path / "strategy_performance_report.csv"
        assert output_file.exists()
        assert "strategy_rule_stack,frequency" in output_file.read_text()
        # Verify mocks were called
        mock_analyze.assert_called_once_with(db_path)
        mock_format_csv.assert_called_once()


@patch("kiss_signal.cli.reporter.analyze_strategy_performance")
@patch("kiss_signal.cli.persistence.get_connection")
def test_analyze_strategies_command_custom_output(mock_get_connection, mock_analyze, sample_config):
    """Test analyze-strategies command with custom output file."""
    mock_conn = mock_get_connection.return_value
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        # Story 17 change: Use per-stock record format instead of aggregated format
        mock_analyze.return_value = [{
            'symbol': 'TEST',
            'strategy_rule_stack': 'test_strategy',
            'edge_score': 0.5,
            'win_pct': 0.6,
            'sharpe': 1.0,
            'total_return': 0.05,
            'total_trades': 10,
            'config_hash': 'test_hash',
            'run_date': '2025-07-13',
            'config_details': '{"test": true}'
        }]
        
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"; persistence.create_database(db_path)
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")
        
        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": "cache/",
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        
        custom_output = "my_strategy_report.csv"
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--output", custom_output])
        
        assert result.exit_code == 0, result.stdout
        assert custom_output in result.stdout
        
        output_file = fs_path / custom_output
        assert output_file.exists()


def test_analyze_strategies_command_no_database(sample_config):
    """Test analyze-strategies command when database doesn't exist."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        config_path = fs_path / "config.yaml"
        nonexistent_db = fs_path / "nonexistent.db"
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")
        
        sample_config_dict = {
            "database_path": str(nonexistent_db),
            "universe_path": "dummy.csv",
            "cache_dir": "cache/",
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        sample_config_dict["universe_path"] = str(dummy_universe_file)
        config_path.write_text(yaml.dump(sample_config_dict))
        
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        
        assert result.exit_code == 1
        assert "Database file not found" in result.stdout


@patch("kiss_signal.cli.reporter.analyze_strategy_performance")
def test_analyze_strategies_command_no_data(mock_analyze, sample_config):
    """Test analyze-strategies command when no historical data exists."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        mock_analyze.return_value = []
        
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        db_path.touch() # Create empty db file
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")

        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": "cache/",
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        
        assert result.exit_code == 0, result.stdout
        assert "No historical strategies found to analyze" in result.stdout


@patch("kiss_signal.cli.reporter.analyze_strategy_performance")
def test_analyze_strategies_command_error_handling(mock_analyze, sample_config):
    """Test analyze-strategies command error handling."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        mock_analyze.side_effect = Exception("Analysis boom!")
        
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        persistence.create_database(db_path)
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST\n")

        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": "cache/",
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        assert result.exit_code == 1
        assert "An unexpected error occurred during analysis: Analysis boom!" in result.stdout


@patch("kiss_signal.cli.reporter.analyze_rule_performance", side_effect=Exception("Analysis boom!"))
def test_analyze_rules_exception_handling(mock_analyze, tmp_path: Path):
    """Test 'analyze-rules' general exception handling."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        persistence.create_database(db_path)
        dummy_universe_file = fs_path / "dummy_universe.csv"
        dummy_universe_file.write_text("symbol\nTEST\n") # Add header and content
        dummy_cache_dir = fs_path / "dummy_cache"
        dummy_cache_dir.mkdir()
        sample_config_dict = {
            "database_path": str(db_path),
            "universe_path": str(dummy_universe_file),
            "cache_dir": str(dummy_cache_dir),
            "cache_refresh_days": 7,
            "historical_data_years": 3,
            "hold_period": 20,
            "min_trades_threshold": 10,
            "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
            "reports_output_dir": "reports/",
            "edge_score_threshold": 0.5,
        }
        config_path.write_text(yaml.dump(sample_config_dict))
        rules_path = fs_path / "config" / "rules.yaml"
        rules_path.parent.mkdir(exist_ok=True)
        rules_path.write_text(VALID_RULES_YAML)
        result = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result.exit_code == 1
        assert "An unexpected error occurred during analysis: Analysis boom!" in result.stdout
        result_verbose = runner.invoke(app, ["--verbose", "--config", str(config_path), "--rules", str(rules_path), "analyze-rules"])
        assert result_verbose.exit_code == 1
        assert "An unexpected error occurred during analysis: Analysis boom!" in result_verbose.stdout
        assert "Traceback (most recent call last)" in result_verbose.stdout


