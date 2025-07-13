# src/kiss_signal/persistence.py
"""SQLite persistence layer for storing backtesting results and trading signals."""

from pathlib import Path  # Standard library
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import sqlite3
import json
import logging
import hashlib
import shutil
from datetime import datetime

if TYPE_CHECKING:
    from .config import RulesConfig

__all__ = [
    "create_database",
    "save_strategies_batch",
    "add_new_positions_from_signals",
    "get_open_positions",
    "close_positions_batch",
    "get_connection",
    "Connection",
    "migrate_strategies_table_v2",
    "generate_config_hash",
    "create_config_snapshot",
    "get_active_strategy_combinations",
]

logger = logging.getLogger(__name__)

# Type alias for clarity
Connection = sqlite3.Connection

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
    config_snapshot TEXT,
    config_hash TEXT,
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
    exit_reason TEXT,
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


# impure
def get_connection(db_path: Path) -> Connection:
    """Creates and returns a new database connection with WAL mode enabled.
    
    Automatically runs migration if needed on first connection.
    """
    try:
        # Check if migration is needed before connecting
        if db_path.exists():
            # Quick check to see if we need migration
            conn_check = sqlite3.connect(str(db_path), timeout=10)
            cursor = conn_check.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            conn_check.close()
            
            if 'config_snapshot' not in columns or 'config_hash' not in columns:
                migrate_strategies_table_v2(db_path)
        
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database at {db_path}: {e}")
        raise


