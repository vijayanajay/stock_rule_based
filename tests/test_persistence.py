# tests/test_persistence.py
"""Tests for the persistence module."""

import pytest
import sqlite3
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
import typing
import numpy as np
import pandas as pd

from kiss_signal.persistence import create_database, save_strategies_batch, add_new_positions_from_signals
from kiss_signal.persistence import get_open_positions, close_positions_batch # Import missing functions
from kiss_signal import persistence  # Import persistence module for migration functions


@pytest.fixture
def temp_db_path(tmp_path: Path) -> typing.Generator[Path, None, None]:
    """Provide a temporary database file path."""
    db_path = tmp_path / "test.db"
    yield db_path


@pytest.fixture
def sample_strategies() -> List[Dict[str, Any]]:
    """Sample strategy data matching backtester output format."""
    return [
        {
            "symbol": "RELIANCE",
            "rule_stack": [{'name': 'sma_10_20_crossover', 'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}}],
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            "total_trades": 50,
            "avg_return": 2.5
        },
        {
            "symbol": "INFY",
            "rule_stack": [{'name': 'rsi_oversold_30', 'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30.0}}],
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
        # temp_db_path fixture ensures it's clean
        
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

    def test_create_database_failure(self, temp_db_path: Path):
        """Test database creation failure."""
        # temp_db_path fixture ensures it's clean

        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test DB error")) as mock_connect:
            with pytest.raises(sqlite3.Error, match="Test DB error"):
                create_database(temp_db_path)

        mock_connect.assert_called_once_with(str(temp_db_path))
        assert not temp_db_path.exists() # Should not have been created


class TestSaveStrategiesBatch:
    """Test batch save functionality."""
    
    def test_save_strategies_batch_success(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test successful batch save of strategies."""
        create_database(temp_db_path)
        
        run_timestamp = "2025-06-24T10:00:00"
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, sample_strategies, run_timestamp)
        
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
            assert json.loads(rows[0][1]) == [{'name': 'rsi_oversold_30', 'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30.0}}]
            assert rows[0][2] == 0.68
            
            assert rows[1][0] == "RELIANCE"
            assert json.loads(rows[1][1]) == [{'name': 'sma_10_20_crossover', 'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}}]
            assert rows[1][2] == 0.75
    
    def test_save_strategies_batch_empty_list(self, temp_db_path: Path) -> None:
        """Test handling of empty strategy list."""
        create_database(temp_db_path)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, [], "2025-06-24T10:00:00")
        
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
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, invalid_strategies, "2025-06-24T10:00:00")
        
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
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, invalid_strategies, "2025-06-24T10:00:00")
        
        assert result is False
    
    def test_save_strategies_batch_with_closed_connection(self, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test that save_strategies_batch fails with a closed connection."""
        conn = sqlite3.connect(":memory:")
        conn.close()
        result = save_strategies_batch(conn, sample_strategies, "2025-06-24T10:00:00")
        assert result is False

    def test_save_strategies_batch_insert_error(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]):
        """Test transaction rollback on unique constraint violation."""
        create_database(temp_db_path)
        
        # Add a duplicate strategy to the list to cause a UNIQUE constraint failure
        strategies_with_duplicate = sample_strategies + [sample_strategies[0]]
        
        run_timestamp = "2025-07-15T10:00:00"
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            # The batch save should fail because of the unique constraint violation on the last item.
            # The transaction should be rolled back, leaving the table empty.
            result = save_strategies_batch(conn, strategies_with_duplicate, run_timestamp)

        assert result is False
        
        # Verify no data was saved due to rollback
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 0

    def test_save_strategies_batch_with_numpy_int(self, temp_db_path: Path) -> None:
        """Test that numpy integer types are correctly stored as standard integers."""
        create_database(temp_db_path)

        # Create a strategy where total_trades is a numpy integer type
        numpy_strategies = [
            {
                "symbol": "RELIANCE",
                "rule_stack": [{'name': 'test_rule', 'type': 'test_type', 'params': {}}],
                "edge_score": 0.5, "win_pct": 0.5, "sharpe": 1.0,
                "total_trades": np.int64(25),  # Use a numpy integer type
                "avg_return": 0.01
            }
        ]

        run_timestamp = "2025-07-23T12:00:00"
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, numpy_strategies, run_timestamp)

        assert result is True

        # Verify the data was saved and its type is INTEGER in the database
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_trades, typeof(total_trades) FROM strategies WHERE symbol = 'RELIANCE'")
            row = cursor.fetchone()
            assert row is not None
            total_trades, type_of_trades = row
            assert total_trades == 25
            assert type_of_trades == 'integer'


class TestGetOpenPositions:
    """Tests for fetching open positions."""

    def test_get_open_positions_success(self, temp_db_path: Path):
        """Test successfully fetching open positions."""
        create_database(temp_db_path)
        signals = [
            {'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': json.dumps(['rule1'])},
            {'ticker': 'INFY', 'date': '2025-01-02', 'entry_price': 1500.0, 'rule_stack_used': json.dumps(['rule2'])}
        ]
        add_new_positions_from_signals(temp_db_path, signals)

        # Manually close one position to test filtering
        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.execute("UPDATE positions SET status = 'CLOSED' WHERE symbol = 'INFY'")
            conn.commit()

        open_positions = get_open_positions(temp_db_path)
        assert len(open_positions) == 1
        assert open_positions[0]['symbol'] == 'RELIANCE'
        assert open_positions[0]['entry_price'] == 100.0
        assert json.loads(open_positions[0]['rule_stack_used']) == ['rule1']

    def test_get_open_positions_empty(self, temp_db_path: Path):
        """Test fetching when no open positions exist."""
        create_database(temp_db_path)
        open_positions = get_open_positions(temp_db_path)
        assert len(open_positions) == 0

    def test_get_open_positions_db_error(self, temp_db_path: Path):
        """Test DB error handling when fetching open positions."""
        # temp_db_path exists but sqlite3.connect will be patched
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Fetch failed")):
            open_positions = get_open_positions(temp_db_path)
        assert open_positions == []


class TestClosePositionsBatch:
    """Tests for closing positions in batch."""

    def test_close_positions_batch_success(self, temp_db_path: Path):
        """Test successfully closing positions."""
        create_database(temp_db_path)
        signals = [
            {'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': '["ruleA"]'},
            {'ticker': 'INFY', 'date': '2025-01-02', 'entry_price': 1500.0, 'rule_stack_used': '["ruleB"]'}
        ]
        add_new_positions_from_signals(temp_db_path, signals)

        open_pos = get_open_positions(temp_db_path)
        assert len(open_pos) == 2

        positions_to_close = [
            {'id': open_pos[0]['id'], 'exit_date': '2025-01-10', 'exit_price': 110.0, 'final_return_pct': 10.0, 'exit_reason': 'TP'},
            {'id': open_pos[1]['id'], 'exit_date': '2025-01-11', 'exit_price': 1400.0, 'final_return_pct': -6.67, 'exit_reason': 'SL'}
        ]
        close_positions_batch(temp_db_path, positions_to_close)

        remaining_open_pos = get_open_positions(temp_db_path)
        assert len(remaining_open_pos) == 0

        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.row_factory = sqlite3.Row
            closed = conn.execute("SELECT * FROM positions WHERE status = 'CLOSED' ORDER BY symbol").fetchall()
            assert len(closed) == 2
            assert closed[0]['symbol'] == 'INFY'
            assert closed[0]['exit_price'] == 1400.0
            assert closed[1]['symbol'] == 'RELIANCE'
            assert closed[1]['exit_price'] == 110.0

    def test_close_positions_batch_empty_list(self, temp_db_path: Path):
        """Test closing positions with an empty list."""
        create_database(temp_db_path)
        # Add some open positions first
        signals = [{'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': '[]'}]
        add_new_positions_from_signals(temp_db_path, signals)

        close_positions_batch(temp_db_path, []) # Call with empty list

        open_pos = get_open_positions(temp_db_path)
        assert len(open_pos) == 1 # Position should remain open

    def test_close_positions_batch_db_error(self, temp_db_path: Path):
        """Test DB error handling when closing positions."""
        create_database(temp_db_path)
        signals = [{'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': '[]'}]
        add_new_positions_from_signals(temp_db_path, signals)
        open_pos = get_open_positions(temp_db_path)

        positions_to_close = [{'id': open_pos[0]['id'], 'exit_date': '2025-01-10', 'exit_price': 110.0}]

        with patch('sqlite3.connect') as mock_connect:
            mock_conn_instance = mock_connect.return_value
            mock_cursor_instance = mock_conn_instance.cursor.return_value

            # Setup side effects for execute on the mock cursor
            # 1. BEGIN TRANSACTION
            # 2. UPDATE positions (this one fails)
            # 3. ROLLBACK
            mock_cursor_instance.execute.side_effect = [
                None,  # For BEGIN TRANSACTION
                sqlite3.Error("Update failed"), # For UPDATE
                None   # For ROLLBACK
            ]
            close_positions_batch(temp_db_path, positions_to_close)

        # Verify position is still open (rollback occurred)
        final_open_pos = get_open_positions(temp_db_path)
        assert len(final_open_pos) == 1
        assert final_open_pos[0]['id'] == open_pos[0]['id']


class TestAddPositions:
    """Tests for adding new positions."""

    def test_add_new_position_skips_existing_open(self, temp_db_path: Path):
        """Test that adding a new position is skipped if one is already open for the symbol."""
        create_database(temp_db_path)
        
        # Add an initial open position for RELIANCE
        initial_signal = [{'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': '[]'}]
        add_new_positions_from_signals(temp_db_path, initial_signal)
        
        # Try to add another position for RELIANCE
        new_signal = [{'ticker': 'RELIANCE', 'date': '2025-01-02', 'entry_price': 105.0, 'rule_stack_used': '[]'}]
        add_new_positions_from_signals(temp_db_path, new_signal)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM positions WHERE symbol = 'RELIANCE'")
            count = cursor.fetchone()[0]
            assert count == 1 # Should still be 1, not 2

    def test_add_new_positions_empty_list(self, temp_db_path: Path):
        """Test adding new positions with an empty signal list."""
        create_database(temp_db_path)
        add_new_positions_from_signals(temp_db_path, [])
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM positions")
            assert cursor.fetchone()[0] == 0

    def test_add_new_positions_db_error(self, temp_db_path: Path):
        """Test DB error handling when adding new positions."""
        create_database(temp_db_path)
        signals = [{'ticker': 'RELIANCE', 'date': '2025-01-01', 'entry_price': 100.0, 'rule_stack_used': '[]'}]

        with patch('sqlite3.connect') as mock_connect:
            mock_conn_instance = mock_connect.return_value
            mock_cursor_instance = mock_conn_instance.cursor.return_value

            # Setup side effects for execute on the mock cursor
            # 1. BEGIN TRANSACTION (called by the context manager implicitly sometimes, or explicitly)
            # 2. SELECT symbol FROM positions WHERE status = 'OPEN'
            # 3. INSERT INTO positions (this one fails)
            # 4. ROLLBACK
            execute_effects = [
                None,  # For BEGIN TRANSACTION (if explicit, or first call in with block)
                mock_cursor_instance,  # For SELECT open symbols (to allow .fetchall())
                sqlite3.Error("Insert failed"), # For INSERT
                None   # For ROLLBACK
            ]
             # If the "BEGIN TRANSACTION" is implicit due to "with sqlite3.connect(...)"
             # then the first execute call we care about is the SELECT.
             # The code uses "with sqlite3.connect(...) as conn: cursor = conn.cursor(); cursor.execute("BEGIN TRANSACTION")"
             # So, the explicit "BEGIN TRANSACTION" is the first.

            mock_cursor_instance.execute.side_effect = execute_effects
            mock_cursor_instance.fetchall.return_value = [] # For the SELECT open symbols query

            add_new_positions_from_signals(temp_db_path, signals)

        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM positions")
            assert cursor.fetchone()[0] == 0 # No data should be inserted
    
    def test_save_strategies_multiple_batches(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]) -> None:
        """Test saving multiple batches to same database."""
        create_database(temp_db_path)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            # Save first batch
            result1 = save_strategies_batch(conn, sample_strategies, "2025-06-24T10:00:00")
            assert result1 is True
            
            # Save second batch with different timestamp
            result2 = save_strategies_batch(conn, sample_strategies, "2025-06-24T11:00:00")
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
        # temp_db_path fixture ensures it's clean
        
        # Create database
        create_database(temp_db_path)
        
        # Save strategies
        with sqlite3.connect(str(temp_db_path)) as conn:
            result = save_strategies_batch(conn, sample_strategies, "2025-06-24T10:00:00")
        
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
            assert json.loads(rows[0][1]) == [{'name': 'rsi_oversold_30', 'type': 'rsi_oversold', 'params': {'period': 14, 'oversold_threshold': 30.0}}]
            assert rows[0][2] == 0.68
            assert rows[0][3] == 58.0
            assert rows[0][4] == 0.9
            assert rows[0][5] == 42
            assert rows[0][6] == 1.8
            assert rows[0][7] == "2025-06-24T10:00:00"
            
            # Verify second strategy (RELIANCE)
            assert rows[1][0] == "RELIANCE"
            assert json.loads(rows[1][1]) == [{'name': 'sma_10_20_crossover', 'type': 'sma_crossover', 'params': {'fast_period': 10, 'slow_period': 20}}]
            assert rows[1][2] == 0.75

class TestMigrationV2:
    """Tests for strategies table v2 migration functionality."""
    
    def test_migrate_strategies_table_v2_fresh_database(self, temp_db_path: Path) -> None:
        """Test migration on a fresh database with new schema."""
        # Create a fresh database with the new schema - migration should be called automatically
        persistence.create_database(temp_db_path)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            # Verify all columns exist after automatic migration
            cursor = conn.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            assert 'config_snapshot' in columns
            assert 'config_hash' in columns
            
            # Check version
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            assert version >= 2

    def test_migrate_strategies_table_v2_with_existing_data(self, temp_db_path: Path) -> None:
        """Test migration preserves existing data and adds new columns."""
        # Create old schema manually
        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    run_timestamp TEXT NOT NULL,
                    rule_stack TEXT NOT NULL,
                    edge_score REAL NOT NULL,
                    win_pct REAL NOT NULL,
                    sharpe REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    avg_return REAL NOT NULL
                )
            """)
            
            # Insert test data
            test_data = [
                ("RELIANCE", "2025-07-13T10:00:00", '[{"name": "test_rule"}]', 0.75, 0.65, 1.2, 15, 0.08),
                ("INFY", "2025-07-13T10:00:00", '[{"name": "another_rule"}]', 0.68, 0.60, 1.1, 12, 0.06)
            ]
            
            for data in test_data:
                conn.execute("""
                    INSERT INTO strategies (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            conn.commit()
        
        # Run migration
        persistence.migrate_strategies_table_v2(temp_db_path)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            # Verify new columns exist
            cursor = conn.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            assert 'config_snapshot' in columns
            assert 'config_hash' in columns
            
            # Verify data preserved
            cursor = conn.execute("SELECT COUNT(*) FROM strategies")
            count = cursor.fetchone()[0]
            assert count == 2
            
            # Verify legacy data marked properly
            cursor = conn.execute("SELECT config_hash, config_snapshot FROM strategies")
            rows = cursor.fetchall()
            for config_hash, config_snapshot in rows:
                assert config_hash == 'legacy'
                assert json.loads(config_snapshot) == {"legacy": True}

    def test_migrate_strategies_table_v2_idempotent(self, temp_db_path: Path) -> None:
        """Test that migration can be run multiple times safely."""
        persistence.create_database(temp_db_path)
        
        # Run migration again - should be safe
        persistence.migrate_strategies_table_v2(temp_db_path)
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            # Should only have one instance of each column
            assert columns.count('config_snapshot') == 1
            assert columns.count('config_hash') == 1

    def test_config_functions(self, temp_db_path: Path) -> None:
        """Test config generation and snapshot functions."""
        from kiss_signal.config import Config, EdgeScoreWeights
        
        # Create a temporary universe file for testing
        universe_file = temp_db_path.parent / "test_universe.csv"
        universe_file.write_text("symbol\nRELIANCE\nINFY\n")
        
        # Create mock config objects using proper RulesConfig structure
        from kiss_signal.config import RulesConfig, RuleDef
        rules_config = RulesConfig(
            baseline=RuleDef(
                type="sma_crossover", 
                name="sma_10_20_crossover", 
                params={"fast": 10, "slow": 20}
            ),
            layers=[
                RuleDef(
                    type="rsi_oversold", 
                    name="rsi_oversold_30", 
                    params={"period": 14, "threshold": 30}
                )
            ]
        )
        
        app_config = Config(
            database_path=str(temp_db_path),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports",
            edge_score_threshold=0.5
        )
        
        # Test generate_config_hash (expects dict format)
        rules_dict = rules_config.model_dump()
        hash1 = persistence.generate_config_hash(rules_dict, app_config)
        hash2 = persistence.generate_config_hash(rules_dict, app_config)
        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 8  # 8-character prefix
        
        # Test create_config_snapshot (expects dict format)
        snapshot = persistence.create_config_snapshot(rules_dict, app_config, "2025-07-13")
        assert 'rules_hash' in snapshot
        assert 'universe_path' in snapshot
        assert 'freeze_date' in snapshot
        assert snapshot['freeze_date'] == "2025-07-13"
        assert len(json.dumps(snapshot)) < 1024  # < 1KB
        
        # Test get_active_strategy_combinations (expects RulesConfig object)
        from kiss_signal.config import get_active_strategy_combinations
        combinations = get_active_strategy_combinations(rules_config)
        assert len(combinations) >= 2  # At least the buy rules
        for combo in combinations:
            parsed = json.loads(combo)
            assert isinstance(parsed, list)

class TestClearAndRecalculateStrategies:
    """Test the clear_and_recalculate_strategies function comprehensively."""

    def test_clear_and_recalculate_basic_functionality(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]):
        """Test basic clear and recalculate functionality."""
        # Set up test data
        create_database(temp_db_path)
        
        # Create mock universe file
        universe_file = temp_db_path.parent / "test_universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        from kiss_signal.config import Config, EdgeScoreWeights, RulesConfig, RuleDef
        from kiss_signal import persistence
        from unittest.mock import patch, MagicMock
        
        # Create mock configs
        rules_config = RulesConfig(
            baseline=RuleDef(type="sma_crossover", name="sma_10_20", params={"fast": 10, "slow": 20}),
            layers=[]
        )
        
        app_config = Config(
            database_path=str(temp_db_path),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        # Mock the heavy dependencies
        with patch('kiss_signal.data') as mock_data, \
             patch('kiss_signal.backtester') as mock_backtester, \
             patch('rich.console.Console') as mock_console, \
             patch('builtins.input', return_value='y'):
            
            mock_data.load_universe.return_value = ["RELIANCE", "INFY"]
            mock_data.get_price_data.return_value = None  # Simulate no data
            
            mock_bt = MagicMock()
            mock_bt.find_optimal_strategies.return_value = []
            mock_backtester.Backtester.return_value = mock_bt
            
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            # Test with preserve_all=True
            result = persistence.clear_and_recalculate_strategies(
                temp_db_path, app_config, rules_config, 
                force=True, preserve_all=True
            )
            
            assert isinstance(result, list)
            mock_console_instance.print.assert_called()

    def test_clear_and_recalculate_with_existing_data(self, temp_db_path: Path, sample_strategies: List[Dict[str, Any]]):
        """Test clear and recalculate with existing database data."""
        create_database(temp_db_path)
        
        # Add some existing strategies
        with sqlite3.connect(str(temp_db_path)) as conn:
            save_strategies_batch(conn, sample_strategies, "2025-01-01T12:00:00", {}, "testhash")
        
        universe_file = temp_db_path.parent / "test_universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        from kiss_signal.config import Config, EdgeScoreWeights, RulesConfig, RuleDef
        from kiss_signal import persistence
        from unittest.mock import patch, MagicMock
        
        rules_config = RulesConfig(
            baseline=RuleDef(type="sma_crossover", name="sma_10_20", params={"fast": 10, "slow": 20}),
            layers=[]
        )
        
        app_config = Config(
            database_path=str(temp_db_path),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        with patch('kiss_signal.data') as mock_data, \
             patch('kiss_signal.backtester') as mock_backtester, \
             patch('rich.console.Console') as mock_console:
            
            mock_data.load_universe.return_value = ["RELIANCE"]
            mock_data.get_price_data.return_value = None
            
            mock_bt = MagicMock()
            mock_bt.find_optimal_strategies.return_value = []
            mock_backtester.Backtester.return_value = mock_bt
            
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            result = persistence.clear_and_recalculate_strategies(
                temp_db_path, app_config, rules_config, force=True
            )
            
            assert isinstance(result, list)

    def test_clear_and_recalculate_with_successful_backtesting(self, temp_db_path: Path):
        """Test clear and recalculate with successful backtesting results."""
        create_database(temp_db_path)
        
        universe_file = temp_db_path.parent / "test_universe.csv"
        universe_file.write_text("RELIANCE\n")
        
        from kiss_signal.config import Config, EdgeScoreWeights, RulesConfig, RuleDef
        from kiss_signal import persistence
        from unittest.mock import patch, MagicMock
        import pandas as pd
        
        rules_config = RulesConfig(
            baseline=RuleDef(type="sma_crossover", name="sma_10_20", params={"fast": 10, "slow": 20}),
            layers=[]
        )
        
        app_config = Config(
            database_path=str(temp_db_path),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        # Mock successful price data
        mock_price_data = pd.DataFrame({
            'Close': [100.0] * 200,
            'High': [105.0] * 200,
            'Low': [95.0] * 200,
            'Volume': [1000] * 200
        }, index=pd.date_range('2023-01-01', periods=200))
        
        with patch('kiss_signal.data') as mock_data, \
             patch('kiss_signal.backtester') as mock_backtester, \
             patch('rich.console.Console') as mock_console:
            
            mock_data.load_universe.return_value = ["RELIANCE"]
            mock_data.get_price_data.return_value = mock_price_data
            
            # Mock successful strategy results
            mock_strategy = {
                "rule_stack": [{"type": "sma_crossover", "name": "test", "params": {}}],
                "edge_score": 0.75,
                "win_pct": 65.0,
                "sharpe": 1.2,
                "total_trades": 50,
                "avg_return": 2.5
            }
            
            mock_bt = MagicMock()
            mock_bt.find_optimal_strategies.return_value = [mock_strategy]
            mock_backtester.Backtester.return_value = mock_bt
            
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            result = persistence.clear_and_recalculate_strategies(
                temp_db_path, app_config, rules_config, force=True
            )
            
            assert len(result) == 1
            assert result[0]["symbol"] == "RELIANCE"
            assert result[0]["edge_score"] == 0.75

    def test_clear_and_recalculate_error_handling(self, temp_db_path: Path):
        """Test error handling in clear_and_recalculate_strategies."""
        create_database(temp_db_path)
        
        universe_file = temp_db_path.parent / "test_universe.csv"
        universe_file.write_text("RELIANCE\n")
        
        from kiss_signal.config import Config, EdgeScoreWeights, RulesConfig, RuleDef
        from kiss_signal import persistence
        from unittest.mock import patch, MagicMock
        
        rules_config = RulesConfig(
            baseline=RuleDef(type="sma_crossover", name="sma_10_20", params={"fast": 10, "slow": 20}),
            layers=[]
        )
        
        app_config = Config(
            database_path=str(temp_db_path),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        with patch('kiss_signal.data') as mock_data, \
             patch('kiss_signal.backtester') as mock_backtester, \
             patch('rich.console.Console') as mock_console:
            
            mock_data.load_universe.return_value = ["RELIANCE"]
            mock_data.get_price_data.side_effect = Exception("Data fetch error")
            
            mock_bt = MagicMock()
            mock_backtester.Backtester.return_value = mock_bt
            
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            # Should handle exceptions gracefully and continue
            result = persistence.clear_and_recalculate_strategies(
                temp_db_path, app_config, rules_config, force=True
            )
            
            assert isinstance(result, list)


class TestGetConnectionEdgeCases:
    """Test get_connection function edge cases and migration scenarios."""

    def test_get_connection_with_migration_needed(self, temp_db_path: Path):
        """Test get_connection when migration is needed."""
        # Create old database schema manually (without new columns)
        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    run_timestamp TEXT NOT NULL,
                    rule_stack TEXT NOT NULL,
                    edge_score REAL NOT NULL,
                    win_pct REAL NOT NULL,
                    sharpe REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    avg_return REAL NOT NULL
                );
            """)
            conn.commit()
        
        from kiss_signal import persistence
        
        # This should trigger migration
        conn = persistence.get_connection(temp_db_path)
        
        # Check that new columns exist after migration
        cursor = conn.execute("PRAGMA table_info(strategies)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'config_snapshot' in columns
        assert 'config_hash' in columns
        conn.close()

    def test_get_connection_database_error(self, temp_db_path: Path):
        """Test get_connection when database connection fails."""
        from kiss_signal import persistence
        from unittest.mock import patch
        
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(sqlite3.Error):
                persistence.get_connection(temp_db_path)

    def test_get_connection_already_migrated(self, temp_db_path: Path):
        """Test get_connection with already migrated database."""
        create_database(temp_db_path)  # Creates v2 schema
        
        from kiss_signal import persistence
        
        # Should not trigger migration
        conn = persistence.get_connection(temp_db_path)
        
        # Verify connection works and WAL mode is enabled
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == 'wal'
        conn.close()


class TestCreateDatabaseEdgeCases:
    """Test create_database function edge cases."""

    def test_create_database_parent_directory_creation(self, tmp_path: Path):
        """Test create_database creates parent directories."""
        db_path = tmp_path / "subdir" / "another_subdir" / "test.db"
        
        create_database(db_path)
        
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_create_database_oserror(self, tmp_path: Path):
        """Test create_database handles OS errors."""
        from unittest.mock import patch
        
        db_path = tmp_path / "test.db"
        
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                create_database(db_path)


class TestConfigHashAndSnapshot:
    """Test config hash and snapshot functions."""

    def test_generate_config_hash_deterministic(self, tmp_path: Path):
        """Test that config hash generation is deterministic."""
        from kiss_signal.config import Config, EdgeScoreWeights
        from kiss_signal import persistence
        
        # Create a temporary universe file
        universe_file = tmp_path / "universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        rules_config = {"baseline": {"type": "sma_crossover"}, "layers": []}
        
        app_config = Config(
            database_path=str(tmp_path / "test.db"),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        hash1 = persistence.generate_config_hash(rules_config, app_config)
        hash2 = persistence.generate_config_hash(rules_config, app_config)
        
        assert hash1 == hash2
        assert len(hash1) == 8
        assert isinstance(hash1, str)

    def test_generate_config_hash_different_configs(self, tmp_path: Path):
        """Test that different configs produce different hashes."""
        from kiss_signal.config import Config, EdgeScoreWeights
        from kiss_signal import persistence
        
        # Create a temporary universe file
        universe_file = tmp_path / "universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        rules_config1 = {"baseline": {"type": "sma_crossover"}, "layers": []}
        rules_config2 = {"baseline": {"type": "rsi_oversold"}, "layers": []}
        
        app_config = Config(
            database_path=str(tmp_path / "test.db"),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        hash1 = persistence.generate_config_hash(rules_config1, app_config)
        hash2 = persistence.generate_config_hash(rules_config2, app_config)
        
        assert hash1 != hash2

    def test_create_config_snapshot_with_freeze_date(self, tmp_path: Path):
        """Test config snapshot creation with freeze date."""
        from kiss_signal.config import Config, EdgeScoreWeights
        from kiss_signal import persistence
        
        # Create a temporary universe file
        universe_file = tmp_path / "universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        rules_config = {"baseline": {"type": "sma_crossover"}, "layers": []}
        
        app_config = Config(
            database_path=str(tmp_path / "test.db"),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        snapshot = persistence.create_config_snapshot(rules_config, app_config, "2025-07-15")
        
        assert snapshot['freeze_date'] == "2025-07-15"
        assert 'rules_hash' in snapshot
        assert 'universe_path' in snapshot
        assert 'hold_period' in snapshot
        assert 'timestamp' in snapshot
        assert len(snapshot['rules_hash']) == 16

    def test_create_config_snapshot_without_freeze_date(self, tmp_path: Path):
        """Test config snapshot creation without freeze date."""
        from kiss_signal.config import Config, EdgeScoreWeights
        from kiss_signal import persistence
        
        # Create a temporary universe file
        universe_file = tmp_path / "universe.csv"
        universe_file.write_text("RELIANCE\nINFY\n")
        
        rules_config = {"baseline": {"type": "sma_crossover"}, "layers": []}
        
        app_config = Config(
            database_path=str(tmp_path / "test.db"),
            universe_path=str(universe_file),
            cache_dir="cache",
            cache_refresh_days=7,
            historical_data_years=3,
            hold_period=20,
            min_trades_threshold=10,
            edge_score_threshold=0.5,
            edge_score_weights=EdgeScoreWeights(win_pct=0.6, sharpe=0.4),
            reports_output_dir="reports"
        )
        
        snapshot = persistence.create_config_snapshot(rules_config, app_config)
        
        assert snapshot['freeze_date'] is None
        assert 'timestamp' in snapshot


class TestSaveStrategiesBatchEdgeCases:
    """Test additional edge cases for save_strategies_batch."""

    def test_save_strategies_batch_with_pydantic_models(self, temp_db_path: Path):
        """Test save_strategies_batch with Pydantic model rule stacks."""
        create_database(temp_db_path)
        
        from kiss_signal.config import RuleDef
        
        # Create strategy with Pydantic models
        rule_def = RuleDef(type="sma_crossover", name="test", params={"fast": 10, "slow": 20})
        strategy = {
            "symbol": "TEST",
            "rule_stack": [rule_def],  # Pydantic model
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            "total_trades": 50,
            "avg_return": 2.5
        }
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            success = save_strategies_batch(conn, [strategy], "2025-01-01T12:00:00")
            assert success

    def test_save_strategies_batch_assertion_errors(self, temp_db_path: Path):
        """Test save_strategies_batch assertion errors."""
        create_database(temp_db_path)
        
        # Test with missing total_trades key
        strategy_missing_key = {
            "symbol": "TEST",
            "rule_stack": [],
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            # Missing total_trades
            "avg_return": 2.5
        }
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            success = save_strategies_batch(conn, [strategy_missing_key], "2025-01-01T12:00:00")
            assert not success

        # Test with None total_trades
        strategy_none_trades = {
            "symbol": "TEST",
            "rule_stack": [],
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            "total_trades": None,
            "avg_return": 2.5
        }
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            success = save_strategies_batch(conn, [strategy_none_trades], "2025-01-01T12:00:00")
            assert not success

        # Test with negative total_trades
        strategy_negative_trades = {
            "symbol": "TEST",
            "rule_stack": [],
            "edge_score": 0.75,
            "win_pct": 65.0,
            "sharpe": 1.2,
            "total_trades": -5,
            "avg_return": 2.5
        }
        
        with sqlite3.connect(str(temp_db_path)) as conn:
            success = save_strategies_batch(conn, [strategy_negative_trades], "2025-01-01T12:00:00")
            assert not success


class TestAddNewPositionsFromSignalsEdgeCases:
    """Test additional edge cases for add_new_positions_from_signals."""

    def test_add_positions_with_rule_stack_json(self, temp_db_path: Path):
        """Test adding positions with pre-formatted rule_stack_used JSON."""
        create_database(temp_db_path)
        
        signals = [
            {
                'ticker': 'RELIANCE',
                'date': '2025-01-15',
                'entry_price': 2500.0,
                'rule_stack_used': '["sma_crossover", "rsi_oversold"]'  # Pre-formatted JSON
            }
        ]
        
        add_new_positions_from_signals(temp_db_path, signals)
        
        positions = get_open_positions(temp_db_path)
        assert len(positions) == 1
        assert positions[0]['symbol'] == 'RELIANCE'
        assert positions[0]['rule_stack_used'] == '["sma_crossover", "rsi_oversold"]'

    def test_add_positions_fallback_rule_stack(self, temp_db_path: Path):
        """Test adding positions with fallback rule_stack handling."""
        create_database(temp_db_path)
        
        signals = [
            {
                'ticker': 'INFY',
                'date': '2025-01-15',
                'entry_price': 1800.0,
                'rule_stack': 'single_rule'  # Fallback to rule_stack
            }
        ]
        
        add_new_positions_from_signals(temp_db_path, signals)
        
        positions = get_open_positions(temp_db_path)
        assert len(positions) == 1
        assert positions[0]['symbol'] == 'INFY'


class TestMigrateStrategiesTableV2EdgeCases:
    """Test migration function edge cases."""

    def test_migrate_v2_with_data_and_pragma_check(self, temp_db_path: Path):
        """Test migration with existing data and version checking."""
        # Create old schema with some data
        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    rule_stack TEXT NOT NULL,
                    edge_score REAL NOT NULL,
                    win_pct REAL NOT NULL,
                    sharpe REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    avg_return REAL NOT NULL,
                    run_timestamp TEXT NOT NULL
                );
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO strategies 
                (symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, run_timestamp)
                VALUES ('TEST', '[]', 0.5, 50.0, 1.0, 10, 1.5, '2025-01-01T12:00:00')
            """)
            
            # Set version to 1
            conn.execute("PRAGMA user_version = 1;")
            conn.commit()
        
        from kiss_signal import persistence
        
        # Run migration
        persistence.migrate_strategies_table_v2(temp_db_path)
        
        # Verify migration succeeded
        with sqlite3.connect(str(temp_db_path)) as conn:
            # Check version updated
            version = conn.execute("PRAGMA user_version;").fetchone()[0]
            assert version == 2
            
            # Check data preserved
            rows = conn.execute("SELECT symbol, config_snapshot, config_hash FROM strategies").fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 'TEST'
            assert rows[0][1] == '{"legacy": true}'  # Legacy placeholder
            assert rows[0][2] == 'legacy'

    def test_migrate_v2_error_handling(self, temp_db_path: Path):
        """Test migration error handling."""
        from kiss_signal import persistence
        from unittest.mock import patch
        
        # Create a corrupted database scenario
        with sqlite3.connect(str(temp_db_path)) as conn:
            conn.execute("CREATE TABLE strategies (id INTEGER);")  # Minimal table
            conn.execute("PRAGMA user_version = 1;")
            conn.commit()
        
        # Mock an error during migration
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            # Mock fetchone to return a proper version number
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = 1  # Version 1
            mock_conn.execute.return_value.fetchone.return_value = mock_result
            mock_conn.execute.side_effect = [
                mock_conn.execute.return_value,  # First call (version check) succeeds
                sqlite3.Error("Migration failed")  # Second call fails
            ]
            mock_connect.return_value.__enter__.return_value = mock_conn
            
            with pytest.raises(sqlite3.Error):
                persistence.migrate_strategies_table_v2(temp_db_path)


class TestAdditionalPersistenceFunctions:
    """Test remaining persistence functions for full coverage."""

    def test_close_positions_transaction_rollback(self, temp_db_path: Path):
        """Test close_positions_batch transaction rollback on error."""
        create_database(temp_db_path)
        
        # Add an open position first
        signals = [{'ticker': 'TEST', 'date': '2025-01-15', 'entry_price': 100.0, 'rule_stack_used': '[]'}]
        add_new_positions_from_signals(temp_db_path, signals)
        
        positions = get_open_positions(temp_db_path)
        assert len(positions) == 1
        
        # Try to close with invalid data that will cause an error
        invalid_position = {
            'id': positions[0]['id'],
            'exit_date': '2025-01-20',
            'exit_price': 'invalid_price',  # This should cause an error
            'final_return_pct': 10.0,
            'final_nifty_return_pct': 5.0,
            'days_held': 5,
            'exit_reason': 'test'
        }
        
        from unittest.mock import patch
        
        # Mock sqlite3 to raise an error during UPDATE
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = [
                None,  # BEGIN TRANSACTION
                sqlite3.Error("Update failed"),  # UPDATE statement
                None   # ROLLBACK
            ]
            mock_connect.return_value.__enter__.return_value = mock_conn
            
            # This should handle the error gracefully
            close_positions_batch(temp_db_path, [invalid_position])
            
            # Verify rollback was called
            mock_cursor.execute.assert_any_call("ROLLBACK")

    def test_add_positions_transaction_rollback(self, temp_db_path: Path):
        """Test add_new_positions_from_signals transaction rollback on error."""
        create_database(temp_db_path)
        
        signals = [{'ticker': 'TEST', 'date': '2025-01-15', 'entry_price': 100.0}]
        
        from unittest.mock import patch
        
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = [
                None,  # BEGIN TRANSACTION  
                MagicMock(),  # SELECT for open_symbols
                sqlite3.Error("Insert failed"),  # INSERT statement
                None   # ROLLBACK
            ]
            mock_cursor.fetchall.return_value = []  # No existing open positions
            mock_connect.return_value.__enter__.return_value = mock_conn
            
            # This should handle the error gracefully
            add_new_positions_from_signals(temp_db_path, signals)
            
            # Verify rollback was called
            mock_cursor.execute.assert_any_call("ROLLBACK")
