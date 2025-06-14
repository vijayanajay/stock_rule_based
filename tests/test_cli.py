"""Tests for CLI module."""

import pytest
from typer.testing import CliRunner

from kiss_signal.cli import app


runner = CliRunner()


def test_cli_help():
    """Test CLI help display."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "quickedge" in result.stdout.lower()


def test_run_command_basic():
    """Test basic run command."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0
    assert "Foundation setup complete" in result.stdout


def test_run_command_verbose():
    """Test run command with verbose flag."""
    result = runner.invoke(app, ["run", "--verbose"])
    assert result.exit_code == 0


def test_run_command_freeze_date():
    """Test run command with freeze date."""
    result = runner.invoke(app, ["run", "--freeze-data", "2025-01-01"])
    assert result.exit_code == 0
