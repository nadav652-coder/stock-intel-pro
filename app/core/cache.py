"""
Local Caching Layer: In-Memory TTL Cache backed by SQLite persistence.
Zero cost, high performance, prevents duplicate external API hits.
"""

import time
import json
import sqlite3
from typing import Any, Optional
from app.core.config import CACHE_DB_PATH, settings

class CacheManager:
    def __init__(self, db_path: str = str(CACHE_DB_PATH), default_ttl: int = settings.CACHE_TTL_SECONDS):
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, tuple[float, Any]] = {}
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_cache (
                        cache_key TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[CacheManager] Warning initializing SQLite cache: {e}")

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        # 1. Check memory cache first
        if key in self._memory_cache:
            expires_at, val = self._memory_cache[key]
            if now < expires_at:
                return val
            else:
                del self._memory_cache[key]

        # 2. Check SQLite cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data_json, expires_at FROM api_cache WHERE cache_key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if row:
                    data_json, expires_at = row
                    if now < expires_at:
                        val = json.loads(data_json)
                        self._memory_cache[key] = (expires_at, val)
                        return val
                    else:
                        cursor.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
                        conn.commit()
        except Exception as e:
            print(f"[CacheManager] Error reading SQLite cache: {e}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl
        self._memory_cache[key] = (expires_at, value)
        try:
            data_json = json.dumps(value, default=str)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_cache (cache_key, data_json, expires_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        data_json = excluded.data_json,
                        expires_at = excluded.expires_at
                """, (key, data_json, expires_at))
                conn.commit()
        except Exception as e:
            print(f"[CacheManager] Error writing to SQLite cache: {e}")

    def clear(self) -> None:
        self._memory_cache.clear()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM api_cache")
                conn.commit()
        except Exception as e:
            print(f"[CacheManager] Error clearing cache: {e}")

cache = CacheManager()
