"""Integration tests for backtester functionality.

Tests specifically for backtester integration with rule configurations.
"""

import pytest
import pandas as pd
from datetime import date
import tempfile

from kiss_signal.config import RulesConfig, Config, WalkForwardConfig, EdgeScoreWeights
from kiss_signal.backtester import Backtester


class TestBacktesterRuleIntegration:
    """Tests specifically for backtester integration with rule configurations."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = [100 + i * 0.1 for i in range(100)]
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [1000] * 100
        }, index=dates)

    @pytest.fixture
    def test_config(self):
        """Create a proper Config object for testing."""
        # Create temporary files for required paths
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("symbol\nTEST.NS\n")
            universe_path = f.name
        
        return Config(
            universe_path=universe_path,
            historical_data_years=2,
            cache_dir="cache",
            hold_period=20,
            min_trades_threshold=5,
            database_path="test.db",
            reports_output_dir="reports",
            edge_score_threshold=0.6,
            walk_forward=WalkForwardConfig(
                enabled=True,
                training_period='60d',
                testing_period='20d',
                step_size='20d',
                min_trades_per_period=1
            ),
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
        )
    
    def test_rule_function_lookup(self):
        """Test that rule types from YAML map correctly to rule functions."""
        from kiss_signal import rules as rules_module
        
        # Test rule configurations from actual rules.yaml
        test_rules = [
            {'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}},
            {'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30}},
            {'type': 'ema_crossover', 'params': {'fast_period': 12, 'slow_period': 26}}
        ]
        
        for rule in test_rules:
            rule_type = rule['type']
            rule_function = getattr(rules_module, rule_type, None)
            assert rule_function is not None, f"Rule function {rule_type} not found"
            assert callable(rule_function), f"Rule {rule_type} is not callable"
    
    def test_rule_parameter_validation(self, sample_price_data):
        """Test that rule parameters are properly validated."""
        from kiss_signal.rules import sma_crossover, rsi_oversold, ema_crossover
        
        # Test each rule function with valid parameters
        sma_signals = sma_crossover(sample_price_data, fast_period=10, slow_period=20)
        assert isinstance(sma_signals, pd.Series)
        assert len(sma_signals) == len(sample_price_data)
        
        rsi_signals = rsi_oversold(sample_price_data, period=14, oversold_threshold=30.0)
        assert isinstance(rsi_signals, pd.Series)
        assert len(rsi_signals) == len(sample_price_data)
        
        ema_signals = ema_crossover(sample_price_data, fast_period=12, slow_period=26)
        assert isinstance(ema_signals, pd.Series)
        assert len(ema_signals) == len(sample_price_data)

    def test_backtester_with_real_rules(self, sample_price_data, test_config):
        """Test backtester with actual rule configurations."""
        # Create a minimal rules config as a dict
        rules_config = {
            'entry_signals': [
                {
                    'name': 'sma_10_20_crossover',
                    'type': 'sma_crossover',
                    'params': {'fast_period': 10, 'slow_period': 20}
                },
                {
                    'name': 'rsi_oversold_30',
                    'type': 'rsi_oversold',
                    'params': {'period': 14, 'oversold_threshold': 30.0}
                }
            ]
        }
        # Convert dict to Pydantic model as expected by the function
        rules_config_obj = RulesConfig(**rules_config)
        backtester = Backtester(hold_period=20, min_trades_threshold=5)

        # With small test data and insufficient RSI data, this should fail loudly
        with pytest.raises(ValueError, match="WALK-FORWARD FAILURE.*No valid out-of-sample results"):
            strategies = backtester.find_optimal_strategies(
                price_data=sample_price_data,
                rules_config=rules_config_obj,
                symbol='TEST',
                market_data=None,
                freeze_date=date(2023, 3, 31),
                config=test_config
            )
