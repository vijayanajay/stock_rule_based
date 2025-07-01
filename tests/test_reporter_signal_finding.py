"""
Tests for the reporter module - specifically for the new signal finding logic.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import sqlite3
import pandas as pd
from datetime import date, timedelta

from src.kiss_signal import reporter


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Provides a consistent mock DataFrame for signal testing."""
    dates = pd.to_datetime(pd.date_range(end=date.today(), periods=50, freq='D'))
    return pd.DataFrame({
        'open': [100] * 50, 'high': [100] * 50, 'low': [100] * 50,
        'close': [100 + i for i in range(50)], 'volume': [1000] * 50
    }, index=dates)


class TestFindSignalsInWindow:
    """Tests the _find_signals_in_window helper function."""

    def test_single_rule_with_signal(self, mock_price_data):
        """Test that a single rule producing a signal is handled correctly."""
        rule_stack = [{'type': 'sma_crossover', 'params': {}}]
        mock_signals = pd.Series([False] * 49 + [True], index=mock_price_data.index)

        with patch('src.kiss_signal.rules.sma_crossover', return_value=mock_signals) as mock_rule_func:
            result = reporter._find_signals_in_window(mock_price_data, rule_stack)
            mock_rule_func.assert_called_once()
            assert result.sum() == 1
            assert result.iloc[-1]

    def test_multiple_rules_and_logic(self, mock_price_data):
        """Test that multiple rules are correctly combined with AND logic."""
        rule_stack = [
            {'type': 'sma_crossover', 'params': {}},
            {'type': 'rsi_oversold', 'params': {}}
        ]
        signals_a = pd.Series([False, True, True, False], index=mock_price_data.index[:4])
        signals_b = pd.Series([False, True, False, True], index=mock_price_data.index[:4])

        with patch('src.kiss_signal.rules.sma_crossover', return_value=signals_a), \
             patch('src.kiss_signal.rules.rsi_oversold', return_value=signals_b):
            result = reporter._find_signals_in_window(mock_price_data.head(4), rule_stack)
            
            # Expected result is a logical AND of signals_a and signals_b
            expected = pd.Series([False, True, False, False], index=mock_price_data.index[:4])
            pd.testing.assert_series_equal(result, expected)
            assert result.sum() == 1

    def test_no_signals_produced(self, mock_price_data):
        """Test behavior when no rules trigger a signal."""
        rule_stack = [{'type': 'sma_crossover', 'params': {}}]
        mock_signals = pd.Series(False, index=mock_price_data.index)

        with patch('src.kiss_signal.rules.sma_crossover', return_value=mock_signals):
            result = reporter._find_signals_in_window(mock_price_data, rule_stack)
            assert result.sum() == 0

    def test_empty_data_or_rules(self, mock_price_data):
        """Test that empty inputs are handled gracefully."""
        # Empty rule stack
        result_empty_rules = reporter._find_signals_in_window(mock_price_data, [])
        assert result_empty_rules.sum() == 0

        # Empty price data
        result_empty_data = reporter._find_signals_in_window(pd.DataFrame(), [{'type': 'sma', 'params': {}}])
        assert result_empty_data.empty


class TestIdentifyNewSignalsWithWindow:
    """Tests the modified _identify_new_signals function."""

    @pytest.fixture
    def setup_db(self, tmp_path: Path):
        """Creates a temporary database with one optimal strategy."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """
)
            conn.execute(
                "INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('TEST', '[{"name": "test_rule", "type": "sma_crossover", "params": {}}]', 0.8, 'test_run', 0.6, 1.5, 20, 0.02)
            )
        return db_path

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_finds_signal_within_hold_period(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify a signal within the hold_period window is reported."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20 # Explicitly set for clarity
        
        # Mock data and signals
        mock_get_price.return_value = mock_price_data
        
        # Signal is 5 days ago (within 20-day window)
        signal_date = date.today() - timedelta(days=5)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date] = True
        
        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config)

            assert len(result) == 1
            assert result[0]['ticker'] == 'TEST'
            assert result[0]['date'] == signal_date.strftime('%Y-%m-%d')

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_ignores_signal_outside_hold_period(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify a signal outside the hold_period window is ignored."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20

        mock_get_price.return_value = mock_price_data
        
        # Signal is 25 days ago (outside 20-day window)
        signal_date = date.today() - timedelta(days=25)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date] = True

        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config)
            assert len(result) == 0

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_finds_multiple_recent_signals(self, mock_get_price, setup_db, reporter_config_obj_fixture, mock_price_data):
        """Verify multiple signals within the window are all reported."""
        db_path = setup_db
        config = reporter_config_obj_fixture
        config.hold_period = 20

        mock_get_price.return_value = mock_price_data
        
        # Signals at 3 and 10 days ago
        signal_date_1 = date.today() - timedelta(days=3)
        signal_date_2 = date.today() - timedelta(days=10)
        signals = pd.Series(False, index=mock_price_data.index)
        signals.loc[signals.index.date == signal_date_1] = True
        signals.loc[signals.index.date == signal_date_2] = True

        with patch('src.kiss_signal.reporter._find_signals_in_window', return_value=signals):
            result = reporter._identify_new_signals(db_path, 'test_run', config)
            
            assert len(result) == 2
            dates_found = {r['date'] for r in result}
            assert signal_date_1.strftime('%Y-%m-%d') in dates_found
            assert signal_date_2.strftime('%Y-%m-%d') in dates_found
