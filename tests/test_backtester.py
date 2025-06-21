"""Test suite for Backtester module.

Tests the core backtesting functionality including signal generation,
portfolio creation, metrics calculation, and strategy ranking.
"""

import pytest
from pathlib import Path

import pandas as pd
import numpy as np
import vectorbt as vbt

from kiss_signal.backtester import Backtester


class TestBacktester:
    """Test suite for Backtester class."""

    def test_init_default_parameters(self):
        """Test backtester initialization with default parameters."""
        backtester = Backtester()
        assert backtester.hold_period == 20
        assert backtester.min_trades_threshold == 10    
    
    def test_init_custom_parameters(self):
        """Test backtester initialization with custom parameters."""
        backtester = Backtester(hold_period=30, min_trades_threshold=15)
        assert backtester.hold_period == 30
        assert backtester.min_trades_threshold == 15

    def test_calc_edge_score_basic(self):
        """Test edge score calculation with basic inputs."""
        backtester = Backtester()
        weights = {'win_pct': 0.6, 'sharpe': 0.4}
        
        edge_score = backtester.calc_edge_score(0.7, 1.5, weights)
        expected = (0.7 * 0.6) + (1.5 * 0.4)
        assert edge_score == pytest.approx(expected, rel=1e-3)

    def test_calc_edge_score_zero_values(self):
        """Test edge score calculation with zero values."""
        backtester = Backtester()
        weights = {'win_pct': 0.6, 'sharpe': 0.4}
        
        edge_score = backtester.calc_edge_score(0.0, 0.0, weights)
        assert edge_score == 0.0

    def test_calc_edge_score_custom_weights(self):
        """Test edge score calculation with custom weights."""
        backtester = Backtester()
        weights = {'win_pct': 0.8, 'sharpe': 0.2}
        
        edge_score = backtester.calc_edge_score(0.6, 2.0, weights)
        expected = (0.6 * 0.8) + (2.0 * 0.2)
        assert edge_score == pytest.approx(expected, rel=1e-3)

    def test_find_optimal_strategies_empty_list(self):
        """Test find_optimal_strategies with empty rule combinations list."""
        backtester = Backtester()
        
        # Create minimal price data for the test
        price_data = pd.DataFrame({
            'close': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'open': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        result = backtester.find_optimal_strategies([], price_data)
        assert result == []

    def test_generate_signals_empty_rule_stack(self, sample_price_data):
        """Test signal generation with an empty rule stack."""
        backtester = Backtester()
        rule_combo = {
            'rule_stack': [],
            'parameters': {}
        }
        
        entry_signals, exit_signals = backtester._generate_signals(rule_combo, sample_price_data)
        
        # With no rules, entry signals should be all True before exit logic
        assert entry_signals.all()
        assert entry_signals.dtype == bool
        # Exit signals should be generated for every entry
        assert exit_signals.sum() > 0

    def test_generate_signals_sma_crossover(self, sample_price_data):
        """Test signal generation with SMA crossover rule."""
        backtester = Backtester()
        
        rule_combo = {
            'rule_stack': ['sma_crossover'],
            'parameters': {
                'sma_crossover': {
                    'fast_period': 5,
                    'slow_period': 10
                }
            }
        }
        
        entry_signals, exit_signals = backtester._generate_signals(rule_combo, sample_price_data)
        assert isinstance(entry_signals, pd.Series)
        assert isinstance(exit_signals, pd.Series)
        assert len(entry_signals) == len(sample_price_data)
        assert len(exit_signals) == len(sample_price_data)
        assert entry_signals.dtype == bool
        assert exit_signals.dtype == bool

    def test_generate_signals_invalid_rule(self, sample_price_data):
        """Test signal generation with invalid rule name."""
        backtester = Backtester()
        
        rule_combo = {
            'rule_stack': ['nonexistent_rule'],
            'parameters': {}
        }
        
        with pytest.raises(ValueError, match="Rule function 'nonexistent_rule' not found"):
            backtester._generate_signals(rule_combo, sample_price_data)

    def test_generate_signals_missing_parameters(self, sample_price_data):
        """Test signal generation with missing rule parameters."""
        backtester = Backtester()
        
        rule_combo = {
            'rule_stack': ['sma_crossover'],
            'parameters': {}  # Missing sma_crossover parameters
        }
        
        with pytest.raises(ValueError, match="Missing parameters for rule 'sma_crossover'"):
            backtester._generate_signals(rule_combo, sample_price_data)

    def test_create_portfolio_basic(self, sample_price_data):
        """Test basic portfolio creation with entry/exit signals."""
        backtester = Backtester()
        
        # Create simple entry/exit signals
        entry_signals = pd.Series(False, index=sample_price_data.index)
        exit_signals = pd.Series(False, index=sample_price_data.index)
        
        # Add a few entry/exit pairs
        entry_signals.iloc[10] = True
        exit_signals.iloc[30] = True
        entry_signals.iloc[50] = True
        exit_signals.iloc[70] = True
        
        portfolio = backtester._create_portfolio(entry_signals, exit_signals, sample_price_data)
        
        # Verify portfolio object
        assert portfolio is not None
        assert hasattr(portfolio, 'total_return')
        assert hasattr(portfolio, 'trades')

    def test_create_portfolio_no_signals(self, sample_price_data):
        """Test portfolio creation with no signals."""
        backtester = Backtester()
          # No signals
        entry_signals = pd.Series(False, index=sample_price_data.index)
        exit_signals = pd.Series(False, index=sample_price_data.index)
        
        portfolio = backtester._create_portfolio(entry_signals, exit_signals, sample_price_data)
        
        assert isinstance(portfolio, vbt.Portfolio)
        stats = portfolio.stats()
        assert stats['Total Trades'] == 0

    def test_create_portfolio_mismatched_length(self, sample_price_data):
        """Test portfolio creation with mismatched signal lengths."""
        backtester = Backtester()
        # Mismatched length signals
        entry_signals = pd.Series(False, index=sample_price_data.index[:50])
        exit_signals = pd.Series(False, index=sample_price_data.index)
        # vectorbt should raise an error if signal/price shapes are incompatible
        with pytest.raises(Exception):
            backtester._create_portfolio(entry_signals, exit_signals, sample_price_data)

    def test_create_portfolio_invalid_signals(self, sample_price_data):
        """Test error on mismatched entry/exit signals."""
        backtester = Backtester()
        entry_signals = pd.Series([True, False, True], index=sample_price_data.index[:3])
        exit_signals = pd.Series([False, True, False], index=sample_price_data.index[:3])
        with pytest.raises(Exception):
            backtester._create_portfolio(entry_signals, exit_signals, sample_price_data)

@pytest.fixture
def sample_price_data():
    """Generate sample OHLCV price data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)  # For reproducible test data
    
    # Generate realistic price data with some trend
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)  # 0.1% daily return, 2% volatility
    prices = [base_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    closes = prices[1:]  # Remove initial base price
    
    # Generate OHLC from close prices
    data = {
        'date': dates,
        'open': [c * np.random.uniform(0.99, 1.01) for c in closes],
        'high': [c * np.random.uniform(1.00, 1.03) for c in closes],
        'low': [c * np.random.uniform(0.97, 1.00) for c in closes],
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    }
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


@pytest.fixture
def sample_rule_combinations():
    """Generate sample rule combinations for testing."""
    return [
        {
            'rule_stack': ['sma_crossover'],
            'parameters': {
                'sma_crossover': {
                    'fast_period': 10,
                    'slow_period': 20
                }
            }
        },
        {
            'rule_stack': ['rsi_oversold'],
            'parameters': {
                'rsi_oversold': {
                    'period': 14, 'oversold_threshold': 30.0
                }
            }
        }
    ]


class TestBacktesterIntegration:
    """Integration tests for backtester with sample data."""

    def test_find_optimal_strategies_basic_flow(self, sample_price_data, sample_rule_combinations):
        """Test basic flow of find_optimal_strategies with sample data."""
        backtester = Backtester()
          # This test will run the full logic, but we just check the output type for now
        result = backtester.find_optimal_strategies(sample_rule_combinations, sample_price_data)
        assert isinstance(result, list)
        # TODO: Add more assertions once implementation is complete


def create_sample_backtest_data():
    """Create sample backtest data CSV file for testing."""
    data_dir = Path(__file__).parent / "fixtures"
    data_dir.mkdir(exist_ok=True)
    
    # Generate exactly 100 days of sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(123)  # For reproducible test data
    
    # Create realistic price movement
    base_price = 100.0
    returns = np.random.normal(0.0005, 0.015, 100)  # Slight positive drift, realistic volatility
    prices = [base_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    closes = prices[1:]
    
    # Generate OHLC with realistic intraday movement
    data = {
        'Date': dates,
        'Open': [c * np.random.uniform(0.995, 1.005) for c in closes],
        'High': [c * np.random.uniform(1.005, 1.025) for c in closes],
        'Low': [c * np.random.uniform(0.975, 0.995) for c in closes],
        'Close': closes,
        'Volume': np.random.randint(500000, 2000000, 100)
    }
    
    df = pd.DataFrame(data)
    output_path = data_dir / "sample_backtest_data.csv"
    df.to_csv(output_path, index=False)
    
    return output_path


@pytest.fixture
def sample_backtest_data():
    """Load sample backtest data from CSV file, generating it if missing."""
    csv_path = Path(__file__).parent / "fixtures" / "sample_backtest_data.csv"
    if not csv_path.exists():
        # Generate the sample data dynamically instead of skipping
        fixtures_dir = csv_path.parent
        create_sample_backtest_data(fixtures_dir)
    
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    # Enforce the lowercase column contract at the data source (the fixture).
    df.columns = [col.lower() for col in df.columns]
    return df


class TestBacktesterFixtures:
    """Test backtester fixtures and data loading."""
    
    def test_sample_backtest_data_fixture(self, sample_backtest_data: pd.DataFrame) -> None:
        """Test that sample backtest data fixture works correctly."""
        assert sample_backtest_data is not None
        assert isinstance(sample_backtest_data, pd.DataFrame)
        assert len(sample_backtest_data) == 100
        assert list(sample_backtest_data.columns) == ['open', 'high', 'low', 'close', 'volume']
        # Verify data quality - all prices should be positive
        assert (sample_backtest_data['close'] > 0).all()
        assert (sample_backtest_data['open'] > 0).all()
        assert (sample_backtest_data['high'] > 0).all()
        assert (sample_backtest_data['low'] > 0).all()
        assert (sample_backtest_data['volume'] > 0).all()
        # Verify OHLC relationships
        assert (sample_backtest_data['high'] >= sample_backtest_data['low']).all()
        assert (sample_backtest_data['close'] >= sample_backtest_data['low']).all()
        assert (sample_backtest_data['close'] <= sample_backtest_data['high']).all()


if __name__ == "__main__":
    # Create sample data file when run directly
    output_path = create_sample_backtest_data()
    print(f"Sample backtest data created at: {output_path}")
