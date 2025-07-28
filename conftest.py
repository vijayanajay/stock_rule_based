"""Global pytest configuration for optimized test execution."""

import sys
from pathlib import Path

# Add src directory to Python path so tests import from development source, not installed packages
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
import tempfile
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# Standard Test Data Constants
# =============================================================================

VALID_CONFIG_YAML = """
# KISS Signal CLI Configuration - Test Version
universe_path: "data/nifty_large_mid.csv"
historical_data_years: 3
cache_dir: "data/cache"
hold_period: 20
min_trades_threshold: 10
edge_score_weights:
  win_pct: 0.6
  sharpe: 0.4
database_path: "data/kiss_signal.db"
reports_output_dir: "reports/"
edge_score_threshold: 0.50
"""

VALID_RULES_YAML = """
baseline:
  name: "test_baseline"
  type: "sma_crossover"
  params:
    fast_period: 5
    slow_period: 10

momentum:
  name: "test_momentum"
  type: "rsi_oversold"
  params:
    period: 14
    oversold_threshold: 30
"""

SAMPLE_UNIVERSE = "symbol\nRELIANCE\nTCS\nINFY\nHDFCBANK\nICICIBANK\n"


# =============================================================================
# Centralized Test Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_environment():
    """Test environment with complete config.yaml and rules.yaml files.
    
    Creates a temporary directory with:
    - Complete, valid config.yaml (all required Pydantic fields)
    - Valid rules.yaml
    - Universe file with sample stocks
    - Required directory structure (data/, config/, reports/)
    
    Returns the Path to the temporary directory.
    """
    import gc
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure
        (temp_path / "data").mkdir()
        (temp_path / "data" / "cache").mkdir()
        (temp_path / "config").mkdir()
        (temp_path / "reports").mkdir()
        
        # Create complete config.yaml
        config_path = temp_path / "config.yaml"
        with open(config_path, 'w') as f:
            f.write(VALID_CONFIG_YAML)
            
        # Create rules.yaml
        rules_path = temp_path / "config" / "rules.yaml"
        with open(rules_path, 'w') as f:
            f.write(VALID_RULES_YAML)
            
        # Create universe file
        universe_path = temp_path / "data" / "nifty_large_mid.csv"
        with open(universe_path, 'w') as f:
            f.write(SAMPLE_UNIVERSE)
            
        # Create a basic database with required tables for CLI commands
        db_path = temp_path / "data" / "kiss_signal.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create strategies table with exact schema from persistence.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                run_timestamp TEXT NOT NULL,
                rule_stack TEXT NOT NULL,
                edge_score REAL NOT NULL,
                win_pct REAL NOT NULL,
                sharpe REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                avg_return REAL NOT NULL,
                config_snapshot TEXT,
                config_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, rule_stack, run_timestamp)
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, config_hash, created_at)
            VALUES ('RELIANCE', '2024-01-01 00:00:00', 'test_baseline', 0.75, 0.65, 1.2, 15, 0.18, 'hash123', '2024-01-01 00:00:00')
        """)
        
        # Create positions table with exact schema from persistence.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_date TEXT,
                exit_price REAL,
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                rule_stack_used TEXT NOT NULL,
                final_return_pct REAL,
                exit_reason TEXT,
                final_nifty_return_pct REAL,
                days_held INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO positions (symbol, entry_date, entry_price, exit_date, exit_price, status, rule_stack_used, final_return_pct, exit_reason, days_held, created_at)
            VALUES ('RELIANCE', '2024-01-01', 2500.0, '2024-01-21', 2650.0, 'CLOSED', 'test_baseline', 0.06, 'TEST', 20, '2024-01-01 00:00:00')
        """)
        
        # Create indexes to match persistence.py
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategies_symbol_timestamp 
            ON strategies(symbol, run_timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_status_symbol 
            ON positions(status, symbol)
        """)
        
        # Set schema version to match current
        cursor.execute("PRAGMA user_version = 2;")
        
        conn.commit()
        conn.close()
            
        try:
            yield temp_path
        finally:
            # Enhanced database cleanup for Windows compatibility
            import gc
            import time
            
            # Force garbage collection to close any lingering connections
            gc.collect()
            time.sleep(0.2)  # Longer pause for Windows file handles
            
            # Try multiple cleanup strategies for database files
            db_path = temp_path / "data" / "kiss_signal.db"
            for db_file in [db_path, db_path.with_suffix('.db-wal'), db_path.with_suffix('.db-shm')]:
                if db_file.exists():
                    try:
                        # Try to close any potential connections first
                        try:
                            conn_test = sqlite3.connect(str(db_file), timeout=1)
                            conn_test.close()
                        except:
                            pass
                        
                        # Wait and try deletion
                        time.sleep(0.1)
                        db_file.unlink()
                    except (PermissionError, OSError) as e:
                        # Log but don't fail the test - let OS cleanup handle it
                        logger.debug(f"Could not delete {db_file}: {e}")
                        pass


@pytest.fixture(scope="session")
def sample_db():
    """Pre-populated SQLite database with test data.
    
    Creates a temporary database with sample strategies and positions
    for consistent testing across test modules.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Create database with sample data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create strategies table with correct schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                run_timestamp TEXT NOT NULL,
                rule_stack TEXT NOT NULL,
                edge_score REAL NOT NULL,
                win_pct REAL NOT NULL,
                sharpe REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                avg_return REAL NOT NULL,
                config_snapshot TEXT,
                config_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, rule_stack, run_timestamp)
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, config_hash, created_at)
            VALUES ('RELIANCE', '2024-01-01 00:00:00', 'test_baseline', 0.75, 0.65, 1.2, 15, 0.18, 'hash123', '2024-01-01 00:00:00')
        """)
        
        # Create positions table with correct schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_date TEXT,
                exit_price REAL,
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                rule_stack_used TEXT NOT NULL,
                final_return_pct REAL,
                exit_reason TEXT,
                final_nifty_return_pct REAL,
                days_held INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO positions (symbol, entry_date, entry_price, exit_date, exit_price, status, rule_stack_used, final_return_pct, exit_reason, days_held, created_at)
            VALUES ('RELIANCE', '2024-01-01', 2500.0, '2024-01-21', 2650.0, 'CLOSED', 'test_baseline', 0.06, 'TEST', 20, '2024-01-01 00:00:00')
        """)
        
        conn.commit()
        conn.close()
        
        yield db_path
        
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def stock_data_samples():
    """Standard OHLCV test data for consistent testing.
    
    Returns a dictionary of DataFrames with sample price data for multiple symbols.
    Each DataFrame has Date index and OHLCV columns.
    """
    # Generate 365 days of sample data
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=365),
        end=datetime.now(),
        freq='D'
    )
    
    # Sample data for RELIANCE
    reliance_data = pd.DataFrame({
        'Open': 2500.0 + (dates.dayofyear * 0.5),
        'High': 2520.0 + (dates.dayofyear * 0.5),
        'Low': 2480.0 + (dates.dayofyear * 0.5),
        'Close': 2510.0 + (dates.dayofyear * 0.5),
        'Volume': 1000000
    }, index=dates)
    
    # Sample data for TCS
    tcs_data = pd.DataFrame({
        'Open': 3500.0 + (dates.dayofyear * 0.3),
        'High': 3520.0 + (dates.dayofyear * 0.3),
        'Low': 3480.0 + (dates.dayofyear * 0.3),
        'Close': 3510.0 + (dates.dayofyear * 0.3),
        'Volume': 800000
    }, index=dates)
    
    return {
        'RELIANCE': reliance_data,
        'TCS': tcs_data,
        'INFY': tcs_data.copy(),  # Reuse TCS pattern for INFY
        'HDFCBANK': reliance_data.copy(),  # Reuse RELIANCE pattern
        'ICICIBANK': reliance_data.copy()
    }


# =============================================================================
# Legacy Fixtures (for backward compatibility)
# =============================================================================

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
