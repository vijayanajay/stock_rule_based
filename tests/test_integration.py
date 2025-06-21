"""Integration tests for the full KISS Signal CLI workflow.

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
from kiss_signal.backtester import Backtester
from kiss_signal import data


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""
    
    @pytest.fixture
    def integration_env(self):
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
INFY,Infosys Ltd,IT"""
            universe_path.write_text(universe_content)
              # Create sample price data for cache
            sample_dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
            np.random.seed(42) # for reproducibility
            
            for symbol in ['RELIANCE', 'INFY']:
                # Create more realistic price data using a random walk
                base_price = 100.0
                returns = np.random.normal(loc=0.0005, scale=0.02, size=len(sample_dates))
                
                close_prices = [base_price]
                for r in returns:
                    close_prices.append(close_prices[-1] * (1 + r))
                
                prices = []
                for i, date in enumerate(sample_dates):
                    close = close_prices[i+1]
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
                'min_trades_threshold': 5,  # Lower threshold for test data
                'edge_score_weights': {
                    'win_pct': 0.6,
                    'sharpe': 0.4
                }
            }
            config_path = temp_dir / "config.yaml"
            config_path.write_text(yaml.dump(config_content))
            
            # Create rules.yaml with real rule configurations
            rules_content = {
                'rules': [
                    {
                        'name': 'sma_10_20_crossover',
                        'type': 'sma_crossover',
                        'description': 'Buy when 10-day SMA crosses above 20-day SMA',
                        'params': {
                            'fast_period': 10,
                            'slow_period': 20
                        }
                    },
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
        config = load_config(integration_env['config_path'])
        rules = load_rules(integration_env['rules_path'])
        
        # Verify config structure
        assert config.universe_path == str(integration_env['universe_path'])
        assert config.hold_period == 20
        assert config.min_trades_threshold == 5
        
        # Verify rules structure
        assert len(rules) == 2
        assert all('name' in rule for rule in rules)
        assert all('type' in rule for rule in rules)
        assert all('params' in rule for rule in rules)
        
        # Verify rule types match available functions
        from kiss_signal import rules as rules_module
        for rule in rules:
            rule_type = rule['type']
            assert hasattr(rules_module, rule_type), f"Rule function {rule_type} not found"
    
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
    
    def test_backtester_with_real_rules(self, integration_env):
        """Test backtester with actual rule configurations."""
        config = load_config(integration_env['config_path'])
        rules_config = load_rules(integration_env['rules_path'])
        
        backtester = Backtester(
            hold_period=config.hold_period,
            min_trades_threshold=config.min_trades_threshold
        )
        
        # Test with real data and rules
        symbol = 'RELIANCE'
        price_data = data.get_price_data(
            symbol=symbol,
            cache_dir=integration_env['cache_dir'],
            freeze_date=date(2024, 6, 1),
            years=config.historical_data_years
        )
        
        # This should not raise an exception
        strategies = backtester.find_optimal_strategies(
            rule_combinations=rules_config,
            price_data=price_data,
            freeze_date=date(2024, 6, 1),
        )
        
        # Verify results structure
        assert isinstance(strategies, list)
        for strategy in strategies:
            assert 'rule_stack' in strategy
            assert 'edge_score' in strategy
            assert 'win_pct' in strategy
            assert 'sharpe' in strategy
            assert 'total_trades' in strategy
    
    def test_end_to_end_cli_workflow(self, integration_env):
        """Test the complete CLI workflow without mocking."""
        runner = CliRunner()

        result = runner.invoke(app, [
            "run",
            "--config", str(integration_env['config_path']),
            "--rules", str(integration_env['rules_path']),
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
            "run", 
            "--config", "nonexistent.yaml",
            "--rules", str(integration_env['rules_path'])
        ])
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout
        
        # Test with missing rules file
        result = runner.invoke(app, [
            "run",
            "--config", str(integration_env['config_path']),
            "--rules", "nonexistent.yaml"
        ])
        assert result.exit_code == 1
        assert "Rules file not found" in result.stdout
        
        # Test with invalid freeze date
        result = runner.invoke(app, [
            "run",
            "--config", str(integration_env['config_path']),
            "--rules", str(integration_env['rules_path']),
            "--freeze-data", "invalid-date"
        ])
        assert result.exit_code == 1


class TestBacktesterRuleIntegration:
    """Tests specifically for backtester integration with rule configurations."""
    
    def test_rule_function_lookup(self):
        """Test that rule types from YAML map correctly to rule functions."""
        from kiss_signal import rules as rules_module
        
        # Test rule configurations from actual rules.yaml
        test_rules = [
            {'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}},
            {'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30}},
            {'type': 'ema_crossover', 'params': {'fast_period': 12, 'slow_period': 26}}
        ]
        
        for rule in test_rules:
            rule_type = rule['type']
            rule_function = getattr(rules_module, rule_type, None)
            assert rule_function is not None, f"Rule function {rule_type} not found"
            assert callable(rule_function), f"Rule {rule_type} is not callable"
    
    def test_rule_parameter_validation(self):
        """Test that rule parameters are properly validated."""
        from kiss_signal.rules import sma_crossover, rsi_oversold, ema_crossover
        
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = [100 + i * 0.1 for i in range(100)]
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [1000] * 100
        }, index=dates)
        
        # Test each rule function with valid parameters
        sma_signals = sma_crossover(df, fast_period=10, slow_period=20)
        assert isinstance(sma_signals, pd.Series)
        assert len(sma_signals) == len(df)
        
        rsi_signals = rsi_oversold(df, period=14, oversold_threshold=30.0)
        assert isinstance(rsi_signals, pd.Series)
        assert len(rsi_signals) == len(df)
        
        ema_signals = ema_crossover(df, fast_period=12, slow_period=26)
        assert isinstance(ema_signals, pd.Series)
        assert len(ema_signals) == len(df)
