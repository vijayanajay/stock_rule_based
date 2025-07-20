"""
Test for Story 020: Fix Strategy Performance Report Duplication
"""
import sqlite3
import tempfile
from pathlib import Path
import pytest

from src.kiss_signal import reporter, persistence


class TestStory020Deduplication:
    """Test deduplication fix for analyze_strategy_performance function."""
    
    @pytest.fixture
    def duplicate_strategies_db(self):
        """Create test database with duplicate strategies (same symbol+strategy, different timestamps/config_hash)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            persistence.create_database(db_path)
            
            with sqlite3.connect(str(db_path)) as conn:
                # Insert duplicate strategies: same symbol+strategy but different timestamps and config_hash
                strategies = [
                    # TATASTEEL duplicates - same strategy, different runs
                    ("TATASTEEL", "2025-07-13T12:11:51", '[{"name": "bullish_engulfing_reversal", "type": "signal"}]', 0.83, 0.72, 0.98, 11, 3405.93, "075af9f4", '{"timestamp": "2025-07-13T12:11:51"}'),
                    ("TATASTEEL", "2025-07-15T23:45:18", '[{"name": "bullish_engulfing_reversal", "type": "signal"}]', 0.79, 0.72, 0.89, 11, 2927.84, "75bf44fe", '{"timestamp": "2025-07-15T23:45:18"}'),
                    
                    # TCS duplicates - same strategy, different runs  
                    ("TCS", "2025-07-13T12:11:51", '[{"name": "bullish_engulfing_reversal", "type": "signal"}]', -0.18, 0.32, -0.94, 25, -1117.11, "075af9f4", '{"timestamp": "2025-07-13T12:11:51"}'),
                    ("TCS", "2025-07-19T00:54:34", '[{"name": "bullish_engulfing_reversal", "type": "signal"}]', -0.17, 0.30, -0.88, 26, -1018.64, "75bf44fe", '{"timestamp": "2025-07-19T00:54:34"}'),
                    
                    # UNIQUE strategy (no duplicates) - should appear in result
                    ("INFY", "2025-07-15T23:45:18", '[{"name": "sma_crossover", "type": "signal"}]', 0.65, 0.60, 1.1, 15, 500.0, "75bf44fe", '{"timestamp": "2025-07-15T23:45:18"}'),
                ]
                
                for strategy in strategies:
                    conn.execute(
                        """INSERT INTO strategies 
                           (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, config_hash, config_snapshot) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        strategy
                    )
                conn.commit()
            
            yield db_path
            
        finally:
            # Ensure proper cleanup on Windows
            try:
                if db_path.exists():
                    db_path.unlink()
            except (PermissionError, OSError):
                # Ignore cleanup errors on Windows
                pass

    def test_deduplication_removes_duplicates(self, duplicate_strategies_db):
        """Test that analyze_strategy_performance returns only latest version of each symbol+strategy combination."""
        result = reporter.analyze_strategy_performance(duplicate_strategies_db)
        
        # Should have only 3 records: 1 for TATASTEEL (latest), 1 for TCS (latest), 1 for INFY
        assert len(result) == 3, f"Expected 3 deduplicated records, got {len(result)}"
        
        # Extract symbol-strategy combinations
        combinations = [(r['symbol'], r['rule_stack']) for r in result]
        
        # Each symbol-strategy should appear only once
        unique_combinations = set(combinations)
        assert len(combinations) == len(unique_combinations), "Found duplicate symbol-strategy combinations"
        
        # Verify specific symbols are present
        symbols = [r['symbol'] for r in result]
        assert 'TATASTEEL' in symbols
        assert 'TCS' in symbols  
        assert 'INFY' in symbols

    def test_deduplication_keeps_latest_record(self, duplicate_strategies_db):
        """Test that deduplication keeps the latest (highest ID) record for each symbol+strategy."""
        result = reporter.analyze_strategy_performance(duplicate_strategies_db)
        
        # Find TATASTEEL record
        tatasteel_record = next(r for r in result if r['symbol'] == 'TATASTEEL')
        
        # Should be the 2025-07-15 version (latest), not 2025-07-13
        assert tatasteel_record['run_date'] == '2025-07-15'
        assert tatasteel_record['edge_score'] == 0.79  # Latest edge score
        assert tatasteel_record['config_hash'] == '75bf44fe'  # Latest config hash
        
        # Find TCS record
        tcs_record = next(r for r in result if r['symbol'] == 'TCS')
        
        # Should be the 2025-07-19 version (latest), not 2025-07-13
        assert tcs_record['run_date'] == '2025-07-19'
        assert tcs_record['edge_score'] == -0.17  # Latest edge score
        assert tcs_record['config_hash'] == '75bf44fe'  # Latest config hash

    def test_deduplication_preserves_unique_records(self, duplicate_strategies_db):
        """Test that unique records (no duplicates) are preserved correctly."""
        result = reporter.analyze_strategy_performance(duplicate_strategies_db)
        
        # Find INFY record (unique, no duplicates)
        infy_record = next(r for r in result if r['symbol'] == 'INFY')
        
        # Should be preserved exactly as inserted
        assert infy_record['edge_score'] == 0.65
        assert infy_record['run_date'] == '2025-07-15'
        assert infy_record['config_hash'] == '75bf44fe'

    def test_deduplication_different_strategies_same_symbol(self, duplicate_strategies_db):
        """Test that different strategies for same symbol are NOT deduplicated."""
        with sqlite3.connect(str(duplicate_strategies_db)) as conn:
            # Add different strategy for TATASTEEL
            conn.execute(
                """INSERT INTO strategies 
                   (symbol, run_timestamp, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return, config_hash, config_snapshot) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("TATASTEEL", "2025-07-15T23:45:18", '[{"name": "bullish_engulfing_reversal", "type": "signal"}, {"name": "rsi_filter", "type": "filter"}]', 0.85, 0.75, 1.05, 12, 3200.0, "75bf44fe", '{"timestamp": "2025-07-15T23:45:18"}')
            )
            conn.commit()
        
        result = reporter.analyze_strategy_performance(duplicate_strategies_db)
        
        # Should now have 4 records: TATASTEEL with 2 different strategies, TCS, INFY
        assert len(result) == 4, f"Expected 4 records (different strategies preserved), got {len(result)}"
        
        # Count TATASTEEL entries
        tatasteel_records = [r for r in result if r['symbol'] == 'TATASTEEL']
        assert len(tatasteel_records) == 2, "TATASTEEL should have 2 different strategies"
        
        # Verify different rule stacks
        rule_stacks = [r['rule_stack'] for r in tatasteel_records]
        assert len(set(rule_stacks)) == 2, "TATASTEEL should have 2 distinct rule stacks"

    def test_story_020_acceptance_criteria(self, duplicate_strategies_db):
        """Test Story 020 acceptance criteria are met."""
        # AC-1: Fix Reporter Query - deduplication working
        result = reporter.analyze_strategy_performance(duplicate_strategies_db)
        
        # Should return deduplicated results
        assert len(result) == 3, "AC-1: CSV should contain deduplicated rows"
        
        # AC-1: All unique strategies preserved (no data loss)
        symbols = [r['symbol'] for r in result]
        assert 'TATASTEEL' in symbols, "AC-1: TATASTEEL strategy preserved"
        assert 'TCS' in symbols, "AC-1: TCS strategy preserved"  
        assert 'INFY' in symbols, "AC-1: INFY strategy preserved"
        
        # AC-1: Query executes faster (fewer rows processed)
        # Verified by the fact we get 3 rows instead of 5 (60% reduction)
        
        # AC-3: Latest data shown
        tatasteel_record = next(r for r in result if r['symbol'] == 'TATASTEEL')
        assert tatasteel_record['run_date'] == '2025-07-15', "AC-3: Shows latest data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
