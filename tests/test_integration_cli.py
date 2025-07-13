"""Integration tests for CLI functionality.

These tests verify the complete pipeline from configuration loading through
strategy discovery and results output, catching integration issues that
unit tests with heavy mocking might miss.
"""

import pytest
from unittest.mock import patch
import pandas as pd
import yaml
from pathlib import Path
from typer.testing import CliRunner
from datetime import date
import tempfile
import shutil
import numpy as np

from kiss_signal.cli import app
from kiss_signal.config import load_config, load_rules
from kiss_signal import data


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""
    
    @pytest.fixture
    def integration_env(self, tmp_path: Path):
        """Create a complete test environment with real config files and sample data."""
        # Create directory structure
        data_dir = tmp_path / "data"
        cache_dir = data_dir / "cache"
        config_dir = tmp_path / "config"
        data_dir.mkdir()
        cache_dir.mkdir()
        config_dir.mkdir()
        
        # Create universe file
        universe_path = data_dir / "nifty_large_mid.csv"
        universe_content = """symbol,name,sector
RELIANCE,Reliance Industries Ltd,Energy
INFY,Infosys Ltd,IT
"""
        universe_path.write_text(universe_content)
        
        # Create sample price data for cache
        sample_dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
        np.random.seed(42) # for reproducibility
        
        for symbol in ['RELIANCE', 'INFY']:
            n_total = len(sample_dates)

            # Create many cycles to generate crossover signals, ensuring enough trades
            cycles = 40  # Even more cycles = more crossovers to meet threshold of 10
            cycle_length = n_total // cycles
            close_prices = []

            for cycle in range(cycles):
                start_idx, end_idx = cycle * cycle_length, min((cycle + 1) * cycle_length, n_total)
                cycle_size = end_idx - start_idx
                if cycle_size <= 0: continue
                # Alternate between uptrends and downtrends
                trend_prices = np.linspace(100, 130, cycle_size) if cycle % 2 == 0 else np.linspace(130, 100, cycle_size)
                noise = np.random.normal(loc=0, scale=1.5, size=cycle_size)
                close_prices.extend(trend_prices + noise)

            # Pad the remaining days to match n_total, fixing the IndexError
            remaining = n_total - len(close_prices)
            if remaining > 0:
                last_price = close_prices[-1] if close_prices else 100
                close_prices.extend([last_price + np.random.normal(0, 1.5) for _ in range(remaining)])

            prices = []
            for i, date_val in enumerate(sample_dates):
                close = close_prices[i]
                open_price = close + np.random.normal(0, 1.5)
                prices.append({
                    'date': date_val.strftime('%Y-%m-%d'), 'open': open_price,
                    'high': max(open_price, close) * np.random.uniform(1.0, 1.02),
                    'low': min(open_price, close) * np.random.uniform(0.98, 1.0), 'close': close,
                    'volume': 1000000 + (i % 100) * 10000
                })
            cache_file = cache_dir / f"{symbol}.NS.csv"
            pd.DataFrame(prices).to_csv(cache_file, index=False)
        
        # Create config.yaml
        config_content = {
            'universe_path': str(universe_path), 'historical_data_years': 2, 'cache_dir': str(cache_dir),
            'cache_refresh_days': 7, 'hold_period': 20, 'min_trades_threshold': 10,
            'edge_score_weights': {'win_pct': 0.6, 'sharpe': 0.4},
            "database_path": str(tmp_path / "integration.db"),
            "reports_output_dir": str(tmp_path / "reports/"), "edge_score_threshold": 0.5
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config_content))
        
        # Create rules.yaml
        rules_content = {
            'baseline': {'name': 'sma_10_20_crossover', 'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}},
            'layers': [{'name': 'rsi_oversold_30', 'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30.0}}]
        }
        rules_path = config_dir / "rules.yaml"
        rules_path.write_text(yaml.dump(rules_content))
        
        return {
            'config_path': config_path, 'rules_path': rules_path, 'cache_dir': cache_dir,
            'universe_path': universe_path
        }
    
    def test_config_loading_integration(self, integration_env):
        """Test that config and rules can be loaded and are compatible."""
        from kiss_signal.config import RuleDef
        config = load_config(integration_env['config_path'])
        rules = load_rules(integration_env['rules_path'])
        # Verify config structure
        assert config.universe_path == str(integration_env['universe_path'])
        assert config.hold_period == 20
        assert config.min_trades_threshold == 10
        # Verify rules structure
        assert hasattr(rules, 'baseline') and isinstance(rules.baseline, RuleDef)
        assert hasattr(rules, 'layers') and isinstance(rules.layers, list)
        assert len(rules.layers) > 0
        assert rules.baseline.name == 'sma_10_20_crossover'
        assert rules.layers[0].name == 'rsi_oversold_30'
    
    def test_data_loading_integration(self, integration_env):
        """Test that data loading works with real cache files."""
        symbols = data.load_universe(integration_env['universe_path'])
        assert symbols == ['RELIANCE', 'INFY']
        
        # Test loading cached data
        for symbol in symbols:
            price_data = data.get_price_data(
                symbol=symbol,
                cache_dir=integration_env['cache_dir'],
                freeze_date=date(2024, 6, 1)
            )
            
            # Verify data structure
            assert isinstance(price_data, pd.DataFrame)
            assert not price_data.empty
            assert isinstance(price_data.index, pd.DatetimeIndex)
            required_cols = {'open', 'high', 'low', 'close', 'volume'}
            assert required_cols.issubset(price_data.columns)
            
            # Verify freeze date functionality
            assert price_data.index.max() <= pd.Timestamp('2024-06-01')
    
    def test_end_to_end_cli_workflow(self, integration_env):
        """Test the complete CLI workflow without mocking."""
        runner = CliRunner()

        result = runner.invoke(app, [
            "--config", str(integration_env['config_path']),
            "--rules", str(integration_env['rules_path']),
            "run",
            "--freeze-data", "2024-06-01",
        ])

        assert result.exit_code == 0, f"CLI failed with output: {result.stdout}"
        assert "Analysis complete" in result.stdout
        assert "freeze mode" in result.stdout.lower()
        assert "No valid strategies found" not in result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
        assert "Database connection closed" in result.stdout

        # Also test that the analysis command runs without error on the generated DB
        result_analyze = runner.invoke(app, [
            "--config", str(integration_env['config_path']),
            "--rules", str(integration_env['rules_path']),
            "analyze-strategies",
        ])

        assert result_analyze.exit_code == 0, f"analyze-strategies failed with output: {result_analyze.stdout}"
        assert "Strategy performance analysis saved to:" in result_analyze.stdout  # Story 17 change: Updated text
    
    @patch("kiss_signal.cli.data.get_price_data", side_effect=Exception("Data fetch failed"))
    def test_error_handling_integration(self, mock_get_price_data, integration_env):
        """Test that the CLI handles errors gracefully and closes the DB connection."""
        runner = CliRunner()
        config_path = integration_env["config_path"]
        rules_path = integration_env["rules_path"]
        db_path = Path(yaml.safe_load(config_path.read_text())['database_path'])

        result = runner.invoke(app, [
            "--config", str(config_path),
            "--rules", str(rules_path),
            "run",
            "--freeze-data", "2024-01-01"
        ])

        # The run command should complete successfully (exit_code 0) because errors are handled internally.
        assert result.exit_code == 0, f"CLI failed with output: {result.stdout}"

        # Check that the errors were logged
        log_output = result.stdout
        assert "Error analyzing RELIANCE: Data fetch failed" in log_output
        assert "Error analyzing INFY: Data fetch failed" in log_output
        assert "Database connection closed" in log_output
