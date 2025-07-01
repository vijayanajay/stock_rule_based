"""
Tests for the reporter module - Identify New Signals Edge Cases.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import pandas as pd

from src.kiss_signal import reporter
from src.kiss_signal.config import Config # Already imported by local sample_config, but good for clarity if removing local.

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


class TestIdentifyNewSignalsEdgeCases:
    """Edge case tests for _identify_new_signals."""

    @patch('src.kiss_signal.reporter.data.get_price_data', side_effect=Exception("Data load failed"))
    def test_identify_signals_data_load_failure(self, mock_get_price_data, tmp_path, reporter_config_obj_fixture):
        """Test signal identification when data loading fails."""
        # db_path = tmp_path / "test.db" # Using path from fixture
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir exists

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', '[{"type": "sma_crossover"}]', 0.7, 'test_run', 0.5, 1.0, 10, 0.01)
            )

        result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0

    def test_identify_signals_json_decode_error(self, tmp_path, reporter_config_obj_fixture):
        """Test signal identification when rule_stack is invalid JSON."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', 'this is not json', 0.7, 'test_run', 0.5, 1.0, 10, 0.01) # Invalid JSON
            )

        # Mock get_price_data to avoid actual data fetching for this specific test
        with patch('src.kiss_signal.reporter.data.get_price_data') as mock_get_price:
            mock_get_price.return_value = pd.DataFrame({'close': [100]}) # Dummy DataFrame
            result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0
        # Add log check if possible, or ensure no exception is raised out

    def test_identify_signals_rule_stack_not_list(self, tmp_path, reporter_config_obj_fixture):
        """Test signal identification when rule_stack is valid JSON but not a list."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            # Test with a JSON object instead of a list
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', '{"type": "sma_crossover"}', 0.7, 'test_run', 0.5, 1.0, 10, 0.01)
            )
            # Test with null
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('INFY', 'null', 0.7, 'test_run', 0.5, 1.0, 10, 0.01)
            )

        with patch('src.kiss_signal.reporter.data.get_price_data') as mock_get_price:
            mock_get_price.return_value = pd.DataFrame({'close': [100]})
            result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0

    def test_identify_signals_empty_rule_stack_list(self, tmp_path, reporter_config_obj_fixture):
        """Test signal identification when rule_stack is an empty JSON list."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', '[]', 0.7, 'test_run', 0.5, 1.0, 10, 0.01) # Empty list
            )

        with patch('src.kiss_signal.reporter.data.get_price_data') as mock_get_price:
            mock_get_price.return_value = pd.DataFrame({'close': [100]})
            result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0

    def test_identify_signals_rule_def_not_dict(self, tmp_path, reporter_config_obj_fixture):
        """Test signal identification when a rule_def in stack is not a dict."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', '["not_a_dict"]', 0.7, 'test_run', 0.5, 1.0, 10, 0.01) # Rule def is a string
            )

        with patch('src.kiss_signal.reporter.data.get_price_data') as mock_get_price:
            mock_get_price.return_value = pd.DataFrame({'close': [100]})
            result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0

    @patch('src.kiss_signal.reporter._find_signals_in_window', side_effect=Exception("Unexpected signal check error"))
    @patch('src.kiss_signal.reporter.data.get_price_data')
    def test_identify_signals_unexpected_error_in_processing(
        self, mock_get_price_data, mock_find_signals, tmp_path, reporter_config_obj_fixture
    ):
        """Test generic exception handling during signal processing loop."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    symbol TEXT, rule_stack TEXT, edge_score REAL, run_timestamp TEXT,
                    win_pct REAL, sharpe REAL, total_trades INTEGER, avg_return REAL
                )
            """)
            conn.execute(
                "INSERT INTO strategies (symbol, rule_stack, edge_score, run_timestamp, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('RELIANCE', '[{"type": "sma_crossover"}]', 0.7, 'test_run', 0.5, 1.0, 10, 0.01)
            )

        mock_get_price_data.return_value = pd.DataFrame({'close': [100.0, 101.0]}, index=pd.to_datetime(['2023-01-01', '2023-01-02']))

        result = reporter._identify_new_signals(db_path, 'test_run', reporter_config_obj_fixture)
        assert len(result) == 0
        mock_find_signals.assert_called() # Ensure it was called before the error
