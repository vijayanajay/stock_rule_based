"""Tests for the performance monitoring module."""

import pytest
import time
from unittest.mock import patch

from kiss_signal.performance import PerformanceMonitor, performance_monitor


def test_performance_monitor_context_manager():
    """Test the monitor_execution context manager."""
    monitor = PerformanceMonitor()
    with monitor.monitor_execution("test_block"):
        time.sleep(0.01)

    assert "test_block" in monitor.metrics
    assert monitor.metrics["test_block"].duration >= 0.01
    assert monitor.metrics["test_block"].function_name == "test_block"


def test_performance_monitor_decorator():
    """Test the profile_performance decorator."""
    monitor = PerformanceMonitor()

    @monitor.profile_performance
    def sample_function():
        time.sleep(0.01)
        return "done"

    result = sample_function()

    assert result == "done"
    assert "sample_function" in monitor.metrics
    assert monitor.metrics["sample_function"].duration >= 0.01


def test_get_summary():
    """Test the get_summary method."""
    monitor = PerformanceMonitor()
    with monitor.monitor_execution("fast_op"):
        time.sleep(0.01)
    with monitor.monitor_execution("slow_op"):
        time.sleep(0.02)

    summary = monitor.get_summary()

    assert summary['total_functions'] == 2
    assert summary['total_duration'] == pytest.approx(0.03, abs=0.01)
    assert summary['slowest_function'] == "slow_op"


def test_get_summary_empty():
    """Test get_summary with no metrics."""
    monitor = PerformanceMonitor()
    summary = monitor.get_summary()
    assert summary == {}


@patch('kiss_signal.performance.logger')
def test_duration_warning(mock_logger):
    """Test that a warning is logged if duration exceeds threshold."""
    monitor = PerformanceMonitor()
    monitor.thresholds['duration_warning'] = 0.01

    with monitor.monitor_execution("long_running_task"):
        time.sleep(0.02)

    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args[0][0]
    assert "exceeded duration threshold" in call_args
    assert "long_running_task" in call_args


def test_global_monitor_instance():
    """Test that the global performance_monitor instance works."""
    # Reset metrics for isolated test
    performance_monitor.metrics.clear()

    @performance_monitor.profile_performance
    def global_test_func():
        pass

    global_test_func()

    assert "global_test_func" in performance_monitor.metrics
