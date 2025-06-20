# tests/test_persistence.py
"""Tests for the persistence module."""

import pytest
import sqlite3
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from kiss_signal.persistence import create_database, save_strategies_batch


@pytest.fixture
def temp_db_path() -> Path:
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def sample_strategies() -> List[Dict[str, Any]]:
    """Sample strategy data matching backtester output format."""
    return [
        {
            "symbol": "RELIANCE",
            "rule_stack": ["sma_10_20_crossover"],
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            "total_trades": 50,
            "avg_return": 2.5
        },
        {
            "symbol": "INFY",
            "rule_stack": ["rsi_oversold", "ema_crossover"],
            "edge_score": 0.68,
            "win_pct": 58.0,
            "sharpe": 0.9,
            "total_trades": 42,
            "avg_return": 1.8
        }
    ]


class TestCreateDatabase:
    """Test database creation functionality."""
    
    def test_create_database_success(self, temp_db_path: Path) -> None:
        """Test successful database creation with schema."""
        # Remove the temp file to test creation
        temp_db_path.unlink()
        
        create_database(temp_db_path)
        
        # Verify file was created
        assert temp_db_path.exists()
        
        # Verify schema was created correctly
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            
            # Check strategies table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategies'")
            result = cursor.fetchone()
            assert result is not None
            
            # Check index exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_strategies_symbol_timestamp'")
            result = cursor.fetchone()
            assert result is not None
            
            # Verify WAL mode is enabled
            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            assert mode.upper() == "WAL"
    
    def test_create_database_idempotent(self, temp_db_path: Path) -> None:
        """Test that creating database multiple times is safe."""
        create_database(temp_db_path)
        create_database(temp_db_path)  # Should not fail
        
        assert temp_db_path.exists()


class TestSaveStrategiesBatch:
    """Test batch save functionality."""
    
    def test_save_strategies_batch_success(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test successful batch save of strategies."""
        create_database(temp_db_path)
        
        run_timestamp = "2025-06-24T10:00:00"
        result = save_strategies_batch(temp_db_path, sample_strategies, run_timestamp)
        
        assert result is True
        
        # Verify data was saved correctly
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 2
            
            # Verify specific data
            cursor.execute("SELECT symbol, rule_stack, edge_score FROM strategies ORDER BY symbol")
            rows = cursor.fetchall()
            
            assert rows[0][0] == "INFY"
            assert json.loads(rows[0][1]) == ["rsi_oversold", "ema_crossover"]
            assert rows[0][2] == 0.68
            
            assert rows[1][0] == "RELIANCE"
            assert json.loads(rows[1][1]) == ["sma_10_20_crossover"]
            assert rows[1][2] == 0.75
    
    def test_save_strategies_batch_empty_list(self, temp_db_path: Path) -> None:
        """Test handling of empty strategy list."""
        create_database(temp_db_path)
        
        result = save_strategies_batch(temp_db_path, [], "2025-06-24T10:00:00")
        
        assert result is True
        
        # Verify no data was added
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 0
    
    def test_save_strategies_batch_transaction_rollback(self, temp_db_path: Path) -> None:
        """Test transaction rollback on error."""
        create_database(temp_db_path)
        
        # Create invalid strategy data (missing required field)
        invalid_strategies = [
            {
                "symbol": "RELIANCE",
                "rule_stack": ["sma_crossover"],
                # Missing edge_score and other required fields
            }
        ]
        
        result = save_strategies_batch(temp_db_path, invalid_strategies, "2025-06-24T10:00:00")
        
        assert result is False
        
        # Verify no partial data was saved
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 0
    
    def test_save_strategies_batch_invalid_rule_stack(self, temp_db_path: Path) -> None:
        """Test handling of invalid rule_stack data."""
        create_database(temp_db_path)
        
        # Create strategy with non-serializable rule_stack
        invalid_strategies = [
            {
                "symbol": "RELIANCE",
                "rule_stack": lambda x: x,  # Non-serializable object
                "edge_score": 0.75,
                "win_pct": 65.0,
                "sharpe": 1.2,
                "total_trades": 50,
                "avg_return": 2.5
            }
        ]
        
        result = save_strategies_batch(temp_db_path, invalid_strategies, "2025-06-24T10:00:00")
        
        assert result is False
    
    def test_save_strategies_batch_database_not_exists(self, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test handling of non-existent database file."""
        non_existent_path = Path("/tmp/non_existent.db")
        
        result = save_strategies_batch(non_existent_path, sample_strategies, "2025-06-24T10:00:00")
        
        assert result is False
    
    def test_save_strategies_multiple_batches(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test saving multiple batches to same database."""
        create_database(temp_db_path)
        
        # Save first batch
        result1 = save_strategies_batch(temp_db_path, sample_strategies, "2025-06-24T10:00:00")
        assert result1 is True
        
        # Save second batch with different timestamp
        result2 = save_strategies_batch(temp_db_path, sample_strategies, "2025-06-24T11:00:00")
        assert result2 is True
        
        # Verify both batches are saved
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 4  # 2 strategies × 2 batches
            
            # Verify different timestamps
            cursor.execute("SELECT DISTINCT run_timestamp FROM strategies ORDER BY run_timestamp")
            timestamps = [row[0] for row in cursor.fetchall()]
            assert timestamps == ["2025-06-24T10:00:00", "2025-06-24T11:00:00"]


class TestIntegration:
    """Integration tests for persistence functionality."""
    
    def test_create_and_save_workflow(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test complete workflow: create database then save strategies."""
        # Remove temp file to test full creation
        temp_db_path.unlink()
        
        # Create database
        create_database(temp_db_path)
        
        # Save strategies
        result = save_strategies_batch(temp_db_path, sample_strategies, "2025-06-24T10:00:00")
        
        assert result is True
        assert temp_db_path.exists()
        
        # Verify complete data integrity
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, rule_stack, edge_score, win_pct, sharpe, 
                       total_trades, avg_return, run_timestamp
                FROM strategies 
                ORDER BY symbol
            """)
            rows = cursor.fetchall()
            
            assert len(rows) == 2
            
            # Verify first strategy (INFY)
            assert rows[0][0] == "INFY"
            assert json.loads(rows[0][1]) == ["rsi_oversold", "ema_crossover"]
            assert rows[0][2] == 0.68
            assert rows[0][3] == 58.0
            assert rows[0][4] == 0.9
            assert rows[0][5] == 42
            assert rows[0][6] == 1.8
            assert rows[0][7] == "2025-06-24T10:00:00"
            
            # Verify second strategy (RELIANCE)
            assert rows[1][0] == "RELIANCE"
            assert json.loads(rows[1][1]) == ["sma_10_20_crossover"]
            assert rows[1][2] == 0.75