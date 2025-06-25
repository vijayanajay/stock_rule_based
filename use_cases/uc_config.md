| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_CONFIG_BS_UC003 – Load and Validate Configuration | Date: 08/07/24 |

# KS_CONFIG_BS_UC003 – Load and Validate Configuration

**1. Brief Description**

This use case allows an actor to load and validate application parameters and trading rules from YAML files, ensuring they conform to the required data schema before being used by the application.

The use case can be called:
- At the start of the main CLI `run` command to load `config.yaml`.
- At the start of the main CLI `run` command to load `rules.yaml`.

**2. Actors**

**2.1 Primary Actors**
1. **CLI Orchestrator** – The main application component that requires validated configuration objects to operate.

**2.2 Secondary Actors**
- PyYAML Library
- Pydantic Library

**3. Conditions**

**3.1 Pre-Condition**
- A YAML file (`config.yaml` or `rules.yaml`) exists at a specified path.

**3.2 Post Conditions on success**
1. A validated Pydantic `Config` object or a list of rule dictionaries is returned.
2. All configuration values are guaranteed to be of the correct type and within valid ranges.

**3.3 Post Conditions on Failure**
1. An exception (`FileNotFoundError`, `yaml.YAMLError`, or `pydantic.ValidationError`) is raised.
2. No configuration object is returned.

**4. Trigger**

1. A request to load a configuration file is issued by the Primary Actor. This request must contain:
    a. A `Path` object pointing to the configuration file (`config_path` or `rules_path`).

**5. Main Flow: KS_CONFIG_BS_UC003.MF – Load and Validate Configuration**

10. The system checks if the file exists at the given path.
    10.10. The system validates the path object is not None.
    10.20. The system checks file existence using Path.exists().
    <<config_path.exists() = True>>
    *See Exception Flow 1: KS_CONFIG_BS_UC003.XF01 – File Not Found*

20. The system reads the file content and parses it as YAML.
    20.10. The system reads file content as text with UTF-8 encoding.
    <<content = config_path.read_text(encoding='utf-8')>>
    20.20. The system parses YAML content using safe_load to prevent code execution.
    <<data = yaml.safe_load(content)>>
    20.30. The system validates that parsed data is a dictionary (for config) or list (for rules).
    *See Exception Flow 2: KS_CONFIG_BS_UC003.XF02 – Invalid YAML Syntax*

30. The system instantiates a Pydantic `Config` model (or processes the rules list) with the parsed data, triggering validation.
    30.10. For config files, the system creates Config model instance with comprehensive validation.
    <<config_obj = Config(**data)>>
    30.20. Pydantic automatically validates field types, constraints, and custom validation rules.
    30.30. Pydantic validates universe_path exists and is a file using field_validator decorator.
    <<@field_validator("universe_path") def validate_universe_path(cls, v): if not Path(v).exists(): raise ValueError(f"Universe file not found: {v}")>>
    30.40. Field validators run during model instantiation to ensure file references are valid.
    30.50. Pydantic validates edge_score_weights sum to 1.0 using model_validator with mode='after'.
    <<@model_validator(mode='after') def check_weights_sum(self): if abs(total - 1.0) > 1e-6: raise ValueError(f'Weights must sum to 1.0, got {total}')>>
    30.60. Model validators run after all field validation to check relationships between fields.
    30.70. The 1e-6 tolerance handles floating-point precision issues in weight summation.
    30.80. For rules files, the system validates structure: dict with 'rules' key containing list.
    <<if not isinstance(data, dict) or "rules" not in data: raise ValueError("Rules file must be a dictionary with a 'rules' key")>>
    30.90. Rules validation ensures the YAML structure matches expected format for rule processing.
    30.100. The system validates each rule has required fields and proper structure.
    <<if not isinstance(rules, list): raise ValueError("The 'rules' key must contain a list of rule configurations")>>
    30.110. List validation ensures rules can be iterated during backtesting operations.
    *See Exception Flow 3: KS_CONFIG_BS_UC003.XF03 – Configuration Validation Failed*

40. The system returns the validated configuration object to the primary actor.
    40.10. For config files, returns validated Config instance.
    40.20. For rules files, returns validated list of rule dictionaries.
    40.30. The system logs successful configuration loading.

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_CONFIG_BS_UC003.XF01 – File Not Found**

10. At **step 10 of the main flow**, the system determines the file does not exist.
    <<config_path.exists() = False>>
20. The system raises a `FileNotFoundError` exception.
99. The use case ends.

**6.2 Exception Flow 2: KS_CONFIG_BS_UC003.XF02 – Invalid YAML Syntax**

10. At **step 20 of the main flow**, the YAML parser encounters a syntax error.
    <<yaml.YAMLError>>
20. The system raises a `ValueError` or `yaml.YAMLError` exception, wrapping the original error.
99. The use case ends.

**6.3 Exception Flow 3: KS_CONFIG_BS_UC003.XF03 – Configuration Validation Failed**

10. At **step 30 of the main flow**, the Pydantic model validation fails due to missing fields, incorrect data types, or failed custom validation rules.
    <<pydantic.ValidationError>>
20. The system raises a `ValueError` or `pydantic.ValidationError` exception with a descriptive message.
99. The use case ends.

**7. Notes / Assumptions**

- This use case covers both `load_config` and `load_rules` functions, as their logic is analogous.
- The Config Pydantic model defines comprehensive validation rules for all application settings.
- EdgeScoreWeights is a separate Pydantic model ensuring weights are between 0-1 and sum to 1.0.
- YAML safe_load prevents execution of arbitrary Python code in configuration files.
- UTF-8 encoding ensures proper handling of special characters in configuration files.
- Rules validation ensures the YAML structure is a dict with 'rules' key containing a list.
- The Config model includes default values for optional fields (cache_refresh_days=7, hold_period=20, etc.).
- Field validators use Pydantic v2 syntax with @field_validator decorator.
- Model validators use mode='after' to validate relationships between fields.
- Configuration validation includes path existence checks for referenced files using Path objects.
- Error messages provide specific details about validation failures for debugging.
- The system handles empty YAML files by checking if data is None after parsing.
- Pydantic Field constraints use ge (greater equal), le (less equal), gt (greater than) for numeric validation.

**8. Issues**

| No: | Description: | Date | Action: | Status |
|---|---|---|---|---|
| 1. | | | | |

**9. Revision History**

| Date | Rev | Who | Description | Reference |
|---|---|---|---|---|
| 08/07/24 | 1.0 | AI | Initial document creation. | |

**10. Reference Documentation**

| Document Name | Version | Description | Location |
|---|---|---|---|
| `src/kiss_signal/config.py` | | Source code for the configuration module with Pydantic models. | Git Repository |
| `pydantic` | | Data validation library using Python type annotations. | PyPI |
| `PyYAML` | | YAML parser and emitter for Python. | PyPI |
