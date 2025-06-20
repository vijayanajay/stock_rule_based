"""Tests for Signal Generator module."""

import pytest
import pandas as pd
import numpy as np

from kiss_signal.signal_generator import SignalGenerator


class TestSignalGenerator:
    """Test suite for SignalGenerator class."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data that reliably generates SMA crossovers."""
        # Create data that starts in downtrend, then reverses to uptrend
        # This ensures slow SMA > fast SMA initially, then fast crosses above
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        
        prices = []
        for i in range(len(dates)):
            if i < 50:
                # Initial downtrend: slow SMA will be > fast SMA
                price = 120 - i * 0.8 + (i % 3 - 1) * 0.5
            else:
                # Strong uptrend: fast SMA will cross above slow SMA
                price = 70 + (i - 50) * 1.2 + (i % 3 - 1) * 0.5
            prices.append(max(price, 1.0))  # Ensure positive prices
        
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': [1000 + i * 10 for i in range(len(dates))]
        }, index=dates)
        df.index.name = 'Date'
        return df
    
    @pytest.fixture
    def sample_rules_config(self):
        """Sample rules configuration for testing."""
        return {
            "rules": [
                {
                    "name": "sma_10_20_crossover",
                    "type": "sma_crossover",
                    "params": {
                        "fast_period": 10,
                        "slow_period": 20
                    }
                },
                {
                    "name": "rsi_oversold_30",
                    "type": "rsi_oversold",
                    "params": {
                        "period": 14,
                        "oversold_threshold": 30.0
                    }
                },
                {
                    "name": "ema_12_26_crossover",
                    "type": "ema_crossover",
                    "params": {
                        "fast_period": 12,
                        "slow_period": 26
                    }
                }
            ]
        }
    
    @pytest.fixture
    def signal_generator(self, sample_rules_config):
        """Create SignalGenerator instance for testing."""
        return SignalGenerator(sample_rules_config, hold_period=20)
    
    def test_init_default_parameters(self, sample_rules_config):
        """Test initialization with default parameters."""
        generator = SignalGenerator(sample_rules_config)
        assert generator.hold_period == 20
        assert generator.rules_config == sample_rules_config
    
    def test_init_custom_hold_period(self, sample_rules_config):
        """Test initialization with custom hold period."""
        generator = SignalGenerator(sample_rules_config, hold_period=30)
        assert generator.hold_period == 30
    
    def test_evaluate_rule_sma_crossover(self, signal_generator, sample_price_data):
        """Test evaluate_rule with SMA crossover."""
        signals = signal_generator.evaluate_rule("sma_10_20_crossover", sample_price_data)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_price_data)
        assert signals.dtype == bool
        # Should have some signals in a trending market
        assert signals.sum() > 0
    
    def test_evaluate_rule_rsi_oversold(self, signal_generator, sample_price_data):
        """Test evaluate_rule with RSI oversold."""
        signals = signal_generator.evaluate_rule("rsi_oversold_30", sample_price_data)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_price_data)
        assert signals.dtype == bool
    
    def test_evaluate_rule_ema_crossover(self, signal_generator, sample_price_data):
        """Test evaluate_rule with EMA crossover."""
        signals = signal_generator.evaluate_rule("ema_12_26_crossover", sample_price_data)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_price_data)
        assert signals.dtype == bool
    
    def test_evaluate_rule_invalid_name(self, signal_generator, sample_price_data):
        """Test evaluate_rule with invalid rule name."""
        with pytest.raises(ValueError, match="Rule not found: invalid_rule"):
            signal_generator.evaluate_rule("invalid_rule", sample_price_data)
    
    def test_evaluate_rule_insufficient_data(self, signal_generator):
        """Test evaluate_rule with insufficient data."""
        # Create very small dataset
        dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
        small_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 1000, 1000, 1000, 1000]
        }, index=dates)
        
        # Should handle gracefully and return signals (even if all False)
        signals = signal_generator.evaluate_rule("sma_10_20_crossover", small_data)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(small_data)
    
    def test_generate_signals_single_rule(self, signal_generator, sample_price_data):
        """Test generate_signals with single rule."""
        rule_stack = ["sma_10_20_crossover"]
        signals = signal_generator.generate_signals("TEST.NS", sample_price_data, rule_stack)
        
        assert isinstance(signals, pd.DataFrame)
        
        if len(signals) > 0:
            # Check schema
            expected_columns = ['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata']
            assert all(col in signals.columns for col in expected_columns)
            
            # Check signal types
            signal_types = signals['signal_type'].unique()
            assert all(sig_type in ['BUY', 'SELL'] for sig_type in signal_types)
            
            # Check symbol
            assert all(signals['symbol'] == "TEST.NS")
            
            # Check rule_stack
            assert all(signals['rule_stack'].apply(lambda x: x == rule_stack))
    
    def test_generate_signals_multiple_rules_and_logic(self, signal_generator, sample_price_data):
        """Test generate_signals with multiple rules using AND logic."""
        rule_stack = ["sma_10_20_crossover", "rsi_oversold_30"]
        signals = signal_generator.generate_signals("TEST.NS", sample_price_data, rule_stack)
        
        assert isinstance(signals, pd.DataFrame)
        
        # Should have fewer signals than single rule due to AND logic
        single_rule_signals = signal_generator.generate_signals("TEST.NS", sample_price_data, ["sma_10_20_crossover"])
        
        if len(signals) > 0 and len(single_rule_signals) > 0:
            buy_signals = signals[signals['signal_type'] == 'BUY']
            single_buy_signals = single_rule_signals[single_rule_signals['signal_type'] == 'BUY']
            assert len(buy_signals) <= len(single_buy_signals)
    
    def test_generate_signals_time_based_exit(self, signal_generator, sample_price_data):
        """Test generate_signals creates time-based sell signals."""
        rule_stack = ["sma_10_20_crossover"]
        signals = signal_generator.generate_signals("TEST.NS", sample_price_data, rule_stack)
        
        if len(signals) > 0:
            buy_signals = signals[signals['signal_type'] == 'BUY']            
            sell_signals = signals[signals['signal_type'] == 'SELL']
            
            # Should have sell signals for buy signals with sufficient future data
            assert len(sell_signals) <= len(buy_signals)
            
            # Check sell signal metadata
            if len(sell_signals) > 0:
                sell_signal = sell_signals.iloc[0]
                assert sell_signal['metadata']['exit_reason'] == 'time_based'
                assert 'buy_timestamp' in sell_signal['metadata']
                assert 'buy_price' in sell_signal['metadata']
                assert 'sell_price' in sell_signal['metadata']

    def test_generate_signals_empty_rule_stack(self, signal_generator, sample_price_data):
        """Test generate_signals with empty rule stack."""
        signals = signal_generator.generate_signals("TEST.NS", sample_price_data, [])
        
        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == 0
        expected_columns = ['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata']
        assert all(col in signals.columns for col in expected_columns)

    def test_generate_signals_no_triggers(self, signal_generator):
        """Test generate_signals when no rules trigger."""
        # Create flat price data that won't trigger crossovers
        # Using lowercase columns to adhere to data contract
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        flat_data = pd.DataFrame({
            'open': [100] * 50,
            'high': [100.5] * 50,
            'low': [99.5] * 50,
            'close': [100] * 50,
            'volume': [1000] * 50
        }, index=dates)
        
        signals = signal_generator.generate_signals("TEST.NS", flat_data, ["sma_10_20_crossover"])
        
        assert isinstance(signals, pd.DataFrame)
        # May or may not have signals depending on the specific rule behavior
    
    def test_missing_price_data_columns(self, signal_generator):
        """Test generate_signals with missing required columns."""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        incomplete_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        }, index=dates)
        
        with pytest.raises(ValueError, match="price_data must have columns"):
            signal_generator.generate_signals("TEST.NS", incomplete_data, ["sma_10_20_crossover"])
    
    def test_invalid_price_data_index(self, signal_generator):
        """Test generate_signals with non-DateTimeIndex."""
        invalid_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1000, 1000]
        })  # No DateTimeIndex
        
        with pytest.raises(ValueError, match="price_data must have DateTimeIndex"):
            signal_generator.generate_signals("TEST.NS", invalid_data, ["sma_10_20_crossover"])
    
    def test_signal_deduplication(self, signal_generator, sample_price_data):
        """Test that duplicate signals are not generated."""
        rule_stack = ["sma_10_20_crossover"]
        signals = signal_generator.generate_signals("TEST.NS", sample_price_data, rule_stack)
        
        if len(signals) > 0:
            # Check for duplicate timestamps with same signal type
            buy_signals = signals[signals['signal_type'] == 'BUY']
            if len(buy_signals) > 1:
                timestamps = buy_signals['timestamp']
                assert len(timestamps) == len(timestamps.unique()), "Duplicate buy signals found"
    
    def test_create_empty_signals_dataframe(self, signal_generator):
        """Test _create_empty_signals_dataframe helper method."""
        empty_df = signal_generator._create_empty_signals_dataframe()
        
        assert isinstance(empty_df, pd.DataFrame)
        assert len(empty_df) == 0
        expected_columns = ['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata']
        assert list(empty_df.columns) == expected_columns
    
    def test_calculate_exit_date_sufficient_data(self, signal_generator, sample_price_data):
        """Test _calculate_exit_date with sufficient future data."""
        buy_date = sample_price_data.index[10]  # Pick a date with future data
        exit_date = signal_generator._calculate_exit_date(buy_date, sample_price_data.index)
        
        assert exit_date is not None
        assert exit_date > buy_date
        # Should be exactly hold_period days later (available trading days)
        future_dates = sample_price_data.index[sample_price_data.index > buy_date]
        expected_exit = future_dates[signal_generator.hold_period - 1]
        assert exit_date == expected_exit
    
    def test_calculate_exit_date_insufficient_data(self, signal_generator, sample_price_data):
        """Test _calculate_exit_date with insufficient future data."""
        buy_date = sample_price_data.index[-5]  # Pick a date near the end
        exit_date = signal_generator._calculate_exit_date(buy_date, sample_price_data.index)
        
        # Should return the last available date if insufficient data
        future_dates = sample_price_data.index[sample_price_data.index > buy_date]
        if len(future_dates) > 0:
            assert exit_date == future_dates[-1]
        else:
            assert exit_date is None
    
    def test_calculate_exit_date_no_future_data(self, signal_generator, sample_price_data):
        """Test _calculate_exit_date with no future data."""
        buy_date = sample_price_data.index[-1]  # Last date
        exit_date = signal_generator._calculate_exit_date(buy_date, sample_price_data.index)
        
        assert exit_date is None


