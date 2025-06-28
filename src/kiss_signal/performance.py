"""Performance monitoring and profiling utilities for KISS Signal CLI."""

import time
import logging
import psutil
import functools
from typing import Dict, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    duration: float
    memory_peak_mb: float
    memory_start_mb: float
    cpu_percent: float
    function_name: str

class PerformanceMonitor:
    """Centralized performance monitoring."""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.thresholds = {
            'duration_warning': 30.0,  # seconds
            'memory_warning': 500.0,   # MB
        }
    
    def profile_performance(self, func: Callable) -> Callable:
        """Decorator for monitoring function performance."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.monitor_execution(func.__name__) as metrics:
                result = func(*args, **kwargs)
                self.metrics[func.__name__] = metrics
                self._check_thresholds(metrics)
                return result
        return wrapper
    
    @contextmanager
    def monitor_execution(self, name: str):
        """Context manager for monitoring code execution."""
        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()
        
        metrics = None  # Initialize metrics
        try:
            yield metrics
        finally:
            duration = time.time() - start_time
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = process.cpu_percent()
            
            metrics = PerformanceMetrics(
                duration=duration,
                memory_peak_mb=max(start_memory, end_memory),
                memory_start_mb=start_memory,
                cpu_percent=max(start_cpu, end_cpu),
                function_name=name
            )
            
            logger.info(f"{name} completed in {duration:.2f}s, "
                       f"memory: {end_memory:.1f}MB, cpu: {end_cpu:.1f}%")
    
    def _check_thresholds(self, metrics: PerformanceMetrics) -> None:
        """Check performance against thresholds and warn if exceeded."""
        if metrics.duration > self.thresholds['duration_warning']:
            logger.warning(f"{metrics.function_name} exceeded duration threshold: "
                          f"{metrics.duration:.2f}s > {self.thresholds['duration_warning']}s")
        
        if metrics.memory_peak_mb > self.thresholds['memory_warning']:
            logger.warning(f"{metrics.function_name} exceeded memory threshold: "
                          f"{metrics.memory_peak_mb:.1f}MB > {self.thresholds['memory_warning']}MB")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {}
        
        total_duration = sum(m.duration for m in self.metrics.values())
        avg_memory = sum(m.memory_peak_mb for m in self.metrics.values()) / len(self.metrics)
        
        return {
            'total_functions': len(self.metrics),
            'total_duration': total_duration,
            'avg_memory_mb': avg_memory,
            'slowest_function': max(self.metrics.values(), key=lambda m: m.duration).function_name,
        }

# Global instance
performance_monitor = PerformanceMonitor()
