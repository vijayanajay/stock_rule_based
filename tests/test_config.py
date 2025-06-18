"""Tests for configuration module."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from kiss_signal.config import Config, EdgeScoreWeights, load_config


def test_edge_score_weights_valid():
    """Test valid EdgeScoreWeights."""
    weights = EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
    assert weights.win_pct == 0.6
    assert weights.sharpe == 0.4


def test_edge_score_weights_invalid_sum():
    """Test EdgeScoreWeights with invalid sum."""
    with pytest.raises(ValidationError):
        EdgeScoreWeights(win_pct=0.5, sharpe=0.6)  # Sum = 1.1


def test_config_validation(sample_config):
    """Test Config model validation."""
    with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
        sample_config["universe_path"] = fp.name
        config = Config(**sample_config)
        assert config.hold_period == 20
        assert config.edge_score_weights.win_pct == 0.6


def test_load_config(temp_dir, sample_config):
    """Test config loading from file."""
    universe_file = temp_dir / "universe.csv"
    universe_file.touch()
    sample_config["universe_path"] = str(universe_file)
    config_path = temp_dir / "config.yaml"
    config_path.write_text(yaml.dump(sample_config))
    config = load_config(config_path)
    assert config.hold_period == 20
    assert config.min_trades_threshold == 10
    assert config.min_trades_threshold == 10


def test_load_config_missing_file():
    """Test config loading with missing file."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("nonexistent.yaml"))


class TestConfig:
    """Test cases for configuration management."""

    def test_config_defaults(self):
        """Test default configuration values."""
        with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
            config = Config(universe_path=fp.name)
            assert config.universe_path == fp.name
            assert config.historical_data_years == 3
            assert config.cache_dir == "data"
            assert config.cache_refresh_days == 7
            assert config.hold_period == 20
            assert config.min_trades_threshold == 10
            assert config.freeze_date is None

    def test_config_validation_historical_years(self):
        """Test validation of historical_data_years."""
        # Valid range
        with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
            config = Config(universe_path=fp.name, historical_data_years=5)
            assert config.historical_data_years == 5

            # Invalid - too low
            with pytest.raises(ValidationError):
                Config(universe_path=fp.name, historical_data_years=0)

            # Invalid - too high
            with pytest.raises(ValidationError):
                Config(universe_path=fp.name, historical_data_years=15)

    def test_config_validation_cache_refresh_days(self):
        """Test validation of cache_refresh_days."""
        # Valid value
        with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
            config = Config(universe_path=fp.name, cache_refresh_days=14)
            assert config.cache_refresh_days == 14

            # Invalid - negative
            with pytest.raises(ValidationError):
                Config(universe_path=fp.name, cache_refresh_days=-1)

    def test_config_universe_path_validation(self):
        """Test universe path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid universe file
            universe_path = Path(temp_dir) / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

            # Valid path
            config = Config(universe_path=str(universe_path))
            assert config.universe_path == str(universe_path)

            # Invalid - file doesn't exist
            with pytest.raises(ValidationError, match="Universe file not found"):
                Config(universe_path="nonexistent.csv")            # Invalid - path is directory
            with pytest.raises(ValidationError, match="Universe path is not a file"):
                Config(universe_path=temp_dir)

    def test_config_freeze_date(self):
        """Test freeze date configuration."""
        with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
            # Valid date
            config = Config(universe_path=fp.name, freeze_date=date(2025, 1, 15))
            assert config.freeze_date == date(2025, 1, 15)

            # None value
            config = Config(universe_path=fp.name, freeze_date=None)
            assert config.freeze_date is None


class TestLoadConfig:
    """Test cases for configuration loading."""

    def test_load_config_success(self):
        """Test successful config loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file first
            universe_path = Path(temp_dir) / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

            # Create config file
            config_path = Path(temp_dir) / "config.yaml"
            config_data = {
                "universe_path": str(universe_path),
                "historical_data_years": 5,
                "cache_refresh_days": 14,
                "hold_period": 20,
                "min_trades_threshold": 10,                "edge_score_weights": {
                    "win_pct": 0.5,
                    "sharpe": 0.5
                }
            }
            
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            
            config = load_config(config_path)
            assert config.universe_path == str(universe_path)
            assert config.historical_data_years == 5
            assert config.cache_refresh_days == 14
            assert config.hold_period == 20
            assert config.min_trades_threshold == 10

    def test_load_config_missing_file(self):
        """Test loading config from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("nonexistent.yaml"))

    def test_load_config_invalid_yaml(self):
        """Test loading config from malformed YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            config_path = Path(f.name)
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_config(config_path)
        finally:
            config_path.unlink()

    def test_load_config_with_freeze_date(self):
        """Test loading config with freeze date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create universe file first
            universe_path = Path(temp_dir) / "universe.csv"
            universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")            # Create config file with freeze date
            config_path = Path(temp_dir) / "config.yaml"
            config_data = {
                "universe_path": str(universe_path),
                "freeze_date": "2025-01-15",
                "hold_period": 20,
                "min_trades_threshold": 10,
                "edge_score_weights": {
                    "win_pct": 0.6,
                    "sharpe": 0.4
                }
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            
            config = load_config(config_path)
            assert config.freeze_date == date(2025, 1, 15)
