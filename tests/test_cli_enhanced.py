"""
Comprehensive unit tests for the enhanced CLI module.

Tests all CLI commands, options, error handling, user interactions, and new features.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typer.testing import CliRunner
from datetime import date
import yaml
import pandas as pd

# Import the enhanced CLI components
from src.meqsap.cli import (
    app,
    _validate_and_load_config,
    _handle_dry_run_mode,
    _handle_data_acquisition,
    _execute_backtest_pipeline,
    _generate_output,
    _generate_error_message,
    _get_recovery_suggestions,
)

# Import custom exceptions and types
from src.meqsap.config import StrategyConfig
from src.meqsap.data import DataError
from src.meqsap.backtest import BacktestError, BacktestAnalysisResult, BacktestResult
from src.meqsap.reporting import ReportingError
from src.meqsap.exceptions import (
    MEQSAPError,
    ConfigurationError,
    DataAcquisitionError,
    BacktestExecutionError,
    ReportGenerationError,
)


# Test data
VALID_YAML_CONTENT = yaml.dump({
    "ticker": "AAPL",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "strategy_type": "MovingAverageCrossover", 
    "strategy_params": {"fast_ma": 10, "slow_ma": 20}
})

INVALID_YAML_CONTENT = """
ticker: AAPL
start_date: 2023-01-01
end_date: 2023-12-31
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 10
  slow_ma: [broken yaml
"""


class TestEnhancedCLIMain:
    """Test the enhanced main CLI command with all new features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Mock configuration object
        self.mock_config = Mock(spec=StrategyConfig)
        self.mock_config.strategy_type = "MovingAverageCrossover"
        self.mock_config.ticker = "AAPL"
        self.mock_config.start_date = date(2023, 1, 1)
        self.mock_config.end_date = date(2023, 12, 31)
        
        # Mock strategy params
        self.mock_strategy_params = Mock()
        self.mock_strategy_params.model_dump.return_value = {
            "fast_ma": 10, "slow_ma": 20
        }
        self.mock_config.validate_strategy_params.return_value = self.mock_strategy_params
        
        # Mock analysis result
        self.mock_analysis_result = Mock(spec=BacktestAnalysisResult)
        self.mock_analysis_result.primary_result = Mock()
        self.mock_analysis_result.primary_result.total_trades = 5
        
        # Mock market data
        self.mock_market_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [103, 104, 105],
            'volume': [1000, 1100, 1200]
        })

    def test_help_command(self):
        """Test that help command works and shows enhanced help."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "MEQSAP" in result.output
        assert "--report" in result.output
        assert "--verbose" in result.output # This is a global option, but also shown in subcommand
        assert "--validate-only" in result.output # Specific to analyze

    def test_mutually_exclusive_flags(self):
        """Test that verbose and quiet flags are mutually exclusive."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_path, "--verbose", "--quiet"])
            assert result.exit_code == 1
            assert "cannot be used together" in result.output
        finally:
            os.unlink(config_path)

    @patch('src.meqsap.cli._main_pipeline')
    def test_successful_execution(self, mock_pipeline):
        """Test successful pipeline execution."""
        mock_pipeline.return_value = 0
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_path])
            assert result.exit_code == 0
            mock_pipeline.assert_called_once()
        finally:
            os.unlink(config_path)

    @patch('src.meqsap.cli._main_pipeline')
    def test_pipeline_failure(self, mock_pipeline):
        """Test pipeline failure handling."""
        mock_pipeline.return_value = 1
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_path])
            assert result.exit_code == 1
        finally:
            os.unlink(config_path)


class TestConfigurationValidation:
    """Test enhanced configuration validation functionality."""

    def test_validate_and_load_config_success(self):
        """Test successful configuration validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = Path(f.name)
        
        try:
            with patch('src.meqsap.cli.validate_config') as mock_validate:
                mock_config = Mock(spec=StrategyConfig)
                mock_config.strategy_type = "MovingAverageCrossover"
                mock_config.ticker = "AAPL"
                mock_config.start_date = date(2023, 1, 1)
                mock_config.end_date = date(2023, 12, 31)
                mock_validate.return_value = mock_config
                
                mock_params = Mock()
                mock_params.model_dump.return_value = {"fast_ma": 10, "slow_ma": 20}
                mock_config.validate_strategy_params.return_value = mock_params
                
                result = _validate_and_load_config(config_path, verbose=False, quiet=True)
                assert result == mock_config
        finally:
            os.unlink(config_path)

    def test_validate_config_file_not_found(self):
        """Test configuration validation with missing file."""
        config_path = Path("/nonexistent/config.yaml")
        
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_and_load_config(config_path, verbose=False, quiet=True)
        
        assert "not found" in str(exc_info.value)

    def test_validate_config_invalid_yaml(self):
        """Test configuration validation with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(INVALID_YAML_CONTENT)
            config_path = Path(f.name)
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _validate_and_load_config(config_path, verbose=False, quiet=True)
            assert "Invalid YAML in configuration" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_validate_config_wrong_extension(self):
        """Test configuration validation with wrong file extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _validate_and_load_config(config_path, verbose=False, quiet=True)
            
            assert "yaml or .yml extension" in str(exc_info.value)
        finally:
            os.unlink(config_path)


class TestDryRunMode:
    """Test dry-run mode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=StrategyConfig)
        self.mock_config.strategy_type = "MovingAverageCrossover"
        self.mock_config.ticker = "AAPL"
        self.mock_config.start_date = date(2023, 1, 1)
        self.mock_config.end_date = date(2023, 12, 31)

    def test_dry_run_mode_quiet(self):
        """Test dry-run mode with quiet flag."""
        exit_code = _handle_dry_run_mode(self.mock_config, quiet=True)
        assert exit_code == 0

    def test_dry_run_mode_verbose(self):
        """Test dry-run mode with verbose output."""
        exit_code = _handle_dry_run_mode(self.mock_config, quiet=False)
        assert exit_code == 0


