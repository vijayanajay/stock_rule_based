<!-- Status: Completed -->
# Story: Project Setup and Configuration Module Implementation

## Description
As a foundation for the MEQSAP project, we need to set up the project structure and implement the configuration module that will load and validate user strategy YAML files.

## Acceptance Criteria
1. Project structure is set up according to the architecture document
2. A Pydantic schema is implemented to validate strategy configurations
3. The configuration module can load a YAML file and validate it against the schema
4. Basic CLI entry point is implemented to start the application
5. Unit tests are implemented to verify configuration validation works correctly
6. Documentation is added to explain configuration options

## Implementation Details

### Project Structure
Set up the project structure as defined in the architecture document:
```
meqsap/
├── .github/workflows/
│   └── main.yml
├── docs/
│   └── architecture.md
├── src/
│   └── meqsap/
│       ├── __init__.py
│       ├── config.py
│       ├── cli.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   └── test_config.py
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

### Configuration Module Implementation
Create the `config.py` module that will:
1. Define a Pydantic model hierarchy for strategy configurations
2. Implement a strategy validation schema based on the PRD requirements
3. Create functions to load and validate YAML files
4. **Implement a strategy factory pattern for extensibility** that would allow easier addition of new strategies in the future
5. **Ensure the config module is completely independent of other modules**, following the modular monolith pattern from the architecture document

#### Configuration Module Pseudocode

**Component:** `Configuration Module`
**Function:** `load_yaml_config`

**Inputs:**
* A file path string pointing to the YAML configuration file.

**Output:**
* A dictionary containing the parsed YAML configuration data.

**Steps:**
1. **Attempt to open and read the configuration file.**
   * Open the file at the provided file path in read mode.
   * Use a context manager (`with` statement) to ensure proper file handling.

2. **Parse the YAML content.**
   * Use the `yaml.safe_load` function to convert the file's contents to a Python dictionary.
   * This ensures malformed YAML is handled safely and potential code injection is prevented.

3. **Handle potential errors.**
   * If the file is not found, raise a clear `ConfigError` with a message indicating the file couldn't be found.
   * If the YAML is invalid, raise a `ConfigError` with details about the parsing failure.

4. **Return the parsed configuration data.**
   * Return the dictionary containing all configuration parameters from the YAML file.

**Component:** `Configuration Module`
**Function:** `validate_config`

**Inputs:**
* A dictionary containing the parsed YAML configuration data.

**Output:**
* A validated `StrategyConfig` object.

**Steps:**
1. **Create a StrategyConfig instance.**
   * Pass the configuration dictionary to the `StrategyConfig` constructor.
   * Allow Pydantic to perform initial validation of required fields and basic formats.

2. **Validate strategy-specific parameters.**
   * Extract the strategy type from the main configuration.
   * Use the `StrategyFactory` to create the appropriate validator for the strategy type.
   * Pass the strategy parameters to the validator.

3. **Handle validation errors.**
   * Capture any validation exceptions from either the main config or strategy-specific validation.
   * Wrap them in a user-friendly `ConfigError` with clear details about what failed.

4. **Return the validated configuration.**
   * Return the fully validated `StrategyConfig` object for use by other modules.

#### Sample Pydantic Schema Structure
```python
from pydantic import BaseModel, Field, validator
from typing import Union, Dict, Any, Literal, Optional
from datetime import datetime, date
import yaml
import re

class BaseStrategyParams(BaseModel):
    """Base class for all strategy parameters."""
    pass

class MovingAverageCrossoverParams(BaseStrategyParams):
    fast_ma: int = Field(..., gt=0, description="Fast moving average period")
    slow_ma: int = Field(..., gt=0, description="Slow moving average period")
    
    @validator('slow_ma')
    def slow_ma_must_be_greater_than_fast_ma(cls, v, values):
        if 'fast_ma' in values and v <= values['fast_ma']:
            raise ValueError('slow_ma must be greater than fast_ma')
        return v

