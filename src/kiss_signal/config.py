"""Configuration loading and Pydantic models."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from datetime import date
import yaml
from pydantic import BaseModel, Field, model_validator, field_validator

__all__ = [
    "Config",
    "EdgeScoreWeights",
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

    @field_validator("universe_path")
    @classmethod
    def validate_universe_path(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Universe file not found: {v}")
        if not path.is_file():
            raise ValueError(f"Universe path is not a file: {v}")
        return v

def load_config(config_path: Path) -> Config:
    """Load application configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}") from e
    if data is None:
        raise ValueError("Config file is empty or contains only comments")
    return Config(**data)

def load_rules(rules_path: Path) -> List[Dict[str, Any]]:
    """Load trading rules from a YAML file."""
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    try:
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file: {e}") from e
    if not isinstance(data, dict) or "rules" not in data:
        raise ValueError("Rules file must be a dictionary with a 'rules' key.")
    rules = data["rules"]
    if not isinstance(rules, list):
        raise ValueError("The 'rules' key must contain a list of rule configurations.")
    return rules
