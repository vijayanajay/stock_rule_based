# Structural Test Failures Analysis
## Date: 2025-06-15

## Identified Test Failures

1. **test_cli.py::test_cli_help FAILED** - CLI help display test failing
2. **test_cli.py::test_run_command_basic FAILED** - Basic run command test failing  
3. **test_cli.py::test_run_command_verbose FAILED** - Verbose run command test failing
4. **test_cli.py::test_run_command_freeze_date FAILED** - Freeze date command test failing
5. **test_config.py::test_load_config_missing_file FAILED** - Config file loading test failing

## Root Cause Analysis (Structural Issues)

### 1. **Working Directory Mismatch in CLI Tests**
**Issue**: CLI tests assume `config.yaml` exists in test working directory, but tests run from project root while CLI tries to load from current working directory.

**Structural Problem**: 
- Tests use Typer's `CliRunner` which doesn't change working directory
- CLI module uses relative paths (`config.yaml`) instead of project-relative paths
- No dependency injection for config path in CLI commands

### 2. **Inconsistent Exception Handling Pattern**
**Issue**: `test_config.py::test_load_config_missing_file` expects `FileNotFoundError` but config module wraps it in `ValueError`.

**Structural Problem**:
- Inconsistent exception transformation - some places wrap, others don't
- Test expectations don't match actual implementation behavior
- No standardized error handling pattern across modules

### 3. **Module Import Warning (Secondary)**
**Issue**: RuntimeWarning about `kiss_signal.cli` found in sys.modules
**Structural Problem**: CLI module designed for both direct execution and module import, causing import ordering issues

## Antipatterns Identified

### 1. **Implicit Working Directory Dependency** 
- CLI assumes specific working directory without validation
- No explicit path resolution strategy
- Tests don't control working directory context

### 2. **Exception Swallowing Anti-pattern**
- Converting specific exceptions (`FileNotFoundError`) to generic ones (`ValueError`)
- Makes debugging harder and breaks test expectations
- Loses valuable error context

### 3. **Tight Coupling to File System**
- CLI directly couples to file system without abstraction
- No dependency injection for configuration sources
- Hard to test without real file system

## Immediate Fixes Required

### Fix 1: Update config.py to preserve FileNotFoundError
```python
def load_config(config_path: str = "config.yaml") -> Config:
    """Load and validate configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return Config(**data)
    except FileNotFoundError:
        # Don't wrap FileNotFoundError - let it bubble up
        raise
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
```

### Fix 2: Add working directory management to CLI tests
```python
def test_run_command_basic(temp_dir, config_file):
    """Test basic run command with proper working directory."""
    # Change to temp directory with config file
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 0
        assert "Foundation setup complete" in result.stdout
    finally:
        os.chdir(old_cwd)
```

### Fix 3: Add path resolution to CLI module
```python
def resolve_config_path(config_path: str = "config.yaml") -> str:
    """Resolve config path relative to project root or current directory."""
    if Path(config_path).exists():
        return config_path
    
    # Try project root
    project_root = Path(__file__).parent.parent.parent
    project_config = project_root / config_path
    if project_config.exists():
        return str(project_config)
    
    return config_path  # Return original for proper error handling
```

## Memory Entry for docs/memory.md

**Issue**: CLI tests failing due to working directory assumptions and inconsistent exception handling

**Root Cause**: 
1. CLI assumes `config.yaml` in current working directory, but tests run from different context
2. Exception wrapping pattern breaks test expectations (`FileNotFoundError` → `ValueError`)

**Fix Pattern**:
1. Always preserve specific exceptions unless transformation adds value
2. Use explicit path resolution in CLI modules instead of assuming working directory
3. Control working directory in tests when testing file-dependent CLI commands

**Prevention**: 
- Avoid hardcoded relative paths in CLI modules
- Use dependency injection for file system dependencies
- Test file-dependent code with controlled directory contexts
- Don't wrap exceptions unless adding meaningful context