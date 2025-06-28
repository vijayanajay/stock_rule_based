"""Global pytest configuration for optimized test execution."""

import pytest
import tempfile
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def temp_data_dir():
    """Session-scoped temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def benchmark_price_data():
    """Session-scoped price data for benchmark tests."""
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=365),
        end=datetime.now(),
        freq='D'
    )
    
    return pd.DataFrame({
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 100000
    }, index=dates)


def pytest_configure(config):
    """Configure pytest for performance optimization."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "benchmark: mark test as a performance benchmark"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for better performance."""
    for item in items:
        # Mark benchmark tests
        if "benchmark" in item.nodeid:
            item.add_marker(pytest.mark.benchmark)
        
        # Mark potentially slow tests
        if any(keyword in item.nodeid for keyword in ["integration", "slow", "io"]):
            item.add_marker(pytest.mark.slow)