class StrategyConfig(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    strategy_type: Literal["MovingAverageCrossover"] = Field(
        ..., description="Type of trading strategy to backtest"
    )
    strategy_params: Dict[str, Any] = Field(..., description="Strategy-specific parameters")
    
    # Validation for core fields
    @validator('ticker')
    def validate_ticker(cls, v):
        if not re.match(r'^[A-Za-z0-9.\-]+$', v):
            raise ValueError('ticker must contain only letters, numbers, dots, and hyphens')
        return v
    
    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    def validate_strategy_params(self) -> BaseStrategyParams:
        """Validate strategy parameters based on strategy_type."""
        if self.strategy_type == "MovingAverageCrossover":
            return MovingAverageCrossoverParams(**self.strategy_params)
        raise ValueError(f"Unknown strategy type: {self.strategy_type}")

# Strategy Factory Pattern
class StrategyFactory:
    """Factory for creating strategy parameter validators."""
    
    @staticmethod
    def create_strategy_validator(strategy_type: str, params: Dict[str, Any]) -> BaseStrategyParams:
        """Create and return the appropriate strategy validator based on strategy_type."""
        if strategy_type == "MovingAverageCrossover":
            return MovingAverageCrossoverParams(**params)
        # Future strategy types can be added here
        raise ValueError(f"Unknown strategy type: {strategy_type}")
```

### Basic CLI Implementation
Create a minimal `cli.py` module that:
1. Uses Typer to define the command-line interface
2. Takes a path to a YAML configuration file
3. Loads and validates the configuration
4. Prints validation results

#### CLI Implementation Pseudocode

**Component:** `CLI Module`
**Function:** `process_config` (main command)

**Inputs:**
* A file path to the YAML configuration file.
* A flag indicating whether to display verbose output.

**Output:**
* Success message or error details printed to the console.
* Exit code (0 for success, non-zero for failure).

**Steps:**
1. **Create the Typer application.**
   * Initialize a new Typer app instance.
   * Configure app metadata like name, version, and description.

2. **Define the main command function.**
   * Set up the command to accept a configuration file path argument.
   * Add a `--verbose` flag option to control output detail.
   * Add a `--version` flag to display version information.

3. **Process the configuration file.**
   * Call the `Configuration Module`'s `load_yaml_config` function with the provided file path.
   * Call the `validate_config` function with the loaded data.

4. **Handle the results.**
   * If validation succeeds:
     * In verbose mode, print the full configuration details.
     * In normal mode, print a simple success message.
   * If any errors occur during loading or validation:
     * Print a clear error message with details about what failed.
     * Exit with a non-zero status code to indicate failure.

5. **Set up the entry point.**
   * Add code that calls the Typer app when the script is run directly.
   * This enables the CLI to be invoked via `python -m meqsap.cli`.

#### Strategy Factory Pattern Pseudocode

**Component:** `Configuration Module`
**Function:** `StrategyFactory.create_strategy_validator`

**Inputs:**
* A string indicating the strategy type.
* A dictionary containing strategy-specific parameters.

**Output:**
* A validated strategy parameters object (subclass of `BaseStrategyParams`).

**Steps:**
1. **Map strategy types to validator classes.**
   * Maintain a mapping dictionary that connects strategy type names to their corresponding parameter validator classes.
   * Initially include only the `MovingAverageCrossover` strategy.
   * Design the mapping to be extensible for future strategy types.

2. **Verify the requested strategy type exists.**
   * Check if the provided strategy type string exists in the mapping.
   * If not, raise a clear error indicating the strategy type is unknown.

3. **Create and validate the strategy parameters.**
   * Get the appropriate validator class for the requested strategy type.
   * Instantiate the validator class with the provided parameters.
   * Allow Pydantic's validation to run on the parameters.

4. **Handle validation failures.**
   * If parameter validation fails, catch the exception.
   * Raise a clear error that indicates which parameters were invalid and why.

5. **Return the validated parameters object.**
   * Return the fully validated strategy parameters object.

### Unit Tests
Create tests that verify:
1. Valid configurations pass validation
2. Invalid configurations fail with appropriate error messages
3. Edge cases are handled correctly
4. The strategy factory correctly instantiates strategy validators

#### Unit Testing Pseudocode

**Component:** `Test Module`
**Function:** `test_config.py Test Suite`

**Testing Strategy:**
* Create a comprehensive suite of tests that verify all aspects of configuration loading and validation.
* Use pytest fixtures to prepare test data and reduce duplication.
* Test both success and failure paths to ensure proper error handling.

**Test Categories and Steps:**

1. **YAML Loading Tests**
   * **Test successful loading:**
     * Create a temporary file with valid YAML content.
     * Call the `load_yaml_config` function.
     * Verify the returned dictionary matches the expected structure and values.
   
   * **Test malformed YAML:**
     * Create a temporary file with invalid YAML syntax.
     * Call `load_yaml_config` and expect a `ConfigError`.
     * Verify the error message clearly indicates the YAML syntax problem.
   
   * **Test empty or missing files:**
     * Call `load_yaml_config` with a non-existent file path.
     * Verify it raises the appropriate error with a clear message.
     * Test with an empty file and verify proper handling.

2. **Configuration Validation Tests**
   * **Test valid configuration:**
     * Create a dictionary with all required fields properly formatted.
     * Call `validate_config` and verify it returns a proper `StrategyConfig` object.
     * Verify all fields in the returned object match the input values.
   
   * **Test missing required fields:**
     * Create dictionaries with various required fields missing.
     * Call `validate_config` on each and verify appropriate validation errors.
   
   * **Test field format validation:**
     * Test ticker symbol validation with valid and invalid formats.
     * Test date validation with proper and improper date formats.
     * Test date ordering validation (end_date must be after start_date).

3. **Strategy Factory Tests**
   * **Test valid strategy types:**
     * Call the factory with "MovingAverageCrossover" and valid parameters.
     * Verify it returns a properly instantiated `MovingAverageCrossoverParams` object.
   
   * **Test unknown strategy types:**
     * Call the factory with a non-existent strategy type.
     * Verify it raises an appropriate error with a clear message.
   
   * **Test invalid strategy parameters:**
     * Call the factory with valid strategy types but invalid parameters.
     * For MovingAverageCrossover, test with fast_ma > slow_ma.
     * Verify it raises validation errors with clear messages about the constraints.

## Tasks

### 1. Project Structure Setup
- [x] **1.1.** Create the base project directory structure
- [x] **1.2.** Initialize Git repository (if not already done)
- [x] **1.3.** Create .gitignore file with standard Python patterns
- [ ] **1.4.** Set up virtual environment with Python 3.9+
- [x] **1.5.** Create initial README.md with project overview
- [x] **1.6.** Create initial requirements.txt file with key dependencies:
  - [x] **1.6.1.** pydantic
  - [x] **1.6.2.** pyyaml
  - [x] **1.6.3.** typer
  - [x] **1.6.4.** pytest (for testing)
- [x] **1.7.** Create basic pyproject.toml for packaging

### 2. Configuration Module Implementation
- [ ] **2.1.** Create src/meqsap directory and initialize it as a Python package
- [ ] **2.2.** Add py.typed marker file to enable type checking
- [ ] **2.3.** Implement BaseStrategyParams class
- [ ] **2.4.** Implement MovingAverageCrossoverParams class with validation rules
- [ ] **2.5.** Implement StrategyConfig class:
  - [ ] **2.5.1.** Define core fields (ticker, dates, strategy_type)
  - [ ] **2.5.2.** Add validation for ticker symbol format
  - [ ] **2.5.3.** Add validation for date range (end_date > start_date)
  - [ ] **2.5.4.** Implement validate_strategy_params method
- [ ] **2.6.** Implement StrategyFactory class for extensibility:
  - [ ] **2.6.1.** Design create_strategy_validator static method
  - [ ] **2.6.2.** Add support for MovingAverageCrossover strategy
- [ ] **2.7.** Create functions to load and process YAML files:
  - [ ] **2.7.1.** Implement load_yaml_config function using yaml.safe_load
  - [ ] **2.7.2.** Implement validate_config function to create StrategyConfig instance

### 3. CLI Implementation
- [x] **3.1.** Create basic cli.py module
- [x] **3.2.** Setup Typer application instance
- [x] **3.3.** Implement main command to process config files:
  - [x] **3.3.1.** Add parameter for config file path
  - [x] **3.3.2.** Add --verbose flag
  - [x] **3.3.3.** Add --version flag
- [x] **3.4.** Connect CLI to config module functionality
- [x] **3.5.** Add user-friendly error handling and feedback

### 4. Unit Testing
- [x] **4.1.** Set up tests directory structure
- [x] **4.2.** Create test_config.py with pytest fixtures
- [ ] **4.3.** Write tests for YAML loading:
  - [ ] **4.3.1.** Test successful loading of valid YAML
  - [ ] **4.3.2.** Test handling of malformed YAML
  - [ ] **4.3.3.** Test handling of empty YAML files
- [ ] **4.4.** Write tests for config validation:
  - [ ] **4.4.1.** Test validation of valid configs
  - [ ] **4.4.2.** Test ticker validation rules
  - [ ] **4.4.3.** Test date validation rules
  - [ ] **4.4.4.** Test strategy-specific parameter validation
- [ ] **4.5.** Write tests for StrategyFactory:
  - [ ] **4.5.1.** Test factory with valid strategy types and params
  - [ ] **4.5.2.** Test factory with unknown strategy types
  - [ ] **4.5.3.** Test factory with invalid strategy parameters

### 5. Documentation
- [ ] **5.1.** Add comprehensive docstrings to all modules, classes, and functions
- [ ] **5.2.** Create sample YAML configuration files for examples
- [ ] **5.3.** Update README.md with usage instructions and examples
- [ ] **5.4.** Document project structure and module responsibilities

## Resources
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [YAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)

## Definition of Done
1. Project structure is set up
2. Configuration module is implemented and working with a strategy factory pattern
3. Basic CLI is working
4. All unit tests pass
5. Code is properly documented
6. Code follows project coding standards
7. The config module is completely independent from other modules
