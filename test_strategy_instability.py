#!/usr/bin/env python3
"""Test script for strategy instability detection."""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kiss_signal.backtester import Backtester
from kiss_signal.config import EdgeScoreWeights

@pytest.fixture
def backtester_instance():
    """Provides a Backtester instance for tests."""
    return Backtester()

@pytest.fixture
def unstable_oos_results():
    """Provides a list of OOS results with unstable strategies."""
    # Create mock OOS results with different strategies per period
    return [
        {
            "symbol": "TEST",
            "rule_stack": [{"name": "sma_cross", "type": "sma_crossover", "params": {"short": 10, "long": 20}}],
            "edge_score": 0.7,
            "win_pct": 0.6,
            "sharpe": 1.2,
            "total_trades": 15,
            "avg_return": 0.05,
            "oos_period_start": "2021-01-01",
            "oos_test_start": "2021-07-01",
            "oos_test_end": "2021-09-30"
        },
        {
            "symbol": "TEST", 
            "rule_stack": [{"name": "rsi_signal", "type": "rsi_oversold", "params": {"threshold": 30}}],
            "edge_score": 0.8,
            "win_pct": 0.65,
            "sharpe": 1.5,
            "total_trades": 12,
            "avg_return": 0.07,
            "oos_period_start": "2021-04-01",
            "oos_test_start": "2021-10-01", 
            "oos_test_end": "2021-12-31"
        },
        {
            "symbol": "TEST",
            "rule_stack": [{"name": "volume_spike", "type": "volume_spike", "params": {"period": 20}}],
            "edge_score": 0.6,
            "win_pct": 0.55,
            "sharpe": 1.0,
            "total_trades": 18,
            "avg_return": 0.03,
            "oos_period_start": "2021-07-01",
            "oos_test_start": "2022-01-01",
            "oos_test_end": "2022-03-31"
        }
    ]

@pytest.fixture
def stable_oos_results():
    """Provides a list of OOS results with a stable strategy."""
    # Test with stable strategies (same rule across periods)
    return [
        {
            "symbol": "TEST",
            "rule_stack": [{"name": "sma_cross", "type": "sma_crossover", "params": {"short": 10, "long": 20}}],
            "edge_score": 0.7,
            "win_pct": 0.6,
            "sharpe": 1.2,
            "total_trades": 15,
            "avg_return": 0.05,
            "oos_period_start": "2021-01-01"
        },
        {
            "symbol": "TEST",
            "rule_stack": [{"name": "sma_cross", "type": "sma_crossover", "params": {"short": 10, "long": 20}}],
            "edge_score": 0.8,
            "win_pct": 0.65,
            "sharpe": 1.5,
            "total_trades": 12,
            "avg_return": 0.07,
            "oos_period_start": "2021-04-01"
        }
    ]

def test_strategy_instability_is_detected(backtester_instance, unstable_oos_results):
    """Verify that unstable strategies trigger an instability warning."""
    result = backtester_instance._consolidate_oos_results(unstable_oos_results, "TEST", EdgeScoreWeights(win_pct=0.6, sharpe=0.4))
    assert result['strategy_stability_score'] < 0.7
    assert result['strategy_instability_warning'] is not None
    assert "STRATEGY INSTABILITY DETECTED" in result['strategy_instability_warning']

def test_strategy_stability_is_detected(backtester_instance, stable_oos_results):
    """Verify that stable strategies do not trigger an instability warning."""
    stable_result = backtester_instance._consolidate_oos_results(stable_oos_results, "TEST", EdgeScoreWeights(win_pct=0.6, sharpe=0.4))
    assert stable_result['strategy_stability_score'] >= 0.9
    assert stable_result['strategy_instability_warning'] is None
