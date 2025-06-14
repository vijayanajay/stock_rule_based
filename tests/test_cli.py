"""Tests for CLI module."""

import pytest
import os
from pathlib import Path
from typer.testing import CliRunner
import typer

from kiss_signal.cli import app


runner = CliRunner()


def test_cli_help() -> None:
    """Test CLI help display."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "quickedge" in result.stdout.lower()


def test_run_command_basic(temp_dir: Path, config_file: Path) -> None:
    """Test basic run command with proper working directory."""
    # Change to temp directory with config file
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Foundation setup complete" in result.stdout
    finally:
        os.chdir(old_cwd)


def test_run_command_verbose(temp_dir: Path, config_file: Path) -> None:
    """Test run command with verbose flag."""
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        result = runner.invoke(app, ["--verbose"])
        assert result.exit_code == 0
    finally:
        os.chdir(old_cwd)


def test_run_command_freeze_date(temp_dir: Path, config_file: Path) -> None:
    """Test run command with freeze date."""
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        result = runner.invoke(app, ["--freeze-data", "2025-01-01"])
        assert result.exit_code == 0
    finally:
        os.chdir(old_cwd)
