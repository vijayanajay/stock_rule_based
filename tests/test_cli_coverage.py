"""Tests for CLI module - Coverage enhancement to reach 90%+.

Following KISS principles: small, focused tests targeting uncovered lines.
"""

from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import pytest
from rich.console import Console

from kiss_signal.cli import app, _show_banner, _create_progress_context
from kiss_signal.config import RuleDef


runner = CliRunner()


def get_valid_config_content(universe_path: str, db_path: str = "data/test.db") -> str:
    """Helper to create valid config content with proper edge score weights."""
    return f"""
cache_dir: data
database_path: {db_path}
universe_path: {universe_path}
freeze_date: null
historical_data_years: 3
cache_refresh_days: 1
hold_period: 20
min_trades_threshold: 10
edge_score_threshold: 0.5
reports_output_dir: reports
edge_score_weights:
  win_pct: 0.6
  sharpe: 0.4
"""


class TestCLIHelperFunctions:
    """Test uncovered helper functions."""

    def test_show_banner_function(self) -> None:
        """Test _show_banner function displays correctly."""
        console = Console(record=True)
        with patch('kiss_signal.cli.console', console):
            _show_banner()
            output = console.export_text()
            assert "KISS Signal CLI" in output
            assert "QuickEdge" in output

    def test_create_progress_context(self) -> None:
        """Test _create_progress_context creates progress object."""
        progress = _create_progress_context()
        assert progress is not None
        # Test that it's a proper progress object
        assert hasattr(progress, 'add_task')
        assert hasattr(progress, 'update')


class TestClearAndRecalculateCommand:
    """Test clear-and-recalculate command paths."""

    @patch("kiss_signal.cli.persistence.clear_and_recalculate_strategies")
    def test_clear_and_recalculate_success(self, mock_clear_recalc, sample_config, tmp_path):
        """Test clear-and-recalculate command successful execution."""
        with runner.isolated_filesystem() as fs:
            # Setup test environment with complete config
            config_path = Path(fs) / "config.yaml"
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")
            
            # Create database file
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            from kiss_signal import persistence
            persistence.create_database(db_path)
            
            mock_clear_recalc.return_value = {
                'cleared_count': 5, 'preserved_count': 10, 'new_strategies': 8
            }

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--force"
            ])
            
            assert result.exit_code == 0
            assert "Cleared: 5 strategies" in result.stdout
            mock_clear_recalc.assert_called_once()

    def test_clear_and_recalculate_db_not_found(self, sample_config, tmp_path):
        """Test clear-and-recalculate with missing database."""
        with runner.isolated_filesystem() as fs:
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path), "data/nonexistent.db"))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate"
            ])
            
            assert result.exit_code == 1
            assert "Database file not found" in result.stdout

    @patch("kiss_signal.cli.persistence.clear_and_recalculate_strategies")
    def test_clear_and_recalculate_with_freeze_date(self, mock_clear_recalc, sample_config, tmp_path):
        """Test clear-and-recalculate with freeze date option."""
        with runner.isolated_filesystem() as fs:
            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            from kiss_signal import persistence
            persistence.create_database(db_path)
            
            mock_clear_recalc.return_value = {'cleared_count': 0, 'preserved_count': 0, 'new_strategies': 0}

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate",
                "--freeze-data", "2024-01-01",
                "--preserve-all"
            ])
            
            assert result.exit_code == 0
            mock_clear_recalc.assert_called_once()
            assert mock_clear_recalc.call_args[1]['preserve_all'] is True
            assert mock_clear_recalc.call_args[1]['freeze_date'] == "2024-01-01"


