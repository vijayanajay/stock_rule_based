"""Configuration management with Pydantic validation."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, model_validator

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
    """Main application configuration."""
    universe_path: str = Field(..., description="Path to universe CSV file")
    hold_period: int = Field(..., gt=0, description="Days to hold position")
    min_trades_threshold: int = Field(..., gt=0, description="Minimum trades for valid backtest")
    edge_score_weights: EdgeScoreWeights
    historical_data_years: int = Field(3, gt=0, description="Years of historical data")
    cache_refresh_days: int = Field(7, gt=0, description="Cache refresh frequency")
    freeze_date: Optional[str] = Field(default=None, description="Optional freeze date YYYY-MM-DD")


def load_config(config_path: Path) -> Config:
    """Load and validate configuration from YAML file."""
    try:
        data = yaml.safe_load(config_path.read_text())
        if data is None:
            raise ValueError(f"Config file is empty: {config_path}")
        return Config(**data)
    except FileNotFoundError:
        # Don't wrap FileNotFoundError - preserve specific exception type
        raise
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
