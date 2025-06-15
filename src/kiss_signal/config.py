"""Configuration management with Pydantic validation."""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = ["Config", "EdgeScoreWeights", "load_config"]

logger = logging.getLogger(__name__)


class EdgeScoreWeights(BaseModel):
    """Edge score calculation weights."""
    win_pct: float = Field(..., ge=0.0, le=1.0, description="Win percentage weight")
    sharpe: float = Field(..., ge=0.0, le=1.0, description="Sharpe ratio weight")

    @model_validator(mode='after')
    def check_weights_sum(self) -> 'EdgeScoreWeights':
        """Validate that weights sum to 1.0."""
        total = self.win_pct + self.sharpe
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f'Weights must sum to 1.0, got {total}')
        return self


class Config(BaseModel):
    """Configuration model for KISS Signal CLI."""

    universe_path: str = Field(default="data/nifty_large_mid.csv", description="Path to universe CSV file")
    historical_data_years: int = Field(default=3, ge=1, le=10, description="Years of historical data")
    cache_dir: str = Field(default="data/cache", description="Directory for cached data files")
    cache_refresh_days: int = Field(default=7, ge=1, description="Cache refresh frequency")
    hold_period: int = Field(default=20, gt=0, description="Days to hold positions")
    min_trades_threshold: int = Field(default=10, ge=0, description="Minimum trades for valid backtest")
    freeze_date: Optional[date] = Field(default=None, description="Optional freeze date YYYY-MM-DD")
    edge_score_weights: EdgeScoreWeights = Field(
        default_factory=lambda: EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
        description="Weights for calculating the EdgeScore"
    )

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
    """Load configuration from YAML file.

    Args:
        config_path: Path to the config YAML file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
        ValueError: If config validation fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}") from e

    # An empty file or a file with only comments loads as None. Pydantic can
    # handle an empty dict, but we want to enforce that the config file is
    # explicitly present and not empty.
    if data is None:
        raise ValueError("Config file is empty or contains only comments")

    return Config(**data)
