"""
Configuration module for MEQSAP.

This module handles loading and validation of strategy configurations from YAML files.
"""

from typing import Any, Dict, Literal, Optional, Type
from datetime import date
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

from .exceptions import ConfigurationError


class BaseStrategyParams(BaseModel):
    """Base class for all strategy parameters."""

    def get_required_data_coverage_bars(self) -> int:
        """
        Returns the minimum number of data bars required by the strategy for its calculations.
        This is the raw requirement from the strategy's perspective (e.g., longest MA period).
        The vibe check framework might apply additional safety factors (e.g., 2x this value).

        This method MUST be overridden by concrete strategy parameter classes.
        """
        raise NotImplementedError(
            "Strategy parameter classes must implement 'get_required_data_coverage_bars'."
        )


class MovingAverageCrossoverParams(BaseStrategyParams):
    """Parameters for the Moving Average Crossover strategy."""

    fast_ma: int = Field(..., gt=0, description="Fast moving average period")
    slow_ma: int = Field(..., gt=0, description="Slow moving average period")

    @field_validator("slow_ma")
    @classmethod
    def slow_ma_must_be_greater_than_fast_ma(cls, v: int, info: Any) -> int:
        """Validate that slow_ma is greater than fast_ma."""
        if "fast_ma" in info.data and v <= info.data["fast_ma"]:
            raise ValueError("slow_ma must be greater than fast_ma")
        return v

    def get_required_data_coverage_bars(self) -> int:
        """Return the slow MA period as the minimum data requirement."""
        return self.slow_ma


class StrategyConfig(BaseModel):
    """
    Configuration for a trading strategy backtest.
    
    Date Range Convention (per ADR-002):
    - start_date: First day to include in analysis (inclusive)
    - end_date: Last day to include in analysis (INCLUSIVE)
    
    Example: start_date="2022-01-01", end_date="2022-12-31" 
    will analyze data from Jan 1 through Dec 31, 2022 (both days included).
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    strategy_type: Literal["MovingAverageCrossover"] = Field(
        ..., description="Type of trading strategy to backtest"
    )
    strategy_params: Dict[str, Any] = Field(
        ..., description="Strategy-specific parameters"
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Validate ticker symbol format."""
        if not re.match(r"^[A-Za-z0-9.\-]+$", v):
            raise ValueError("ticker must contain only letters, numbers, dots, and hyphens")
        return v

    @model_validator(mode="after")
    def end_date_must_be_after_start_date(self) -> "StrategyConfig":
        """Validate that end_date is after start_date."""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    def validate_strategy_params(self) -> BaseStrategyParams:
        """Validate strategy parameters based on strategy_type."""
        return StrategyFactory.create_strategy_validator(
            self.strategy_type, self.strategy_params
        )


class StrategyFactory:
    """Factory for creating strategy parameter validators."""

    _strategy_validators: Dict[str, Type[BaseStrategyParams]] = {
        "MovingAverageCrossover": MovingAverageCrossoverParams,
    }

    @classmethod
    def create_strategy_validator(
        cls, strategy_type: str, params: Dict[str, Any]
    ) -> BaseStrategyParams:
        """Create and return the appropriate strategy validator based on strategy_type.

        Args:
            strategy_type: The type of strategy to validate
            params: Strategy-specific parameters

        Returns:
            A validated strategy parameters object

        Raises:
            ValueError: If the strategy type is unknown
        """
        validator_class = cls._strategy_validators.get(strategy_type)
        if not validator_class:
            raise ConfigurationError(f"Unknown strategy type: {strategy_type}")

        try:
            return validator_class(**params)
        except ValueError as e: # Pydantic validation errors are ValueErrors
            raise ConfigurationError(f"Invalid parameters for strategy {strategy_type}: {e}")

    @classmethod
    def validate_strategy_params(
        cls, strategy_type: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate strategy parameters and return validated dict.
        
        Args:
            strategy_type: The type of strategy to validate
            params: Strategy-specific parameters
            
        Returns:
            A dictionary of validated parameters
            
        Raises:
            ConfigurationError: If validation fails
        """
        try:
            validated_params = cls.create_strategy_validator(strategy_type, params)
            return validated_params.model_dump()
        except (ValidationError, ConfigurationError) as e:
            raise ConfigurationError(f"Invalid parameters for strategy {strategy_type}: {e}")


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """Load a YAML configuration file.

    Args:
        file_path: Path to the YAML configuration file

    Returns:
        A dictionary containing the parsed YAML configuration

    Raises:
        ConfigurationError: If the file can't be found or contains invalid YAML
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file)
            if not config_data:
                raise ConfigurationError("Empty configuration file")
            return config_data
    except FileNotFoundError:
        raise ConfigurationError(f"Configuration file not found: {file_path}")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration: {str(e)}")
    except Exception as e:
        raise ConfigurationError(f"Error loading configuration: {str(e)}")


def validate_config(config_data: Dict[str, Any]) -> StrategyConfig:
    """Validate a configuration dictionary against the schema.

    Args:
        config_data: A dictionary containing the configuration data

    Returns:
        A validated StrategyConfig object

    Raises:
        ConfigurationError: If the configuration is invalid
    """
    try:
        # Create and validate the main config
        config = StrategyConfig(**config_data)
        # Validate strategy params
        config.strategy_params = StrategyFactory.validate_strategy_params(
            config.strategy_type, config.strategy_params
        )
        return config
    except ConfigurationError as e:
        # Re-raise ConfigurationError as-is
        raise e
    except ValueError as e:
        raise ConfigurationError(f"Configuration validation failed: {str(e)}")
    except Exception as e:
        raise ConfigurationError(f"Unexpected error in configuration validation: {str(e)}")
