import pytest
from pydantic import ValidationError
from pathlib import Path
from typing import Any, Dict
import yaml # Import yaml

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


def test_config_universe_path_is_dir(sample_config: Dict[str, Any], tmp_path: Path) -> None:
    """Test that a universe_path pointing to a directory raises ValueError."""
    # Create a directory where the universe file is expected
    universe_dir = tmp_path / "universe_as_dir"
    universe_dir.mkdir()

    invalid_config_data = sample_config.copy()
    invalid_config_data["universe_path"] = str(universe_dir)

    with pytest.raises(ValidationError, match="Universe path is not a file"):
        Config(**invalid_config_data)


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Test loading a config file with invalid YAML content."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("key: value\n  bad_indent: true")
    with pytest.raises(ValueError, match="Invalid YAML in config file"):
        load_config(config_file)

def test_load_config_empty_file(tmp_path: Path) -> None:
    """Test loading an empty config file."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("") # Empty file
    with pytest.raises(ValueError, match="Config file is empty or contains only comments"):
        load_config(config_file)

    config_file_comment = tmp_path / "comment_only.yaml"
    config_file_comment.write_text("# This is just a comment")
    with pytest.raises(ValueError, match="Config file is empty or contains only comments"):
        load_config(config_file_comment)


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


def test_load_rules_missing_file(tmp_path: Path) -> None:
    """Test that loading a non-existent rules file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_rules(tmp_path / "nonexistent_rules.yaml")

def test_load_rules_invalid_yaml(tmp_path: Path) -> None:
    """Test loading a rules file with invalid YAML content."""
    rules_file = tmp_path / "invalid_rules.yaml"
    rules_file.write_text("baseline:\n  name: base\n  type: t\n  params: {}\n bad_indent: true")
    with pytest.raises(ValueError, match="Invalid YAML in rules file"): # Expecting this to be wrapped by load_rules
        load_rules(rules_file)


def test_load_rules_empty_file(tmp_path: Path) -> None:
    """Test loading an empty rules file."""
    rules_file = tmp_path / "empty_rules.yaml"
    rules_file.write_text("") # Empty file
    with pytest.raises(ValueError, match="Rules file is empty or contains only comments"):
        load_rules(rules_file)

    rules_file_comment = tmp_path / "comment_only_rules.yaml"
    rules_file_comment.write_text("# This is just a comment in rules")
    with pytest.raises(ValueError, match="Rules file is empty or contains only comments"):
        load_rules(rules_file_comment)


def test_rules_config_with_context_filters(tmp_path: Path) -> None:
    """Test that RulesConfig properly loads context_filters field."""
    rules_content = """
baseline:
  name: "test_baseline"
  type: "close_above_sma"
  params:
    period: 20
layers:
  - name: "test_layer"
    type: "volume_above_sma"
    params:
      period: 10
sell_conditions:
  - name: "test_sell"
    type: "close_below_sma"
    params:
      period: 5
context_filters:
  - name: "filter_market_is_bullish"
    type: "market_above_sma"
    description: "Context 1: Don't fight the tape. The NIFTY 50 index must be above its 50-day SMA."
    params:
      index_symbol: "^NSEI"
      period: 50
"""
    rules_file = tmp_path / "test_rules.yaml"
    rules_file.write_text(rules_content)
    
    rules_config = load_rules(rules_file)
    
    # Verify all fields are properly loaded
    assert rules_config.baseline.name == "test_baseline"
    assert len(rules_config.layers) == 1
    assert len(rules_config.sell_conditions) == 1
    assert len(rules_config.context_filters) == 1
    
    # Verify context_filters specific content
    context_filter = rules_config.context_filters[0]
    assert context_filter.name == "filter_market_is_bullish"
    assert context_filter.type == "market_above_sma"
    assert context_filter.params["index_symbol"] == "^NSEI"
    assert context_filter.params["period"] == 50


def test_rules_config_without_context_filters(tmp_path: Path) -> None:
    """Test that RulesConfig works with empty context_filters (backward compatibility)."""
    rules_content = """
baseline:
  name: "test_baseline"
  type: "close_above_sma"
  params:
    period: 20
"""
    rules_file = tmp_path / "minimal_rules.yaml"
    rules_file.write_text(rules_content)
    
    rules_config = load_rules(rules_file)
    
    # Verify context_filters defaults to empty list
    assert rules_config.context_filters == []
    assert len(rules_config.context_filters) == 0


def test_rules_config_with_preconditions(tmp_path: Path) -> None:
    """Test that RulesConfig handles preconditions correctly (Story 023)."""
    rules_content = """
preconditions:
  - name: "stock_in_long_term_uptrend"
    type: "price_above_long_sma"
    description: "Stock must be above its 200-day SMA"
    params:
      period: 200
  - name: "stock_is_sufficiently_volatile"
    type: "is_volatile"
    description: "Stock must have sufficient volatility"
    params:
      period: 14
      atr_threshold_pct: 0.02

baseline:
  name: "test_baseline"
  type: "close_above_sma"
  params:
    period: 20
"""
    rules_file = tmp_path / "rules_with_preconditions.yaml"
    rules_file.write_text(rules_content)
    
    rules_config = load_rules(rules_file)
    
    # Verify preconditions are loaded correctly
    assert len(rules_config.preconditions) == 2
    
    # Check first precondition
    first_precondition = rules_config.preconditions[0]
    assert first_precondition.name == "stock_in_long_term_uptrend"
    assert first_precondition.type == "price_above_long_sma"
    assert first_precondition.params["period"] == 200
    
    # Check second precondition
    second_precondition = rules_config.preconditions[1]
    assert second_precondition.name == "stock_is_sufficiently_volatile" 
    assert second_precondition.type == "is_volatile"
    assert second_precondition.params["period"] == 14
    assert second_precondition.params["atr_threshold_pct"] == 0.02


def test_rules_config_without_preconditions(tmp_path: Path) -> None:
    """Test that RulesConfig works with empty preconditions (backward compatibility)."""
    rules_content = """
baseline:
  name: "test_baseline"
  type: "close_above_sma"
  params:
    period: 20
"""
    rules_file = tmp_path / "minimal_rules.yaml"
    rules_file.write_text(rules_content)
    
    rules_config = load_rules(rules_file)
    
    # Verify preconditions defaults to empty list
    assert rules_config.preconditions == []
    assert len(rules_config.preconditions) == 0