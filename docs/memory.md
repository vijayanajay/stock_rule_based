+### Inconsistent CLI Application Pattern (2025-06-15)
+**Issue**: `ImportError: cannot import name 'app'` during test collection, caused by `__init__.py` attempting to import a CLI application object that was not defined in `cli.py`.
+**Root Cause**: A structural mismatch between the CLI implementation and package design. `cli.py` used the simple `typer.run(function)` pattern, suitable for standalone scripts, while `__init__.py` and `pyproject.toml` expected a reusable `typer.Typer` object named `app` for integration into the larger package and for correct script entry point generation.
+**Fix**: 
+1. Refactored `cli.py` to define a central `app = typer.Typer()` instance and registered the main function as a command using `@app.command()`.
+2. Changed the `pyproject.toml` script entry point from `kiss_signal.cli:main` to `kiss_signal.cli:app`.
+3. Modified `tests/test_cli.py` to import and use the shared `app` object, making tests more aligned with the actual application structure.
+**Prevention**: For CLI tools intended to be part of an importable package, consistently use the `typer.Typer()` application object pattern. This ensures the CLI is a well-defined, importable component, preventing structural conflicts between module implementation and package-level integration.
+
 ---
 
 Last Updated