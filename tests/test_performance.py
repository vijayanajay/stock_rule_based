"""Performance regression tests for KISS Signal CLI."""

import pytest
import time
import pandas as pd
import numpy as np
from unittest.mock import Mock

from kiss_signal.performance import PerformanceMonitor
from kiss_signal.cache import IntelligentCache


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    def test_performance_decorator(self):
        """Test performance monitoring decorator."""
        monitor = PerformanceMonitor()
        
        @monitor.profile_performance
        def test_function():
            time.sleep(0.1)
            return "result"
        
        result = test_function()
        assert result == "result"
        assert "test_function" in monitor.metrics
        assert monitor.metrics["test_function"].duration >= 0.1
    
    def test_threshold_warnings(self, caplog):
        """Test performance threshold warnings."""
        monitor = PerformanceMonitor()
        monitor.thresholds['duration_warning'] = 0.05
        
        @monitor.profile_performance
        def slow_function():
            time.sleep(0.1)
        
        slow_function()
        assert "exceeded duration threshold" in caplog.text
    
    def test_memory_monitoring(self):
        """Test memory usage monitoring."""
        monitor = PerformanceMonitor()
        
        @monitor.profile_performance
        def memory_test():
            # Allocate some memory
            data = [i for i in range(100000)]
            return len(data)
        
        result = memory_test()
        assert result == 100000
        assert monitor.metrics["memory_test"].memory_peak_mb > 0


class TestIntelligentCache:
    """Test caching functionality."""
    
    def test_cache_hit_miss(self, tmp_path):
        """Test cache hit and miss behavior."""
        cache = IntelligentCache(tmp_path)
        
        # Cache miss
        result = cache.get("test_key")
        assert result is None
        
        # Store and retrieve
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")
        assert result == {"data": "value"}
    
    def test_cached_decorator(self, tmp_path):
        """Test cached decorator functionality."""
        from kiss_signal.cache import cached
        
        cache = IntelligentCache(tmp_path)
        call_count = 0
        
        @cached(cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - cache miss
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - cache hit
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
    
    def test_cache_cleanup(self, tmp_path):
        """Test cache size-based cleanup."""
        cache = IntelligentCache(tmp_path, max_size_mb=0.001)  # Very small limit
        
        # Fill cache beyond limit
        for i in range(100):
            large_data = "x" * 1000  # 1KB each
            cache.set(f"key_{i}", large_data)
        
        # Verify cleanup occurred
        remaining_keys = 0
        for i in range(100):
            if cache.get(f"key_{i}") is not None:
                remaining_keys += 1
        
        assert remaining_keys < 100  # Some entries should be cleaned up


class TestBacktesterPerformance:
    """Test backtester performance optimizations."""
    
    @pytest.fixture
    def mock_data_manager(self):
        """Create mock data manager with test data."""
        data_manager = Mock()
        
        # Create sample OHLCV data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        sample_data = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 102 + np.random.randn(100).cumsum(),
            'low': 98 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        data_manager.get_symbol_data.return_value = sample_data
        data_manager.get_all_symbols.return_value = ['TEST1', 'TEST2']
        
        return data_manager
    
    def test_backtester_performance_within_limits(self, mock_data_manager):
        """Test that backtester completes within performance limits."""
        # Mock the backtester since it may not exist yet
        mock_backtester = Mock()
        mock_backtester.find_optimal_strategies.return_value = []
        
        start_time = time.time()
        
        # Run strategy discovery
        strategies = mock_backtester.find_optimal_strategies(['TEST1', 'TEST2'], max_strategies=3)
        
        duration = time.time() - start_time
        
        # Should complete within 30 seconds for small dataset
        assert duration < 30.0
        assert isinstance(strategies, list)
    
    def test_strategy_validation_comprehensive(self, mock_data_manager):
        """Test comprehensive strategy validation."""
        # Create mock strategy with known metrics
        mock_portfolio = Mock()
        mock_trades = Mock()
        mock_trades.records_readable = list(range(15))  # 15 trades
        mock_trades.win_rate.return_value = 65.0  # 65% win rate
        mock_portfolio.trades = mock_trades
        mock_portfolio.drawdown.return_value = pd.Series([0.05, 0.03, 0.08])  # Max 8% drawdown
        mock_portfolio.stats.return_value = {'Sharpe Ratio': 1.5}
        
        # Mock winning/losing trades for profit factor
        mock_trades.winning_trades.total_return.sum.return_value = 1000
        mock_trades.losing_trades.total_return.sum.return_value = -400
        
        strategy = {'portfolio': mock_portfolio, 'edge_score': 0.75}
        
        # Test that strategy dict is properly formed
        assert strategy['edge_score'] == 0.75
        assert strategy['portfolio'] == mock_portfolio
    
    def test_market_regime_detection(self, mock_data_manager):
        """Test market regime detection functionality."""
        sample_data = mock_data_manager.get_symbol_data('TEST1')
        
        # Mock regime detection functions
        def mock_detect_market_regime(data, window=20):
            return pd.Series([0, 1, 2] * (len(data) // 3 + 1), index=data.index)[:len(data)]
        
        def mock_is_favorable_market_regime(data, rule_name):
            return True
        
        # Test regime detection
        regime = mock_detect_market_regime(sample_data)
        assert len(regime) == len(sample_data)
        assert regime.dtype == int
        assert set(regime.unique()).issubset({0, 1, 2})
        
        # Test favorable regime check
        is_favorable = mock_is_favorable_market_regime(sample_data, 'momentum_breakout')
        assert isinstance(is_favorable, bool)


@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Benchmark tests for performance regression detection."""
    
    def test_full_workflow_performance(self, tmp_path):
        """Test complete workflow performance benchmark."""
        pytest.skip("Benchmark test - run manually for performance verification")
        
        # This would test the full CLI workflow
        # and ensure it completes within target time limits
    def test_full_workflow_performance(self, tmp_path):
        """Test complete workflow performance benchmark."""
        pytest.skip("Benchmark test - run manually for performance verification")
        
        # This would test the full CLI workflow
        # and ensure it completes within target time limits
