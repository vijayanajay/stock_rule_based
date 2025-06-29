"""
Tests for the reporter module - Signal Checking.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path # Not directly used by TestCheckForSignal, but common in tests
import pandas as pd

from src.kiss_signal import reporter
# Config and other fixtures like sample_strategies, sample_rules_config might not be needed
# if TestCheckForSignal only uses sample_price_data.


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    dates = pd.date_range('2025-01-01', periods=30, freq='D')
    return pd.DataFrame({
        'open': [100 + i for i in range(30)],
        'high': [105 + i for i in range(30)],
        'low': [95 + i for i in range(30)],
        'close': [102 + i for i in range(30)],
        'volume': [1000000] * 30
    }, index=dates)


class TestCheckForSignal:
    """Test _check_for_signal private function."""

    def test_check_signal_with_valid_rule(self, sample_price_data):
        """Test signal checking with valid rule."""
        rule_def = {
            'type': 'sma_crossover',
            'params': {'short_window': 5, 'long_window': 10}
        }

        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            # Mock rule function that returns signals
            mock_func = Mock()
            mock_signals = pd.Series([False] * 29 + [True], index=sample_price_data.index)
            mock_func.return_value = mock_signals
            mock_rules.sma_crossover = mock_func

            result = reporter._check_for_signal(sample_price_data, rule_def)

            assert result is True
            mock_func.assert_called_once_with(sample_price_data, short_window=5, long_window=10)

    def test_check_signal_no_signal(self, sample_price_data):
        """Test when rule returns no signal."""
        rule_def = {
            'type': 'sma_crossover',
            'params': {'short_window': 5, 'long_window': 10}
        }

        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_func = Mock()
            mock_signals = pd.Series([False] * 30, index=sample_price_data.index)
            mock_func.return_value = mock_signals
            mock_rules.sma_crossover = mock_func

            result = reporter._check_for_signal(sample_price_data, rule_def)

            assert result is False

    def test_check_signal_empty_data(self):
        """Test with empty price data."""
        empty_data = pd.DataFrame()
        rule_def = {'type': 'sma_crossover', 'params': {}}

        result = reporter._check_for_signal(empty_data, rule_def)
        assert result is False

    def test_check_signal_unknown_rule(self, sample_price_data):
        """Test with unknown rule type."""
        rule_def = {'type': 'unknown_rule', 'params': {}}

        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_rules.unknown_rule = None
            del mock_rules.unknown_rule  # Simulate missing attribute

            result = reporter._check_for_signal(sample_price_data, rule_def)
            assert result is False

    def test_check_signal_rule_exception(self, sample_price_data):
        """Test when rule function raises exception."""
        rule_def = {'type': 'sma_crossover', 'params': {}}

        with patch('src.kiss_signal.reporter.rules') as mock_rules:
            mock_func = Mock(side_effect=Exception("Rule error"))
            mock_rules.sma_crossover = mock_func

            result = reporter._check_for_signal(sample_price_data, rule_def)
            assert result is False
