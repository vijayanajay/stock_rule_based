"""
Comprehensive test suite for CLI integration and error handling.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner
import pandas as pd
from io import StringIO

from src.meqsap.cli import app
from src.meqsap.config import StrategyConfig
from src.meqsap.exceptions import ConfigurationError
from src.meqsap.data import DataError
from src.meqsap.backtest import BacktestError, BacktestAnalysisResult, BacktestResult
from src.meqsap.reporting import ReportingError
from src.meqsap.exceptions import MEQSAPError


class TestConfigurationErrorScenarios:
    """Test various configuration error scenarios and recovery suggestions."""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_missing_required_fields(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""ticker: "AAPL" # Missing strategy_type, start_date, end_date""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            # For handled errors in _main_pipeline leading to typer.Exit,
            # _generate_error_message is NOT called by analyze_command's main except block.
            # Stdout will only contain what was printed before the exit.
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_invalid_date_formats(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "invalid-date-format"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_invalid_parameter_ranges(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: { "fast_ma": -5, "slow_ma": 20 }""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_malformed_yaml_syntax(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
  start_date: "2023-01-01" # Malformed
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_circular_date_range(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-12-31"
end_date: "2023-01-01"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)

class TestDataAcquisitionErrorScenarios:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('src.meqsap.cli.fetch_market_data')
    def test_network_connection_failure(self, mock_fetch_market_data):
        mock_fetch_market_data.side_effect = DataError("Connection timeout")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "GOODTICKER"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 2, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Fetching market data for GOODTICKER" in result.stdout
        finally:
            os.unlink(config_file)
    
    @patch('src.meqsap.cli.validate_config')
    @patch('src.meqsap.cli.load_yaml_config')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_invalid_ticker_symbol(self, mock_fetch_market_data, mock_load_yaml, mock_validate_config):
        mock_config_obj = Mock(spec=StrategyConfig)
        mock_config_obj.strategy_type = "MovingAverageCrossover"
        mock_config_obj.ticker = "MOCKFAIL"
        mock_config_obj.start_date = date(2023,1,1)
        mock_config_obj.end_date = date(2023,12,31)
        mock_config_obj.validate_strategy_params.return_value = Mock()

        mock_load_yaml.return_value = {"ticker": "MOCKFAIL", "strategy_type": "MovingAverageCrossover", "start_date": "2023-01-01", "end_date": "2023-12-31"}
        mock_validate_config.return_value = mock_config_obj

        mock_fetch_market_data.side_effect = DataError("No data found for symbol MOCKFAIL")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "MOCKFAIL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 2, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Fetching market data for MOCKFAIL" in result.stdout
        finally:
            os.unlink(config_file)
    
    @patch('src.meqsap.cli.run_complete_backtest')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_insufficient_data_period(self, mock_fetch_market_data, mock_run_complete_backtest):
        mock_fetch_market_data.return_value = pd.DataFrame({'Open': [100], 'Close': [100]})
        mock_run_complete_backtest.side_effect = BacktestError("Insufficient data points for MA 50/100")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-01-02"
strategy_params: {"fast_ma": 50, "slow_ma": 100}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 3, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Running backtest analysis..." in result.stdout
        finally:
            os.unlink(config_file)
    
    @patch('src.meqsap.cli.fetch_market_data')
    def test_api_rate_limiting(self, mock_fetch_market_data):
        mock_fetch_market_data.side_effect = DataError("Rate limit exceeded")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 2, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Fetching market data for AAPL" in result.stdout
        finally:
            os.unlink(config_file)

class TestBacktestExecutionErrorScenarios:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('src.meqsap.cli.run_complete_backtest')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_mathematical_computation_errors(self, mock_fetch_market_data, mock_run_complete_backtest):
        mock_fetch_market_data.return_value = pd.DataFrame({'Open':[100],'High':[100],'Low':[100],'Close':[100],'Volume':[100]})
        mock_run_complete_backtest.side_effect = BacktestError("Division by zero in Sharpe calculation")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 3, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Running backtest analysis..." in result.stdout
        finally:
            os.unlink(config_file)
    
    @patch('src.meqsap.cli.run_complete_backtest')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_memory_exhaustion_errors(self, mock_fetch_market_data, mock_run_complete_backtest):
        mock_fetch_market_data.return_value = pd.DataFrame({'Close': [100, 101, 102]})
        mock_run_complete_backtest.side_effect = MemoryError("Not enough memory")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 3, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Running backtest analysis..." in result.stdout # Check for earlier message
            # The specific "Not enough memory" will be in suggestions if _generate_error_message was called
            # but for exit code 3 from _main_pipeline, it's not.
        finally:
            os.unlink(config_file)
    
    @patch('src.meqsap.cli.validate_config')
    @patch('src.meqsap.cli.load_yaml_config')
    def test_invalid_strategy_parameters(self, mock_load_yaml_config, mock_validate_config):
        mock_load_yaml_config.return_value = {
            "strategy_type": "MovingAverageCrossover", "ticker": "AAPL",
            "start_date": "2023-01-01", "end_date": "2023-12-31",
            "strategy_params": {"fast_ma": 50, "slow_ma": 10}        }
        mock_validate_config.side_effect = ConfigurationError("Fast MA (50) must be less than Slow MA (10).")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: { "fast_ma": 50, "slow_ma": 10 } """)
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            assert result.exit_code == 1, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Loading configuration from" in result.stdout
        finally:
            os.unlink(config_file)