class TestAnalyzeSymbolHelperFunction:
    """Test _analyze_symbol helper function edge cases."""

    @patch("kiss_signal.cli.data.get_price_data")
    def test_analyze_symbol_none_price_data(self, mock_get_price_data, sample_config):
        """Test _analyze_symbol when get_price_data returns None."""
        from kiss_signal.cli import _analyze_symbol
        from kiss_signal import backtester
        
        mock_get_price_data.return_value = None
        bt = backtester.Backtester()
        
        result = _analyze_symbol(
            symbol="TEST",
            app_config=sample_config,
            rules_config={"baseline": {"type": "sma_crossover"}},
            freeze_date=None,
            bt=bt
        )
        
        assert result == []

    @patch("kiss_signal.cli.data.get_price_data")
    def test_analyze_symbol_insufficient_data(self, mock_get_price_data, sample_config):
        """Test _analyze_symbol with insufficient data."""
        from kiss_signal.cli import _analyze_symbol
        from kiss_signal import backtester
        import pandas as pd
        
        # Create small dataframe with insufficient data
        small_df = pd.DataFrame({'Close': [100, 101, 102]})
        mock_get_price_data.return_value = small_df
        
        bt = backtester.Backtester()
        
        result = _analyze_symbol(
            symbol="TEST",
            app_config=sample_config,
            rules_config={"baseline": {"type": "sma_crossover"}},
            freeze_date=None,
            bt=bt
        )
        
        assert result == []


class TestPerformanceMonitoringPaths:
    """Test performance monitoring code paths."""

    @patch("kiss_signal.cli.performance_monitor.get_summary")
    @patch("kiss_signal.cli._run_backtests")
    def test_run_command_with_performance_summary(self, mock_run_backtests, mock_get_summary, sample_config):
        """Test run command with verbose flag to trigger performance summary."""
        with runner.isolated_filesystem() as fs:
            mock_run_backtests.return_value = []
            mock_get_summary.return_value = {
                'total_duration': 1.5,
                'slowest_function': 'test_function'
            }

            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            # Create universe file with proper 'symbol' column header
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "--verbose",
                "run"
            ])
            
            assert "Performance Summary" in result.stdout
            assert "Total Duration: 1.50s" in result.stdout
            assert "test_function" in result.stdout


class TestLogFileCreationErrorHandling:
    """Test log file creation error handling paths."""

    @patch("kiss_signal.cli.console.export_text")
    @patch("kiss_signal.cli._run_backtests")
    def test_run_command_log_file_error_handling(self, mock_run_backtests, mock_export_text, sample_config):
        """Test run command handles log file creation errors gracefully."""
        with runner.isolated_filesystem() as fs:
            mock_run_backtests.return_value = []
            mock_export_text.return_value = "Test log content"

            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            # Create universe file with proper 'symbol' column header
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")
            
            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")

            # Mock Path.write_text to raise OSError
            with patch("pathlib.Path.write_text") as mock_write:
                mock_write.side_effect = OSError("Permission denied")
                
                result = runner.invoke(app, [
                    "--config", str(config_path),
                    "--rules", str(rules_path),
                    "run"
                ])
                
                # Should still succeed despite log file error
                assert "Critical error: Could not save log file" in result.stdout

    @patch("kiss_signal.cli.console.export_text")
    @patch("pathlib.Path.exists")
    def test_analyze_strategies_log_file_error_handling(self, mock_path_exists, mock_export_text, sample_config):
        """Test analyze-strategies command handles log file creation errors."""
        with runner.isolated_filesystem() as fs:
            mock_export_text.return_value = "Test log content"
            # Mock Path.exists to return True for database check to pass initial validation
            mock_path_exists.return_value = True

            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            # Create universe file with proper 'symbol' column header
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")

            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path), "data/nonexistent.db"))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")

            # Mock Path.write_text to raise OSError
            with patch("pathlib.Path.write_text") as mock_write:
                mock_write.side_effect = OSError("Disk full")
                
                result = runner.invoke(app, [
                    "--config", str(config_path),
                    "--rules", str(rules_path),
                    "analyze-strategies"
                ])
                
                assert "Critical error: Could not save log file" in result.stdout