class TestDataAcquisition:
    """Test enhanced data acquisition functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=StrategyConfig)
        self.mock_config.ticker = "AAPL"
        self.mock_config.start_date = date(2023, 1, 1)
        self.mock_config.end_date = date(2023, 12, 31)
        
        self.mock_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [103, 104, 105],
            'volume': [1000, 1100, 1200]
        })

    @patch('src.meqsap.cli.fetch_market_data')
    def test_successful_data_acquisition(self, mock_fetch):
        """Test successful data acquisition."""
        mock_fetch.return_value = self.mock_data
        
        result = _handle_data_acquisition(self.mock_config, verbose=False, quiet=True)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        mock_fetch.assert_called_once_with("AAPL", date(2023, 1, 1), date(2023, 12, 31))

    @patch('src.meqsap.cli.fetch_market_data')
    def test_data_acquisition_failure(self, mock_fetch):
        """Test data acquisition failure handling."""
        mock_fetch.side_effect = DataError("Network error")
        
        with pytest.raises(DataAcquisitionError) as exc_info:
            _handle_data_acquisition(self.mock_config, verbose=False, quiet=True)
        
        assert "Failed to acquire market data" in str(exc_info.value)


class TestBacktestExecution:
    """Test enhanced backtest execution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=StrategyConfig)
        self.mock_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [103, 104, 105],
            'volume': [1000, 1100, 1200]
        })
        
        self.mock_analysis_result = Mock(spec=BacktestAnalysisResult)

    @patch('src.meqsap.cli.run_complete_backtest')
    def test_successful_backtest_execution(self, mock_backtest):
        """Test successful backtest execution."""
        mock_backtest.return_value = self.mock_analysis_result
        
        result = _execute_backtest_pipeline(
            self.mock_data, self.mock_config, verbose=False, quiet=True
        )
        
        assert result == self.mock_analysis_result
        mock_backtest.assert_called_once_with(self.mock_config, self.mock_data)

    @patch('src.meqsap.cli.run_complete_backtest')
    def test_backtest_execution_failure(self, mock_backtest):
        """Test backtest execution failure handling."""
        mock_backtest.side_effect = BacktestError("Computation error")
        
        with pytest.raises(BacktestExecutionError) as exc_info:
            _execute_backtest_pipeline(
                self.mock_data, self.mock_config, verbose=False, quiet=True
            )
        
        assert "Backtest execution failed" in str(exc_info.value)


