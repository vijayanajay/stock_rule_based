"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

import yaml
import pandas as pd
from kiss_signal.config import Config


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


@pytest.fixture
def simple_price_data():
    """Simple 3-day OHLCV data for basic testing and validation."""
    return pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000, 1000, 1000]
    }, index=pd.date_range('2023-01-01', periods=3, freq='D'))


@pytest.fixture
def trending_price_data():
    """Generate trending price data for crossover and signal testing."""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    # Create trending price data that should trigger crossovers
    base_price = 100
    trend = 0.5  # Positive trend
    
    prices = []
    for i in range(len(dates)):
        price = base_price + trend * i + (i % 5 - 2)  # Add some volatility
        prices.append(price)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000 + i * 10 for i in range(len(dates))]
    }, index=dates)


@pytest.fixture
def test_environment(tmp_path: Path) -> Path:
    """Create a test environment with necessary directories and files."""
    # Create required directories
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_dir = data_dir / "cache"
    cache_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    
    # Create config files
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(yaml.dump({
        "universe_path": "data/nifty_large_mid.csv",
        "historical_data_years": 1,
        "cache_dir": "data/cache",
        "cache_refresh_days": 30,
        "hold_period": 20,
        "min_trades_threshold": 10,
        "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
        "database_path": "data/test.db",
        "reports_output_dir": "reports/",
        "edge_score_threshold": 0.5,
        "portfolio_initial_capital": 100000.0,
        "risk_per_trade_pct": 0.01,
        "seeker_min_edge_score": 0.60,
        "seeker_min_trades": 20
    }))
    
    rules_yaml = config_dir / "rules.yaml"
    rules_yaml.write_text("""
entry_signals:
  - name: "test_baseline"
    type: "sma_crossover"
    params:
      fast_period: 5
      slow_period: 10
""")
    
    # Create universe file
    universe_file = data_dir / "nifty_large_mid.csv"
    universe_file.write_text("symbol,name\nRELIANCE.NS,Reliance Industries\nTCS.NS,TCS\n")
    
    return tmp_path


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Create a test Config object."""
    universe_file = tmp_path / "test_universe.csv"
    universe_file.write_text("symbol,name\nRELIANCE.NS,Reliance Industries\nTCS.NS,TCS\n")
    
    config_data = {
        "universe_path": str(universe_file),
        "historical_data_years": 1,
        "cache_dir": str(tmp_path / "cache/"),
        "cache_refresh_days": 30,
        "hold_period": 20,
        "min_trades_threshold": 10,
        "edge_score_weights": {"win_pct": 0.6, "sharpe": 0.4},
        "database_path": str(tmp_path / "test.db"),
        "reports_output_dir": str(tmp_path / "reports/"),
        "edge_score_threshold": 0.5
    }
    return Config(**config_data)
