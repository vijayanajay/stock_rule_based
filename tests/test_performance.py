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
    with patch('time.time', side_effect=[1000.0, 1000.01, 1000.02, 1000.04, 1000.06, 1000.07]):
        with monitor.monitor_execution("fast_op"):
            time.sleep(0.01)  # sleep is fine here as we mock time.time
        with monitor.monitor_execution("slow_op"):
            time.sleep(0.02)  # sleep is fine here as we mock time.time

    summary = monitor.get_summary()

    assert summary['total_functions'] == 2
    # fast_op duration = 1000.01 - 1000.0 = 0.01. slow_op = 1000.06 - 1000.04 = 0.02
    assert summary['total_duration'] == pytest.approx(0.03, abs=1e-3)
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


@pytest.mark.slow
def test_performance_benchmark_simulation():
    """
    A simple benchmark simulation.

    This is not a full integration test but serves as a placeholder for
    the 60-ticker benchmark requirement, ensuring the performance monitoring
    tools can capture and report on longer-running processes without adding
    heavy dependencies like pytest-benchmark.
    """
    monitor = PerformanceMonitor()
    monitor.thresholds['duration_warning'] = 10.0  # Set a high threshold for this test

    @monitor.profile_performance
    def _simulated_ticker_analysis():
        """Simulates analysis for one ticker."""
        time.sleep(0.001)  # A small but not negligible delay

    with monitor.monitor_execution("full_60_ticker_run"):
        for _ in range(60):
            _simulated_ticker_analysis()

    assert "full_60_ticker_run" in monitor.metrics
    assert monitor.metrics["full_60_ticker_run"].duration >= 60 * 0.001
