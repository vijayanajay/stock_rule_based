"""Simplified tests for CLI min_trades parameter functionality."""

import pytest
from pathlib import Path
from typing import Any, Dict
import tempfile
from unittest.mock import patch, MagicMock

from kiss_signal.cli import _run_backtests
from kiss_signal.config import Config
import pandas as pd


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "database_path": "test_data/test.db",
        "cache_dir": "test_data/cache",
        "universe_path": "test_data/nifty_large_mid.csv",
        "historical_data_years": 2,
        "hold_period": 20,
        "min_trades_threshold": 10,
        "reports_output_dir": "test_data/reports",
        "edge_score_threshold": 0.5,
        "edge_score_weights": {
            "win_pct": 0.6,
            "sharpe": 0.4
        }
    }


class TestMinTradesParameter:
    """Test suite for min_trades parameter functionality."""

    def test_run_backtests_with_none_min_trades_uses_config_default(self, sample_config):
        """Test that _run_backtests uses config default when min_trades_threshold is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=None
                        )
                        
                        # Should use config's min_trades_threshold (10)
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=10
                        )

    def test_run_backtests_with_explicit_min_trades_overrides_config(self, sample_config):
        """Test that _run_backtests uses explicit min_trades_threshold when provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=5
                        )
                        
                        # Should use provided min_trades_threshold (5), not config (10)
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=5
                        )

    def test_run_backtests_with_zero_min_trades_saves_all_strategies(self, sample_config):
        """Test that min_trades_threshold=0 allows all strategies to be saved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file for validation
            universe_path = Path(temp_dir) / "nifty_large_mid.csv"
            universe_path.write_text("symbol,name,sector\nTEST,Test,IT\n")
            sample_config["universe_path"] = str(universe_path)
            
            app_config = Config(**sample_config)
        
            with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
                with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                    with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                        _run_backtests(
                            app_config=app_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=0
                        )
                        
                        # Should use min_trades_threshold=0 to save all strategies
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=0
                        )

    def test_run_backtests_falls_back_to_zero_when_getattr_default_used(self):
        """Test that _run_backtests falls back to 0 when getattr returns default."""
        # Create a mock config object that will return 0 as default for min_trades_threshold
        mock_config = MagicMock()
        mock_config.hold_period = 20
        
        with patch("kiss_signal.cli.backtester.Backtester") as mock_backtester:
            with patch("kiss_signal.cli.data.load_universe", return_value=["TEST"]):
                with patch("kiss_signal.cli._analyze_symbol", return_value=[]):
                    with patch("kiss_signal.cli.getattr") as mock_getattr:
                        # Mock getattr to return 20 for hold_period and 0 for min_trades_threshold (default)
                        def side_effect(obj, attr, default=None):
                            if attr == "hold_period":
                                return 20
                            elif attr == "min_trades_threshold":
                                return default  # Return the default value (0)
                            return getattr(obj, attr, default)
                        
                        mock_getattr.side_effect = side_effect
                        
                        _run_backtests(
                            app_config=mock_config,
                            rules_config={},
                            symbols=["TEST"],
                            freeze_date=None,
                            min_trades_threshold=None
                        )
                        
                        # Should fall back to 0 when getattr returns default
                        mock_backtester.assert_called_once_with(
                            hold_period=20,
                            min_trades_threshold=0
                        )


def test_min_trades_logic_directly():
    """Test the min_trades logic in isolation."""
    # Test case 1: min_trades_threshold provided
    threshold = 5 if 5 is not None else getattr(MagicMock(), "min_trades_threshold", 0)
    assert threshold == 5
    
    # Test case 2: min_trades_threshold is None, config has value
    mock_config = MagicMock()
    mock_config.min_trades_threshold = 10
    threshold = None if None is not None else getattr(mock_config, "min_trades_threshold", 0)
    assert threshold == 10
    
    # Test case 3: min_trades_threshold is None, config doesn't have value (uses default)
    mock_config_no_attr = MagicMock()
    del mock_config_no_attr.min_trades_threshold  # Remove the attribute
    threshold = None if None is not None else getattr(mock_config_no_attr, "min_trades_threshold", 0)
    assert threshold == 0
