# src/kiss_signal/persistence.py
"""SQLite persistence layer for storing backtesting results and trading signals."""

from pathlib import Path
from typing import List, Dict, Any
import sqlite3
import json
import logging

__all__ = ["create_database", "save_strategies_batch"]

logger = logging.getLogger(__name__)

# Database schema constants
CREATE_STRATEGIES_TABLE = """
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    rule_stack TEXT NOT NULL,
    edge_score REAL NOT NULL,
    win_pct REAL NOT NULL,
    sharpe REAL NOT NULL,
    total_trades INTEGER NOT NULL,
    avg_return REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_STRATEGIES = """
CREATE INDEX IF NOT EXISTS idx_strategies_symbol_timestamp 
ON strategies(symbol, run_timestamp);
"""

def create_database(db_path: Path) -> None:
    """Create SQLite database with the strategies schema and enables WAL mode.
    
    Args:
        db_path: Path to the SQLite database file
        
    Raises:
        sqlite3.Error: If database creation or schema setup fails
        OSError: If directory creation or file permissions fail
    """
    logger.info(f"Creating database at {db_path}")
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            # Enable WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            logger.debug("Enabled WAL mode for concurrent access")
            
            # Create strategies table
            conn.execute(CREATE_STRATEGIES_TABLE)
            logger.debug("Created strategies table")
            
            # Create index for performance
            conn.execute(CREATE_INDEX_STRATEGIES)
            logger.debug("Created index on strategies table")
            
            conn.commit()
            logger.info(f"Successfully created database at {db_path}")
            
    except sqlite3.Error as e:
        logger.error(f"Failed to create database at {db_path}: {e}")
        raise
    except OSError as e:
        logger.error(f"Failed to create directory or access file {db_path}: {e}")
        raise

def save_strategies_batch(db_path: Path, strategies: List[Dict[str, Any]], run_timestamp: str) -> bool:
    """Save a batch of strategy results in a single transaction.
    
    Args:
        db_path: Path to the SQLite database file
        strategies: List of strategy dictionaries from backtester
        run_timestamp: ISO 8601 timestamp string for this run
        
    Returns:
        True if successful, False if failed
        
    Note:
        Uses atomic transaction - all strategies saved or none.
        rule_stack list is serialized to JSON string for storage.
    """
    if not strategies:
        logger.info("No strategies to save - skipping batch save")
        return True
    
    logger.info(f"Saving {len(strategies)} strategies to {db_path}")
    
    insert_sql = """
    INSERT INTO strategies (
        run_timestamp, symbol, rule_stack, edge_score, 
        win_pct, sharpe, total_trades, avg_return
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        logger.debug("Started transaction for batch save")
        
        for strategy in strategies:
            # Serialize rule_stack list to JSON string
            rule_stack_json = json.dumps(strategy["rule_stack"])
            
            cursor.execute(insert_sql, (
                run_timestamp,
                strategy["symbol"],
                rule_stack_json,
                strategy["edge_score"],
                strategy["win_pct"],
                strategy["sharpe"],
                strategy["total_trades"],
                strategy["avg_return"]
            ))
        
        # Commit transaction
        cursor.execute("COMMIT")
        logger.info(f"Successfully saved {len(strategies)} strategies")
        return True
        
    except sqlite3.Error as e:
        if conn:
            try:
                conn.rollback()
                logger.debug("Rolled back transaction due to error")
            except sqlite3.Error:
                pass  # Rollback can fail if connection is broken
        logger.error(f"Batch save failed: {e}")
        return False
    except (KeyError, TypeError, json.JSONEncodeError) as e:
        if conn:
            try:
                conn.rollback()
                logger.debug("Rolled back transaction due to data error")
            except sqlite3.Error:
                pass
        logger.error(f"Invalid strategy data: {e}")
        return False
    finally:
        if conn:
            conn.close()
