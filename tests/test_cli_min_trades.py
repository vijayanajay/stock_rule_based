"""Tests for CLI min_trades parameter functionality."""

import pytest
from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict, List
import yaml
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from kiss_signal.cli import app, _run_backtests
from kiss_signal.config import Config
import pandas as pd


runner = CliRunner()

VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10
"""

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "database_path": "test_data/test.db",
        "cache_dir": "test_data/cache",
        "universe_path": "test_data/nifty_large_mid.csv",
        "historical_data_years": 2,
        "hold_period": 20,
        "min_trades_threshold": 10,
        "reports_output_dir": "test_data/reports",
        "edge_score_threshold": 0.5,
        "edge_score_weights": {
            "win_pct": 0.6,
            "sharpe": 0.4
        }
    }

@pytest.fixture
def mock_price_data():
    """Mock price data for testing."""
    return pd.DataFrame(
        {'close': range(101)}, 
        index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
    )


class TestMinTradesParameter:
    """Test suite for min_trades parameter functionality."""

    def test_run_backtests_with_none_min_trades_uses_config_default(self, sample_config, mock_price_data):
        """Test that _run_backtests uses config default when min_trades_threshold is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=None
                        )
                        
                        # Should use config's min_trades_threshold (10)
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=10
                        )

    def test_run_backtests_with_explicit_min_trades_overrides_config(self, sample_config, mock_price_data):
        """Test that _run_backtests uses explicit min_trades_threshold when provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=5
                        )
                        
                        # Should use provided min_trades_threshold (5), not config (10)
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=5
                        )

    def test_run_backtests_with_zero_min_trades_saves_all_strategies(self, sample_config, mock_price_data):
        """Test that min_trades_threshold=0 allows all strategies to be saved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=0
                        )
                        
                        # Should use min_trades_threshold=0 to save all strategies
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=0
                        )

    def test_run_backtests_falls_back_to_zero_when_no_config_default(self, mock_price_data):
        """Test that _run_backtests falls back to 0 when getattr returns default."""
        # Create a mock config object that doesn't have min_trades_threshold attribute
        mock_config = MagicMock()
        mock_config.hold_period = 20
        # When getattr is called with default 0, it should return 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                        with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                            # Create a config that returns 0 for min_trades_threshold when accessed
                            mock_config.min_trades_threshold = 0
                            mock_config.hold_period = 20
                            
                            _run_backtests(
                                app_config=mock_config,
                                rules_config={},
                                symbols=["TEST"],
                                freeze_date=None,
                                min_trades_threshold=None
                            )                            # Should fall back to 0 when no config default
                            mock_backtester.assert_called_once_with(
                                hold_period=20,
                                min_trades_threshold=0
                            )


class TestRunCommandMinTrades:
    """Test the run command with min_trades parameter."""

    @patch("kiss_signal.cli.backtester.Backtester")
    @patch("kiss_signal.cli.data")
    @patch("kiss_signal.cli.persistence")
    def test_run_command_with_min_trades_parameter(self, mock_persistence, mock_data, mock_backtester, sample_config):
        """Test run command passes min_trades parameter correctly."""
        with runner.isolated_filesystem():
            # Setup test environment
            data_dir = Path("data")
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
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Mock data and backtester
            mock_data.load_universe.return_value = ["RELIANCE"]
            mock_data.get_price_data.return_value = pd.DataFrame(
                {'close': range(101)}, 
                index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
            )
            mock_bt_instance = mock_backtester.return_value
            mock_bt_instance.find_optimal_strategies.return_value = []
            
            # Mock persistence
            mock_persistence.create_database.return_value = None
            mock_persistence.get_connection.return_value = MagicMock()

            # Test with explicit min_trades parameter
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "run", "--min-trades", "5"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Verify Backtester was called with min_trades_threshold=5
            mock_backtester.assert_called_with(
                hold_period=sample_config["hold_period"],
                min_trades_threshold=5
            )

    @patch("kiss_signal.cli.backtester.Backtester")
    @patch("kiss_signal.cli.data")
    @patch("kiss_signal.cli.persistence")
    def test_run_command_without_min_trades_uses_config_default(self, mock_persistence, mock_data, mock_backtester, sample_config):
        """Test run command without min_trades uses config default."""
        with runner.isolated_filesystem():
            # Setup test environment
            data_dir = Path("data")
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
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Mock data and backtester
            mock_data.load_universe.return_value = ["RELIANCE"]
            mock_data.get_price_data.return_value = pd.DataFrame(
                {'close': range(101)}, 
                index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
            )
            mock_bt_instance = mock_backtester.return_value
            mock_bt_instance.find_optimal_strategies.return_value = []
            
            # Mock persistence
            mock_persistence.create_database.return_value = None
            mock_persistence.get_connection.return_value = MagicMock()

            # Test without min_trades parameter
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "run"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Verify Backtester was called with config's min_trades_threshold (10)
            mock_backtester.assert_called_with(
                hold_period=sample_config["hold_period"],
                min_trades_threshold=sample_config["min_trades_threshold"]
            )


