"""Configuration management with Pydantic validation."""

import logging
from datetime import date
from pathlib import Path
from typing import Optional, Any, Dict

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

# Rule function registry - imported functions  
from .rules import sma_crossover, rsi_oversold, ema_crossover

__all__ = [
    "Config", 
    "EdgeScoreWeights", 
    "SMAParams", 
    "RSIParams", 
    "EMAParams",
    "RULE_REGISTRY",
    "validate_rule_params", 
    "get_rule_function", 
    "load_app_config"
]

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


class SMAParams(BaseModel):
    """Parameters for SMA crossover rule."""
    fast_period: int = Field(default=10, ge=2, le=50, description="Fast SMA period")
    slow_period: int = Field(default=20, ge=5, le=200, description="Slow SMA period")
    
    @model_validator(mode='after')
    def check_period_order(self) -> 'SMAParams':
        """Validate fast_period < slow_period."""
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


class RSIParams(BaseModel):
    """Parameters for RSI oversold rule."""
    period: int = Field(default=14, ge=2, le=50, description="RSI calculation period")
    oversold_threshold: float = Field(default=30.0, ge=10, le=40, description="RSI oversold threshold")


class EMAParams(BaseModel):
    """Parameters for EMA crossover rule."""
    fast_period: int = Field(default=10, ge=2, le=50, description="Fast EMA period")
    slow_period: int = Field(default=20, ge=5, le=200, description="Slow EMA period")
    
    @model_validator(mode='after')
    def check_period_order(self) -> 'EMAParams':
        """Validate fast_period < slow_period."""
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


# Rule parameter models mapping
RULE_PARAM_MODELS: Dict[str, type[BaseModel]] = {
    'sma_crossover': SMAParams,
    'rsi_oversold': RSIParams,
    'ema_crossover': EMAParams,
}

# Rule function registry
RULE_REGISTRY = {
    'sma_crossover': sma_crossover,
    'rsi_oversold': rsi_oversold,
    'ema_crossover': ema_crossover,
}


def validate_rule_params(rule_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate rule parameters using Pydantic models.
    
    Args:
        rule_type: Type of rule (e.g., 'sma_crossover')
        params: Rule parameters to validate
    
    Returns:
        Validated parameters with defaults applied
    
    Raises:
        ValueError: If rule type unknown or parameters invalid
    """
    if rule_type not in RULE_PARAM_MODELS:
        raise ValueError(f"Unknown rule type: {rule_type}")
    
    param_model = RULE_PARAM_MODELS[rule_type]
    try:
        validated = param_model(**params)
        return validated.model_dump()
    except ValidationError as e:
        # Convert Pydantic validation errors to user-friendly messages
        for error in e.errors():
            field = error['loc'][0] if error['loc'] else 'parameter'
            error_type = error['type']
            
            if error_type == 'int_parsing':
                raise ValueError(f"{field} must be an integer")
            elif error_type == 'less_than_equal':
                max_val = error.get('ctx', {}).get('le', 'maximum')
                raise ValueError(f"{field} must be between 1 and {max_val}")
            elif error_type == 'greater_than_equal':
                min_val = error.get('ctx', {}).get('ge', 'minimum')
                raise ValueError(f"{field} must be between {min_val} and maximum")
            elif error_type == 'missing':
                raise ValueError(f"{field} is required")
            else:
                raise ValueError(f"{field} validation error: {error['msg']}")
        
        # Fallback for any unhandled validation errors
        raise ValueError(f"Parameter validation failed: {str(e)}")


def get_rule_function(rule_type: str) -> Any:
    """Get rule function by type name.
    
    Args:
        rule_type: Type of rule to retrieve
        
    Returns:
        Rule function
        
    Raises:
        ValueError: If rule type is not registered
    """
    if rule_type not in RULE_REGISTRY:
        available = list(RULE_REGISTRY.keys())
        raise ValueError(f"Unknown rule type: {rule_type}. Available: {available}")
    
    return RULE_REGISTRY[rule_type]


def load_app_config(config_path: Path, rules_path: Optional[Path] = None) -> Config:
    """Load unified application configuration from YAML files.

    Args:
        config_path: Path to the main config YAML file
        rules_path: Optional path to the rules YAML file

    Returns:
        Parsed configuration object with all settings

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
        ValueError: If config validation fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Check rules file exists if provided
    if rules_path and not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

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
