"""Configuration loading and Pydantic models."""

import logging  # Standard library
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from datetime import date
import yaml
from pydantic import BaseModel, Field, field_validator, ValidationInfo, ValidationError

__all__ = [
    "Config",
    "EdgeScoreWeights",
    "RulesConfig",
    "RuleDef",
    "load_config",
    "load_rules",
    "get_active_strategy_combinations",
]

logger = logging.getLogger(__name__)

class EdgeScoreWeights(BaseModel):
    win_pct: float = Field(..., ge=0.0, le=1.0)
    sharpe: float = Field(..., ge=0.0, le=1.0)

    @field_validator("sharpe")
    def _weights_sum_to_one(cls, v: float, info: ValidationInfo) -> float:
        if "win_pct" in info.data:
            total = v + info.data["win_pct"]
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v

class Config(BaseModel):
    """Defines the structure of the main config.yaml file."""
    universe_path: str
    historical_data_years: int = Field(..., gt=0)
    cache_dir: str
    cache_refresh_days: Optional[int] = Field(default=1, ge=0)  # DEPRECATED: kept for compatibility
    hold_period: int = Field(..., gt=0)
    min_trades_threshold: int = Field(..., ge=0)
    edge_score_weights: EdgeScoreWeights
    database_path: str
    reports_output_dir: str
    edge_score_threshold: float = Field(..., ge=0.0, le=1.0)
    freeze_date: Optional[date] = None
    verbose: bool = False

    # The following are not in config.yaml but can be part of the object
    # for runtime convenience, hence they are optional.
    log_path: Optional[str] = None
    report_dir: Optional[str] = None

    @field_validator("universe_path")
    @classmethod
    def validate_universe_path(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Universe file not found: {v}")
        if not path.is_file():
            raise ValueError(f"Universe path is not a file: {v}")
        return v

class RuleDef(BaseModel):
    """Defines a single rule with its type and parameters."""
    name: str
    type: str
    params: Dict[str, Any]
    description: Optional[str] = None

class RulesConfig(BaseModel):
    """Defines the structure of the rules.yaml file."""
    baseline: RuleDef
    layers: List[RuleDef] = []
    sell_conditions: List[RuleDef] = Field(default_factory=list)
    context_filters: List[RuleDef] = Field(default_factory=list)  # NEW SIMPLE FIELD
    validation: Optional[Dict[str, Any]] = None # Allow validation block

# impure
def load_config(config_path: Path) -> Config:
    """Load and validate config from YAML file using Pydantic."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {config_path}") from e

    if data is None:
        raise ValueError("Config file is empty or contains only comments")

    try:
        return Config(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration in {config_path}: {e}") from e

# impure
def load_rules(rules_path: Path) -> RulesConfig:
    """Load and validate trading rules from a YAML file using Pydantic."""
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file: {rules_path}") from e

    if data is None:
        raise ValueError("Rules file is empty or contains only comments")

    try:
        return RulesConfig(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid rules configuration in {rules_path}: {e}") from e


def get_active_strategy_combinations(rules_config: "RulesConfig") -> List[str]:
    """Parse RulesConfig to extract all possible strategy combinations.
    
    Args:
        rules_config: RulesConfig object with baseline and layers
        
    Returns:
        List of JSON-serialized rule stacks that match current configuration
    """
    combinations: List[List[RuleDef]] = []
    
    # Generate baseline strategy
    if rules_config.baseline:
        combinations.append([rules_config.baseline])
        
        # Generate baseline + each layer combination
        for layer in rules_config.layers:
            combinations.append([rules_config.baseline, layer])
    
    # Convert each combination to JSON string
    return [json.dumps([r.model_dump() for r in combo]) for combo in combinations]
