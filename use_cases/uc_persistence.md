| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data | Date: 08/07/24 |

# KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data

**1. Brief Description**

This use case allows an actor to create the application database and to save and retrieve trading-related data, such as optimal strategies and trade positions. It ensures data is stored reliably and transactionally.

The use case can be called:
- To create the database schema on the first run.
- By the CLI orchestrator to save backtesting results.
- By the Reporter module to add new positions or retrieve open ones.

**2. Actors**

**2.1 Primary Actors**
1. **CLI Orchestrator** – Needs to save the results of a backtesting run.
2. **Reporter Module** – Needs to add new positions, retrieve open positions, and update closed positions.

**2.2 Secondary Actors**
- sqlite3 Library
- File System

**3. Conditions**

**3.1 Pre-Condition**
- The path for the database file is writable.
- The data to be saved (e.g., a list of strategies) is well-formed.

**3.2 Post Conditions on success**
1. The database file is created with the correct schema if it doesn't exist.
2. The provided data is successfully written to the appropriate table(s).
3. For read operations, the requested data is returned to the actor.

**3.3 Post Conditions on Failure**
1. An exception (`sqlite3.Error`, `OSError`) is raised.
2. For write operations, any partial changes are rolled back, leaving the database in its previous state.

**4. Trigger**

1. A request to perform a database operation is issued by a Primary Actor. This could be:
    a. A call to `create_database(db_path)`.
    b. A call to `save_strategies_batch(db_path, strategies, run_timestamp)`.
    c. A call to `get_open_positions(db_path)`.

**5. Main Flow: KS_PERSISTENCE_BS_UC005.MF – Save Strategy Batch**

10. The system receives a list of strategy dictionaries and a `run_timestamp`.
    10.10. The system validates that the strategy list is not empty.
    10.20. The system validates that each strategy contains required fields.

20. The system connects to the SQLite database specified by `db_path`.
    20.10. The system establishes connection using string path conversion.
    <<conn = sqlite3.connect(str(db_path))>>
    20.20. WAL mode is enabled during database creation, not during each connection.
    *See Exception Flow 1: KS_PERSISTENCE_BS_UC005.XF01 – Database Operation Failed*

30. The system begins a database transaction to ensure atomicity.
    30.10. The system starts explicit transaction for batch processing.
    <<cursor.execute("BEGIN TRANSACTION")>>

40. The system iterates through each `strategy` in the list.
    40.10. The system extracts strategy fields: symbol, rule_stack, edge_score, metrics.
    40.20. The system validates that symbol field exists in strategy.

50. For each strategy, the system serializes the `rule_stack` list to a JSON string for database storage.
    50.10. The system converts rule_stack (list of rule definitions) to JSON string for relational storage.
    <<rule_stack_json = json.dumps(strategy["rule_stack"])>>
    50.20. JSON serialization preserves complete rule definitions including parameters and metadata.
    50.30. The system handles JSON serialization errors which would trigger transaction rollback.
    50.40. Serialized rule_stack enables future signal regeneration without external rule files.

60. The system prepares and executes an `INSERT` statement with the strategy's data using parameterized queries.
    60.10. The system uses predefined INSERT SQL with parameter placeholders for security.
    <<insert_sql = "INSERT INTO strategies (run_timestamp, symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?)">> 
    60.20. The system binds parameters to prevent SQL injection attacks using ? placeholders.
    <<cursor.execute(insert_sql, (run_timestamp, strategy["symbol"], rule_stack_json, strategy["edge_score"], strategy["win_pct"], strategy["sharpe"], strategy["total_trades"], strategy["avg_return"]))>>
    60.30. Parameterized queries ensure type safety and prevent malicious SQL injection.
    60.40. The system handles constraint violations (UNIQUE constraint on symbol, rule_stack, run_timestamp).
    60.50. UNIQUE constraint prevents duplicate strategies for the same symbol and run timestamp.
    60.60. Constraint violations are logged but don't abort the entire batch transaction.
    *See Exception Flow 1: KS_PERSISTENCE_BS_UC005.XF01 – Database Operation Failed*

70. After all strategies are processed, the system commits the transaction.
    70.10. The system commits all INSERT operations atomically.
    <<cursor.execute("COMMIT")>>
    70.20. The system logs successful batch save operation.

80. The system closes the database connection and returns a success status.
    80.10. The system ensures connection is properly closed.
    80.20. The system returns True to indicate successful operation.

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_PERSISTENCE_BS_UC005.XF01 – Database Operation Failed**

10. At **any step from 20 to 60**, the system encounters a database-related error (e.g., connection failed, SQL error, constraint violation) or a data formatting error.
    <<sqlite3.Error>> or <<json.JSONDecodeError>>

20. The system attempts to roll back the current transaction to prevent partial data writes.
    <<conn.rollback()>>

30. The system logs the specific error for debugging purposes.

40. The system returns a failure status to the primary actor.

99. The use case ends.

**7. Notes / Assumptions**

- The create_database function creates tables with proper schema: strategies, positions with appropriate indexes.
- Database schema includes UNIQUE constraint on (symbol, rule_stack, run_timestamp) to prevent duplicates.
- The add_new_positions_from_signals function prevents duplicate open positions for the same symbol.
- The get_open_positions function uses SELECT queries with status filtering and returns dict-like rows.
- The close_positions_batch function updates position status and records exit details atomically.
- WAL (Write-Ahead Logging) mode is enabled during database creation to improve concurrency.
- JSON serialization of rule_stack preserves complete rule definitions for future signal generation.
- Parameterized queries prevent SQL injection attacks using ? placeholders.
- Transaction rollback ensures database consistency on any failure during batch operations.
- Database schema includes proper indexes: idx_strategies_symbol_timestamp, idx_positions_status_symbol.
- The positions table includes CHECK constraint ensuring status is either 'OPEN' or 'CLOSED'.
- Connection management uses context managers (with statements) for automatic cleanup.
- Error handling distinguishes between sqlite3.Error, KeyError, TypeError, and json.JSONDecodeError.
- The save_strategies_batch function returns boolean success status rather than raising exceptions.

**8. Issues**

| No: | Description: | Date | Action: | Status |
|---|---|---|---|---|
| 1. | | | | |

**9. Revision History**

| Date | Rev | Who | Description | Reference |
|---|---|---|---|---|
| 08/07/24 | 1.0 | AI | Initial document creation. | |

**10. Reference Documentation**

| Document Name | Version | Description | Location |
|---|---|---|---|
| `src/kiss_signal/persistence.py` | | Source code for the persistence module with SQLite database operations. | Git Repository |
| `sqlite3` | | Built-in Python SQLite database interface. | Python Standard Library |
| `json` | | Built-in JSON encoder and decoder. | Python Standard Library |