class TestSignalGeneratorIntegration:
    """Integration tests for SignalGenerator with real data scenarios."""
    
    @pytest.fixture
    def real_price_data(self):
        """Load real price data from fixtures."""
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_backtest_data.csv')
        
        df = pd.read_csv(fixture_path)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # Ensure column names are lowercase for consistency
        df.columns = df.columns.str.lower()
        
        return df
    
    @pytest.fixture
    def full_rules_config(self):
        """Full rules configuration matching rules.yaml."""
        return {
            "rules": [
                {
                    "name": "sma_10_20_crossover",
                    "type": "sma_crossover",
                    "params": {
                        "fast_period": 10,
                        "slow_period": 20
                    }
                },
                {
                    "name": "rsi_oversold_30",
                    "type": "rsi_oversold",
                    "params": {
                        "period": 14,
                        "oversold_threshold": 30.0
                    }
                },
                {
                    "name": "ema_12_26_crossover",
                    "type": "ema_crossover",
                    "params": {
                        "fast_period": 12,
                        "slow_period": 26
                    }
                }
            ]
        }
    
    def test_integration_with_real_price_data(self, real_price_data, full_rules_config):
        """Test signal generation with real price data."""
        generator = SignalGenerator(full_rules_config, hold_period=20)
        
        # Test with single rule
        signals = generator.generate_signals("REAL.NS", real_price_data, ["sma_10_20_crossover"])
        
        assert isinstance(signals, pd.DataFrame)
        
        if len(signals) > 0:
            # Validate signal structure
            assert all(col in signals.columns for col in 
                      ['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata'])
            
            # Validate timestamps are within data range
            assert all(signals['timestamp'] >= real_price_data.index.min())
            assert all(signals['timestamp'] <= real_price_data.index.max())
            
            # Validate signal metadata
            for _, signal in signals.iterrows():
                assert signal['symbol'] == "REAL.NS"
                assert signal['signal_type'] in ['BUY', 'SELL']
                assert isinstance(signal['metadata'], dict)
    
    def test_integration_with_multiple_rules(self, real_price_data, full_rules_config):
        """Test signal generation with multiple rules."""
        generator = SignalGenerator(full_rules_config, hold_period=15)
        
        # Test with multiple rules
        rule_stack = ["sma_10_20_crossover", "ema_12_26_crossover"]
        signals = generator.generate_signals("MULTI.NS", real_price_data, rule_stack)
        
        assert isinstance(signals, pd.DataFrame)
        
        if len(signals) > 0:
            # Check that all signals have the correct rule stack
            for _, signal in signals.iterrows():
                assert signal['rule_stack'] == rule_stack
    
    def test_performance_with_large_dataset(self, full_rules_config):
        """Test performance with larger dataset."""
        # Create larger dataset
        dates = pd.date_range(start='2020-01-01', end='2024-01-01', freq='D')
        np.random.seed(42)
        
        large_data = pd.DataFrame({
            'open': np.random.normal(100, 10, len(dates)),
            'high': np.random.normal(105, 10, len(dates)),
            'low': np.random.normal(95, 10, len(dates)),
            'close': np.random.normal(100, 10, len(dates)),
            'volume': np.random.randint(10000, 1000000, len(dates))
        }, index=dates)
        
        generator = SignalGenerator(full_rules_config, hold_period=20)
        
        import time
        start_time = time.time()
        signals = generator.generate_signals("LARGE.NS", large_data, ["sma_10_20_crossover"])
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        assert execution_time < 5.0
        assert isinstance(signals, pd.DataFrame)


class TestSignalGeneratorFixtures:
    """Test signal generator fixtures and data loading."""
    
    def test_sample_signal_data_fixture(self):
        """Test that signal generator works with fixture data."""
        # This test ensures the signal generator can work with standard test fixtures
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        fixture_data = pd.DataFrame({
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        rules_config = {
            "rules": [
                {
                    "name": "test_sma",
                    "type": "sma_crossover",
                    "params": {"fast_period": 5, "slow_period": 10}
                }
            ]
        }
        
        generator = SignalGenerator(rules_config, hold_period=10)
        signals = generator.generate_signals("FIXTURE.NS", fixture_data, ["test_sma"])
        
        assert isinstance(signals, pd.DataFrame)
        # Fixture should produce some kind of result (even if empty)
        expected_columns = ['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata']
        assert all(col in signals.columns for col in expected_columns)
