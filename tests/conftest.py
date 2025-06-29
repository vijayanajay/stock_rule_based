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
    """Sample configuration for testing."""
    return {
        "universe_path": "data/nifty_large_mid.csv",
        "cache_dir": "data/cache",
        "hold_period": 20,
        "min_trades_threshold": 10,
        "edge_score_weights": {
            "win_pct": 0.6,
            "sharpe": 0.4
        },
        "historical_data_years": 3,
        "cache_refresh_days": 7,
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
    """
    Sample Config object specifically for reporter tests that need a Config instance.
    Uses tmp_path for unique paths per test.
    """
    from src.kiss_signal.config import Config # Local import to avoid circular dependency if Config uses fixtures

    # Create a minimal universe file for this config
    universe_file = tmp_path / "reporter_test_universe.txt"
    universe_file.write_text("symbol\nRELIANCE\n")

    db_file = tmp_path / "reporter_test.db"
    cache_dir = tmp_path / "reporter_test_cache"
    reports_dir = tmp_path / "reporter_test_reports"

    return Config(
        universe_path=str(universe_file),
        historical_data_years=1, # Keep small for tests
        cache_dir=str(cache_dir),
        cache_refresh_days=30,
        hold_period=20,
        min_trades_threshold=5, # Keep small for tests
        edge_score_weights={'win_pct': 0.6, 'sharpe': 0.4},
        database_path=str(db_file),
        reports_output_dir=str(reports_dir),
        edge_score_threshold=0.50,
        freeze_date=None
    )
