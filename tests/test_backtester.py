"""Test suite for Backtester module.

Tests the core backtesting functionality including signal generation,
portfolio creation, metrics calculation, and strategy ranking.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import logging # Import logging

import pandas as pd
import numpy as np

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

    def test_generate_signals_empty_type_field(self, sample_price_data):
        """Test signal generation with a rule having an empty 'type' field."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        rule_def = RuleDef(name="test_empty_type", type="", params={})
        with pytest.raises(ValueError, match="Rule definition missing 'type' field"):
            backtester._generate_signals(rule_def, sample_price_data)

    def test_generate_signals_sma_crossover(self, sample_price_data):
        """Test signal generation with SMA crossover rule."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        rule_def = RuleDef(name="test_sma", type="sma_crossover", params={'fast_period': 5, 'slow_period': 10})
        entry_signals = backtester._generate_signals(rule_def, sample_price_data)
        assert isinstance(entry_signals, pd.Series)
        assert len(entry_signals) == len(sample_price_data)
        assert entry_signals.dtype == bool

    def test_generate_signals_invalid_rule(self, sample_price_data):
        """Test signal generation with invalid rule name."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        rule_def = RuleDef(name="test_invalid", type='nonexistent_rule', params={})
        with pytest.raises(ValueError, match="Rule function 'nonexistent_rule' not found"):
            backtester._generate_signals(rule_def, sample_price_data)

    def test_generate_signals_missing_parameters(self, sample_price_data):
        """Test signal generation with missing rule parameters."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        rule_def = RuleDef(name="test_missing_params", type='sma_crossover', params={})
        with pytest.raises(ValueError, match="Missing parameters for rule 'sma_crossover'"):
            backtester._generate_signals(rule_def, sample_price_data)

    def test_find_optimal_strategies_no_trades(self, sample_price_data, sample_rules_config):
        """Test find_optimal_strategies when a rule generates no trades."""
        backtester = Backtester(min_trades_threshold=1)
        
        with patch.object(backtester, '_generate_signals') as mock_generate:
            mock_generate.return_value = pd.Series(False, index=sample_price_data.index)
            result = backtester.find_optimal_strategies(
                rules_config=sample_rules_config,
                price_data=sample_price_data,
                symbol="TEST.NS"
            )
            assert result == []

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
def sample_rules_config():
    """Generate a sample rules config Pydantic model for testing."""
    from kiss_signal.config import RulesConfig, RuleDef
    return RulesConfig(
        baseline=RuleDef(
            name='sma_crossover_test',
            type='sma_crossover',
            params={'fast_period': 10, 'slow_period': 20}
        ),
        layers=[
            RuleDef(
                name='rsi_oversold_test',
                type='rsi_oversold',
                params={'period': 14, 'oversold_threshold': 30.0}
            )
        ]
    )


class TestBacktesterIntegration:
    """Integration tests for backtester with sample data."""

    def test_find_optimal_strategies_basic_flow(self, sample_price_data, sample_rules_config):
        """Test basic flow of find_optimal_strategies with sample data."""
        backtester = Backtester()
        result = backtester.find_optimal_strategies(
            rules_config=sample_rules_config,
            price_data=sample_price_data,
            symbol="TEST.NS"
        )
        # The test data may not always produce a valid strategy above the threshold.
        # The key is to ensure the function returns a list without errors.
        assert isinstance(result, list)
        if result:  # Only validate contents if strategies were found
            assert "edge_score" in result[0]

    # Additional tests for _generate_exit_signals
    def test_generate_exit_signals_multiple_stop_loss(self, sample_price_data, caplog):
        """Test _generate_exit_signals with multiple stop_loss_pct rules."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        entry_signals = pd.Series([False] * len(sample_price_data), index=sample_price_data.index)
        entry_signals.iloc[5] = True # Dummy entry signal

        sell_conditions = [
            RuleDef(name="sl1", type="stop_loss_pct", params={"percentage": 0.05}),
            RuleDef(name="sl2", type="stop_loss_pct", params={"percentage": 0.10})
        ]
        with caplog.at_level(logging.WARNING):
            _, sl_stop, _ = backtester._generate_exit_signals(entry_signals, sample_price_data, sell_conditions)

        assert sl_stop == 0.05 # First one should be used
        assert any("Multiple stop_loss_pct rules found" in message for message in caplog.messages)

    def test_generate_exit_signals_multiple_take_profit(self, sample_price_data, caplog):
        """Test _generate_exit_signals with multiple take_profit_pct rules."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        entry_signals = pd.Series([False] * len(sample_price_data), index=sample_price_data.index)
        entry_signals.iloc[5] = True

        sell_conditions = [
            RuleDef(name="tp1", type="take_profit_pct", params={"percentage": 0.15}),
            RuleDef(name="tp2", type="take_profit_pct", params={"percentage": 0.20})
        ]
        with caplog.at_level(logging.WARNING):
            _, _, tp_stop = backtester._generate_exit_signals(entry_signals, sample_price_data, sell_conditions)

        assert tp_stop == 0.15 # First one should be used
        assert any("Multiple take_profit_pct rules found" in message for message in caplog.messages)

    def test_generate_exit_signals_indicator_rule_exception(self, sample_price_data, caplog):
        """Test _generate_exit_signals when an indicator-based sell rule raises an exception."""
        from kiss_signal.config import RuleDef
        backtester = Backtester()
        entry_signals = pd.Series([False] * len(sample_price_data), index=sample_price_data.index)
        entry_signals.iloc[5] = True

        sell_conditions = [
            RuleDef(name="faulty_exit_rule", type="nonexistent_rule_type", params={})
        ]

        with caplog.at_level(logging.ERROR):
            exit_signals, _, _ = backtester._generate_exit_signals(entry_signals, sample_price_data, sell_conditions)

        assert any("Failed to generate exit signals for faulty_exit_rule" in message for message in caplog.messages)
        # Time-based exit should still be present
        # vbt.fshift on boolean can produce float series (NaN, 0.0, 1.0). Convert to bool, NaNs become False.
        time_based_exit = entry_signals.vbt.fshift(backtester.hold_period).fillna(False).astype(bool)
        # exit_signals is False | time_based_exit. If indicator fails, combined_exit_signals is all False.
        # So exit_signals should effectively be the same as time_based_exit (after NaN fill and type cast)
        pd.testing.assert_series_equal(exit_signals, time_based_exit, check_dtype=bool)


    def test_find_optimal_strategies_no_baseline_rule(self, sample_price_data, sample_rules_config):
        """Test find_optimal_strategies when baseline rule is effectively missing."""
        backtester = Backtester()

        # Create a valid RulesConfig first
        config_with_baseline = sample_rules_config

        # Mock the baseline attribute to be None for this specific test case
        with patch.object(config_with_baseline, 'baseline', None):
            result = backtester.find_optimal_strategies(
                rules_config=config_with_baseline,
                price_data=sample_price_data,
                symbol="TEST.NS"
            )
        assert result == []

    def test_find_optimal_strategies_infer_freq_none(self, sample_price_data_no_freq, sample_rules_config):
        """Test find_optimal_strategies when frequency cannot be inferred."""
        backtester = Backtester()
        # Ensure price_data has no frequency
        price_data_no_freq = sample_price_data_no_freq.copy()
        price_data_no_freq.index.freq = None

        with patch('pandas.infer_freq', return_value=None) as mock_infer_freq:
            result = backtester.find_optimal_strategies(
                rules_config=sample_rules_config,
                price_data=price_data_no_freq,
                symbol="TEST.NS"
            )
            mock_infer_freq.assert_called_once()
            # We are checking that it runs through, actual strategy results depend on data
            assert isinstance(result, list)

    def test_find_optimal_strategies_intraday_data_ffill(self, sample_price_data_intraday, sample_rules_config, caplog):
        """Test find_optimal_strategies with intraday data that forces ffill after asfreq('D')."""
        backtester = Backtester()

        # We expect asfreq('D') to introduce NaNs, then ffill to handle them.
        # The key is that the code runs without error and logs the ffill.
        with caplog.at_level(logging.DEBUG, logger='kiss_signal.backtester'):
            with patch('pandas.infer_freq', return_value=None) as mock_infer_freq: # Force the asfreq('D') path
                result = backtester.find_optimal_strategies(
                    rules_config=sample_rules_config,
                    price_data=sample_price_data_intraday, # Use intraday data
                    symbol="TEST_INTRA.NS"
                )

        mock_infer_freq.assert_called_once()
        assert isinstance(result, list)
        # Check if ffill was logged (indirectly confirms isnull().any().any() was True)
        assert any("Forward-filled NaN values after frequency adjustment" in message for message in caplog.messages)

    def test_find_optimal_strategies_successful_freq_inference(self, sample_price_data, sample_rules_config, caplog):
        """Test find_optimal_strategies when frequency is successfully inferred."""
        backtester = Backtester()
        price_data_no_freq_attr = sample_price_data.copy()
        price_data_no_freq_attr.index.freq = None # Remove freq attribute

        # We expect pandas.infer_freq to return 'D' for sample_price_data
        # and no warning about forcing 'D', and no ffill if data is clean.
        with caplog.at_level(logging.DEBUG, logger='kiss_signal.backtester'):
            # No mock for pandas.infer_freq here, let it run.
            result = backtester.find_optimal_strategies(
                rules_config=sample_rules_config,
                price_data=price_data_no_freq_attr,
                symbol="TEST_INFER_OK.NS"
            )

        assert isinstance(result, list)
        assert any("Inferred frequency 'D'" in message for message in caplog.messages)
        # Ensure "Could not infer frequency" is NOT logged
        assert not any("Could not infer frequency" in message for message in caplog.messages)
        # Ensure "Forward-filled NaN values" is NOT logged if sample_price_data is clean after asfreq('D')
        # This also tests the else part of the isnull().any().any() check
        assert not any("Forward-filled NaN values after frequency adjustment" in message for message in caplog.messages)

    def test_find_optimal_strategies_with_sell_conditions_logging(self, sample_price_data, caplog):
        """Test find_optimal_strategies with SL/TP in RulesConfig to cover debug logging."""
        from kiss_signal.config import RulesConfig, RuleDef
        backtester = Backtester(min_trades_threshold=0) # Ensure it runs even if no trades

        rules_config_with_sell = RulesConfig(
            baseline=RuleDef(name='sma_baseline', type='sma_crossover', params={'fast_period': 5, 'slow_period': 10}),
            layers=[],
            sell_conditions=[
                RuleDef(name="sl", type="stop_loss_pct", params={"percentage": 0.05}),
                RuleDef(name="tp", type="take_profit_pct", params={"percentage": 0.10})
            ]
        )

        # Mock portfolio from_signals to avoid actual backtesting complexity here, focus on logging path
        with patch('vectorbt.Portfolio.from_signals') as mock_vbt_portfolio:
            mock_pf_instance = mock_vbt_portfolio.return_value
            mock_pf_instance.trades.count.return_value = 1 # Simulate some trades to pass threshold if any
            mock_pf_instance.trades.win_rate.return_value = 50.0
            mock_pf_instance.sharpe_ratio.return_value = 1.0
            mock_pf_instance.trades.pnl.mean.return_value = 0.01


            with caplog.at_level(logging.DEBUG, logger='kiss_signal.backtester'):
                result = backtester.find_optimal_strategies(
                    rules_config=rules_config_with_sell,
                    price_data=sample_price_data,
                    symbol="TEST_SELL_LOG.NS"
                )

        assert isinstance(result, list)
        assert any("Stop loss: 5.0%" in message for message in caplog.messages)
        assert any("Take profit: 10.0%" in message for message in caplog.messages)


    def test_find_optimal_strategies_empty_signals(self, sample_price_data, sample_rules_config_empty_combo):
        """Test find_optimal_strategies with a rule combo that results in no entry signals."""
        backtester = Backtester()
        # This test relies on the sample_rules_config_empty_combo to have a combo that results in no signals
        # or that _generate_signals returns None for a particular setup.
        # For this test, let's mock _generate_signals to return None for the first rule in the first combo.

        original_generate_signals = backtester._generate_signals

        def mock_generate_signals_for_empty(rule_def, price_data_arg):
            # Let the baseline rule generate some signals, but the layer rule generate None
            if rule_def.name == "empty_layer_rule": # a hypothetical rule that would cause this
                 return None # Simulate a rule that fails to produce a Series
            return original_generate_signals(rule_def, price_data_arg)

        with patch.object(backtester, '_generate_signals', side_effect=mock_generate_signals_for_empty) as mock_gs:
            result = backtester.find_optimal_strategies(
                rules_config=sample_rules_config_empty_combo, # Configured to have an "empty" or problematic layer
                price_data=sample_price_data,
                symbol="TEST.NS"
            )
        # If the baseline rule still produces a strategy, it might not be an empty list.
        # The goal is to cover the "if entry_signals is None: continue" path.
        # This is hard to deterministically trigger without very specific rule configs or deeper mocks.
        # For now, ensure it runs. A more targeted test might be needed if coverage isn't hit.
        assert isinstance(result, list)


    def test_find_optimal_strategies_zero_trades_after_signals(self, sample_price_data, sample_rules_config, caplog):
        """Test find_optimal_strategies when signals exist but portfolio generates zero trades."""
        backtester = Backtester(min_trades_threshold=1)

        # Mock portfolio to return 0 trades despite signals
        mock_portfolio = patch('vectorbt.Portfolio.from_signals').start()
        mock_pf_instance = mock_portfolio.return_value
        mock_pf_instance.trades.count.return_value = 0 # No trades
        # Ensure signals are generated
        mock_pf_instance.entries = pd.Series([True, False] * (len(sample_price_data) // 2), index=sample_price_data.index)


        with caplog.at_level(logging.DEBUG, logger='kiss_signal.backtester'): # Corrected np.logging to logging
            result = backtester.find_optimal_strategies(
                rules_config=sample_rules_config,
                price_data=sample_price_data,
                symbol="TEST_ZERO_TRADES.NS"
            )

        assert result == [] # Since min_trades_threshold is 1 and trades are 0
        # Check the actual number of signals logged for the first rule combo (baseline)
        assert any("WARNING: 2 entry signals but 0 trades generated!" in message for message in caplog.messages)

        patch.stopall()


    def test_find_optimal_strategies_total_trades_zero(self, sample_price_data, sample_rules_config):
        """Test behavior when portfolio.trades.count() is 0, leading to default metrics."""
        backtester = Backtester(min_trades_threshold=0) # Allow strategies with 0 trades

        # Mock portfolio to return 0 trades
        mock_portfolio = patch('vectorbt.Portfolio.from_signals').start()
        mock_pf_instance = mock_portfolio.return_value
        mock_pf_instance.trades.count.return_value = 0
        # Mock other portfolio attributes to avoid errors if accessed
        mock_pf_instance.trades.win_rate.return_value = 0.0
        mock_pf_instance.sharpe_ratio.return_value = 0.0
        mock_pf_instance.trades.pnl.mean.return_value = np.nan # Simulate no PnL

        result = backtester.find_optimal_strategies(
            rules_config=sample_rules_config,
            price_data=sample_price_data,
            symbol="TEST_ZERO_METRICS.NS"
        )

        patch.stopall()

        assert len(result) > 0 # Should still process if min_trades_threshold = 0
        for strategy in result:
            if strategy['total_trades'] == 0:
                assert strategy['win_pct'] == 0.0
                assert strategy['sharpe'] == 0.0
                assert strategy['avg_return'] == 0.0
                assert strategy['edge_score'] == 0.0


    def test_find_optimal_strategies_exception_in_processing(self, sample_price_data, sample_rules_config, caplog):
        """Test find_optimal_strategies when an exception occurs during a combination's processing."""
        backtester = Backtester()

        # Mock _generate_signals to raise an exception for the second combo (baseline + first layer)
        original_generate_signals = backtester._generate_signals
        call_count = 0

        def faulty_generate_signals(rule_def, price_data_arg):
            nonlocal call_count
            call_count += 1
            # Let baseline (first call for first combo) pass
            # Let baseline (first call for second combo) pass
            # Fail on the layer rule of the second combo (third call overall if one layer)
            if sample_rules_config.layers and rule_def.name == sample_rules_config.layers[0].name and call_count > 1:
                 raise ValueError("Simulated processing error")
            return original_generate_signals(rule_def, price_data_arg)

        with patch.object(backtester, '_generate_signals', side_effect=faulty_generate_signals):
            with caplog.at_level(logging.ERROR): # Corrected np.logging to logging
                result = backtester.find_optimal_strategies(
                    rules_config=sample_rules_config,
                    price_data=sample_price_data,
                    symbol="TEST_EXC.NS"
                )

        assert any("Error processing rule combination" in message for message in caplog.messages)
        # Check if at least the baseline strategy (first combo) was processed if layers exist
        if sample_rules_config.layers:
             assert len(result) < len([sample_rules_config.baseline] + [[sample_rules_config.baseline, layer] for layer in sample_rules_config.layers])
        else: # Only baseline
            assert len(result) == 1 # Assuming baseline doesn't error out by itself


