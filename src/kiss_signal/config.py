"""Configuration management with Pydantic validation."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class EdgeScoreWeights(BaseModel):
    """Edge score calculation weights."""
    
    win_pct: float = Field(..., ge=0.0, le=1.0, description="Win percentage weight")
    sharpe: float = Field(..., ge=0.0, le=1.0, description="Sharpe ratio weight")
    
    @field_validator('win_pct', 'sharpe')
    @classmethod
    def check_weights_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError('Weight must be between 0.0 and 1.0')
        return v
    
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
    freeze_date: Optional[str] = Field(None, description="Optional freeze date YYYY-MM-DD")


def load_config(config_path: str = "config.yaml") -> Config:
    """Load and validate configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return Config(**data)
    except FileNotFoundError:
        raise ValueError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def load_rules(rules_path: str = "rules.yaml") -> Dict[str, Any]:
    """Load rules configuration from YAML file."""
    try:
        with open(rules_path, 'r') as f:
            result = yaml.safe_load(f)
            return result if result is not None else {}
    except FileNotFoundError:
        raise ValueError(f"Rules file not found: {rules_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {rules_path}: {e}")
