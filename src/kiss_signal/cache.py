"""Intelligent caching system for expensive calculations."""

import hashlib
import pickle
import sqlite3
import logging
from pathlib import Path
from typing import Any, Optional
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

class IntelligentCache:
    """SQLite-based cache with invalidation and size management."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        self.max_size_mb = max_size_mb
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize cache database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    size_bytes INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)")
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function signature."""
        # Create deterministic hash from function name and arguments
        content = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM cache_entries WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update access time
                conn.execute(
                    "UPDATE cache_entries SET accessed_at = ? WHERE key = ?",
                    (datetime.now(), key)
                )
                try:
                    return pickle.loads(row[0])
                except Exception as e:
                    logger.warning(f"Failed to deserialize cache entry {key}: {e}")
                    # Remove corrupted entry
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Store value in cache."""
        try:
            serialized = pickle.dumps(value)
            size_bytes = len(serialized)
            now = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, accessed_at, size_bytes)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, serialized, now, now, size_bytes))
                
                # Check cache size and cleanup if needed
                self._cleanup_if_needed(conn)
                
        except Exception as e:
            logger.warning(f"Failed to cache value for key {key}: {e}")
    
    def _cleanup_if_needed(self, conn: sqlite3.Connection) -> None:
        """Remove old entries if cache exceeds size limit."""
        cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
        total_size = cursor.fetchone()[0] or 0
        
        if total_size > self.max_size_mb * 1024 * 1024:
            # Remove oldest accessed entries until under limit
            conn.execute("""
                DELETE FROM cache_entries 
                WHERE key IN (
                    SELECT key FROM cache_entries 
                    ORDER BY accessed_at ASC 
                    LIMIT (SELECT COUNT(*) / 4 FROM cache_entries)
                )
            """)
            logger.info("Cache cleanup performed - removed 25% of oldest entries")
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries WHERE key LIKE ?", (f"%{pattern}%",))
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries")

def cached(cache_instance: IntelligentCache, ttl_hours: int = 24):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_instance._generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__} - executing")
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

# Global cache instance
_cache_dir = Path.home() / ".kiss_signal" / "cache"
global_cache = IntelligentCache(_cache_dir)
