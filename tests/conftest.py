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
