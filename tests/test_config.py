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


def test_load_rules_invalid_structure(tmp_path: Path) -> None:
    """Test loading rules with various invalid structures."""
    # Not a dictionary
    rules_path = tmp_path / "rules1.yaml"
    rules_path.write_text("- rule1")
    with pytest.raises(ValueError, match="Rules file must be a dictionary"):
        load_rules(rules_path)

    # Missing 'baseline' key
    rules_path = tmp_path / "rules2.yaml"
    rules_path.write_text("layers: []")
    with pytest.raises(ValueError, match="Rules file must contain a 'baseline' key"):
        load_rules(rules_path)

    # 'baseline' is not a dict
    rules_path = tmp_path / "rules3.yaml"
    rules_path.write_text("baseline: 123")
    with pytest.raises(ValueError, match="The 'baseline' key must contain a rule dictionary"):
        load_rules(rules_path)

    # 'layers' is not a list
    rules_path = tmp_path / "rules4.yaml"
    rules_path.write_text("baseline: {}\nlayers: {}")
    with pytest.raises(ValueError, match="The 'layers' key must contain a list"):
        load_rules(rules_path)