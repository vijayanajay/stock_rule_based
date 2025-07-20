"""
Tests for the 'clear-and-recalculate' CLI command.

This module tests the command's interaction with the persistence layer,
ensuring correct behavior for clearing, preserving, and recalculating strategies.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch
from datetime import date

import pytest
from typer.testing import CliRunner

from kiss_signal.cli import app
from kiss_signal.config import Config, RulesConfig, RuleDef
from kiss_signal import persistence


runner = CliRunner()


def get_valid_config_content(universe_path: str, db_path: str = "data/test.db") -> str:
    """Generate valid config YAML content for testing."""
    return f"""
universe_path: {universe_path}
historical_data_years: 2
cache_dir: data/cache
hold_period: 20
min_trades_threshold: 10
edge_score_weights:
  win_pct: 0.6
  sharpe: 0.4
database_path: {db_path}
reports_output_dir: reports
edge_score_threshold: 0.5
"""


def get_valid_rules_content() -> str:
    """Generate valid rules YAML content for testing."""
    return """
baseline:
  name: sma_crossover
  type: sma_crossover
  params:
    fast: 10
    slow: 20
layers:
  - name: rsi_oversold
    type: rsi_oversold
    params:
      period: 14
      threshold: 30
sell_conditions:
  - name: stop_loss
    type: stop_loss
    params:
      percentage: 0.05
"""


class TestClearAndRecalculateInlineImplementation:
    """Test the new inline implementation of clear-and-recalculate command."""

    @patch("kiss_signal.persistence.clear_and_recalculate_strategies")
    def test_clear_and_recalculate_basic_flow(self, mock_clear_and_recalculate):
        """Test the basic flow of the new inline implementation."""
        with runner.isolated_filesystem() as fs:
            # Setup mock return values
            mock_clear_and_recalculate.return_value = {
                'status': 'success',
                'cleared_count': 5,
                'preserved_count': 10,
                'new_strategies': 2
            }
            
            # Setup test environment
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            persistence.create_database(db_path)

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--force"
            ])
            
            assert result.exit_code == 0
            assert "Cleared: 5 strategies" in result.stdout
            assert "Preserved: 10 historical strategies" in result.stdout
            assert "New strategies found: 2" in result.stdout
            mock_clear_and_recalculate.assert_called_once()

    @patch("kiss_signal.persistence.clear_and_recalculate_strategies")
    def test_preserve_all_mode_skips_clearing(self, mock_clear_and_recalculate):
        """Test that preserve-all mode skips the clearing phase."""
        with runner.isolated_filesystem() as fs:
            # Setup mock return values - simulate preserve-all mode behavior
            mock_clear_and_recalculate.return_value = {
                'status': 'success',
                'cleared_count': 0,  # No clearing in preserve-all mode
                'preserved_count': 0,  # No preservation message in preserve-all mode
                'new_strategies': 1
            }
            
            # Setup test environment
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            persistence.create_database(db_path)

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--preserve-all",
                "--force"
            ])
            
            assert result.exit_code == 0
            assert "Cleared: 0 strategies" in result.stdout
            assert "Preserved: 0 historical strategies" in result.stdout  
            assert "New strategies found: 1" in result.stdout
            mock_clear_and_recalculate.assert_called_once()

    @patch("kiss_signal.persistence.clear_and_recalculate_strategies")
    def test_freeze_date_handling(self, mock_clear_and_recalculate):
        """Test that freeze date is properly parsed and passed through."""
        with runner.isolated_filesystem() as fs:
            # Setup mock return values
            mock_clear_and_recalculate.return_value = {
                'status': 'success',
                'cleared_count': 2,
                'preserved_count': 5,
                'new_strategies': 0
            }
            
            # Setup test environment
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            persistence.create_database(db_path)

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--freeze-data", "2024-01-15",
                "--force"
            ])
            
            assert result.exit_code == 0
            
            # Verify clear_and_recalculate_strategies was called with the correct freeze_date
            mock_clear_and_recalculate.assert_called_once()
            call_args = mock_clear_and_recalculate.call_args
            # Check that freeze_date parameter was passed correctly
            assert 'freeze_date' in call_args.kwargs
            assert call_args.kwargs['freeze_date'] == "2024-01-15"

    @patch("kiss_signal.cli.persistence.get_connection")
    def test_database_error_handling(self, mock_get_connection):
        """Test proper error handling for database operations."""
        with runner.isolated_filesystem() as fs:
            mock_get_connection.side_effect = sqlite3.Error("Database connection failed")
            # Setup test environment
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            persistence.create_database(db_path)

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--force"
            ])
            
            assert result.exit_code == 1
            assert "An unexpected error occurred" in result.stdout




    def test_missing_database_file(self):
        """Test error handling when database file doesn't exist."""
        with runner.isolated_filesystem() as fs:
            # Setup test environment without creating database
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path), "data/nonexistent.db"))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--force"
            ])
            
            assert result.exit_code == 1
            assert "Database file not found" in result.stdout

    @patch("kiss_signal.cli.console.export_text")
    @patch("kiss_signal.cli.persistence.get_connection")
    def test_log_file_creation(self, mock_get_connection, mock_export_text):
        """Test that log files are created properly even on errors."""
        with runner.isolated_filesystem() as fs:
            # Setup test environment
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text(get_valid_rules_content())
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            persistence.create_database(db_path)

            # Mock export_text to return log content
            mock_export_text.return_value = "Test log content"
            
            # Mock database connection to raise an exception
            mock_get_connection.side_effect = Exception("Test error")

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--force"
            ])
            
            assert result.exit_code == 1
            
            # Verify log file creation was attempted
            mock_export_text.assert_called_once_with(clear=False)
            
            # Check that log file exists
            log_file = Path(fs) / "clear_and_recalculate_log.txt"
            assert log_file.exists()
            assert log_file.read_text() == "Test log content"


class TestConfigIntegration:
    """Test integration with config module functions."""

    def test_get_active_strategy_combinations_called(self):
        """Test that get_active_strategy_combinations is properly imported and called."""
        from kiss_signal.config import get_active_strategy_combinations, RulesConfig, RuleDef
        
        # Create test rules config
        rules_config = RulesConfig(
            baseline=RuleDef(name="test", type="sma_crossover", params={"fast": 10, "slow": 20}),
            layers=[
                RuleDef(name="rsi", type="rsi_oversold", params={"period": 14, "threshold": 30})
            ]
        )
        
        # Test the function directly
        combinations = get_active_strategy_combinations(rules_config)
        
        assert len(combinations) == 2  # baseline + baseline+layer
        assert all(isinstance(combo, str) for combo in combinations)
        
        # Verify JSON structure
        for combo in combinations:
            parsed = json.loads(combo)
            assert isinstance(parsed, list)
            assert all(isinstance(rule, dict) for rule in parsed)
            assert all("name" in rule and "type" in rule and "params" in rule for rule in parsed)