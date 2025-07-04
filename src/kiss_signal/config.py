"""Configuration loading and Pydantic models."""

import logging  # Standard library
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from datetime import date
import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator, field_validator

__all__ = [
    "Config",
    "EdgeScoreWeights",
    "RuleDef",
    "RulesConfig",
    "load_config",
    "load_rules",
]

logger = logging.getLogger(__name__)

class EdgeScoreWeights(BaseModel):
    win_pct: float = Field(..., ge=0.0, le=1.0)
    sharpe: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode='after')
    def check_weights_sum(self) -> 'EdgeScoreWeights':
        total = self.win_pct + self.sharpe
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f'Weights must sum to 1.0, got {total}')
        return self

class Config(BaseModel):
    universe_path: str
    historical_data_years: int = Field(default=3, ge=1, le=10)
    cache_dir: str = Field(default="data")
    cache_refresh_days: int = Field(default=7, ge=1)
    hold_period: int = Field(default=20, gt=0)
    min_trades_threshold: int = Field(default=10, ge=0)
    edge_score_weights: EdgeScoreWeights = Field(
        default_factory=lambda: EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
    )
    freeze_date: Optional[date] = Field(default=None)
    database_path: str = Field(default="data/kiss_signal.db")
    reports_output_dir: str = Field(default="reports/")
    edge_score_threshold: float = Field(default=0.50, ge=0.0, le=1.0)

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
    validation: Optional[Dict[str, Any]] = None # Allow validation block

# impure
def load_config(config_path: Union[str, Path]) -> Config:
    """Load application configuration from a YAML file."""
    config_path = Path(config_path)  # Convert string to Path if needed
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}") from e
    if data is None:
        raise ValueError("Config file is empty or contains only comments")
    return Config(**data)

# impure
def load_rules(rules_path: Union[str, Path]) -> RulesConfig:
    """Load and validate trading rules from a YAML file using Pydantic."""
    rules_path = Path(rules_path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    try:
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        if data is None:
            raise ValueError("Rules file is empty or contains only comments")
        return RulesConfig(**data)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file: {e}") from e
    except ValidationError as e:
        # Re-raise Pydantic's error for clear, specific feedback
        raise ValueError(f"Invalid rules structure: {e}") from e