class TestOutputGeneration:
    """Test enhanced output generation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_analysis_result = Mock(spec=BacktestAnalysisResult)
        self.mock_analysis_result.primary_result = Mock()
        self.mock_analysis_result.primary_result.total_trades = 5
        self.mock_analysis_result.primary_result.trade_details = []
        
        self.mock_config = Mock(spec=StrategyConfig)

    @patch('src.meqsap.cli.generate_complete_report')
    def test_successful_output_generation(self, mock_generate):
        """Test successful output generation."""
        mock_generate.return_value = "/path/to/report.pdf"
        
        _generate_output(
            analysis_result=self.mock_analysis_result,
            config=self.mock_config,
            report=True,
            output_dir=None,
            quiet=True,
            no_color=False,
            verbose=False,
        )
        
        mock_generate.assert_called_once()

    @patch('src.meqsap.cli.generate_complete_report')
    def test_output_generation_failure(self, mock_generate):
        """Test output generation failure handling."""
        mock_generate.side_effect = ReportingError("File system error")
        
        with pytest.raises(ReportGenerationError) as exc_info:
            _generate_output(
                analysis_result=self.mock_analysis_result,
                config=self.mock_config,
                report=True,
                output_dir=None,
                quiet=True,
                no_color=False,
                verbose=False,
            )
        
        assert "Report generation failed" in str(exc_info.value)


class TestErrorHandling:
    """Test enhanced error handling and recovery suggestions."""

    def test_generate_error_message_basic(self):
        """Test basic error message generation."""
        error = ConfigurationError("Invalid config")
        message = _generate_error_message(error, verbose=False, no_color=True)
        
        assert "ConfigurationError: Invalid config" in message
        assert "Suggested Solutions:" in message

    def test_generate_error_message_verbose(self):
        """Test verbose error message generation."""
        error = ConfigurationError("Invalid config")
        message = _generate_error_message(error, verbose=True, no_color=True)
        
        assert "ConfigurationError: Invalid config" in message
        assert "Debug Information:" in message

    def test_recovery_suggestions_configuration_error(self):
        """Test recovery suggestions for configuration errors."""
        error = ConfigurationError("Invalid config")
        suggestions = _get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("YAML" in suggestion for suggestion in suggestions)

    def test_recovery_suggestions_data_error(self):
        """Test recovery suggestions for data acquisition errors."""
        error = DataAcquisitionError("Network error")
        suggestions = _get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("connection" in suggestion for suggestion in suggestions)

    def test_recovery_suggestions_backtest_error(self):
        """Test recovery suggestions for backtest errors."""
        error = BacktestExecutionError("Computation error")
        suggestions = _get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("strategy" in suggestion for suggestion in suggestions)

    def test_recovery_suggestions_report_error(self):
        """Test recovery suggestions for report generation errors."""
        error = ReportGenerationError("File system error")
        suggestions = _get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("directory" in suggestion for suggestion in suggestions)

    def test_recovery_suggestions_generic_error(self):
        """Test recovery suggestions for generic errors."""
        error = Exception("Generic error")
        suggestions = _get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("verbose" in suggestion for suggestion in suggestions)


class TestVersionCommand:
    """Test version command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_command(self):
        """Test version command output."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "MEQSAP" in result.output
        assert "version" in result.output


class TestCLIIntegration:
    """Test complete CLI integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('src.meqsap.cli.validate_config')
    @patch('src.meqsap.cli.fetch_market_data')
    @patch('src.meqsap.cli.run_complete_backtest')
    @patch('src.meqsap.cli.generate_complete_report')
    def test_complete_pipeline_success(self, mock_report, mock_backtest, mock_data, mock_config):
        """Test complete successful pipeline execution."""
        # Setup mocks
        mock_config_obj = Mock(spec=StrategyConfig)
        mock_config_obj.strategy_type = "MovingAverageCrossover"
        mock_config_obj.ticker = "AAPL"
        mock_config_obj.start_date = date(2023, 1, 1)
        mock_config_obj.end_date = date(2023, 12, 31)
        
        mock_params = Mock()
        mock_params.model_dump.return_value = {"fast_ma": 10, "slow_ma": 20}
        mock_config_obj.validate_strategy_params.return_value = mock_params
        
        mock_config.return_value = mock_config_obj
        
        mock_data.return_value = pd.DataFrame({
            'open': [100], 'high': [105], 'low': [99], 'close': [103], 'volume': [1000]
        })
        
        mock_analysis = Mock(spec=BacktestAnalysisResult)
        mock_analysis.primary_result = Mock()
        mock_analysis.primary_result.total_trades = 0
        mock_backtest.return_value = mock_analysis
        
        mock_report.return_value = None
        
        # Create config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        
        try:
            result = self.runner.invoke(app, ["analyze", config_path, "--quiet"])
            assert result.exit_code == 0
        finally:
            os.unlink(config_path)

    def test_invalid_config_file_path(self):
        """Test handling of invalid config file path."""
        result = self.runner.invoke(app, ["analyze", "/nonexistent/config.yaml"])
        assert result.exit_code == 2  # Typer's exit code for file not found

    @patch('src.meqsap.cli._main_pipeline')
    def test_configuration_error_exit_code(self, mock_pipeline):
        """Test that configuration errors return exit code 1."""
        mock_pipeline.return_value = 1
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_path])
            assert result.exit_code == 1
        finally:
            os.unlink(config_path)

    @patch('src.meqsap.cli._main_pipeline')
    def test_data_error_exit_code(self, mock_pipeline):
        """Test that data errors return exit code 2."""
        mock_pipeline.return_value = 2 # To test the specific code path from _main_pipeline
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_CONTENT)
            config_path = f.name
        try:
            result = self.runner.invoke(app, ["analyze", config_path])
            assert result.exit_code == 2
        finally:
            os.unlink(config_path)


class TestCLIFlags:
    """Test all CLI flags and options."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_report_flag(self):
        """Test --report flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--report" in result.output

    def test_verbose_flag(self):
        """Test --verbose flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--verbose" in result.output

    def test_quiet_flag(self):
        """Test --quiet flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--quiet" in result.output

    def test_dry_run_flag(self):
        """Test --dry-run flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--validate-only" in result.output # --dry-run is an alias for --validate-only

    def test_output_dir_flag(self):
        """Test --output-dir flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--output-dir" in result.output

    def test_no_color_flag(self):
        """Test --no-color flag functionality."""
        result = self.runner.invoke(app, ["analyze", "--help"])
        assert "--no-color" in result.output
