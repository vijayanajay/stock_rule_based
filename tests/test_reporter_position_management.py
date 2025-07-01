"""
Tests for the reporter module - Position Management.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import date
import pandas as pd

from src.kiss_signal import reporter
from src.kiss_signal.config import Config

@pytest.fixture
def config_fixture(tmp_path: Path) -> Config:
    """Provides a Config object for testing."""
    universe_file = tmp_path / "universe.csv"
    universe_file.write_text("symbol\nRELIANCE\n")
    return Config(
        universe_path=str(universe_file),
        historical_data_years=1,
        cache_dir=str(tmp_path / "cache"),
        cache_refresh_days=30,
        hold_period=20,
        min_trades_threshold=5,
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        database_path=str(tmp_path / "test.db"),
        reports_output_dir=str(tmp_path / "reports"),
        edge_score_threshold=0.50,
        freeze_date=date(2025, 7, 1)
    )

class TestPositionManagement:
    """Tests for position management logic in the reporter."""

    @patch('src.kiss_signal.data.get_price_data')
    def test_manage_open_positions(self, mock_get_price_data, config_fixture: Config):
        """Test separation of positions to hold and close."""
        open_positions = [
            {'id': 1, 'symbol': 'HOLD', 'entry_date': '2025-06-20', 'entry_price': 100.0},
            {'id': 2, 'symbol': 'CLOSE', 'entry_date': '2025-06-01', 'entry_price': 200.0},
        ]

        def get_mock_data(symbol, **kwargs):
            if symbol == 'CLOSE':
                return pd.DataFrame({'close': [220.0]}, index=[pd.to_datetime('2025-07-01')])
            if symbol == '^NSEI':
                return pd.DataFrame({'close': [10000, 10100]}, index=pd.to_datetime(['2025-06-01', '2025-07-01']))
            return None
        mock_get_price_data.side_effect = get_mock_data

        to_hold, to_close = reporter._manage_open_positions(open_positions, config_fixture)

        assert len(to_hold) == 1
        assert to_hold[0]['symbol'] == 'HOLD'
        
        assert len(to_close) == 1
        assert to_close[0]['symbol'] == 'CLOSE'
        assert to_close[0]['exit_price'] == 220.0
        assert to_close[0]['final_return_pct'] == pytest.approx(10.0)
        assert to_close[0]['final_nifty_return_pct'] == pytest.approx(1.0)

    @patch('src.kiss_signal.data.get_price_data')
    def test_calculate_open_position_metrics(self, mock_get_price_data, config_fixture: Config):
        """Test calculation of metrics for open positions."""
        open_positions = [
            {'symbol': 'METRIC', 'entry_date': '2025-06-15', 'entry_price': 50.0}
        ]

        def get_mock_data(symbol, **kwargs):
            if symbol == 'METRIC':
                return pd.DataFrame({'close': [55.0]}, index=[pd.to_datetime('2025-07-01')])
            if symbol == '^NSEI':
                return pd.DataFrame({'close': [10000, 9900]}, index=pd.to_datetime(['2025-06-15', '2025-07-01']))
            return None
        mock_get_price_data.side_effect = get_mock_data

        augmented = reporter._calculate_open_position_metrics(open_positions, config_fixture)

        assert len(augmented) == 1
        pos = augmented[0]
        assert pos['symbol'] == 'METRIC'
        assert pos['current_price'] == 55.0
        assert pos['return_pct'] == pytest.approx(10.0)
        assert pos['nifty_return_pct'] == pytest.approx(-1.0)
        assert pos['days_held'] == 16