class TestReportGenerationErrorScenarios:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('src.meqsap.cli.generate_complete_report')
    @patch('src.meqsap.cli.run_complete_backtest')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_pdf_generation_permission_error(self, mock_fetch_market_data, mock_run_complete_backtest, mock_generate_complete_report):
        mock_fetch_market_data.return_value = pd.DataFrame({'Close': [100]})
        mock_run_complete_backtest.return_value = Mock(spec=BacktestAnalysisResult)
        mock_generate_complete_report.side_effect = ReportingError("Permission denied for PDF")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-12-31"
strategy_params: {"fast_ma": 10, "slow_ma": 20}""")
            config_file = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_file, "--report"], catch_exceptions=True)
            assert result.exit_code == 4, f"EXIT CODE: {result.exit_code}\nSTDOUT: {result.stdout}"
            assert "Generating reports" in result.stdout # Check for earlier message
        finally:
            os.unlink(config_file)

class TestProgressAndUserExperience:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('src.meqsap.cli.Progress')
    @patch('src.meqsap.cli.fetch_market_data')
    def test_progress_indicators_data_download(self, mock_fetch_market_data, mock_progress_constructor):
        mock_fetch_market_data.return_value = pd.DataFrame({'Close': [100, 101, 102]})
        mock_progress_instance = MagicMock()
        mock_progress_constructor.return_value.__enter__.return_value = mock_progress_instance
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategy_type: "MovingAverageCrossover"
ticker: "AAPL"
start_date: "2023-01-01"
end_date: "2023-01-03"
strategy_params: {"fast_ma": 1, "slow_ma": 2}""")
            config_file = f.name
        try:
            with patch('src.meqsap.cli.run_complete_backtest', return_value=Mock(spec=BacktestAnalysisResult)), \
                 patch('src.meqsap.cli.generate_complete_report', return_value=None):
                self.runner.invoke(app, ["analyze", config_file], catch_exceptions=True)
            mock_progress_constructor.assert_called()
            mock_progress_instance.add_task.assert_any_call("Downloading market data...", total=None)
        finally:
            os.unlink(config_file)
    
    def test_colored_output_generation(self):
        from rich.console import Console
        console = Console(force_terminal=True, color_system="truecolor")
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            console.print("Test message", style="green")
            output = mock_stdout.getvalue()
            assert '\x1b[' in output
    
    def test_terminal_capability_detection(self):
        from rich.console import Console
        console_with_color = Console(force_terminal=True)
        assert console_with_color.is_terminal is True
        console_without_color = Console(force_terminal=False, color_system=None)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            console_without_color.print("No color", style="red")
            output = mock_stdout.getvalue()
            assert '\x1b[' not in output

class TestVersionAndDiagnostics:
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_version_information_display(self):
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "MEQSAP version:" in result.stdout

class TestCrossPlatformCompatibility:
    def test_file_path_handling(self):
        from pathlib import Path
        if sys.platform == "win32": test_path = r"C:\path\to\config.yaml"
        else: test_path = "/path/to/config.yaml"
        path_obj = Path(test_path)
        assert isinstance(path_obj, Path) and str(path_obj) == test_path
    
    def test_console_output_compatibility(self):
        from rich.console import Console
        console = Console(); assert console is not None
        with patch('sys.stdout', new_callable=StringIO): console.print("Test message with unicode: ✓")
    
    def test_permission_handling(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content"); test_file = f.name
        try:
            assert os.path.exists(test_file)
            if sys.platform != "win32": os.chmod(test_file, 0o644); assert os.access(test_file, os.R_OK)
        finally: os.unlink(test_file)
    
    def test_terminal_detection(self):
        is_terminal = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty(); assert isinstance(is_terminal, bool)

class TestPerformanceAndOptimization:
    def setup_method(self): self.runner = CliRunner()
    def test_startup_time_optimization(self): # FIXME: mix_stderr issue likely here too if not fixed by parent
        import time; start_time = time.time(); result = self.runner.invoke(app, ["--help"]); end_time = time.time()
        assert (end_time - start_time) < 2.0 and result.exit_code == 0
    
    def test_operation_timing(self):
        import time; start_time = time.time(); time.sleep(0.01); end_time = time.time()
        elapsed = end_time - start_time; assert elapsed >= 0.01 and elapsed < 0.1
