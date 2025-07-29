"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

import yaml


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing - COMPLETE config with all required fields."""
    return {
        "universe_path": "data/test_universe.csv",
        "historical_data_years": 1,
        "cache_dir": "data/test_cache",
        "hold_period": 20,
        "min_trades_threshold": 10,
        "edge_score_weights": {
            "win_pct": 0.6,
            "sharpe": 0.4
        },
        "database_path": "data/test_kiss_signal.db",
        "reports_output_dir": "test_reports/",
        "edge_score_threshold": 0.5,
        "freeze_date": None
    }


@pytest.fixture
def sample_rules() -> Dict[str, Any]:
    """Sample rules configuration for testing."""
    return {
        "rules": [
            {
                "name": "sma_crossover",
                "type": "trend",
                "enabled": True,
                "signal_type": "buy",
                "params": {
                    "fast_period": 10,
                    "slow_period": 20
                }
            }
        ],
        "max_rule_stack_size": 3,
        "min_rule_stack_size": 1,
        "exit_strategy": "time_based_only"
    }


@pytest.fixture
def config_file(temp_dir, sample_config):
    """Create temporary config.yaml file."""
    config_path = temp_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def rules_file(temp_dir, sample_rules):
    """Create temporary rules.yaml file."""
    rules_path = temp_dir / "rules.yaml"
    with open(rules_path, 'w') as f:
        yaml.dump(sample_rules, f)
    return rules_path


@pytest.fixture
def reporter_config_obj_fixture(tmp_path: Path) -> "Config":
    """Fixture for a Config object for reporter tests."""
    # Import moved inside fixture to avoid early module loading before coverage instrumentation
    from kiss_signal.config import Config
    
    db_file = tmp_path / "test.db"
    reports_dir = tmp_path / "test_reports/"
    # Create the dummy universe file that the Config object will validate
    dummy_universe = tmp_path / "test_universe.csv"
    dummy_universe.write_text("symbol\nTEST\n")
    return Config(
        universe_path=str(dummy_universe), # Use the path to the created file
        historical_data_years=1,
        cache_dir=str(tmp_path / "test_cache/"),
        cache_refresh_days=30,
        hold_period=5,
        min_trades_threshold=5, # Keep small for tests
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        database_path=str(db_file),
        reports_output_dir=str(reports_dir), # Corrected field name
        edge_score_threshold=0.50
    )