class TestDisplayResultsFunction:
    """Test _display_results function edge cases."""

    def test_display_results_with_strategies(self, sample_config):
        """Test _display_results with actual strategy data."""
        from kiss_signal.cli import _display_results
        from rich.console import Console
        
        strategies = [
            {
                "symbol": "TEST1", 
                "rule_stack": [RuleDef(type='sma_crossover', name='sma_test', params={})],
                "edge_score": 0.85,
                "win_pct": 0.6,
                "sharpe": 1.2,
                "total_trades": 15
            },
            {
                "symbol": "TEST2",
                "rule_stack": [RuleDef(type='rsi_oversold', name='rsi_test', params={})],
                "edge_score": 0.75,
                "win_pct": 0.55,
                "sharpe": 0.9,
                "total_trades": 12
            }
        ]
        
        console = Console(record=True)
        with patch('kiss_signal.cli.console', console):
            _display_results(strategies)
            output = console.export_text()
            assert "Top Strategies by Edge Score" in output
            assert "TEST1" in output
            assert "0.850" in output  # edge_score formatted
            assert "Analysis complete" in output


class TestMainCallbackEdgeCases:
    """Test main callback function edge cases."""

    def test_main_callback_resilient_parsing(self):
        """Test main callback with resilient parsing enabled."""
        from kiss_signal.cli import main
        
        # Create a mock context with resilient_parsing=True
        class MockContext:
            def __init__(self):
                self.resilient_parsing = True
        
        ctx = MockContext()
        
        # Should return early without any processing
        result = main(ctx, "config.yaml", "rules.yaml", False)
        assert result is None

    def test_main_callback_config_loading_error(self):
        """Test main callback handles config loading errors."""
        from kiss_signal.cli import main
        import typer
        
        # Create a mock context with resilient_parsing=False
        class MockContext:
            def __init__(self):
                self.resilient_parsing = False
                self.obj = None
        
        ctx = MockContext()
        
        # This should raise typer.Exit(1) due to file not found
        with pytest.raises(typer.Exit):
            main(ctx, "nonexistent_config.yaml", "nonexistent_rules.yaml", False)


class TestClearAndRecalculateErrorHandling:
    """Test clear-and-recalculate command error handling."""

    @patch("kiss_signal.cli.persistence.get_connection")
    def test_clear_and_recalculate_exception_handling(self, mock_get_connection, sample_config):
        """Test clear-and-recalculate handles exceptions properly."""
        with runner.isolated_filesystem() as fs:
            mock_get_connection.side_effect = ValueError("Database corruption")

            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")

            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))
            
            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")
            
            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            from kiss_signal import persistence
            persistence.create_database(db_path)

            result = runner.invoke(app, [
                "--config", str(config_path),
                "--rules", str(rules_path),
                "clear-and-recalculate"
            ])
            
            assert result.exit_code == 1
            assert "An unexpected error occurred" in result.stdout

    @patch("kiss_signal.cli.persistence.clear_and_recalculate_strategies")
    @patch("kiss_signal.cli.persistence.get_connection")
    @patch("kiss_signal.cli.console.export_text")
    def test_clear_and_recalculate_log_file_error(self, mock_export_text, mock_get_connection, mock_clear_recalc, sample_config):
        """Test clear-and-recalculate log file error handling."""
        with runner.isolated_filesystem() as fs:
            mock_export_text.return_value = "Test log content"

            universe_path = Path(fs) / "data" / "universe.csv"
            universe_path.parent.mkdir(exist_ok=True)
            universe_path.write_text("symbol\nRELIANCE\nINFY\n")

            config_path = Path(fs) / "config.yaml"
            config_path.write_text(get_valid_config_content(str(universe_path)))

            rules_path = Path(fs) / "config" / "rules.yaml"
            rules_path.parent.mkdir(exist_ok=True)
            rules_path.write_text("baseline:\n  name: test\n  type: sma_crossover\n  params: {fast: 5, slow: 10}")

            db_path = Path(fs) / "data" / "test.db"
            db_path.parent.mkdir(exist_ok=True)
            from kiss_signal import persistence
            persistence.create_database(db_path)

            # Mock database connection
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [0]  # no records to delete
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_get_connection.return_value = mock_conn

            # Mock persistence clear_and_recalculate_strategies to return success
            mock_clear_recalc.return_value = {
                'cleared_count': 0,
                'preserved_count': 0,
                'new_strategies': 0
            }            # Mock Path.write_text to raise OSError
            with patch("pathlib.Path.write_text") as mock_write:
                mock_write.side_effect = OSError("No space left")
                
                result = runner.invoke(app, [
                    "--config", str(config_path),
                    "--rules", str(rules_path),
                    "clear-and-recalculate"
                ])
                
                assert "Critical error: Could not save log file" in result.stdout