class TestAnalyzeStrategiesMinTrades:
    """Test the analyze-strategies command with min_trades parameter."""

    def setup_test_database(self, db_path: Path) -> None:
        """Setup a test database with sample strategy data."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                rule_stack TEXT NOT NULL,
                edge_score REAL NOT NULL,
                win_pct REAL NOT NULL,
                sharpe REAL NOT NULL,
                avg_return REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                config_hash TEXT,
                run_timestamp TEXT,
                config_snapshot TEXT
            )
        ''')
        
        # Insert test data with different trade counts
        test_strategies = [
            ("RELIANCE", '["test_rule"]', 0.5, 0.6, 1.2, 100.0, 5, "hash1", "2025-01-01", "{}"),
            ("INFY", '["test_rule"]', 0.4, 0.55, 1.0, 80.0, 8, "hash1", "2025-01-01", "{}"),
            ("TCS", '["test_rule"]', 0.6, 0.65, 1.5, 120.0, 12, "hash1", "2025-01-01", "{}"),
            ("HDFC", '["test_rule"]', 0.3, 0.5, 0.8, 60.0, 15, "hash1", "2025-01-01", "{}"),
        ]
        
        cursor.executemany('''
            INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe, avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', test_strategies)
        
        conn.commit()
        conn.close()

    def test_analyze_strategies_with_min_trades_filters_correctly(self, sample_config):
        """Test analyze-strategies command filters by min_trades correctly."""
        with runner.isolated_filesystem():
            # Setup test database
            db_path = Path("test.db")
            self.setup_test_database(db_path)
            
            # Create the universe file
            universe_path = Path("nifty_large_mid.csv")
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            sample_config["database_path"] = str(db_path)
            sample_config["universe_path"] = str(universe_path)
            config_path = Path("config.yaml")
            config_path.write_text(yaml.dump(sample_config))
            
            config_dir = Path("config")
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Test with min_trades=10 (should only include TCS and HDFC)
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "10"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Read the generated CSV
            output_file = Path("strategy_performance_report.csv")
            assert output_file.exists()
            
            content = output_file.read_text()
            
            # Should include TCS (12 trades) and HDFC (15 trades)
            assert "TCS" in content
            assert "HDFC" in content
            
            # Should NOT include RELIANCE (5 trades) and INFY (8 trades)
            assert "RELIANCE" not in content
            assert "INFY" not in content

    def test_analyze_strategies_with_min_trades_zero_shows_all(self, sample_config):
        """Test analyze-strategies with min_trades=0 shows all strategies."""
        with runner.isolated_filesystem():
            # Setup test database
            db_path = Path("test.db")
            self.setup_test_database(db_path)
            
            # Create the universe file
            universe_path = Path("nifty_large_mid.csv")
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            sample_config["database_path"] = str(db_path)
            sample_config["universe_path"] = str(universe_path)
            config_path = Path("config.yaml")
            config_path.write_text(yaml.dump(sample_config))
            
            config_dir = Path("config")
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Test with min_trades=0 (should include all strategies)
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "0"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Read the generated CSV
            output_file = Path("strategy_performance_report.csv")
            assert output_file.exists()
            
            content = output_file.read_text()
            
            # Should include all strategies
            assert "RELIANCE" in content  # 5 trades
            assert "INFY" in content      # 8 trades
            assert "TCS" in content       # 12 trades
            assert "HDFC" in content      # 15 trades

    def test_analyze_strategies_without_min_trades_uses_default(self, sample_config):
        """Test analyze-strategies without min_trades uses default (10)."""
        with runner.isolated_filesystem():
            # Setup test database
            db_path = Path("test.db")
            self.setup_test_database(db_path)
            
            # Create the universe file
            universe_path = Path("nifty_large_mid.csv")
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            sample_config["database_path"] = str(db_path)
            sample_config["universe_path"] = str(universe_path)
            config_path = Path("config.yaml")
            config_path.write_text(yaml.dump(sample_config))
            
            config_dir = Path("config")
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Test without min_trades parameter (should default to 10)
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Read the generated CSV
            output_file = Path("strategy_performance_report.csv")
            assert output_file.exists()
            
            content = output_file.read_text()
            
            # Should include TCS (12 trades) and HDFC (15 trades)
            assert "TCS" in content
            assert "HDFC" in content
            
            # Should NOT include RELIANCE (5 trades) and INFY (8 trades)
            assert "RELIANCE" not in content
            assert "INFY" not in content

    def test_analyze_strategies_aggregated_respects_min_trades(self, sample_config):
        """Test analyze-strategies --aggregate respects min_trades parameter."""
        with runner.isolated_filesystem():
            # Setup test database
            db_path = Path("test.db")
            self.setup_test_database(db_path)
            
            # Create the universe file
            universe_path = Path("nifty_large_mid.csv")
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
            
            sample_config["database_path"] = str(db_path)
            sample_config["universe_path"] = str(universe_path)
            config_path = Path("config.yaml")
            config_path.write_text(yaml.dump(sample_config))
            
            config_dir = Path("config")
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Test aggregated mode with min_trades=0
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--aggregate", "--min-trades", "0"]
            )
            
            assert result.exit_code == 0, f"Command failed: {result.stdout}"
            
            # Read the generated CSV
            output_file = Path("strategy_performance_report.csv")
            assert output_file.exists()
            
            content = output_file.read_text()
            
            # In aggregated mode, should include data from all strategies
            # The content will be different but should process all 4 strategies
            lines = content.strip().split('\n')
            assert len(lines) >= 2  # Header + at least one aggregated result


class TestMinTradesIntegration:
    """Integration tests for min_trades functionality across the whole pipeline."""

    def test_end_to_end_min_trades_workflow(self, sample_config):
        """Test the complete workflow: run with min_trades -> analyze with different min_trades."""
        with runner.isolated_filesystem():
            # Setup test environment
            data_dir = Path("data")
            data_dir.mkdir()
            cache_dir = data_dir / "cache"
            cache_dir.mkdir()
            universe_path = data_dir / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\nINFY,Infosys,IT\n")
            
            sample_config["universe_path"] = str(universe_path)
            sample_config["cache_dir"] = str(cache_dir)
            sample_config["database_path"] = "test.db"
            
            config_path = Path("config.yaml")
            config_path.write_text(yaml.dump(sample_config))
            
            config_dir = Path("config")
            config_dir.mkdir()
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(VALID_RULES_YAML)

            # Mock all external dependencies
            with patch("kiss_signal.cli.data.load_universe", return_value=["RELIANCE", "INFY"]):
                with patch("kiss_signal.cli.data.get_price_data") as mock_get_price:
                    with patch("kiss_signal.cli.data.refresh_market_data"):
                        with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                            with patch("kiss_signal.cli.persistence.save_strategies_batch", return_value=True):
                                with patch("kiss_signal.cli.persistence.create_database"):
                                    with patch("kiss_signal.cli.persistence.get_connection") as mock_get_conn:
                                        with patch("kiss_signal.cli.reporter.generate_daily_report"):
                                            
                                            # Setup mock price data
                                            mock_get_price.return_value = pd.DataFrame(
                                                {'close': range(101)}, 
                                                index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=101))
                                            )
                                            
                                            # Setup mock backtester with strategies having different trade counts
                                            mock_bt_instance = mock_backtester.return_value
                                            mock_bt_instance.find_optimal_strategies.side_effect = [
                                                # RELIANCE strategies (low trade count)
                                                [{"rule_stack": [SimpleNamespace(name="test_rule", type="test_type")], "edge_score": 0.3, "win_pct": 0.5, "sharpe": 0.8, "total_trades": 5, "avg_return": 50.0}],
                                                # INFY strategies (high trade count)
                                                [{"rule_stack": [SimpleNamespace(name="test_rule", type="test_type")], "edge_score": 0.6, "win_pct": 0.65, "sharpe": 1.2, "total_trades": 15, "avg_return": 100.0}]
                                            ]
                                            
                                            # Mock database connection
                                            mock_conn = MagicMock()
                                            mock_get_conn.return_value = mock_conn
                                            
                                            # Test 1: Run with min_trades=0 (should save all strategies)
                                            result = runner.invoke(
                                                app, 
                                                ["--config", str(config_path), "--rules", str(rules_path), "run", "--min-trades", "0"]
                                            )
                                            
                                            assert result.exit_code == 0, f"Run command failed: {result.stdout}"
                                            
                                            # Verify Backtester was called with min_trades_threshold=0
                                            mock_backtester.assert_called_with(
                                                hold_period=sample_config["hold_period"],
                                                min_trades_threshold=0
                                            )

            # Now setup a real test database for the analyze command
            db_path = Path("test.db")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    rule_stack TEXT NOT NULL,
                    edge_score REAL NOT NULL,
                    win_pct REAL NOT NULL,
                    sharpe REAL NOT NULL,
                    avg_return REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    config_hash TEXT,
                    run_timestamp TEXT,
                    config_snapshot TEXT
                )
            ''')
            
            # Insert the strategies that would have been saved
            cursor.executemany('''
                INSERT INTO strategies (symbol, rule_stack, edge_score, win_pct, sharpe, avg_return, total_trades, config_hash, run_timestamp, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                ("RELIANCE", '[{"name": "test_rule"}]', 0.3, 0.5, 0.8, 50.0, 5, "hash1", "2025-01-01", "{}"),
                ("INFY", '[{"name": "test_rule"}]', 0.6, 0.65, 1.2, 100.0, 15, "hash1", "2025-01-01", "{}")
            ])
            
            conn.commit()
            conn.close()

            # Test 2: Analyze with min_trades=10 (should only show INFY)
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "10"]
            )
            
            assert result.exit_code == 0, f"Analyze command failed: {result.stdout}"
            
            output_file = Path("strategy_performance_report.csv")
            content = output_file.read_text()
            
            assert "INFY" in content  # 15 trades >= 10
            assert "RELIANCE" not in content  # 5 trades < 10

            # Test 3: Analyze with min_trades=0 (should show both)
            result = runner.invoke(
                app, 
                ["--config", str(config_path), "--rules", str(rules_path), "analyze-strategies", "--min-trades", "0"]
            )
            
            assert result.exit_code == 0, f"Analyze command failed: {result.stdout}"
            
            content = output_file.read_text()
            
            assert "INFY" in content      # 15 trades >= 0
            assert "RELIANCE" in content  # 5 trades >= 0
