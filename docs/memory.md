# MEQSAP Memory File

## What NOT To Do: Common AI-Induced Pitfalls

### Import & Package Structure

**DON'T** write tests for modules that don't exist or have incomplete package structure.
- Always create `__init__.py` files for package hierarchy
- Verify imports work before writing tests: `python -c "from src.meqsap.cli import app"`
- Mock specifications must match actual return types (`spec=pd.DataFrame`, not `spec=Path`)

**DON'T** rely on `if __name__ == "__main__":` for modules executed with `python -m`.
- Use dedicated `main()` function for CLI entry points
- Test both direct execution and module execution patterns

### CLI Testing Anti-Patterns

**DON'T** test CLI help/commands without understanding the command structure.
- Use proper subcommand syntax: `["analyze", config, "--flag"]`, not `[config, "--flag"]`
- Test subcommand help with `["analyze", "--help"]`, not just `["--help"]`
- Verify CLI structure before writing tests: `python -m src.meqsap.cli --help`

**DON'T** assume Typer API stability.
- Remove deprecated arguments like `mix_stderr` from `CliRunner()`
- Pin Typer versions or test against updates regularly

**DON'T** mock functions to raise exceptions when testing return codes.
- Mock return values: `function.return_value = code`
- Not exceptions: `function.side_effect = Exception()` (bypasses internal error handling)

### Configuration & Schema Evolution

**DON'T** update Pydantic models without updating all test fixtures.
- Search project-wide for model instantiations when changing schemas
- Use factory functions for complex models to centralize test data creation
- Example: `MovingAverageCrossoverParams` field changes require updating all test helpers

**DON'T** hardcode configuration values in tests.
- Use constants for strategy types: `STRATEGY_TYPES = Literal["MovingAverageCrossover"]`
- Keep naming conventions consistent: PascalCase for strategy types, not snake_case

### Exception Handling

**DON'T** create duplicate exception classes.
- Single source of truth: use `exceptions.py`, not local classes in modules
- Import canonical exceptions: `from meqsap.exceptions import ConfigurationError`
- Don't alias imports that create ambiguity

**DON'T** reference unimplemented methods in factory patterns.
- Implement all factory methods before creating dependent code
- Use `mypy` to catch missing method references early

## Exception Handling Anti-Patterns

### Missing Exception Definitions
**Issue**: CLI module imports `ConfigError` from `config.py` but the exception class doesn't exist, causing import failures across all CLI tests.

**Root Cause**: Interface contract violation - dependent module expects exception class that isn't defined in the target module.

**Fix**: Define missing exception classes in their expected modules or update import statements to reference the correct location.

**Prevention**: 
- Verify all custom exceptions are defined before importing them
- Use a dedicated `exceptions.py` module for shared exceptions when appropriate
- Run basic import tests: `python -c "from module import exception_class"`

### Testing Fragility

**DON'T** assert exact CLI help text that depends on library formatting.
- Check for key terms ("Error", "MEQSAP"), not exact message strings
- Update test assertions when docstrings change

**DON'T** assume test structure matches implementation without verification.
- Inspect actual implementation before writing tests
- Use `typer.testing.CliRunner` with actual command structure
- Mock at module boundaries where functions are actually called

### Debugging Pattern

When CLI tests uniformly fail with exit code 2:
1. **First** check imports: `python -c "from module import app"`
2. **Then** check CLI help: `python -m module --help`  
3. **Then** check command structure: `python -m module subcommand --help`
4. **Finally** check runtime execution with mocks

**Remember**: Exit code 2 indicates framework-level failures (imports, command registration, argument parsing), not logic errors.
