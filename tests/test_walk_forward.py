"""Unit tests for walk-forward analysis functionality."""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from kiss_signal.config import Config, WalkForwardConfig, EdgeScoreWeights, RulesConfig, RuleDef
from kiss_signal.backtester import Backtester


class TestWalkForwardAnalysis:
    """Test suite for walk-forward analysis."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.01)
        
        return pd.DataFrame({
            'Open': prices,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(10000, 100000, len(dates))
        }, index=dates)
    
    @pytest.fixture
    def walk_forward_config(self):
        """Create walk-forward configuration."""
        return WalkForwardConfig(
            enabled=True,
            training_period="365d",
            testing_period="90d", 
            step_size="90d",
            min_trades_per_period=5
        )
    
    @pytest.fixture
    def sample_rules_config(self):
        """Create sample rules configuration."""
        return RulesConfig(
            entry_signals=[
                RuleDef(name="test_rule", type="sma_cross", params={"short": 10, "long": 20})
            ],
            exit_conditions=[]
        )
    
    @pytest.fixture
    def backtester_instance(self):
        """Create backtester instance."""
        return Backtester(hold_period=10, min_trades_threshold=5)
    
    def test_parse_period(self, backtester_instance):
        """Test period parsing functionality."""
        bt = backtester_instance
        
        assert bt._parse_period("365d") == 365
        assert bt._parse_period("12m") == 360  # 12 * 30
        assert bt._parse_period("2y") == 730   # 2 * 365
        
        with pytest.raises(ValueError):
            bt._parse_period("invalid")
    
    def test_get_rolling_periods(self, backtester_instance, sample_price_data):
        """Test rolling periods generation."""
        bt = backtester_instance
        
        periods = bt._get_rolling_periods(
            sample_price_data, 
            training_days=365, 
            testing_days=90, 
            step_days=90
        )
        
        assert len(periods) > 0
        assert isinstance(periods[0], pd.Timestamp)
        
        # Check that periods are spaced correctly
        if len(periods) > 1:
            diff = periods[1] - periods[0]
            assert diff.days == 90
    
    def test_get_rolling_periods_insufficient_data(self, backtester_instance):
        """Test rolling periods with insufficient data."""
        bt = backtester_instance
        
        # Create very short data
        short_data = pd.DataFrame(
            {'Close': [100, 101, 102]},
            index=pd.date_range('2023-01-01', periods=3, freq='D')
        )
        
        periods = bt._get_rolling_periods(
            short_data,
            training_days=365,
            testing_days=90,
            step_days=90
        )
        
        assert len(periods) == 0
    
    def test_walk_forward_config_validation(self):
        """Test walk-forward configuration validation."""
        # Valid config
        config = WalkForwardConfig(
            enabled=True,
            training_period="365d",
            testing_period="90d",
            step_size="30d",
            min_trades_per_period=5
        )
        assert config.enabled is True
        assert config.training_period == "365d"
    
    def test_legacy_in_sample_optimization_warning(self, backtester_instance, sample_price_data, sample_rules_config, caplog):
        """Test that in-sample optimization produces warning."""
        bt = backtester_instance
        
        # Mock the actual legacy optimization to avoid complex setup
        with patch.object(bt, '_test_single_rule', return_value=None):
            bt._legacy_in_sample_optimization(
                sample_price_data,
                sample_rules_config,
                "TEST"
            )
        
        # Check that warning was logged
        assert "USING IN-SAMPLE OPTIMIZATION" in caplog.text
        assert "NOT reliable for live trading" in caplog.text
    
    def test_find_optimal_strategies_in_sample_flag(self, backtester_instance, sample_price_data, sample_rules_config):
        """Test that in_sample flag properly routes to legacy optimization."""
        bt = backtester_instance
        
        with patch.object(bt, '_legacy_in_sample_optimization', return_value=[]) as mock_legacy:
            bt.find_optimal_strategies(
                price_data=sample_price_data,
                rules_config=sample_rules_config,
                symbol="TEST",
                in_sample=True
            )
            
            mock_legacy.assert_called_once()
    
    def test_find_optimal_strategies_walk_forward_enabled(self, backtester_instance, sample_price_data, sample_rules_config, walk_forward_config):
        """Test that walk-forward is used when enabled in config."""
        bt = backtester_instance
        
        # Create a temporary universe file for the test
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("symbol\nTEST\n")
            temp_universe_path = f.name
        
        try:
            config = Config(
                universe_path=temp_universe_path,
                historical_data_years=3,
                cache_dir="cache",
                hold_period=10,
                min_trades_threshold=5,
                edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
                database_path="test.db",
                reports_output_dir="reports/",
                edge_score_threshold=0.5,
                walk_forward=walk_forward_config
            )
            
            with patch.object(bt, 'walk_forward_backtest', return_value=[]) as mock_wf:
                bt.find_optimal_strategies(
                    price_data=sample_price_data,
                    rules_config=sample_rules_config,
                    symbol="TEST",
                    config=config,
                    in_sample=False
                )
                
                mock_wf.assert_called_once()
        finally:
            # Clean up the temporary file
            os.unlink(temp_universe_path)
    
    def test_consolidate_oos_results_empty(self, backtester_instance):
        """Test consolidation with empty results."""
        bt = backtester_instance
        result = bt._consolidate_oos_results([], "TEST")
        assert result is None
    
    def test_consolidate_oos_results_valid(self, backtester_instance):
        """Test consolidation with valid results."""
        bt = backtester_instance
        
        oos_results = [
            {
                "total_trades": 10,
                "edge_score": 0.6,
                "win_pct": 0.7,
                "sharpe": 1.2,
                "avg_return": 0.05,
                "rule_stack": [{"name": "test", "type": "test"}]
            },
            {
                "total_trades": 15,
                "edge_score": 0.8,
                "win_pct": 0.8,
                "sharpe": 1.5,
                "avg_return": 0.07,
                "rule_stack": [{"name": "test", "type": "test"}]
            }
        ]
        
        result = bt._consolidate_oos_results(oos_results, "TEST")
        
        assert result is not None
        assert result["symbol"] == "TEST"
        assert result["total_trades"] == 25  # 10 + 15
        assert result["oos_periods"] == 2
        assert result["is_oos"] is True
        
        # Check simple averages (not weighted)
        expected_edge = (0.6 + 0.8) / 2  # Simple average
        assert abs(result["edge_score"] - expected_edge) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
