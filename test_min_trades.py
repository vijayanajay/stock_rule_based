"""Additional tests for min-trades functionality."""

from typer.testing import CliRunner
from pathlib import Path
import yaml
from unittest.mock import patch
from kiss_signal.cli import app
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


@patch("kiss_signal.cli.reporter.analyze_strategy_performance")
@patch("kiss_signal.cli.persistence.get_connection")
def test_analyze_strategies_command_min_trades_filter(mock_get_connection, mock_analyze):
    """Test analyze-strategies command with --min-trades parameter."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        # Mock strategy data with different trade counts
        mock_analyze.return_value = [
            {
                'symbol': 'TEST1',
                'strategy_rule_stack': 'high_trade_strategy',
                'edge_score': 0.6,
                'win_pct': 0.65,
                'sharpe': 1.2,
                'total_return': 0.05,
                'total_trades': 15,  # Above default threshold
                'config_hash': 'test_hash',
                'run_date': '2025-07-21',
                'config_details': '{"test": true}'
            },
            {
                'symbol': 'TEST2',
                'strategy_rule_stack': 'low_trade_strategy',
                'edge_score': 0.8,
                'win_pct': 0.75,
                'sharpe': 1.5,
                'total_return': 0.08,
                'total_trades': 5,  # Below default threshold
                'config_hash': 'test_hash',
                'run_date': '2025-07-21',
                'config_details': '{"test": true}'
            }
        ]
        
        # Setup database and config
        config_path = fs_path / "config.yaml"
        db_path = fs_path / "test.db"
        persistence.create_database(db_path)
        
        dummy_universe_file = fs_path / "dummy.csv"
        dummy_universe_file.write_text("symbol\nTEST1\nTEST2\n")
        
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
        
        # Test with default min-trades (should use default 10)
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"])
        assert result.exit_code == 0, result.stdout
        mock_analyze.assert_called_with(db_path, min_trades=10)
        
        # Test with custom min-trades (should include low-trade strategies)
        mock_analyze.reset_mock()
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "3"])
        assert result.exit_code == 0, result.stdout
        mock_analyze.assert_called_with(db_path, min_trades=3)
        
        # Test with min-trades = 0 (show all)
        mock_analyze.reset_mock()
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "0"])
        assert result.exit_code == 0, result.stdout
        mock_analyze.assert_called_with(db_path, min_trades=0)


@patch("kiss_signal.cli.reporter.analyze_strategy_performance_aggregated")
@patch("kiss_signal.cli.persistence.get_connection")
def test_analyze_strategies_command_min_trades_aggregated(mock_get_connection, mock_analyze):
    """Test analyze-strategies command with --min-trades parameter in aggregated mode."""
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        
        mock_analyze.return_value = [{
            'strategy_rule_stack': 'test_strategy',
            'frequency': 3,
            'avg_edge_score': 0.7,
            'avg_win_pct': 0.68,
            'avg_sharpe': 1.3,
            'avg_return': 0.06,
            'avg_trades': 8.0,
            'top_symbols': 'TEST1 (1), TEST2 (1), TEST3 (1)',
            'config_hash': 'test_hash',
            'run_date': '2025-07-21',
            'config_details': '{"test": true}'
        }]
        
        # Setup database and config
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
        
        # Test aggregated mode with custom min-trades
        result = runner.invoke(app, ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--aggregate", "--min-trades", "5"])
        assert result.exit_code == 0, result.stdout
        mock_analyze.assert_called_with(db_path, min_trades=5)
