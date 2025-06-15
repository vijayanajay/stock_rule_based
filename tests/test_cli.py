"""Tests for CLI module."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml

from kiss_signal.cli import app


# Test imports first
def test_cli_import() -> None:
    """Test that CLI app can be imported without issues."""
    assert app is not None
    assert hasattr(app, 'registered_commands')

runner = CliRunner()


def test_help_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout.lower()


def test_run_command_basic(sample_config: Dict[str, Any]) -> None:
    """Test basic run command with isolated filesystem."""
    with runner.isolated_filesystem():
        Path("config.yaml").write_text(yaml.dump(sample_config))
        # Since run is the default command, don't pass "run" as an argument
        result = runner.invoke(app, [])
        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Stdout: {result.stdout}"
        assert "Foundation setup complete" in result.stdout


def test_run_command_verbose(sample_config: Dict[str, Any]) -> None:
    """Test run command with verbose flag and isolated filesystem."""
    with runner.isolated_filesystem():
        Path("config.yaml").write_text(yaml.dump(sample_config))
        result = runner.invoke(app, ["--verbose"])
        assert result.exit_code == 0, result.stdout


def test_run_command_freeze_date(sample_config: Dict[str, Any]) -> None:
    """Test run command with freeze date and isolated filesystem."""
    with runner.isolated_filesystem():
        Path("config.yaml").write_text(yaml.dump(sample_config))
        result = runner.invoke(
            app,
            ["--freeze-data", "2025-01-01"],
        )
        assert result.exit_code == 0, result.stdout


def test_run_command_no_config() -> None:
    """Test run command without config file to see the error."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, [])        # This should fail with exit code 1 (our app error), not 2 (typer error)
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout
