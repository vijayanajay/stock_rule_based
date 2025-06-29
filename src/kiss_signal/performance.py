"""Performance monitoring and profiling utilities for KISS Signal CLI."""

__all__ = ["performance_monitor"]

import time
import logging
import functools
from typing import Dict, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    duration: float
    function_name: str

class PerformanceMonitor:
    """Monitors and profiles performance of code blocks and functions."""
    def __init__(self) -> None:
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.thresholds = {
            'duration_warning': 30.0,  # seconds
        }
    
    @contextmanager
    def monitor_execution(self, name: str) -> Any:
        """Context manager for monitoring code execution."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            metrics = PerformanceMetrics(
                duration=duration,
                function_name=name,
            )
            self.metrics[name] = metrics
            self._check_thresholds(metrics)
            logger.info(f"{name} completed in {duration:.2f}s")
    
    def profile_performance(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for monitoring function performance."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self.monitor_execution(func.__name__):
                return func(*args, **kwargs)
        return wrapper

    def _check_thresholds(self, metrics: PerformanceMetrics) -> None:
        if metrics.duration > self.thresholds['duration_warning']:
            logger.warning(f"{metrics.function_name} exceeded duration threshold: "
                          f"{metrics.duration:.2f}s > {self.thresholds['duration_warning']}s")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {}
        
        total_duration = sum(m.duration for m in self.metrics.values())
        return {
            'total_functions': len(self.metrics),
            'total_duration': total_duration,
            'slowest_function': max(self.metrics.values(), key=lambda m: m.duration).function_name,
        }

# Global instance
performance_monitor = PerformanceMonitor()
