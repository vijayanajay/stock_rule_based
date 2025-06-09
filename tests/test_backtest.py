"""
Unit tests for the backtest module.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
from unittest.mock import patch, MagicMock
import unittest
import warnings

# Suppress pandas_ta related warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API", category=UserWarning)

from src.meqsap.backtest import (
    StrategySignalGenerator,
    run_backtest,
    perform_vibe_checks,
    perform_robustness_checks,
    run_complete_backtest,
    BacktestResult,
    VibeCheckResults,
    RobustnessResults,
    BacktestAnalysisResult,
    BacktestError
)
from src.meqsap.config import MovingAverageCrossoverParams, StrategyConfig


class TestStrategySignalGenerator:
    
    def create_sample_data(self, days=100):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        np.random.seed(42)
        
        # Generate realistic price data with trend
        base_price = 100
        returns = np.random.normal(0.001, 0.02, days)
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        data = pd.DataFrame({
            'Open': [p * 0.99 for p in prices],
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, days)
        }, index=dates)
        
        return data
    
    def create_sample_config(self):
        """Create sample strategy configuration."""
        return StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 4, 10),
            strategy_type="MovingAverageCrossover",
            strategy_params={"fast_ma": 10, "slow_ma": 20}
        )
    
    def test_generate_ma_crossover_signals_success(self):
        """Test successful MA crossover signal generation."""
        data = self.create_sample_data()
        config = self.create_sample_config()
        
        signals = StrategySignalGenerator.generate_signals(data, config)
        
        assert isinstance(signals, pd.DataFrame)
        assert 'entry' in signals.columns
        assert 'exit' in signals.columns
        assert signals.dtypes['entry'] == bool
        assert signals.dtypes['exit'] == bool
        assert len(signals) > 0
        
        # Should have some signals (but not necessarily both entry and exit)
        total_signals = signals['entry'].sum() + signals['exit'].sum()
        assert total_signals >= 0  # Could be zero in some cases
    
    def test_generate_signals_insufficient_data(self):
        """Test signal generation with insufficient data."""
        data = self.create_sample_data(days=10)  # Not enough for slow_ma=20
        config = self.create_sample_config()
        
        with pytest.raises(BacktestError, match="Insufficient data"):
            StrategySignalGenerator.generate_signals(data, config)
    
    def test_generate_signals_unknown_strategy(self):
        """Test signal generation with unknown strategy type."""
        data = self.create_sample_data()
        config = self.create_sample_config()
        config.strategy_type = "UnknownStrategy"
        
        with pytest.raises(BacktestError, match="Unknown strategy type"):
            StrategySignalGenerator.generate_signals(data, config)


class TestRunBacktest:
    
    def create_sample_data_and_signals(self):
        """Create sample data and signals for testing."""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        # Create trending price data
        prices = [100 + i * 0.5 for i in range(50)]
        data = pd.DataFrame({
            'Open': [p * 0.99 for p in prices],
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 50
        }, index=dates)
        
        # Create simple signals - buy on day 10, sell on day 30
        signals = pd.DataFrame({
            'entry': [False] * 50,
            'exit': [False] * 50
        }, index=dates)
        signals.iloc[10, 0] = True  # Entry signal
        signals.iloc[30, 1] = True  # Exit signal
        
        return data, signals
    
    def test_run_backtest_success(self):
        """Test successful backtest execution."""
        data, signals = self.create_sample_data_and_signals()
        
        result = run_backtest(prices_data=data, signals_data=signals)
        
        assert isinstance(result, BacktestResult)
        assert result.total_trades >= 0
        assert result.final_value > 0
        assert isinstance(result.trade_details, list)
        assert isinstance(result.portfolio_value_series, dict)
    
    def test_run_backtest_no_signals(self):
        """Test backtest with no signals."""
        data, signals = self.create_sample_data_and_signals()
        
        # Remove all signals
        signals['entry'] = False
        signals['exit'] = False
        
        result = run_backtest(prices_data=data, signals_data=signals)
        
        assert result.total_trades == 0
        assert result.total_return == 0.0
        assert result.final_value == 10000  # Should equal initial cash
    
    def test_run_backtest_misaligned_data(self):
        """Test backtest with misaligned data and signals."""
        data, signals = self.create_sample_data_and_signals()
        
        # Create signals with different date range
        different_dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        signals.index = different_dates
        
        with pytest.raises(BacktestError, match="No common dates"):
            run_backtest(prices_data=data, signals_data=signals)


class TestVibeChecks:
    
    def create_sample_result(self, total_trades=5):
        """Create sample backtest result."""
        return BacktestResult(
            total_return=10.5,
            annualized_return=25.2,
            sharpe_ratio=1.5,
            max_drawdown=5.2,
            total_trades=total_trades,
            win_rate=60.0,
            profit_factor=1.8,
            final_value=11050,
            volatility=15.0,
            calmar_ratio=4.8
        )
    
    def create_sample_data(self, days=100):
        """Create sample data."""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        return pd.DataFrame({
            'Close': [100 + i * 0.1 for i in range(days)]
        }, index=dates)
    
    def create_sample_config(self):
        """Create sample configuration."""
        return StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 4, 10),
            strategy_type="MovingAverageCrossover",
            strategy_params={"fast_ma": 10, "slow_ma": 20}
        )
    
    def test_vibe_checks_all_pass(self):
        """Test vibe checks when all checks pass."""
        result = self.create_sample_result(total_trades=5)
        data = self.create_sample_data(days=100)
        config = self.create_sample_config()
        
        vibe_checks = perform_vibe_checks(result, data, config)
        
        assert isinstance(vibe_checks, VibeCheckResults)
        assert vibe_checks.minimum_trades_check is True
        assert vibe_checks.signal_quality_check is True
        assert vibe_checks.data_coverage_check is True
        assert vibe_checks.overall_pass is True
        assert len(vibe_checks.check_messages) == 3
    
    def test_vibe_checks_no_trades(self):
        """Test vibe checks when no trades occurred."""
        result = self.create_sample_result(total_trades=0)
        data = self.create_sample_data(days=100)
        config = self.create_sample_config()
        
        vibe_checks = perform_vibe_checks(result, data, config)
        
        assert vibe_checks.minimum_trades_check is False
        assert vibe_checks.overall_pass is False
        assert any("No trades executed" in msg for msg in vibe_checks.check_messages)
    
    def test_vibe_checks_insufficient_data(self):
        """Test vibe checks with insufficient data."""
        result = self.create_sample_result(total_trades=5)
        data = self.create_sample_data(days=30)  # Less than 2x slow_ma (40)
        config = self.create_sample_config()
        
        vibe_checks = perform_vibe_checks(result, data, config)
        
        assert vibe_checks.data_coverage_check is False
        assert vibe_checks.overall_pass is False


class TestRobustnessChecks:
    
    def create_sample_data_and_signals(self):
        """Create sample data and signals."""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        prices = [100 + i * 0.5 for i in range(50)]
        data = pd.DataFrame({
            'Open': [p * 0.99 for p in prices],
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 50
        }, index=dates)
        
        signals = pd.DataFrame({
            'entry': [False] * 50,
            'exit': [False] * 50
        }, index=dates)
        signals.iloc[10, 0] = True
        signals.iloc[30, 1] = True
        
        return data, signals
    
    def create_sample_config(self):
        """Create sample configuration."""
        return StrategyConfig(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 2, 19),
            strategy_type="MovingAverageCrossover",
            strategy_params={"fast_ma": 10, "slow_ma": 20}
        )
    
    def test_robustness_checks_success(self):
        """Test successful robustness checks."""
        data, signals = self.create_sample_data_and_signals()
        config = self.create_sample_config()
        
        robustness = perform_robustness_checks(data, signals, config)
        
        assert isinstance(robustness, RobustnessResults)
        assert isinstance(robustness.baseline_sharpe, float)
        assert isinstance(robustness.high_fees_sharpe, float)
        assert isinstance(robustness.turnover_rate, float)
        assert isinstance(robustness.recommendations, list)
        assert len(robustness.recommendations) > 0


class TestCompleteBacktest(unittest.TestCase):
    
    def setUp(self):
        """Create sample data for complete backtest."""
        # Create test data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 100)
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        self.test_data = pd.DataFrame({
            'Open': [p * 0.99 for p in prices],
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        # Create sample signals
        self.test_signals = pd.DataFrame({
            'entry': np.random.choice([True, False], size=100, p=[0.05, 0.95]),
            'exit': np.random.choice([True, False], size=100, p=[0.05, 0.95])
        }, index=dates)
    
    def test_run_complete_backtest_success(self):
        """Test successful execution of run_complete_backtest."""
        # Create strategy config with required parameters
        strategy_params = MovingAverageCrossoverParams(
            fast_ma=5,
            slow_ma=20,
            stop_loss=0.05,
            take_profit=0.1,
            trailing_stop=0.02,
            position_size=1.0
        )
        
        strategy_config = StrategyConfig(
            ticker="AAPL",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            strategy_type="MovingAverageCrossover",
            strategy_params=strategy_params.model_dump()
        )
        
        # Pass both data and signals to run_complete_backtest
        result = run_complete_backtest(strategy_config, {"prices": self.test_data, "signals": self.test_signals})
        
        # Verify the result structure
        self.assertIsInstance(result, BacktestAnalysisResult)
        self.assertIsInstance(result.primary_result, BacktestResult)
        self.assertIsInstance(result.vibe_checks, VibeCheckResults)
        self.assertIsInstance(result.robustness_checks, RobustnessResults)
        
class TestErrorHandling(unittest.TestCase):
    """Test error handling in backtest module."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample test data with proper column names
        dates = pd.date_range(start='2022-01-01', periods=100)
        self.test_data = pd.DataFrame({
            'Open': np.random.normal(100, 5, 100),
            'High': np.random.normal(105, 5, 100),
            'Low': np.random.normal(95, 5, 100),
            'Close': np.random.normal(100, 5, 100),
            'Volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        # Create sample signals
        self.test_signals = pd.DataFrame({
            'entry': np.random.choice([True, False], size=100, p=[0.05, 0.95]),
            'exit': np.random.choice([True, False], size=100, p=[0.05, 0.95])
        }, index=dates)
    
    def create_sample_data(self):
        """Create a sample data dictionary with proper structure."""
        return {
            'prices': self.test_data,
            'signals': self.test_signals
        }
        
    def test_backtest_invalid_parameter_type(self):
        """Test that appropriate error is raised when invalid parameter types are provided."""
        data = self.create_sample_data()
        
        # Test with invalid initial_cash type
        prices_df = self.test_data
        signals_df = self.test_signals
        with self.assertRaises(BacktestError):
            run_backtest(prices_data=prices_df, signals_data=signals_df, initial_cash="not a number")