# impure
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
            
            # Set schema version to 2 since we created with the new schema
            conn.execute("PRAGMA user_version = 2;")
            logger.debug("Set database version to 2")
            
            conn.commit()
            logger.info(f"Successfully created database at {db_path}")
            
        # Migration is not needed for fresh databases since they're created with v2 schema
        # But we still call it for existing databases that need migration
        if db_path.exists():
            with sqlite3.connect(str(db_path)) as conn:
                current_version = conn.execute("PRAGMA user_version;").fetchone()[0]
                if current_version < 2:
                    migrate_strategies_table_v2(db_path)
            
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
        final_nifty_return_pct = ?, days_held = ?, exit_reason = ?
    WHERE id = ?;
    """
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        try:
            for pos in closed_positions:
                cursor.execute(update_sql, (
                    pos.get('exit_date'), pos.get('exit_price'), pos.get('final_return_pct'),
                    pos.get('final_nifty_return_pct'), pos.get('days_held'), pos.get('exit_reason'),
                    pos['id']
                ))
            cursor.execute("COMMIT")
            logger.info(f"Closed {len(closed_positions)} positions.")
        except sqlite3.Error as e:
            logger.error(f"Failed to close positions: {e}")
            cursor.execute("ROLLBACK")

# impure
def save_strategies_batch(
    db_connection: Connection, 
    strategies: List[Dict[str, Any]], 
    run_timestamp: str,
    config_snapshot: Optional[Dict[str, Any]] = None,
    config_hash: Optional[str] = None
) -> bool:
    """Save a batch of strategy results using an existing database connection.
    
    Args:
        db_connection: An active SQLite database connection.
        strategies: List of strategy dictionaries from backtester.
        run_timestamp: ISO 8601 timestamp string for this run.
        config_snapshot: Optional configuration snapshot for context.
        config_hash: Optional configuration hash for grouping.
        
    Returns:
        True if successful, False if failed.
    """
    if not strategies:
        logger.info("No strategies to save - skipping batch save")
        return True
    
    logger.info(f"Saving {len(strategies)} strategies to the database.")
    
    insert_sql = """
    INSERT INTO strategies (
        run_timestamp, symbol, rule_stack, edge_score, 
        win_pct, sharpe, total_trades, avg_return, config_snapshot, config_hash
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor = db_connection.cursor()
        cursor.execute("BEGIN")
        logger.debug("Started transaction for batch save")
        
        for strategy in strategies:
            # Debug logging for total_trades before assertion
            logger.debug(f"Strategy {strategy.get('symbol', 'N/A')} total_trades: type={type(strategy.get('total_trades'))}, value={strategy.get('total_trades')!r}")
            
            # Hard assertions to catch data corruption and validate thresholds
            assert "total_trades" in strategy, "total_trades key missing from strategy dict"
            assert strategy["total_trades"] is not None, "total_trades cannot be None"
            
            # Handle numpy integer types by converting to Python int
            total_trades = strategy["total_trades"]
            total_trades_value = int(total_trades) if hasattr(total_trades, "item") else int(total_trades)
            # Sanity check to prevent bad data from being stored (should be non-negative)
            assert total_trades_value >= 0, f"total_trades must be non-negative, got {total_trades_value}"
            
            rule_stack = strategy["rule_stack"]
            if rule_stack and hasattr(rule_stack[0], 'model_dump'):
                rule_stack_json = json.dumps([rule.model_dump() for rule in rule_stack])
            else:
                rule_stack_json = json.dumps(rule_stack)
            
            # Log the value being inserted
            logger.debug(f"Inserting total_trades as: {total_trades_value} (type: {type(total_trades_value)})")
            
            cursor.execute(insert_sql, (
                run_timestamp,
                strategy["symbol"],
                rule_stack_json,
                strategy["edge_score"],
                strategy["win_pct"],
                strategy["sharpe"],
                total_trades_value,  # Use the explicit int value
                strategy["avg_return"],
                json.dumps(config_snapshot) if config_snapshot else '{}',
                config_hash or 'unknown'
            ))
        
        db_connection.commit()
        logger.info(f"Successfully saved {len(strategies)} strategies")
        return True
        
    except (sqlite3.Error, KeyError, TypeError, json.JSONDecodeError, AssertionError) as e:
        try:
            db_connection.rollback()
            logger.debug("Rolled back transaction due to error")
        except sqlite3.Error:
            pass
        logger.error(f"Batch save failed: {e}")
        return False

# impure
def migrate_strategies_table_v2(db_path: Path) -> None:
    """Migrates the strategies table to version 2 by adding new columns.
    
    Args:
        db_path: Path to the SQLite database file
        
    Raises:
        sqlite3.Error: If migration fails
    """
    logger.info(f"Starting migration of strategies table at {db_path}")
    try:
        with sqlite3.connect(str(db_path)) as conn:
            # Check current schema version
            current_version = conn.execute("PRAGMA user_version;").fetchone()[0]
            logger.info(f"Current database version: {current_version}")
            
            # If already at latest version, do nothing
            if current_version >= 2:
                logger.info("Database is already at the latest version. Migration not required.")
                return
            
            # Begin transaction
            conn.execute("BEGIN")
            logger.debug("Started transaction for migration")
            
            # Rename existing table
            conn.execute("ALTER TABLE strategies RENAME TO strategies_old;")
            logger.info("Renamed old strategies table")
            
            # Create new strategies table
            conn.execute(CREATE_STRATEGIES_TABLE)
            logger.info("Created new strategies table")
            
            # Recreate the index
            conn.execute(CREATE_INDEX_STRATEGIES)
            logger.info("Created index on new strategies table")
            
            # Copy data from old table to new table
            columns = ["symbol", "run_timestamp", "rule_stack", "edge_score", "win_pct", "sharpe", "total_trades", "avg_return"]
            column_list = ", ".join(columns)
            # Include new columns with legacy placeholders for existing data
            new_column_list = column_list + ", config_snapshot, config_hash"
            legacy_placeholders = "'{}', 'legacy'".format('{"legacy": true}')
            conn.execute(f"INSERT INTO strategies ({new_column_list}) SELECT {column_list}, {legacy_placeholders} FROM strategies_old;")
            logger.info("Copied data to new strategies table with legacy placeholders for config columns")
            
            # Drop old table
            conn.execute("DROP TABLE strategies_old;")
            logger.info("Dropped old strategies table")
            
            # Update schema version
            conn.execute("PRAGMA user_version = 2;")
            logger.info("Updated database version to 2")
            
            conn.commit()
            logger.info("Migration completed successfully")
            
    except sqlite3.Error as e:
        logger.error(f"Migration failed: {e}")
        raise

# impure
def generate_config_hash(rules_config: Dict[str, Any], app_config: Any) -> str:
    """Generate a deterministic hash for configuration context.
    
    Args:
        rules_config: Rules configuration dictionary
        app_config: Application configuration object
        
    Returns:
        8-character hash string for readability
    """
    # Create a deterministic representation of the configuration
    hash_content = {
        'rules_hash': hashlib.sha256(json.dumps(rules_config, sort_keys=True).encode()).hexdigest(),
        'universe_path': str(app_config.universe_path),
        'historical_data_years': app_config.historical_data_years,
        'hold_period': app_config.hold_period,
        'min_trades_threshold': app_config.min_trades_threshold,
        'edge_score_threshold': app_config.edge_score_threshold,
        'edge_score_weights': {
            'win_pct': app_config.edge_score_weights.win_pct,
            'sharpe': app_config.edge_score_weights.sharpe
        }
    }
    
    # Generate deterministic hash
    content_str = json.dumps(hash_content, sort_keys=True)
    full_hash = hashlib.sha256(content_str.encode()).hexdigest()
    return full_hash[:8]  # 8-character prefix for readability


def create_config_snapshot(rules_config: Dict[str, Any], app_config: Any, freeze_date: Optional[str] = None) -> Dict[str, Any]:
    """Create a configuration snapshot for historical context.
    
    Args:
        rules_config: Rules configuration dictionary
        app_config: Application configuration object
        freeze_date: Optional freeze date for backtesting
        
    Returns:
        Configuration snapshot dictionary
    """
    snapshot = {
        'rules_hash': hashlib.sha256(json.dumps(rules_config, sort_keys=True).encode()).hexdigest()[:16],
        'universe_path': str(app_config.universe_path),
        'hold_period': app_config.hold_period,
        'edge_score_threshold': app_config.edge_score_threshold,
        'min_trades_threshold': app_config.min_trades_threshold,
        'freeze_date': freeze_date,
        'timestamp': datetime.now().isoformat()  # Use proper timestamp
    }
    return snapshot


def get_active_strategy_combinations(rules_config: "RulesConfig") -> List[str]:
    """Parse RulesConfig to extract all possible strategy combinations.
    
    Args:
        rules_config: RulesConfig object with baseline and layers
        
    Returns:
        List of JSON-serialized rule stacks that match current configuration
    """
    from .config import RuleDef  # Local import for type checking
    
    combinations: List[List[RuleDef]] = []
    
    # Generate baseline strategy
    if rules_config.baseline:
        combinations.append([rules_config.baseline])
        
        # Generate baseline + each layer combination
        for layer in rules_config.layers:
            combinations.append([rules_config.baseline, layer])
    
    # Convert each combination to JSON string
    return [json.dumps([r.model_dump() for r in combo]) for combo in combinations]
