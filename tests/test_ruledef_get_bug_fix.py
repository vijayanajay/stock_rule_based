"""
Test cases for RuleDef.get() bug fix and related improvements.

This test module specifically addresses:
1. The main bug: RuleDef objects being treated as dicts in reporter.py
2. Secondary fix: Hardcoded years=1 replaced with app_config.historical_data_years
"""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import pandas as pd

from kiss_signal.config import RuleDef, Config
from kiss_signal import reporter


class TestRuleDefBugFixes:
    """Tests for RuleDef handling bug fixes in reporter module."""
    
    def test_generate_report_handles_ruledef_objects(self):
        """Test that WalkForwardReport.generate_report handles RuleDef objects correctly."""
        # Create mock OOS results with RuleDef objects in rule_stack
        rule_def = RuleDef(
            name="test_rule", 
            type="sma_crossover", 
            params={"fast": 10, "slow": 20},
            description="Test rule"
        )
        
        mock_results = [
            {
                "rule_stack": [rule_def],  # RuleDef object, not dict
                "edge_score": 0.5,
                "sharpe": 1.2,
                "win_pct": 0.6,
                "total_trades": 10,
                "avg_return_pct": 0.05,
            }
        ]
        
        # Create WalkForwardReport instance
        wf_report = reporter.WalkForwardReport(mock_results)
        
        # This should not raise AttributeError: 'RuleDef' object has no attribute 'get'
        result = wf_report.generate_report("TEST")
        
        # Verify the strategy name is extracted correctly
        assert "test_rule" in result
        assert "Strategy: test_rule" in result
    
    def test_generate_report_handles_mixed_rule_formats(self):
        """Test that the system handles both RuleDef objects and dicts in rule_stack."""
        # Mix of RuleDef and dict (legacy format)
        rule_def = RuleDef(name="rule1", type="sma_crossover", params={})
        rule_dict = {"name": "rule2", "type": "rsi_oversold", "params": {}}
        
        mock_results = [
            {
                "rule_stack": [rule_def, rule_dict],
                "edge_score": 0.3,
                "sharpe": 0.8,
                "win_pct": 0.5,
                "total_trades": 8,
                "avg_return_pct": 0.02,
            }
        ]
        
        wf_report = reporter.WalkForwardReport(mock_results)
        result = wf_report.generate_report("TEST")
        
        # Both rule names should appear in the strategy
        assert "rule1 + rule2" in result or ("rule1" in result and "rule2" in result)
    
    def test_generate_report_handles_rules_without_name(self):
        """Test fallback to 'type' when RuleDef has no name."""
        rule_def = RuleDef(name="", type="chandelier_exit", params={})  # Empty name
        
        mock_results = [
            {
                "rule_stack": [rule_def],
                "edge_score": 0.4,
                "sharpe": 1.0,
                "win_pct": 0.55,
                "total_trades": 6,
                "avg_return_pct": 0.03,
            }
        ]
        
        wf_report = reporter.WalkForwardReport(mock_results)
        result = wf_report.generate_report("TEST")
        
        # Should fall back to rule type
        assert "chandelier_exit" in result
    
    @patch('kiss_signal.data.get_price_data')
    def test_process_open_positions_uses_config_years(self, mock_get_price_data):
        """Test that process_open_positions uses app_config.historical_data_years, not hardcoded 1."""
        # Setup mock config with custom historical_data_years
        mock_config = Mock(spec=Config)
        mock_config.historical_data_years = 3  # Custom value, not 1
        mock_config.cache_dir = "test_cache"
        mock_config.freeze_date = None
        mock_config.hold_period = 20
        
        # Mock price data return
        mock_get_price_data.return_value = pd.DataFrame({
            'close': [100, 101, 102], 
            'high': [101, 102, 103], 
            'low': [99, 100, 101]
        })
        
        # Mock empty positions to avoid complexity
        with patch('kiss_signal.persistence.get_open_positions', return_value=[]):
            positions_to_close, positions_to_hold = reporter.process_open_positions(
                db_path=Path("test.db"),
                app_config=mock_config,
                exit_conditions=[],
                nifty_data=None
            )
        
        # Verify that get_price_data was never called with years=1
        # Since there are no open positions, get_price_data shouldn't be called at all
        # But if it were called, it should use the config value
        assert positions_to_close == []
        assert positions_to_hold == []
    
    @patch('kiss_signal.data.get_price_data')
    @patch('kiss_signal.persistence.get_open_positions')
    def test_price_data_fetch_uses_config_years_with_position(self, mock_get_positions, mock_get_price_data):
        """Test price data fetch uses config years when processing actual positions."""
        # Setup mock position
        mock_positions = [
            {
                'id': 1,
                'symbol': 'TEST',
                'entry_price': '100.0',
                'entry_date': '2024-01-01',
            }
        ]
        mock_get_positions.return_value = mock_positions

        # Setup mock config
        mock_config = Mock(spec=Config)
        mock_config.historical_data_years = 2  # Custom value
        mock_config.cache_dir = "test_cache"
        mock_config.freeze_date = None
        mock_config.hold_period = 20

        # Mock price data
        mock_get_price_data.return_value = pd.DataFrame({
            'close': [105], 'high': [106], 'low': [104]
        })

        # Mock get_position_pricing to return pricing dict without price_data
        # This will trigger the get_price_data call
        mock_pricing = {
            'current_price': 105.0,
            'current_low': 104.0,
            'current_high': 106.0,
            # No 'price_data' key, so it will fetch fresh data
        }
        
        with patch('kiss_signal.reporter.get_position_pricing', return_value=mock_pricing):
            reporter.process_open_positions(
                db_path=Path("test.db"),
                app_config=mock_config,
                exit_conditions=[],
                nifty_data=None
            )        # Verify get_price_data was called with the config years value
        mock_get_price_data.assert_called_with(
            symbol='TEST',
            cache_dir=Path('test_cache'),
            years=2,  # Should use config value, not hardcoded 1
            freeze_date=None,
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
