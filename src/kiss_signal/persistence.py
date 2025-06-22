# src/kiss_signal/persistence.py
"""SQLite persistence layer for storing backtesting results and trading signals."""

from pathlib import Path
from typing import List, Dict, Any
import sqlite3
import json
import logging

__all__ = [
    "create_database",
    "save_strategies_batch",
    "add_new_positions_from_signals",
    "get_open_positions",
    "close_positions_batch",
]

logger = logging.getLogger(__name__)

# Database schema constants
CREATE_STRATEGIES_TABLE = """
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, rule_stack, run_timestamp)
);
"""

CREATE_POSITIONS_TABLE = """
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
    final_nifty_return_pct REAL,
    days_held INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_STRATEGIES = """
CREATE INDEX IF NOT EXISTS idx_strategies_symbol_timestamp 
ON strategies(symbol, run_timestamp);
"""

CREATE_INDEX_POSITIONS = """
CREATE INDEX IF NOT EXISTS idx_positions_status_symbol ON positions(status, symbol);
"""

def create_database(db_path: Path) -> None:
    """Create SQLite database with the strategies schema and enables WAL mode.
    
    Args:
        db_path: Path to the SQLite database file
        
    Raises:
        sqlite3.Error: If database creation or schema setup fails
    """
    logger.info(f"Creating database at {db_path}")
    try:
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(db_path)) as conn:
            # Enable WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            logger.debug("Enabled WAL mode for concurrent access")
            
            # Create strategies table
            conn.execute(CREATE_STRATEGIES_TABLE)
            logger.debug("Created strategies table")
            
            # Create positions table
            conn.execute(CREATE_POSITIONS_TABLE)
            logger.debug("Created positions table")
            
            # Create index for strategies table
            conn.execute(CREATE_INDEX_STRATEGIES)
            logger.debug("Created index on strategies table")
            
            # Create index for positions table
            conn.execute(CREATE_INDEX_POSITIONS)
            logger.debug("Created index on positions table")
            
            conn.commit()
            logger.info(f"Successfully created database at {db_path}")
            
    except (sqlite3.Error, OSError) as e:
        logger.error(f"Failed to create database at {db_path}: {e}")
        raise

# impure
def add_new_positions_from_signals(db_path: Path, signals: List[Dict[str, Any]]) -> None:
    """Adds new buy signals to the positions table with status 'OPEN'."""
    if not signals:
        return

    insert_sql = """
    INSERT INTO positions (symbol, entry_date, entry_price, status, rule_stack_used)
    VALUES (?, ?, ?, 'OPEN', ?);
    """
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        try:
            open_symbols = {
                row[0] for row in cursor.execute("SELECT symbol FROM positions WHERE status = 'OPEN'").fetchall()
            }
            
            for signal in signals:
                symbol = signal['ticker']
                if symbol in open_symbols:
                    logger.info(f"Skipping new position for {symbol} as one is already open.")
                    continue
                
                rule_stack_json = signal.get('rule_stack_used', json.dumps([signal.get('rule_stack', 'unknown')]))

                cursor.execute(insert_sql, (
                    symbol,
                    signal['date'],
                    signal['entry_price'],
                    rule_stack_json
                ))
                logger.info(f"Added new OPEN position for {symbol} at {signal['entry_price']}.")
            
            cursor.execute("COMMIT")
        except sqlite3.Error as e:
            logger.error(f"Failed to add new positions: {e}")
            cursor.execute("ROLLBACK")

# impure
def get_open_positions(db_path: Path) -> List[Dict[str, Any]]:
    """Fetches all positions with status 'OPEN'."""
    query = "SELECT id, symbol, entry_date, entry_price, rule_stack_used FROM positions WHERE status = 'OPEN' ORDER BY entry_date;"
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            positions = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Fetched {len(positions)} open positions.")
            return positions
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch open positions: {e}")
        return []

# impure
def close_positions_batch(db_path: Path, closed_positions: List[Dict[str, Any]]) -> None:
    """Updates positions to 'CLOSED' and records exit details."""
    if not closed_positions:
        return

    update_sql = """
    UPDATE positions
    SET status = 'CLOSED', exit_date = ?, exit_price = ?, final_return_pct = ?, 
        final_nifty_return_pct = ?, days_held = ?
    WHERE id = ?;
    """
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        try:
            for pos in closed_positions:
                cursor.execute(update_sql, (
                    pos.get('exit_date'), pos.get('exit_price'), pos.get('final_return_pct'),
                    pos.get('final_nifty_return_pct'), pos.get('days_held'), pos['id']
                ))
            cursor.execute("COMMIT")
            logger.info(f"Closed {len(closed_positions)} positions.")
        except sqlite3.Error as e:
            logger.error(f"Failed to close positions: {e}")
            cursor.execute("ROLLBACK")

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
    except (KeyError, TypeError, json.JSONDecodeError) as e:
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
