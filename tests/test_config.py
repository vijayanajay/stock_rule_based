"""Tests for configuration module."""

import pytest
from pydantic import ValidationError
from pathlib import Path

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
    config = Config(**sample_config)
    assert config.hold_period == 20
    assert config.edge_score_weights.win_pct == 0.6


def test_load_config(config_file):
    """Test config loading from file."""
    config = load_config(config_file)
    assert config.hold_period == 20
    assert config.min_trades_threshold == 10


def test_load_config_missing_file():
    """Test config loading with missing file."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("nonexistent.yaml"))


def test_load_config_empty_file(temp_dir: Path):
    """Test config loading with an empty file."""
    empty_file = temp_dir / "empty.yaml"
    empty_file.touch()
    with pytest.raises(ValueError, match="Config file is empty"):
        load_config(empty_file)
