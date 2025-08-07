# Copilot Instructions – KISS Signal CLI

This repository is a Python-based, modular-monolith for rule-based stock signal generation and backtesting. It uses a single-command CLI, explicit data contracts, and a minimal blessed stack (vectorbt, pandas, rich, typer, pydantic, sqlite3). Please follow these guidelines when contributing:

## Code Standards

### Required Before Each Commit
- Run `pytest` and `mypy` on all changes; ensure zero errors and warnings
- Validate that `quickedge run --freeze-data 2025-01-01` completes successfully  
- Keep diffs small, readable, and commented where non-obvious

### Development Flow
- **CLI entry point**: `run.py`
- **Main modules**: `kiss_signal`, `data_manager`, `backtester`, `reporter`, etc.
- **Configs**: `config`
- **Data**: `data`
- **Tests**: `tests`
- **Documentation**: `docs`

## Key Guidelines

### Minimalism
- Fewer lines, fewer dependencies, less indirection
- No new libraries outside the blessed stack

### Explicit Contracts
- All runtime parameters affecting multiple components must be part of a Pydantic model, not attached dynamically

### Module Boundaries
- Keep functions in their home modules
- No cross-module sprawl

### Typing
- Use full type hints on every new line

### Logging
- Use `logging.getLogger(__name__)`
- Respect `--verbose`

### Terminal Output
- Use helpers in `reporter.py` for all rich output

### Testing
- Update or add tests for every change
- Use assertions, not return values, for test outcomes

### No End-to-End Rewrites
- Scope AI/code assistant requests to small, well-defined edits

### Human Review
- Understand every line before you ship it

## Repository Structure

```
kiss_signal/          # Core modules (data, config, CLI, reporting, backtesting)
config/               # YAML rule and strategy configs
data/                 # Market data and cache
docs/                 # Architecture, CLI reference, memory log
tests/                # Pytest-based test suite
```

## Quality Gate

- All tests and type checks pass
- No new dependencies
- No duplicate metrics in DB schema
- Diff is < 25 LOC per change, unless discussed
- Update memory.md for recurring pitfalls

For recurring issues, consult and update memory.md.

Keep it simple, explicit, and pragmatic.

## DON'T

- Add formatting tools, security layers, or CI configs
- Introduce support for non-NSE instruments, GUI, or cron workflows
- Produce page-long code dumps—slice work until the answer is screen-sized
- Chain shell commands with `&&` in prompts or examples

## Blessed Technology Stack

- **vectorbt**: For backtesting and performance analysis
- **pandas**: For data manipulation
- **rich**: For terminal output formatting
- **typer**: For CLI interface
- **pydantic**: For data validation and contracts
- **sqlite3**: For data persistence

No additional dependencies should be added without explicit approval.