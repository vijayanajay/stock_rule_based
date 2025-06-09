"""
Tests for the configuration module.
"""

import os
import tempfile
from datetime import date
import warnings

import pytest
import yaml

from src.meqsap.config import (
    load_yaml_config,
    validate_config,
    StrategyFactory,
    StrategyConfig,
    MovingAverageCrossoverParams,
)
from src.meqsap.exceptions import ConfigurationError

# Suppress pandas_ta related warnings  
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API", category=UserWarning)


# Test fixtures
@pytest.fixture
def valid_config_data():
    """Return a valid configuration dictionary."""
    return {
        "ticker": "AAPL",
        "start_date": date(2020, 1, 1),
        "end_date": date(2021, 1, 1),
        "strategy_type": "MovingAverageCrossover",
        "strategy_params": {
            "fast_ma": 10,
            "slow_ma": 30,
        },
    }


@pytest.fixture
def valid_config_yaml(valid_config_data):
    """Create a temporary file with valid YAML configuration."""
    # Convert Python objects to serializable format
    yaml_data = valid_config_data.copy()
    yaml_data["start_date"] = yaml_data["start_date"].isoformat()
    yaml_data["end_date"] = yaml_data["end_date"].isoformat()
    
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as temp:
        yaml.safe_dump(yaml_data, temp)
        temp_path = temp.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


@pytest.fixture
def invalid_yaml():
    """Create a temporary file with invalid YAML."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as temp:
        temp.write("this: is: invalid: yaml:")
        temp_path = temp.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


@pytest.fixture
def empty_yaml():
    """Create a temporary empty YAML file."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as temp:
        temp_path = temp.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


# YAML Loading Tests
def test_load_yaml_valid(valid_config_yaml):
    """Test loading a valid YAML configuration file."""
    config = load_yaml_config(valid_config_yaml)
    assert isinstance(config, dict)
    assert config["ticker"] == "AAPL"
    assert "start_date" in config
    assert "end_date" in config
    assert config["strategy_type"] == "MovingAverageCrossover"
    assert "strategy_params" in config


def test_load_yaml_file_not_found():
    """Test handling of a non-existent YAML file."""
    with pytest.raises(ConfigurationError) as excinfo:
        load_yaml_config("non_existent_file.yaml")
    assert "not found" in str(excinfo.value)


def test_load_yaml_invalid(invalid_yaml):
    """Test handling of syntactically invalid YAML."""
    with pytest.raises(ConfigurationError) as excinfo:
        load_yaml_config(invalid_yaml)
    assert "Invalid YAML" in str(excinfo.value)


def test_load_yaml_empty(empty_yaml):
    """Test handling of an empty YAML file."""
    with pytest.raises(ConfigurationError) as excinfo:
        load_yaml_config(empty_yaml)
    assert "Empty configuration" in str(excinfo.value)


# Configuration Validation Tests
def test_validate_config_valid(valid_config_data):
    """Test validation of a valid configuration."""
    config = validate_config(valid_config_data)
    assert isinstance(config, StrategyConfig)
    assert config.ticker == "AAPL"
    assert config.start_date == date(2020, 1, 1)
    assert config.end_date == date(2021, 1, 1)
    assert config.strategy_type == "MovingAverageCrossover"


def test_validate_config_missing_fields():
    """Test validation when required fields are missing."""
    incomplete_data = {
        "ticker": "AAPL",
        # Missing start_date
        "end_date": date(2021, 1, 1),
        "strategy_type": "MovingAverageCrossover",
        "strategy_params": {
            "fast_ma": 10,
            "slow_ma": 30,
        },
    }
    
    with pytest.raises(ConfigurationError) as excinfo:
        validate_config(incomplete_data)
    assert "validation failed" in str(excinfo.value)


def test_validate_ticker_format():
    """Test ticker format validation."""
    # Test with invalid ticker format
    invalid_data = {
        "ticker": "AAPL@123",  # Invalid character
        "start_date": date(2020, 1, 1),
        "end_date": date(2021, 1, 1),
        "strategy_type": "MovingAverageCrossover",
        "strategy_params": {
            "fast_ma": 10,
            "slow_ma": 30,
        },
    }
    
    with pytest.raises(ConfigurationError) as excinfo:
        validate_config(invalid_data)
    assert "ticker must contain only" in str(excinfo.value)


def test_validate_dates():
    """Test date validation."""
    # Test with end_date before start_date
    invalid_dates = {
        "ticker": "AAPL",
        "start_date": date(2021, 1, 1),
        "end_date": date(2020, 1, 1),  # End date is before start date
        "strategy_type": "MovingAverageCrossover",
        "strategy_params": {
            "fast_ma": 10,
            "slow_ma": 30,
        },
    }
    
    with pytest.raises(ConfigurationError) as excinfo:
        validate_config(invalid_dates)
    assert "end_date must be after start_date" in str(excinfo.value)


# Strategy Factory Tests
def test_strategy_factory_valid():
    """Test the strategy factory with valid parameters."""
    params = StrategyFactory.create_strategy_validator(
        "MovingAverageCrossover", {"fast_ma": 10, "slow_ma": 30}
    )
    assert isinstance(params, MovingAverageCrossoverParams)
    assert params.fast_ma == 10
    assert params.slow_ma == 30


def test_strategy_factory_unknown_type():
    """Test the strategy factory with an unknown strategy type."""
    with pytest.raises(ConfigurationError) as excinfo:  # Changed from ValueError
        StrategyFactory.create_strategy_validator(
            "UnknownStrategy", {"param1": "value1"}
        )
    assert "Unknown strategy type" in str(excinfo.value)


def test_strategy_factory_invalid_params():
    """Test the strategy factory with invalid parameters."""
    with pytest.raises(ConfigurationError) as excinfo:  # Changed from ValueError
        StrategyFactory.create_strategy_validator(
            "MovingAverageCrossover", {"fast_ma": 30, "slow_ma": 10}  # Invalid: fast > slow
        )
    assert "slow_ma must be greater than fast_ma" in str(excinfo.value)


def test_validate_strategy_params(valid_config_data):
    """Test the validation of strategy-specific parameters."""
    config = StrategyConfig(**valid_config_data)
    params = config.validate_strategy_params()
    assert isinstance(params, MovingAverageCrossoverParams)
    assert params.fast_ma == 10
    assert params.slow_ma == 30
