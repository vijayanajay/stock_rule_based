"""Tests for CLI module."""

from typer.testing import CliRunner
from pathlib import Path
from typing import Any, Dict
import yaml
from unittest.mock import patch

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
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        with patch("kiss_signal.cli.DataManager.refresh_market_data", return_value={}):
            result = runner.invoke(app, [])
            assert result.exit_code == 0, f"Exit code: {result.exit_code}, Stdout: {result.stdout}"
            assert "Data refresh complete." in result.stdout


def test_run_command_verbose(sample_config: Dict[str, Any]) -> None:
    """Test run command with verbose flag and isolated filesystem."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        with patch("kiss_signal.cli.DataManager.refresh_market_data", return_value={}):
            result = runner.invoke(app, ["--verbose"])
            assert result.exit_code == 0, result.stdout


def test_run_command_freeze_date(sample_config: Dict[str, Any]) -> None:
    """Test run command with freeze date and isolated filesystem."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        with patch("kiss_signal.cli.DataManager.refresh_market_data") as mock_refresh:
            result = runner.invoke(app, ["--freeze-data", "2025-01-01"])
            assert result.exit_code == 0, result.stdout
            assert "SKIPPED (freeze mode active)" in result.stdout
            mock_refresh.assert_not_called()


@patch("kiss_signal.cli.DataManager")
def test_run_command_success(mock_dm_class: Any, sample_config: Dict[str, Any]) -> None:
    """Test a successful run command execution with mocks."""
    mock_dm_instance = mock_dm_class.return_value
    mock_dm_instance.refresh_market_data.return_value = {}

    with runner.isolated_filesystem() as fs:
        # Setup a complete and valid file environment
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        
        # Update config to point to the new universe file
        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        result = runner.invoke(app, [])

        assert result.exit_code == 0, result.stdout
        assert "✨ Data refresh complete. Foundation is ready." in result.stdout
        mock_dm_class.assert_called_once()
        mock_dm_instance.refresh_market_data.assert_called_once()


@patch("kiss_signal.cli.DataManager")
def test_run_command_with_freeze_date(mock_dm_class: Any, sample_config: Dict[str, Any]) -> None:
    """Test run command with freeze date skips data refresh."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        result = runner.invoke(app, ["--freeze-data", "2025-01-01"])

        assert result.exit_code == 0, result.stdout
        assert "FREEZE MODE" in result.stdout
        assert "SKIPPED (freeze mode active)" in result.stdout
        mock_dm_class.assert_called_once()
        # DataManager is initialized, but refresh should not be called
        mock_dm_class.return_value.refresh_market_data.assert_not_called()


def test_run_command_invalid_freeze_date(sample_config: Dict[str, Any]) -> None:
    """Test run command with invalid freeze date."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")
        sample_config["universe_path"] = str(universe_path)
        Path("config.yaml").write_text(yaml.dump(sample_config))
        
        # Create config directory and rules file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        (config_dir / "rules.yaml").write_text("rules: []")

        result = runner.invoke(app, ["--freeze-data", "invalid-date"])
        assert result.exit_code == 1
        assert "Invalid isoformat string" in result.stdout


def test_run_command_no_config() -> None:
    """Test run command without config file to see the error."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, [])        # This should fail with exit code 1 (our app error), not 2 (typer error)
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout


def test_run_command_missing_rules():
    """Test run command with missing rules file."""
    with runner.isolated_filesystem() as fs:
        data_dir = Path(fs) / "data"
        data_dir.mkdir()
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_path.write_text("symbol,name,sector\nRELIANCE,Reliance,Energy\n")

        # Create config file pointing to the valid universe file
        with open("config.yaml", "w") as f:
            f.write(f"universe_path: {universe_path}\n")

        result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "Rules file not found" in result.stdout
