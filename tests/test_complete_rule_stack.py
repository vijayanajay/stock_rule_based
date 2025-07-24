# tests/test_complete_rule_stack.py
"""Tests for the complete rule stack fix - ensuring all rules are stored in strategy results."""

import pytest
import pandas as pd
from datetime import date
from unittest.mock import Mock

from src.kiss_signal.backtester import Backtester
from src.kiss_signal.config import RulesConfig, RuleDef


class TestCompleteRuleStack:
    """Test that rule_stack includes all rules used in backtesting."""

    @pytest.fixture
    def sample_price_data(self):
        """Sample price data for testing."""
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        return pd.DataFrame({
            'Open': [100.0] * len(dates),
            'High': [105.0] * len(dates),
            'Low': [95.0] * len(dates),
            'Close': [102.0] * len(dates),
            'Volume': [1000000] * len(dates),
        }, index=dates)

    @pytest.fixture
    def rules_config_with_all_types(self):
        """Rules config with baseline, layers, context filters, and sell conditions."""
        return RulesConfig(
            baseline=RuleDef(
                name="strong_bullish_engulfing",
                type="engulfing_pattern",
                params={"min_body_ratio": 1.5},
                description="Baseline entry rule"
            ),
            layers=[
                RuleDef(
                    name="confirm_with_rsi_recovering",
                    type="rsi_oversold",
                    params={"period": 14, "oversold_threshold": 40.0},
                    description="Layer entry rule"
                )
            ],
            context_filters=[
                RuleDef(
                    name="filter_market_is_bullish",
                    type="market_condition_filter",
                    params={"lookback_period": 20},
                    description="Context filter rule"
                )
            ],
            sell_conditions=[
                RuleDef(
                    name="atr_stop_loss_2x",
                    type="atr_stop_loss",
                    params={"multiplier": 2.0, "period": 14},
                    description="ATR stop loss"
                ),
                RuleDef(
                    name="atr_take_profit_4x",
                    type="atr_take_profit",
                    params={"multiplier": 4.0, "period": 14},
                    description="ATR take profit"
                )
            ]
        )

    def test_rule_stack_includes_all_rule_types(self, sample_price_data, rules_config_with_all_types):
        """Test that rule_stack includes entry, context, and sell rules."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        # Mock the _backtest_combination method to return a valid strategy
        # without actually running the complex backtesting logic
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,  # This will be augmented by our fix
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        assert len(strategies) >= 2, "Should find at least two strategies (baseline, baseline+layer)"
        
        # Test the strategy with baseline + layer (should be the second one)
        baseline_plus_layer_strategy = None
        for strategy in strategies:
            entry_rule_names = [rule.name for rule in strategy['rule_stack'] 
                              if rule.name in ["strong_bullish_engulfing", "confirm_with_rsi_recovering"]]
            if len(entry_rule_names) == 2:  # This is the baseline + layer strategy
                baseline_plus_layer_strategy = strategy
                break
        
        assert baseline_plus_layer_strategy is not None, "Should find baseline + layer strategy"
        
        rule_stack = baseline_plus_layer_strategy['rule_stack']
        rule_names = [rule.name for rule in rule_stack]
        
        # Check that all rule types are present
        assert "strong_bullish_engulfing" in rule_names, "Baseline rule should be in rule_stack"
        assert "confirm_with_rsi_recovering" in rule_names, "Layer rule should be in rule_stack"
        assert "filter_market_is_bullish" in rule_names, "Context filter should be in rule_stack"
        assert "atr_stop_loss_2x" in rule_names, "Stop loss rule should be in rule_stack"
        assert "atr_take_profit_4x" in rule_names, "Take profit rule should be in rule_stack"

    def test_rule_stack_preserves_entry_rules_order(self, sample_price_data, rules_config_with_all_types):
        """Test that entry rules (baseline + layers) come first in rule_stack."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        # Find the strategy with baseline + layer
        baseline_plus_layer_strategy = None
        for strategy in strategies:
            entry_rule_names = [rule.name for rule in strategy['rule_stack'] 
                              if rule.name in ["strong_bullish_engulfing", "confirm_with_rsi_recovering"]]
            if len(entry_rule_names) == 2:  # This is the baseline + layer strategy
                baseline_plus_layer_strategy = strategy
                break
        
        assert baseline_plus_layer_strategy is not None, "Should find baseline + layer strategy"
        
        rule_stack = baseline_plus_layer_strategy['rule_stack']
        
        # Entry rules should be at the beginning
        assert rule_stack[0].name == "strong_bullish_engulfing", "Baseline should be first"
        assert rule_stack[1].name == "confirm_with_rsi_recovering", "Layer should be second"

    def test_rule_stack_includes_context_and_sell_rules_after_entry(self, sample_price_data, rules_config_with_all_types):
        """Test that context and sell rules are appended after entry rules."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        # Find the strategy with baseline + layer
        baseline_plus_layer_strategy = None
        for strategy in strategies:
            entry_rule_names = [rule.name for rule in strategy['rule_stack'] 
                              if rule.name in ["strong_bullish_engulfing", "confirm_with_rsi_recovering"]]
            if len(entry_rule_names) == 2:  # This is the baseline + layer strategy
                baseline_plus_layer_strategy = strategy
                break
        
        assert baseline_plus_layer_strategy is not None, "Should find baseline + layer strategy"
        
        rule_stack = baseline_plus_layer_strategy['rule_stack']
        rule_names = [rule.name for rule in rule_stack]
        
        # Find indices of different rule types
        baseline_idx = rule_names.index("strong_bullish_engulfing")
        layer_idx = rule_names.index("confirm_with_rsi_recovering")
        context_idx = rule_names.index("filter_market_is_bullish")
        stop_loss_idx = rule_names.index("atr_stop_loss_2x")
        take_profit_idx = rule_names.index("atr_take_profit_4x")
        
        # Entry rules should come before context and sell rules
        assert baseline_idx < context_idx, "Baseline should come before context filter"
        assert layer_idx < context_idx, "Layer should come before context filter"
        assert context_idx < stop_loss_idx, "Context filter should come before sell rules"
        assert context_idx < take_profit_idx, "Context filter should come before sell rules"

    def test_multiple_strategies_all_have_complete_rule_stack(self, sample_price_data, rules_config_with_all_types):
        """Test that all strategies in result have complete rule stacks."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        call_count = 0
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            nonlocal call_count
            call_count += 1
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5 - (call_count * 0.1),  # Different scores for sorting
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        # Should have baseline-only and baseline+layer strategies
        assert len(strategies) == 2, "Should have two strategies (baseline, baseline+layer)"
        
        for strategy in strategies:
            rule_names = [rule.name for rule in strategy['rule_stack']]
            
            # All strategies should have all rule types
            assert "filter_market_is_bullish" in rule_names, "All strategies should have context filter"
            assert "atr_stop_loss_2x" in rule_names, "All strategies should have stop loss"
            assert "atr_take_profit_4x" in rule_names, "All strategies should have take profit"

    def test_empty_context_and_sell_rules_handled_gracefully(self, sample_price_data):
        """Test that empty context filters and sell conditions are handled correctly."""
        rules_config = RulesConfig(
            baseline=RuleDef(
                name="strong_bullish_engulfing",
                type="engulfing_pattern",
                params={"min_body_ratio": 1.5},
                description="Baseline entry rule"
            ),
            layers=[],
            context_filters=[],  # Empty
            sell_conditions=[]   # Empty
        )
        
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config,
            symbol="TEST"
        )
        
        assert len(strategies) > 0, "Should handle empty lists gracefully"
        
        strategy = strategies[0]
        rule_names = [rule.name for rule in strategy['rule_stack']]
        
        # Should only have the baseline rule since context and sell are empty
        assert rule_names == ["strong_bullish_engulfing"], "Should only have baseline rule when others are empty"

    def test_baseline_only_strategy_includes_context_and_sell_rules(self, sample_price_data, rules_config_with_all_types):
        """Test that even baseline-only strategies get context and sell rules appended."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        # Find the baseline-only strategy
        baseline_only_strategy = None
        for strategy in strategies:
            entry_rule_names = [rule.name for rule in strategy['rule_stack'] 
                              if rule.name in ["strong_bullish_engulfing", "confirm_with_rsi_recovering"]]
            if len(entry_rule_names) == 1 and entry_rule_names[0] == "strong_bullish_engulfing":
                baseline_only_strategy = strategy
                break
        
        assert baseline_only_strategy is not None, "Should find baseline-only strategy"
        
        rule_stack = baseline_only_strategy['rule_stack']
        rule_names = [rule.name for rule in rule_stack]
        
        # Even baseline-only should have context and sell rules
        assert "strong_bullish_engulfing" in rule_names, "Baseline rule should be in rule_stack"
        assert "filter_market_is_bullish" in rule_names, "Context filter should be in rule_stack"
        assert "atr_stop_loss_2x" in rule_names, "Stop loss rule should be in rule_stack"
        assert "atr_take_profit_4x" in rule_names, "Take profit rule should be in rule_stack"
        
        # Should NOT have the layer rule
        assert "confirm_with_rsi_recovering" not in rule_names, "Layer rule should not be in baseline-only strategy"

    def test_rule_stack_preserves_rule_definitions_structure(self, sample_price_data, rules_config_with_all_types):
        """Test that rule definitions maintain their structure after augmentation."""
        backtester = Backtester(hold_period=20, min_trades_threshold=1)
        
        def mock_backtest_combination(combo, price_data, rules_config, edge_score_weights, symbol):
            return {
                'symbol': symbol,
                'rule_stack': combo,
                'edge_score': 0.5,
                'win_pct': 55.0,
                'sharpe': 0.3,
                'total_trades': 10,
                'avg_return': 5.0
            }
        
        backtester._backtest_combination = mock_backtest_combination
        
        strategies = backtester.find_optimal_strategies(
            price_data=sample_price_data,
            rules_config=rules_config_with_all_types,
            symbol="TEST"
        )
        
        strategy = strategies[0]
        rule_stack = strategy['rule_stack']
        
        # Check that each rule maintains its structure
        for rule in rule_stack:
            assert hasattr(rule, 'name'), "Rule should have name attribute"
            assert hasattr(rule, 'type'), "Rule should have type attribute"
            assert hasattr(rule, 'params'), "Rule should have params attribute"
            assert hasattr(rule, 'description'), "Rule should have description attribute"
