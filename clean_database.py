#!/usr/bin/env python3
"""Database cleanup script for KISS Signal CLI.

This script provides safe database maintenance operations with confirmation prompts.
Following Kailash Nadh principles: simple, direct, no surprises.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Optional

def get_database_path() -> Path:
    """Get database path from config or use default."""
    default_db = Path("data/kiss_signal.db")
    if default_db.exists():
        return default_db
    
    # Fallback locations
    fallbacks = [
        Path("kiss_signal.db"),
        Path("data/test.db"),
        Path("test.db")
    ]
    
    for db_path in fallbacks:
        if db_path.exists():
            return db_path
    
    print(f"⚠️  No database found. Creating new one at {default_db}")
    return default_db

def show_database_stats(db_path: Path) -> None:
    """Display current database statistics."""
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            print(f"📊 DATABASE STATISTICS: {db_path}")
            print("=" * 50)
            
            # Get table counts
            tables = [
                ("strategies", "Trading strategies"),
                ("positions", "Open/closed positions"), 
                ("trades", "Historical trades"),
                ("signals", "Generated signals")
            ]
            
            for table, description in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"{description:.<25} {count:>8} rows")
                except sqlite3.OperationalError:
                    print(f"{description:.<25} {'N/A':>8} (table missing)")
            
            print("=" * 50)
            
            # Check for data corruption indicators
            try:
                cursor.execute("""
                    SELECT symbol, entry_date, 
                           CASE WHEN entry_date > date('now') THEN 'FUTURE' ELSE 'OK' END as status
                    FROM positions 
                    WHERE entry_date > date('now')
                    LIMIT 5
                """)
                future_positions = cursor.fetchall()
                
                if future_positions:
                    print("🚨 CORRUPTION DETECTED:")
                    for symbol, entry_date, status in future_positions:
                        print(f"   {symbol}: entry_date={entry_date} ({status})")
                    print()
                else:
                    print("✅ No corruption detected in positions table")
                    print()
                    
            except sqlite3.OperationalError:
                print("ℹ️  Could not check for corruption (positions table missing)")
                print()
                
    except Exception as e:
        print(f"❌ Error reading database: {e}")

def clean_positions_table(db_path: Path, confirm: bool = True) -> None:
    """Clean corrupted positions from database."""
    if confirm:
        response = input("🗑️  Delete ALL positions? This cannot be undone. (yes/no): ")
        if response.lower() != "yes":
            print("❌ Cancelled")
            return
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Get count before deletion
            cursor.execute("SELECT COUNT(*) FROM positions")
            before_count = cursor.fetchone()[0]
            
            # Delete all positions
            cursor.execute("DELETE FROM positions")
            conn.commit()
            
            print(f"✅ Deleted {before_count} positions from database")
            
    except Exception as e:
        print(f"❌ Error cleaning positions: {e}")

def clean_future_positions(db_path: Path, reference_date: Optional[str] = None) -> None:
    """Clean positions with future entry dates (corruption fix)."""
    if reference_date is None:
        reference_date = date.today().isoformat()
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Count corrupted positions
            cursor.execute("SELECT COUNT(*) FROM positions WHERE entry_date > ?", (reference_date,))
            corrupt_count = cursor.fetchone()[0]
            
            if corrupt_count == 0:
                print("✅ No future positions found")
                return
            
            print(f"🔍 Found {corrupt_count} positions with future entry dates")
            response = input(f"Delete these corrupted positions? (yes/no): ")
            
            if response.lower() == "yes":
                cursor.execute("DELETE FROM positions WHERE entry_date > ?", (reference_date,))
                conn.commit()
                print(f"✅ Deleted {corrupt_count} corrupted positions")
            else:
                print("❌ Cancelled")
                
    except Exception as e:
        print(f"❌ Error cleaning future positions: {e}")

def reset_database(db_path: Path) -> None:
    """Complete database reset - nuclear option."""
    print("☢️  NUCLEAR OPTION: Complete database reset")
    print("This will delete ALL data and recreate empty tables.")
    print()
    
    response = input("Are you absolutely sure? Type 'RESET' to confirm: ")
    if response != "RESET":
        print("❌ Cancelled")
        return
    
    try:
        # Delete existing database
        if db_path.exists():
            db_path.unlink()
            print(f"🗑️  Deleted {db_path}")
        
        # Create fresh database with schema
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Create basic schema (simplified)
            cursor.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    strategy_name TEXT,
                    edge_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE positions (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    entry_date TEXT,
                    entry_price REAL,
                    status TEXT DEFAULT 'OPEN',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print("✅ Created fresh database with empty tables")
            
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

def main():
    """Main cleanup interface."""
    print("🧹 KISS Signal Database Cleanup Utility")
    print("=====================================")
    print()
    
    db_path = get_database_path()
    show_database_stats(db_path)
    
    while True:
        print("\nCLEANUP OPTIONS:")
        print("1. Show database statistics")
        print("2. Clean ALL positions (recommended for corruption)")
        print("3. Clean only future positions (surgical fix)")
        print("4. Complete database reset (nuclear option)")
        print("5. Exit")
        print()
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            show_database_stats(db_path)
        elif choice == "2":
            clean_positions_table(db_path)
        elif choice == "3":
            clean_future_positions(db_path)
        elif choice == "4":
            reset_database(db_path)
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please choose 1-5.")

if __name__ == "__main__":
    main()
