#!/usr/bin/env python3
"""
Database Cleanup Script - Fix Entry Price Corruption

This script cleans up positions with invalid entry prices (zero or negative).
Such positions represent data corruption and must be removed to maintain 
data integrity and proper risk management calculations.

Usage:
    python scripts/cleanup_invalid_positions.py [--db-path PATH] [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Tuple

def main():
    parser = argparse.ArgumentParser(description="Clean up positions with invalid entry prices")
    parser.add_argument(
        "--db-path", 
        type=Path, 
        default=Path("data/kiss_signal.db"),
        help="Path to the database file (default: data/kiss_signal.db)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        print(f"❌ Database file not found: {args.db_path}")
        sys.exit(1)
    
    print(f"🔍 Checking database: {args.db_path}")
    
    # Find corrupted positions
    invalid_count, sample_positions = find_invalid_positions(args.db_path)
    
    if invalid_count == 0:
        print("✅ No invalid positions found. Database is clean.")
        sys.exit(0)
    
    print(f"⚠️  Found {invalid_count} positions with invalid entry prices:")
    print()
    
    # Show sample corrupted data
    for pos in sample_positions[:5]:  # Show up to 5 examples
        print(f"  - ID: {pos[0]}, Symbol: {pos[1]}, Entry Price: {pos[2]}, Status: {pos[3]}")
    
    if len(sample_positions) > 5:
        print(f"  ... and {len(sample_positions) - 5} more")
    
    print()
    
    if args.dry_run:
        print("🔬 DRY RUN: Would delete these positions but taking no action.")
        print("   Run without --dry-run to perform actual cleanup.")
    else:
        print("🧹 Cleaning up invalid positions...")
        deleted_count = cleanup_invalid_positions(args.db_path)
        print(f"✅ Successfully deleted {deleted_count} invalid positions.")
        print("   Database integrity restored.")

def find_invalid_positions(db_path: Path) -> Tuple[int, list]:
    """Find positions with invalid entry prices and return count + sample data."""
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Find all positions with invalid entry prices
        cursor.execute("""
            SELECT id, symbol, entry_price, status 
            FROM positions 
            WHERE entry_price <= 0
            ORDER BY id
        """)
        
        invalid_positions = cursor.fetchall()
        return len(invalid_positions), invalid_positions

def cleanup_invalid_positions(db_path: Path) -> int:
    """Delete positions with invalid entry prices and return count of deleted records."""
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Delete invalid positions
        cursor.execute("""
            DELETE FROM positions 
            WHERE entry_price <= 0
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        return deleted_count

if __name__ == "__main__":
    main()