class TestProcessAndSaveResultsFunction:
    """Test _process_and_save_results helper function."""

    @patch("kiss_signal.cli.persistence.generate_config_hash")
    @patch("kiss_signal.cli.persistence.create_config_snapshot")
    @patch("kiss_signal.cli._display_results")
    @patch("kiss_signal.cli._save_results")
    @patch("kiss_signal.cli._generate_and_save_report")
    def test_process_and_save_results_with_rules_model_dump(
        self, mock_generate_report, mock_save_results, mock_display_results,
        mock_create_snapshot, mock_generate_hash
    ):
        """Test _process_and_save_results with rules_config having model_dump method."""
        from kiss_signal.cli import _process_and_save_results
        from unittest.mock import MagicMock
        
        # Create mock db connection
        db_connection = MagicMock()
        
        # Create mock app_config with all required attributes
        app_config = MagicMock()
        app_config.freeze_date = None
        
        # Create mock rules_config with model_dump method
        rules_config = MagicMock()
        rules_config.model_dump.return_value = {"baseline": {"type": "test"}}
        
        # Mock the persistence functions
        mock_create_snapshot.return_value = {"config": "snapshot"}
        mock_generate_hash.return_value = "testhash123"
        
        all_results = [{"symbol": "TEST", "edge_score": 0.8}]
        
        _process_and_save_results(db_connection, all_results, app_config, rules_config)
        
        mock_display_results.assert_called_once_with(all_results)
        mock_save_results.assert_called_once()
        mock_generate_report.assert_called_once()
        rules_config.model_dump.assert_called_once()

    @patch("kiss_signal.cli.persistence.generate_config_hash")
    @patch("kiss_signal.cli.persistence.create_config_snapshot")
    @patch("kiss_signal.cli._display_results")
    @patch("kiss_signal.cli._save_results")
    @patch("kiss_signal.cli._generate_and_save_report")
    def test_process_and_save_results_without_model_dump(
        self, mock_generate_report, mock_save_results, mock_display_results,
        mock_create_snapshot, mock_generate_hash
    ):
        """Test _process_and_save_results with rules_config without model_dump method."""
        from kiss_signal.cli import _process_and_save_results
        from unittest.mock import MagicMock
        
        # Create mock db connection
        db_connection = MagicMock()
        
        # Create mock app_config with all required attributes
        app_config = MagicMock()
        app_config.freeze_date = None
        
        # Mock the persistence functions
        mock_create_snapshot.return_value = {"config": "snapshot"}
        mock_generate_hash.return_value = "testhash123"
        
        rules_config = {"baseline": {"type": "test"}}  # Plain dict without model_dump
        all_results = [{"symbol": "TEST", "edge_score": 0.8}]
        
        _process_and_save_results(db_connection, all_results, app_config, rules_config)
        
        mock_display_results.assert_called_once_with(all_results)
        mock_save_results.assert_called_once()
        mock_generate_report.assert_called_once()
