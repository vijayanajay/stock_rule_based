"""Performance regression tests for KISS Signal CLI."""

import pytest
from pathlib import Path
import time

from kiss_signal.performance import PerformanceMonitor


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
    
    def test_duration_warning(self, caplog):
        """Test performance threshold warnings."""
        monitor = PerformanceMonitor()
        monitor.thresholds['duration_warning'] = 0.05
        
        @monitor.profile_performance
        def slow_function():
            time.sleep(0.1)
            return True
        
        slow_function()
        assert "exceeded duration threshold" in caplog.text


@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Benchmark tests for performance regression detection."""

    def test_full_workflow_performance(self, tmp_path: Path) -> None:
        """Test complete workflow performance benchmark."""
        pytest.skip("Benchmark test - run manually for performance verification")
        
        # This would test the full CLI workflow
        # and ensure it completes within target time limits
