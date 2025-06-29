"""
Tests for the reporter module - Advanced functionality.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import pandas as pd

from src.kiss_signal import reporter, persistence
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

# Removed TestIdentifyNewSignalsEdgeCases as it's moved to test_reporter_identify_signals.py
# Removed TestCalculateOpenPositionMetricsEdgeCases and TestManageOpenPositionsEdgeCases
# as they are moved to test_reporter_position_management.py

# Removed TestReportFormatting as it will be in its own file or consolidated.

class TestGenerateDailyReport:
    """Test daily report generation."""
    
    @patch('src.kiss_signal.reporter.data.get_price_data')
    @patch('src.kiss_signal.reporter._identify_new_signals')
    def test_generate_report_with_positions(
        self, mock_identify_new_signals, mock_get_price_data, tmp_path, reporter_config_obj_fixture
    ):
        """Test report generation with new, open, and closed positions."""
        # 1. Setup
        db_path = Path(reporter_config_obj_fixture.database_path)
        reporter_output_dir = Path(reporter_config_obj_fixture.reports_output_dir)
        # sample_config is now reporter_config_obj_fixture, its attributes are already set by the fixture
        # reporter_config_obj_fixture.database_path = str(db_path) # No longer needed
        # reporter_config_obj_fixture.reports_output_dir = str(reporter_output_dir) # No longer needed
        # reporter_config_obj_fixture.hold_period = 20 # Use fixture's default or modify if test needs specific value
        
        today = date.today()
        persistence.create_database(db_path)
        with sqlite3.connect(str(db_path)) as conn:
            # Position to be closed (25 days old)
            conn.execute(
                "INSERT INTO positions (symbol, entry_date, entry_price, status, rule_stack_used) VALUES (?, ?, ?, ?, ?)",
                ('WIPRO', (today - timedelta(days=25)).isoformat(), 150.0, 'OPEN', '[]')
            )
            # Position to be held (5 days old)
            conn.execute(
                "INSERT INTO positions (symbol, entry_date, entry_price, status, rule_stack_used) VALUES (?, ?, ?, ?, ?)",
                ('RELIANCE', (today - timedelta(days=5)).isoformat(), 2900.0, 'OPEN', '[]')
            )
            conn.commit()

        # 2. Mock external dependencies
        mock_identify_new_signals.return_value = [
            {'ticker': 'INFY', 'date': today.isoformat(), 'entry_price': 1500.0, 'rule_stack': 'rsi_oversold', 'edge_score': 0.55}
        ]

        def get_mock_price_data(symbol, **kwargs):
            if symbol == 'RELIANCE':
                return pd.DataFrame({'close': [2950.0]}, index=[pd.to_datetime(today)])
            if symbol == 'WIPRO':
                return pd.DataFrame({'close': [160.0]}, index=[pd.to_datetime(today)])
            if symbol == '^NSEI':
                start = kwargs.get('start_date')
                end = kwargs.get('end_date')
                if start == (today - timedelta(days=5)):
                    return pd.DataFrame({'close': [22000.0, 22100.0]}, index=pd.to_datetime([start, end]))
                else: # For the closed position
                    return pd.DataFrame({'close': [21000.0, 21500.0]}, index=pd.to_datetime([start, end]))
            return pd.DataFrame()
        mock_get_price_data.side_effect = get_mock_price_data

        # 3. Run the function
        report_path = reporter.generate_daily_report(
            db_path=db_path,
            run_timestamp="test_run",
            config=sample_config,
        )
        
        # 4. Assertions
        assert report_path is not None
        assert report_path.exists()
        report_content = report_path.read_text()

        assert "**Summary:** 1 New Buy Signals, 1 Open Positions, 1 Positions to Sell." in report_content
        assert "INFY" in report_content and "1500.00" in report_content
        assert "RELIANCE" in report_content and "2900.00" in report_content and "2950.00" in report_content
        assert "WIPRO" in report_content and "End of 20-day holding period." in report_content

        # Verify DB state
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Check new position was added
            new_pos = conn.execute("SELECT * FROM positions WHERE symbol = 'INFY'").fetchone()
            assert new_pos is not None
            assert new_pos['status'] == 'OPEN'
            
            # Check WIPRO was closed
            closed_pos = conn.execute("SELECT * FROM positions WHERE symbol = 'WIPRO'").fetchone()
            assert closed_pos is not None
            assert closed_pos['status'] == 'CLOSED'
            assert closed_pos['exit_price'] == 160.0
            
            # Check RELIANCE is still open
            open_pos = conn.execute("SELECT * FROM positions WHERE symbol = 'RELIANCE'").fetchone()
            assert open_pos is not None
            assert open_pos['status'] == 'OPEN'
    
    @patch('src.kiss_signal.reporter.persistence.get_open_positions', return_value=[])
    @patch('src.kiss_signal.reporter._identify_new_signals', return_value=[])
    @patch('pathlib.Path.write_text', side_effect=OSError("Permission denied"))
    def test_generate_report_file_write_error(
        self, mock_write_text, mock_identify, mock_get_open, reporter_config_obj_fixture
    ):
        """Test that report generation handles file write errors gracefully."""
        db_path = Path(reporter_config_obj_fixture.database_path)
        db_path.touch()  # Ensure the db file exists for the call

        result = reporter.generate_daily_report(
            db_path=db_path,
            run_timestamp="test_run",
            config=reporter_config_obj_fixture,
        )
        assert result is None
        mock_write_text.assert_called_once()

    @patch('src.kiss_signal.reporter._identify_new_signals', side_effect=Exception("Signal ID failed"))
    def test_generate_report_generic_exception(self, mock_identify, tmp_path, reporter_config_obj_fixture):
        """Test that a generic exception is handled and returns None."""
        db_path = Path(reporter_config_obj_fixture.database_path) # Use path from fixture
        db_path.parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir for db exists
        persistence.create_database(db_path)
        
        report_path = reporter.generate_daily_report(
            db_path=db_path,
            run_timestamp="test_run",
            config=reporter_config_obj_fixture,
        )
        assert report_path is None
