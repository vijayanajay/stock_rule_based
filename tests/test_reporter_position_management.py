"""
Tests for the reporter module - Position Management Edge Cases
(Calculating metrics for open positions and managing open/closed positions).
"""

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import pandas as pd

from src.kiss_signal import reporter
from src.kiss_signal.config import Config # Already imported by local sample_config

# @pytest.fixture
# def sample_config(tmp_path: Path): # Now using reporter_config_obj_fixture from conftest.py
#     """Sample config for testing."""
#     universe_file = tmp_path / "test_universe.txt"
#     universe_file.write_text("symbol\nRELIANCE\n")
#     return Config(
#         universe_path=str(tmp_path / "test_universe.txt"),
#         historical_data_years=3,
#         cache_dir=str(tmp_path / "test_cache/"),
#         cache_refresh_days=7,
#         hold_period=20,
#         min_trades_threshold=10,
#         edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
#         database_path=str(tmp_path / "test.db"),
#         reports_output_dir=str(tmp_path / "test_reports/"),
#         edge_score_threshold=0.50
#     )

class TestCalculateOpenPositionMetricsEdgeCases:
    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_calc_metrics_symbol_data_load_failure(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test metrics calculation when symbol's price data load fails."""
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': '2023-01-01', 'entry_price': 100.0}]

        # First call for symbol data (fails), second for Nifty (succeeds)
        mock_get_price_data.side_effect = [
            None,
            pd.DataFrame({'close': [22000.0, 22100.0]}, index=pd.to_datetime(['2023-01-01', date.today()]))
        ]

        result = reporter._calculate_open_position_metrics(open_positions, reporter_config_obj_fixture)

        assert len(result) == 1
        pos = result[0]
        assert pos['current_price'] is None
        assert pos['return_pct'] is None
        # Nifty calculation should still proceed if Nifty data is available
        # assert pos['nifty_return_pct'] is not None # This depends on how Nifty is handled if main symbol fails

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_calc_metrics_nifty_data_load_failure(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test metrics calculation when Nifty's price data load fails."""
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': '2023-01-01', 'entry_price': 100.0}]

        # First call for symbol data (succeeds), second for Nifty (fails)
        mock_get_price_data.side_effect = [
            pd.DataFrame({'close': [100.0, 105.0]}, index=pd.to_datetime(['2023-01-01', date.today()])),
            None
        ]

        result = reporter._calculate_open_position_metrics(open_positions, reporter_config_obj_fixture)

        assert len(result) == 1
        pos = result[0]
        assert pos['current_price'] == 105.0
        assert pos['return_pct'] is not None
        assert pos['nifty_return_pct'] == 0.0 # Should default to 0.0 or be None based on implementation

    @patch('src.kiss_signal.reporter.data.get_price_data', side_effect=Exception("Generic data error"))
    def test_calc_metrics_generic_exception(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test generic exception handling in _calculate_open_position_metrics."""
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': '2023-01-01', 'entry_price': 100.0}]

        result = reporter._calculate_open_position_metrics(open_positions, reporter_config_obj_fixture)

        assert len(result) == 1
        pos = result[0]
        assert pos['current_price'] is None
        assert pos['return_pct'] is None
        assert pos['nifty_return_pct'] is None # Or 0.0 depending on how it's initialized
        mock_get_price_data.assert_called()


class TestManageOpenPositionsEdgeCases:
    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_manage_pos_symbol_exit_data_failure(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test _manage_open_positions when symbol exit price data load fails."""
        today = date.today()
        # Position that should be closed
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': (today - timedelta(days=reporter_config_obj_fixture.hold_period + 5)).isoformat(), 'entry_price': 100.0}]

        mock_get_price_data.side_effect = [
            None, # Fails for RELIANCE exit price
            pd.DataFrame({'close': [22000.0, 22100.0]}, index=pd.to_datetime([(today - timedelta(days=reporter_config_obj_fixture.hold_period + 5)), today])) # Nifty succeeds
        ]

        _, positions_to_close = reporter._manage_open_positions(open_positions, reporter_config_obj_fixture)

        assert len(positions_to_close) == 1
        pos = positions_to_close[0]
        assert pos['exit_price'] is None
        assert pos['final_return_pct'] is None
        assert pos['final_nifty_return_pct'] is None # Corrected assertion

    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_manage_pos_nifty_exit_data_failure(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test _manage_open_positions when Nifty exit data load fails."""
        today = date.today()
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': (today - timedelta(days=reporter_config_obj_fixture.hold_period + 5)).isoformat(), 'entry_price': 100.0}]

        mock_get_price_data.side_effect = [
            pd.DataFrame({'close': [100.0, 105.0]}, index=pd.to_datetime([(today - timedelta(days=reporter_config_obj_fixture.hold_period + 5)), today])), # Symbol succeeds
            None # Nifty fails
        ]

        _, positions_to_close = reporter._manage_open_positions(open_positions, reporter_config_obj_fixture)

        assert len(positions_to_close) == 1
        pos = positions_to_close[0]
        assert pos['exit_price'] == 105.0
        assert pos['final_return_pct'] is not None
        assert pos['final_nifty_return_pct'] == 0.0 # Or None, check implementation

    @patch('src.kiss_signal.reporter.data.get_price_data', side_effect=Exception("Generic data error for manage"))
    def test_manage_pos_generic_exception(self, mock_get_price_data, reporter_config_obj_fixture):
        """Test generic exception handling in _manage_open_positions."""
        today = date.today()
        open_positions = [{'symbol': 'RELIANCE', 'entry_date': (today - timedelta(days=reporter_config_obj_fixture.hold_period + 5)).isoformat(), 'entry_price': 100.0}]

        _, positions_to_close = reporter._manage_open_positions(open_positions, reporter_config_obj_fixture)

        assert len(positions_to_close) == 1
        pos = positions_to_close[0]
        assert pos['exit_price'] is None
        assert pos['final_return_pct'] is None
        assert pos['final_nifty_return_pct'] is None # Or 0.0
        mock_get_price_data.assert_called()
