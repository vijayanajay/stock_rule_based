import pytest
from pydantic import ValidationError
from pathlib import Path
from typing import Any, Dict

from kiss_signal.config import Config, load_config, load_rules


def test_config_model_valid(sample_config: Dict[str, Any], tmp_path: Path) -> None:
    """Test that a valid config dictionary loads correctly."""
    universe_path = tmp_path / "universe.csv"
    universe_path.touch()
    sample_config["universe_path"] = str(universe_path)

    config = Config(**sample_config)
    assert config.hold_period == 20
    assert config.edge_score_weights.win_pct == 0.6


def test_config_model_invalid_weights(sample_config: Dict[str, Any], tmp_path: Path) -> None:
    """Test that weights not summing to 1.0 raises a validation error."""
    universe_path = tmp_path / "universe.csv"
    universe_path.touch()
    sample_config["universe_path"] = str(universe_path)
    sample_config["edge_score_weights"]["win_pct"] = 0.5  # 0.5 + 0.4 != 1.0

    with pytest.raises(ValidationError, match="Weights must sum to 1.0"):
        Config(**sample_config)


def test_load_config_missing_file(tmp_path: Path) -> None:
    """Test that loading a non-existent config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")


@pytest.mark.parametrize(
    "invalid_content, error_match",
    [
        ("layers: []", "Field required"),  # Missing baseline
        ("baseline: 123", "Input should be a valid dictionary"),  # Baseline not a dict
        ("baseline: {}\nlayers: {}", "Field required"),  # Baseline missing fields
        ("baseline: {name: a, type: b, params: {}}\nlayers: {}", "Input should be a valid list"), # Layers not a list
    ],
)
def test_load_rules_invalid_structure_pydantic(
    tmp_path: Path, invalid_content: str, error_match: str
) -> None:
    """Test loading rules with various invalid structures using Pydantic."""
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(invalid_content)
    with pytest.raises(ValueError, match=error_match):
        load_rules(rules_path)