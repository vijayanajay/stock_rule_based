"""
Unit tests for the reporting module.

This module tests all presentation logic, output formatting, table creation,
error handling, and PDF generation scenarios for the MEQSAP reporting system.
"""

import pytest
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import date, datetime
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from typing import Dict, List

from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from src.meqsap.reporting import (
    ReportConfig,
    ExecutiveVerdictData,
    format_percentage,
    format_currency,
    format_number,
    get_performance_color,
    format_performance_metrics,
    determine_overall_verdict,
    create_strategy_summary_table,
    create_performance_table,
    create_vibe_check_table,
    create_robustness_table,
    create_recommendations_panel,
    generate_executive_verdict,
    prepare_returns_for_pyfolio,
    generate_pdf_report,
    generate_complete_report,
    PYFOLIO_AVAILABLE
)

from src.meqsap.backtest import (
    BacktestResult,
    VibeCheckResults,
    RobustnessResults,
    BacktestAnalysisResult
)
from src.meqsap.config import StrategyConfig, MovingAverageCrossoverParams
from src.meqsap.exceptions import ReportingError


class TestReportConfig:
    """Test ReportConfig Pydantic model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ReportConfig()
        
        assert config.include_pdf is False
        assert config.output_directory == "./reports"
        assert config.filename_prefix == "meqsap_report"
        assert config.include_plots is True
        assert config.decimal_places == 2
        assert config.color_output is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ReportConfig(
            include_pdf=True,
            output_directory="/custom/path",
            filename_prefix="custom_report",
            include_plots=False,
            decimal_places=4,
            color_output=False
        )
        
        assert config.include_pdf is True
        assert config.output_directory == "/custom/path"
        assert config.filename_prefix == "custom_report"
        assert config.include_plots is False
        assert config.decimal_places == 4
        assert config.color_output is False
    
    def test_decimal_places_validation(self):
        """Test decimal places validation constraints."""
        # Valid values
        ReportConfig(decimal_places=0)
        ReportConfig(decimal_places=6)
        
        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            ReportConfig(decimal_places=-1)
        
        with pytest.raises(ValueError):
            ReportConfig(decimal_places=7)


class TestExecutiveVerdictData:
    """Test ExecutiveVerdictData Pydantic model."""
    
    def test_valid_data(self):
        """Test valid executive verdict data creation."""
        data = ExecutiveVerdictData(
            strategy_name="MA Crossover",
            ticker="AAPL",
            date_range="2023-01-01 to 2023-12-31",
            total_return="+15.5%",
            annual_return="+15.5%",
            sharpe_ratio="1.25",
            max_drawdown="-8.2%",
            win_rate="65.0%",
            total_trades=45,
            vibe_check_status="PASS",
            robustness_score="Good",
            overall_verdict="PASS"
        )
        
        assert data.strategy_name == "MA Crossover"
        assert data.ticker == "AAPL"
        assert data.total_trades == 45


class TestFormattingFunctions:
    """Test number and metric formatting functions."""
    
    def test_format_percentage(self):
        """Test percentage formatting with various inputs."""
        # Normal values - inputs are already in percentage form
        assert format_percentage(15.55) == "+15.55%"
        assert format_percentage(-8.25) == "-8.25%"
        assert format_percentage(0.0) == "0.00%"
        
        # Without sign
        assert format_percentage(15.55, include_sign=False) == "15.55%"
        assert format_percentage(-8.25, include_sign=False) == "-8.25%"
        
        # Different decimal places
        assert format_percentage(15.55, decimal_places=1) == "+15.6%"
        assert format_percentage(15.55, decimal_places=3) == "+15.550%"
        
        # Edge cases
        assert format_percentage(np.nan) == "N/A"
        assert format_percentage(np.inf) == "N/A"
        assert format_percentage(-np.inf) == "N/A"
    
    def test_format_currency(self):
        """Test currency formatting with various inputs."""
        # Normal values
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(1000000) == "$1,000,000.00"
        assert format_currency(0) == "$0.00"
        assert format_currency(-500.25) == "$-500.25"
        
        # Different decimal places
        assert format_currency(1234.567, decimal_places=0) == "$1,235"
        assert format_currency(1234.567, decimal_places=3) == "$1,234.567"
        
        # Edge cases
        assert format_currency(np.nan) == "N/A"
        assert format_currency(np.inf) == "N/A"
        assert format_currency(-np.inf) == "N/A"
    
    def test_format_number(self):
        """Test number formatting with various inputs."""
        # Normal values
        assert format_number(1.2345) == "1.23"
        assert format_number(-0.5678) == "-0.57"
        assert format_number(0) == "0.00"
        
        # Different decimal places
        assert format_number(1.2345, decimal_places=0) == "1"
        assert format_number(1.2345, decimal_places=4) == "1.2345"
        
        # Edge cases
        assert format_number(np.nan) == "N/A"
        assert format_number(np.inf) == "N/A"
        assert format_number(-np.inf) == "N/A"


class TestPerformanceColors:
    """Test color coding for performance metrics."""
    
    def test_get_performance_color_total_return(self):
        """Test color coding for total return."""
        assert get_performance_color("total_return", 15.0) == "green"  # > 10%
        assert get_performance_color("total_return", 5.0) == "yellow"  # Between -5% and 10%
        assert get_performance_color("total_return", -10.0) == "red"   # < -5%
    
    def test_get_performance_color_sharpe_ratio(self):
        """Test color coding for Sharpe ratio."""
        assert get_performance_color("sharpe_ratio", 1.5) == "green"   # > 1.0
        assert get_performance_color("sharpe_ratio", 0.5) == "yellow"  # Between 0.0 and 1.0
        assert get_performance_color("sharpe_ratio", -0.5) == "red"    # < 0.0
    
    def test_get_performance_color_max_drawdown(self):
        """Test color coding for maximum drawdown (special case)."""
        assert get_performance_color("max_drawdown", -5.0) == "green"   # > -10%
        assert get_performance_color("max_drawdown", -15.0) == "yellow" # Between -25% and -10%
        assert get_performance_color("max_drawdown", -30.0) == "red"    # < -25%
        assert get_performance_color("max_drawdown", 5.0) == "red"      # Invalid positive value
    
    def test_get_performance_color_win_rate(self):
        """Test color coding for win rate."""
        assert get_performance_color("win_rate", 60.0) == "green"   # > 55%
        assert get_performance_color("win_rate", 50.0) == "yellow"  # Between 45% and 55%
        assert get_performance_color("win_rate", 40.0) == "red"     # < 45%
    
    def test_get_performance_color_edge_cases(self):
        """Test color coding for edge cases."""
        assert get_performance_color("unknown_metric", 50.0) == "white"
        assert get_performance_color("total_return", np.nan) == "white"
        assert get_performance_color("total_return", np.inf) == "white"


class TestFormatPerformanceMetrics:
    """Test performance metrics formatting."""
    
    def create_sample_backtest_result(self):
        """Create a sample BacktestResult for testing."""
        return BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,            calmar_ratio=1.89
        )
    
    def test_format_performance_metrics(self):
        """Test formatting of all performance metrics."""
        result = self.create_sample_backtest_result()
        formatted = format_performance_metrics(result, decimal_places=2)
        
        assert formatted["total_return"] == "+15.50%"
        assert formatted["annual_return"] == "+15.50%"
        assert formatted["sharpe_ratio"] == "1.250"
        assert formatted["max_drawdown"] == "-8.20%"
        assert formatted["win_rate"] == "+65.00%"
        assert formatted["volatility"] == "+18.50%"
        assert formatted["calmar_ratio"] == "1.890"
        assert formatted["final_value"] == "$115,500"
        assert formatted["profit_factor"] == "1.800"
    
    def test_format_performance_metrics_custom_decimals(self):
        """Test formatting with custom decimal places."""
        result = self.create_sample_backtest_result()
        formatted = format_performance_metrics(result, decimal_places=1)
        
        # Percentage metrics follow decimal_places exactly
        assert formatted["total_return"] == "+15.5%"
        assert formatted["win_rate"] == "+65.0%"
        assert formatted["volatility"] == "+18.5%"
        
        # Ratio metrics (dimensionless) get decimal_places + 1 for better precision
        assert formatted["sharpe_ratio"] == "1.25"  # 1.25 with 2 decimal places (decimal_places + 1)
        assert formatted["calmar_ratio"] == "1.89"  # 1.89 with 2 decimal places (decimal_places + 1)
        assert formatted["profit_factor"] == "1.80"  # 1.80 with 2 decimal places (decimal_places + 1)
    
    def test_format_performance_metrics_edge_cases(self):
        """Test formatting with edge case values."""
        result = BacktestResult(
            total_return=np.nan,
            annualized_return=np.inf,
            sharpe_ratio=-np.inf,
            max_drawdown=0.0,
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            final_value=0.0,
            volatility=0.0,
            calmar_ratio=0.0
        )
        
        formatted = format_performance_metrics(result)
        
        assert formatted["total_return"] == "N/A"
        assert formatted["annual_return"] == "N/A"
        assert formatted["sharpe_ratio"] == "N/A"


class TestOverallVerdictLogic:
    """Test overall verdict determination logic."""
    
    def create_sample_vibe_checks(self, overall_pass=True):
        """Create sample vibe check results."""
        return VibeCheckResults(
            minimum_trades_check=overall_pass,
            signal_quality_check=overall_pass,
            data_coverage_check=overall_pass,
            overall_pass=overall_pass,
            check_messages=["All checks passed"] if overall_pass else ["Some checks failed"]
        )
    
    def create_sample_robustness_checks(self, sharpe_degradation=25.0, turnover_rate=15.0):
        """Create sample robustness check results."""
        return RobustnessResults(
            baseline_sharpe=1.5,
            high_fees_sharpe=1.2,
            turnover_rate=turnover_rate,
            sharpe_degradation=sharpe_degradation,
            return_degradation=10.0,
            recommendations=["Strategy shows good robustness"]
        )
    
    def create_sample_backtest_result(self, sharpe_ratio=1.5, max_drawdown=-10.0, total_trades=50):
        """Create sample backtest result."""
        return BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,
            calmar_ratio=1.89
        )
    
    def test_determine_overall_verdict_pass(self):
        """Test PASS verdict determination."""
        vibe_checks = self.create_sample_vibe_checks(overall_pass=True)
        robustness_checks = self.create_sample_robustness_checks()
        backtest_result = self.create_sample_backtest_result()
        
        verdict, recommendations = determine_overall_verdict(
            vibe_checks, robustness_checks, backtest_result
        )
        
        assert verdict == "PASS"
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
    
    def test_determine_overall_verdict_fail_vibe_checks(self):
        """Test FAIL verdict due to failed vibe checks."""
        vibe_checks = self.create_sample_vibe_checks(overall_pass=False)
        robustness_checks = self.create_sample_robustness_checks()
        backtest_result = self.create_sample_backtest_result()
        
        verdict, recommendations = determine_overall_verdict(
            vibe_checks, robustness_checks, backtest_result
        )
        
        assert verdict == "FAIL"
        assert "validation checks" in recommendations[0]
    
    def test_determine_overall_verdict_fail_no_trades(self):
        """Test FAIL verdict due to no trades."""
        vibe_checks = self.create_sample_vibe_checks(overall_pass=True)
        robustness_checks = self.create_sample_robustness_checks()
        backtest_result = self.create_sample_backtest_result(total_trades=0)
        
        verdict, recommendations = determine_overall_verdict(
            vibe_checks, robustness_checks, backtest_result
        )
        
        assert verdict == "FAIL"
        assert "no trades" in recommendations[0]
    
    def test_determine_overall_verdict_warning_performance(self):
        """Test WARNING verdict due to performance issues."""
        vibe_checks = self.create_sample_vibe_checks(overall_pass=True)
        robustness_checks = self.create_sample_robustness_checks()
        backtest_result = self.create_sample_backtest_result(sharpe_ratio=0.3)  # Low Sharpe
        
        verdict, recommendations = determine_overall_verdict(
            vibe_checks, robustness_checks, backtest_result
        )
        
        assert verdict == "WARNING"
        assert any("Sharpe ratio" in rec for rec in recommendations)
    
    def test_determine_overall_verdict_fail_multiple_issues(self):
        """Test FAIL verdict due to multiple performance issues."""
        vibe_checks = self.create_sample_vibe_checks(overall_pass=True)
        robustness_checks = self.create_sample_robustness_checks(sharpe_degradation=80.0, turnover_rate=60.0)
        backtest_result = self.create_sample_backtest_result(
            sharpe_ratio=0.3,  # Low Sharpe
            max_drawdown=-35.0  # High drawdown
        )
        
        verdict, recommendations = determine_overall_verdict(
            vibe_checks, robustness_checks, backtest_result
        )
        
        assert verdict == "FAIL"
        assert len(recommendations) >= 3  # Multiple issues


class TestTableCreation:
    """Test Rich table creation functions."""
    
    def create_sample_strategy_config(self):
        """Create a sample strategy configuration."""
        return StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            strategy_type="MovingAverageCrossover",
            strategy_params=MovingAverageCrossoverParams(
                fast_ma=10,
                slow_ma=30
            ).model_dump()
        )
    
    def create_sample_backtest_result(self):
        """Create a sample BacktestResult."""
        return BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,
            calmar_ratio=1.89
        )
    
    def test_create_strategy_summary_table(self):
        """Test strategy summary table creation."""
        strategy_config = self.create_sample_strategy_config()
        backtest_result = self.create_sample_backtest_result()
        
        table = create_strategy_summary_table(strategy_config, backtest_result)
        
        assert isinstance(table, Table)
        assert table.title == "Strategy Summary"
        assert len(table.columns) == 2
    
    def test_create_performance_table(self):
        """Test performance table creation."""
        backtest_result = self.create_sample_backtest_result()
        
        table = create_performance_table(backtest_result)
        
        assert isinstance(table, Table)
        assert table.title == "Performance Metrics"
        assert len(table.columns) == 2
    
    def test_create_performance_table_no_color(self):
        """Test performance table creation without colors."""
        backtest_result = self.create_sample_backtest_result()
        
        table = create_performance_table(backtest_result, color_output=False)
        
        assert isinstance(table, Table)
        # Should still work without color markup
    
    def test_create_vibe_check_table(self):
        """Test vibe check table creation."""
        vibe_checks = VibeCheckResults(
            minimum_trades_check=True,
            signal_quality_check=True,
            data_coverage_check=False,
            overall_pass=False,
            check_messages=["All checks passed", "Some data coverage issues"]
        )
        
        table = create_vibe_check_table(vibe_checks)
        
        assert isinstance(table, Table)
        assert table.title == "Strategy Validation (Vibe Checks)"
        assert len(table.columns) == 3
    
    def test_create_robustness_table(self):
        """Test robustness table creation."""
        robustness_checks = RobustnessResults(
            baseline_sharpe=1.5,
            high_fees_sharpe=1.2,
            turnover_rate=15.0,
            sharpe_degradation=20.0,
            return_degradation=10.0,
            recommendations=["Good robustness"]
        )
        
        table = create_robustness_table(robustness_checks)
        
        assert isinstance(table, Table)
        assert table.title == "Robustness Analysis"
        assert len(table.columns) == 3
    
    def test_create_recommendations_panel(self):
        """Test recommendations panel creation."""
        recommendations = [
            "Consider reducing position sizes",
            "Monitor market conditions closely"
        ]
        
        panel = create_recommendations_panel(recommendations)
        
        assert isinstance(panel, Panel)
        assert panel.title == "Recommendations"
    
    def test_create_recommendations_panel_empty(self):
        """Test recommendations panel with no recommendations."""
        panel = create_recommendations_panel([])
        
        assert isinstance(panel, Panel)
        assert "No specific recommendations" in str(panel.renderable)


class TestExecutiveVerdictGeneration:
    """Test executive verdict generation."""
    
    def create_sample_analysis_result(self):
        """Create a complete sample analysis result."""
        strategy_config = StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            strategy_type="MovingAverageCrossover",
            strategy_params=MovingAverageCrossoverParams(
                fast_ma=10,
                slow_ma=30
            ).model_dump()
        )
        
        backtest_result = BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,
            calmar_ratio=1.89
        )
        
        vibe_checks = VibeCheckResults(
            minimum_trades_check=True,
            signal_quality_check=True,
            data_coverage_check=True,
            overall_pass=True,
            check_messages=["All checks passed"]
        )
        
        robustness_checks = RobustnessResults(
            baseline_sharpe=1.5,
            high_fees_sharpe=1.2,
            turnover_rate=15.0,
            sharpe_degradation=20.0,
            return_degradation=10.0,
            recommendations=["Strategy shows good robustness"]
        )
        
        return BacktestAnalysisResult(
            primary_result=backtest_result,
            vibe_checks=vibe_checks,
            robustness_checks=robustness_checks,
            strategy_config=strategy_config.model_dump()
        )
    
    @patch('src.meqsap.reporting.Console')
    def test_generate_executive_verdict(self, mock_console_class):
        """Test executive verdict generation."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        analysis_result = self.create_sample_analysis_result()
        
        generate_executive_verdict(analysis_result)
        
        # Verify console was created and print was called
        mock_console_class.assert_called_once()
        assert mock_console.print.call_count > 0
    
    @patch('src.meqsap.reporting.Console')
    def test_generate_executive_verdict_custom_config(self, mock_console_class):
        """Test executive verdict generation with custom config."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        analysis_result = self.create_sample_analysis_result()
        config = ReportConfig(color_output=False, decimal_places=1)
        
        generate_executive_verdict(analysis_result, config)
        
        # Verify console was configured correctly
        mock_console_class.assert_called_once_with(force_terminal=False)


class TestPyfolioIntegration:
    """Test pyfolio integration and PDF generation."""
    
    def create_sample_backtest_result_with_series(self):
        """Create a BacktestResult with portfolio value series."""
        # Set random seed for reproducible test results
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        # Simulate portfolio growth
        portfolio_values = [10000 * (1 + 0.001 * i + np.random.normal(0, 0.01)) for i in range(100)]
        
        portfolio_series = {str(date): value for date, value in zip(dates, portfolio_values)}
        
        return BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=portfolio_values[-1],
            volatility=18.5,
            calmar_ratio=1.89,
            portfolio_value_series=portfolio_series
        )
    
    def test_prepare_returns_for_pyfolio(self):
        """Test conversion of backtest results to pyfolio format."""
        backtest_result = self.create_sample_backtest_result_with_series()
        
        returns = prepare_returns_for_pyfolio(backtest_result)
        
        assert isinstance(returns, pd.Series)
        assert len(returns) > 0
        assert returns.index.dtype.kind == 'M'  # datetime index
        # First return should be NaN due to pct_change()
        assert pd.isna(returns.iloc[0]) or len(returns) == 99  # After dropna()
    
    def test_prepare_returns_for_pyfolio_empty_series(self):
        """Test error handling for empty portfolio series."""
        backtest_result = BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,
            calmar_ratio=1.89,
            portfolio_value_series={}
        )
        
        with pytest.raises(ReportingError, match="No portfolio value series available"):
            prepare_returns_for_pyfolio(backtest_result)
    
    @patch('src.meqsap.reporting.PYFOLIO_AVAILABLE', False)
    def test_generate_pdf_report_no_pyfolio(self):
        """Test PDF generation when pyfolio is not available."""
        analysis_result = BacktestAnalysisResult(
            primary_result=self.create_sample_backtest_result_with_series(),
            vibe_checks=VibeCheckResults(
                minimum_trades_check=True,
                signal_quality_check=True,
                data_coverage_check=True,
                overall_pass=True,
                check_messages=[]
            ),
            robustness_checks=RobustnessResults(
                baseline_sharpe=1.5,
                high_fees_sharpe=1.2,
                turnover_rate=15.0,
                sharpe_degradation=20.0,
                return_degradation=10.0,
                recommendations=[]
            ),
            strategy_config={"ticker": "AAPL", "strategy_type": "test"}
        )
        
        with pytest.raises(ReportingError, match="PDF report generation requires pyfolio"):
            generate_pdf_report(analysis_result)
    
    @pytest.mark.skipif(not PYFOLIO_AVAILABLE, reason="pyfolio not available")
    @patch('src.meqsap.reporting.pf.create_full_tear_sheet')
    @patch('src.meqsap.reporting.plt')
    def test_generate_pdf_report_success(self, mock_plt, mock_create_tear_sheet):
        """Test successful PDF generation (mocked)."""
        # Mock pyfolio operations
        mock_fig = MagicMock()
        mock_create_tear_sheet.return_value = mock_fig
        
        analysis_result = BacktestAnalysisResult(
            primary_result=self.create_sample_backtest_result_with_series(),
            vibe_checks=VibeCheckResults(
                minimum_trades_check=True,
                signal_quality_check=True,
                data_coverage_check=True,
                overall_pass=True,
                check_messages=[]
            ),
            robustness_checks=RobustnessResults(
                baseline_sharpe=1.5,
                high_fees_sharpe=1.2,
                turnover_rate=15.0,
                sharpe_degradation=20.0,
                return_degradation=10.0,
                recommendations=[]
            ),
            strategy_config={"ticker": "AAPL", "strategy_type": "test"}
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test_report.pdf")
            
            result_path = generate_pdf_report(analysis_result, output_path)
            
            assert result_path == output_path
            mock_create_tear_sheet.assert_called_once()
            mock_fig.savefig.assert_called_once_with(output_path, format='pdf', bbox_inches='tight', dpi=300)
            mock_plt.close.assert_called_once_with(mock_fig)


class TestCompleteReportGeneration:
    """Test complete report generation workflow."""
    
    def create_sample_analysis_result(self):
        """Create a sample analysis result."""
        strategy_config = StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            strategy_type="MovingAverageCrossover",
            strategy_params=MovingAverageCrossoverParams(
                fast_ma=10,
                slow_ma=30
            ).model_dump()
        )
        
        backtest_result = BacktestResult(
            total_return=15.5,
            annualized_return=15.5,
            sharpe_ratio=1.25,
            max_drawdown=-8.2,
            total_trades=45,
            win_rate=65.0,
            profit_factor=1.8,
            final_value=115500.0,
            volatility=18.5,
            calmar_ratio=1.89,
            portfolio_value_series={"2023-01-01": 10000, "2023-01-02": 10100}
        )
        
        vibe_checks = VibeCheckResults(
            minimum_trades_check=True,
            signal_quality_check=True,
            data_coverage_check=True,
            overall_pass=True,
            check_messages=["All checks passed"]
        )
        
        robustness_checks = RobustnessResults(
            baseline_sharpe=1.5,
            high_fees_sharpe=1.2,
            turnover_rate=15.0,
            sharpe_degradation=20.0,
            return_degradation=10.0,
            recommendations=["Strategy shows good robustness"]
        )
        
        return BacktestAnalysisResult(
            primary_result=backtest_result,
            vibe_checks=vibe_checks,
            robustness_checks=robustness_checks,
            strategy_config=strategy_config.model_dump()
        )
    
    @patch('src.meqsap.reporting.generate_executive_verdict')
    def test_generate_complete_report_terminal_only(self, mock_generate_verdict):
        """Test complete report generation for terminal only."""
        analysis_result = self.create_sample_analysis_result()
        
        result = generate_complete_report(analysis_result, include_pdf=False)
        
        assert result is None  # No PDF generated
        mock_generate_verdict.assert_called_once()
    
    @patch('src.meqsap.reporting.generate_executive_verdict')
    def test_generate_complete_report_quiet_mode(self, mock_generate_verdict):
        """Test complete report generation in quiet mode."""
        analysis_result = self.create_sample_analysis_result()
        
        result = generate_complete_report(analysis_result, quiet=True)
        
        # Should not generate terminal output in quiet mode
        mock_generate_verdict.assert_not_called()
    
    @patch('src.meqsap.reporting.generate_executive_verdict')
    @patch('src.meqsap.reporting.generate_pdf_report')
    @patch('src.meqsap.reporting.Console')
    def test_generate_complete_report_with_pdf(self, mock_console_class, mock_pdf_gen, mock_generate_verdict):
        """Test complete report generation with PDF."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_pdf_gen.return_value = "/path/to/report.pdf"
        
        analysis_result = self.create_sample_analysis_result()
        
        result = generate_complete_report(analysis_result, include_pdf=True)
        
        assert result == "/path/to/report.pdf"
        mock_generate_verdict.assert_called_once()
        mock_pdf_gen.assert_called_once()
    
    @patch('src.meqsap.reporting.generate_executive_verdict')
    @patch('src.meqsap.reporting.generate_pdf_report')
    @patch('src.meqsap.reporting.Console')
    def test_generate_complete_report_pdf_error(self, mock_console_class, mock_pdf_gen, mock_generate_verdict):
        """Test complete report generation with PDF generation error."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_pdf_gen.side_effect = ReportingError("PDF generation failed")
        
        analysis_result = self.create_sample_analysis_result()
        
        result = generate_complete_report(analysis_result, include_pdf=True)
        
        assert result is None  # Should return None on error
        mock_generate_verdict.assert_called_once()
        mock_console.print.assert_called()  # Should print error message


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_format_percentage_with_none(self):
        """Test formatting functions handle None values."""
        assert format_percentage(None) == "N/A"
        assert format_currency(None) == "N/A"
        assert format_number(None) == "N/A"
    
    def test_get_performance_color_with_none(self):
        """Test color determination with None values."""
        assert get_performance_color("total_return", None) == "white"
    
    def test_prepare_returns_empty_after_dropna(self):
        """Test handling when returns series is empty after dropna."""
        # Create a backtest result with constant portfolio values (zero returns)
        backtest_result = BacktestResult(
            total_return=0.0,
            annualized_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            final_value=10000.0,
            volatility=0.0,
            calmar_ratio=0.0,            portfolio_value_series={"2023-01-01": 10000, "2023-01-02": 10000}  # No change
        )
          # Test that the function handles constant portfolio values gracefully
        # This should raise an appropriate error with specific message
        
        with pytest.raises(ReportingError, match=r"Unable to calculate returns|.*empty.*"):
            prepare_returns_for_pyfolio(backtest_result)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_format_percentage_extreme_values(self):
        """Test percentage formatting with extreme values."""
        assert format_percentage(100000.0) == "+100000.00%"
        assert format_percentage(-100000.0) == "-100000.00%"
        assert format_percentage(0.0001, decimal_places=6) == "+0.000100%"