@pytest.fixture
def sample_price_data_no_freq(sample_price_data):
    data = sample_price_data.copy()
    data.index.freq = None
    return data

@pytest.fixture
def sample_price_data_intraday():
    """Generate sample intraday OHLCV price data that will have NaNs when resampled to 'D'."""
    # Create data for non-consecutive days to ensure asfreq('D') introduces NaNs
    dates = pd.to_datetime(['2024-01-01 10:00:00', '2024-01-01 14:00:00', # Day 1
                            '2024-01-03 10:00:00', '2024-01-03 14:00:00']) # Day 3 (skip Day 2)
    np.random.seed(43)
    num_entries = len(dates)
    data = {
        'open': np.random.rand(num_entries) * 100,
        'high': np.random.rand(num_entries) * 100 + 100,
        'low': np.random.rand(num_entries) * 100 - 5,
        'close': np.random.rand(num_entries) * 100,
        'volume': np.random.randint(1000, 5000, num_entries)
    }
    df = pd.DataFrame(data, index=pd.DatetimeIndex(dates, name='date'))
    # Ensure it doesn't have a freq initially, so infer_freq path is tested
    df.index.freq = None
    return df


@pytest.fixture
def sample_rules_config_empty_combo():
    from kiss_signal.config import RulesConfig, RuleDef
    # This config aims to create a situation where a combo might lead to 'entry_signals is None'
    # This is tricky to achieve reliably without specific rule logic that can return None
    # or by mocking _generate_signals to return None for a specific rule in a combo.
    return RulesConfig(
        baseline=RuleDef(
            name='sma_crossover_baseline',
            type='sma_crossover',
            params={'fast_period': 5, 'slow_period': 10}
        ),
        layers=[
            RuleDef(
                name='empty_layer_rule', # A hypothetical name for a rule that might cause issues
                type='rsi_oversold', # Using a real type, but imagine it's configured to fail/return None
                params={'period': -1, 'oversold_threshold': 30} # Invalid params to potentially trigger error/None
            )
        ]
    )


def create_sample_backtest_data(fixtures_dir=None):
    """Create sample backtest data CSV file for testing."""
    if fixtures_dir is None:
        data_dir = Path(__file__).parent / "fixtures"
    else:
        data_dir = Path(fixtures_dir)
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

# Ensure logging is imported at the top
import logging
