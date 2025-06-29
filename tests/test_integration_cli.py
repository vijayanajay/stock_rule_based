"""Integration tests for CLI functionality.

These tests verify the complete pipeline from configuration loading through
strategy discovery and results output, catching integration issues that
unit tests with heavy mocking might miss.
"""

import pytest
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
    
    @pytest.fixture(scope="module")
    def integration_env(self, request):
        """Create a complete test environment with real config files and sample data."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create directory structure
            data_dir = temp_dir / "data"
            cache_dir = data_dir / "cache"
            config_dir = temp_dir / "config"
            
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
                # Generate data with multiple trend changes to ensure SMA crossovers
                n_total = len(sample_dates)

                # Create multiple cycles to generate crossover signals
                cycles = 6  # More cycles = more crossovers
                cycle_length = n_total // cycles
                close_prices = []

                for cycle in range(cycles):
                    start_idx = cycle * cycle_length
                    end_idx = min((cycle + 1) * cycle_length, n_total)
                    cycle_size = end_idx - start_idx

                    # Alternate between uptrends and downtrends
                    if cycle % 2 == 0:
                        # Uptrend: 100 to 130
                        trend_prices = np.linspace(100, 130, cycle_size)
                    else:
                        # Downtrend: 130 to 100
                        trend_prices = np.linspace(130, 100, cycle_size)

                    # Add noise for realism
                    noise = np.random.normal(loc=0, scale=1.5, size=cycle_size)
                    close_prices.extend(trend_prices + noise)

                # Handle any remaining dates (due to division remainder)
                remaining = n_total - len(close_prices)
                if remaining > 0:
                    # Fill remaining with last trend continuation
                    last_price = close_prices[-1] if close_prices else 100
                    for _ in range(remaining):
                        close_prices.append(last_price + np.random.normal(0, 1.5))
                
                prices = []
                for i, date in enumerate(sample_dates):
                    close = close_prices[i]
                    open_price = close * np.random.uniform(0.99, 1.01)
                    high_price = max(open_price, close) * np.random.uniform(1.0, 1.02)
                    low_price = min(open_price, close) * np.random.uniform(0.98, 1.0)
                    prices.append({
                        'date': date,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close,
                        'volume': 1000000 + (i % 100) * 10000
                    })
                
                cache_file = cache_dir / f"{symbol}.NS.csv"
                df = pd.DataFrame(prices)
                df.to_csv(cache_file, index=False)
            
            # Create config.yaml
            config_content = {
                'universe_path': str(universe_path),
                'historical_data_years': 2,
                'cache_dir': str(cache_dir),
                'cache_refresh_days': 7,
                'hold_period': 20,
                'min_trades_threshold': 2,  # Lower threshold for test data
                'edge_score_weights': {
                    'win_pct': 0.6,
                    'sharpe': 0.4
                }
            }
            config_path = temp_dir / "config.yaml"
            config_path.write_text(yaml.dump(config_content))
            
            # Create rules.yaml with real rule configurations
            rules_content = {
                'baseline': {
                    'name': 'sma_10_20_crossover',
                    'type': 'sma_crossover',
                    'description': 'Buy when 10-day SMA crosses above 20-day SMA',
                    'params': {
                        'fast_period': 10,
                        'slow_period': 20
                    }
                },
                'layers': [
                    {
                        'name': 'rsi_oversold_30',
                        'type': 'rsi_oversold',
                        'description': 'Buy when RSI drops below 30',
                        'params': {
                            'period': 14,
                            'oversold_threshold': 30.0
                        }
                    }
                ]
            }
            rules_path = config_dir / "rules.yaml"
            rules_path.write_text(yaml.dump(rules_content))
            
            yield {
                'temp_dir': temp_dir,
                'config_path': config_path,
                'rules_path': rules_path,
                'data_dir': data_dir,
                'cache_dir': cache_dir,
                'universe_path': universe_path
            }
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
    
    def test_config_loading_integration(self, integration_env):
        """Test that config and rules can be loaded and are compatible."""
        from kiss_signal.config import RuleDef
        config = load_config(integration_env['config_path'])
        rules = load_rules(integration_env['rules_path'])
        # Verify config structure
        assert config.universe_path == str(integration_env['universe_path'])
        assert config.hold_period == 20
        assert config.min_trades_threshold == 2
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
        # Check for freeze mode message, case-insensitively
        assert "freeze mode" in result.stdout.lower()
        # Check that strategies were actually found
        assert "No valid strategies found" not in result.stdout
        assert "Top Strategies by Edge Score" in result.stdout
    
    def test_error_handling_integration(self, integration_env):
        """Test error handling in integration scenarios."""
        runner = CliRunner()
        
        # Test with missing config file
        result = runner.invoke(app, [
            "--config", "nonexistent.yaml",
            "--rules", str(integration_env['rules_path']),
            "run",
         ])
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout
        
        # Test with missing rules file
        result = runner.invoke(app, [
            "--config", str(integration_env['config_path']),
            "--rules", "nonexistent.yaml",
            "run",
        ])
        assert result.exit_code == 1
        assert "Rules file not found" in result.stdout
        
        # Test with invalid freeze date
        result = runner.invoke(app, [
            "--config", str(integration_env['config_path']),
            "--rules", str(integration_env['rules_path']),
            "run",
            "--freeze-data", "invalid-date",
        ])
        assert result.exit_code == 1
