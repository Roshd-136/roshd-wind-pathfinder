"""
Data caching and storage module for Roshd Wind Pathfinder.

This module handles:
- Local database for storing wind data
- Caching strategy to reduce API calls
- TTL (Time-To-Live) management
- Data structure design for efficient storage
"""

import sqlite3
import time
from pathlib import Path

import pandas as pd


class WindDataCache:
    """Local cache for wind data using SQLite with TTL support."""

    def __init__(self, db_path: str = "~/.roshd_wind_cache.db"):
        """Initialize the cache database."""
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        """Create the database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wind_data (
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    altitude REAL NOT NULL,
                    timestamp INTEGER NOT NULL,
                    u_component REAL NOT NULL,
                    v_component REAL NOT NULL,
                    ttl INTEGER NOT NULL,
                    PRIMARY KEY (lat, lon, altitude, timestamp)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def _get_ttl(self, data_type: str = "wind") -> int:
        """Get TTL (in seconds) for the specified data type."""
        # Default TTL: 6 hours (21600 seconds) for wind data
        default_ttl = 21600
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM cache_metadata WHERE key = ?",
                (f"ttl_{data_type}",),
            )
            result = cursor.fetchone()
            return int(result[0]) if result else default_ttl

    def _set_ttl(self, data_type: str, ttl_seconds: int) -> None:
        """Set TTL for the specified data type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO cache_metadata (key, value) VALUES (?, ?)",
                (f"ttl_{data_type}", str(ttl_seconds)),
            )
            conn.commit()

    def _is_expired(self, timestamp: int, ttl: int) -> bool:
        """Check if the data is expired based on its timestamp and TTL."""
        return (time.time() - timestamp) > ttl

    def store_wind_data(
        self,
        lat: float,
        lon: float,
        altitude: float,
        timestamp: int,
        u_component: float,
        v_component: float,
        ttl: int | None = None,
    ) -> None:
        """Store wind data in the cache."""
        ttl = ttl or self._get_ttl("wind")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO wind_data
                (lat, lon, altitude, timestamp, u_component, v_component, ttl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lat, lon, altitude, timestamp, u_component, v_component, ttl),
            )
            conn.commit()

    def get_wind_data(
        self,
        lat: float,
        lon: float,
        altitude: float,
        timestamp: int,
    ) -> tuple[float, float] | None:
        """Retrieve wind data from the cache if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u_component, v_component, timestamp, ttl
                FROM wind_data
                WHERE lat = ? AND lon = ? AND altitude = ? AND timestamp = ?
                """,
                (lat, lon, altitude, timestamp),
            )
            result = cursor.fetchone()
            if result:
                u, v, stored_timestamp, ttl = result
                if not self._is_expired(stored_timestamp, ttl):
                    return (u, v)
                else:
                    # Data expired, remove it
                    cursor.execute(
                        "DELETE FROM wind_data WHERE lat = ? AND lon = ? AND altitude = ? AND timestamp = ?",
                        (lat, lon, altitude, timestamp),
                    )
                    conn.commit()
            return None

    def get_wind_data_batch(
        self,
        coordinates: list[tuple[float, float, float, int]],
    ) -> dict[tuple[float, float, float, int], tuple[float, float] | None]:
        """Retrieve multiple wind data points in a single query."""
        results = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for lat, lon, altitude, timestamp in coordinates:
                cursor.execute(
                    """
                    SELECT u_component, v_component, timestamp, ttl
                    FROM wind_data
                    WHERE lat = ? AND lon = ? AND altitude = ? AND timestamp = ?
                    """,
                    (lat, lon, altitude, timestamp),
                )
                result = cursor.fetchone()
                if result:
                    u, v, stored_timestamp, ttl = result
                    if not self._is_expired(stored_timestamp, ttl):
                        results[(lat, lon, altitude, timestamp)] = (u, v)
                    else:
                        # Data expired, remove it
                        cursor.execute(
                            "DELETE FROM wind_data WHERE lat = ? AND lon = ? AND altitude = ? AND timestamp = ?",
                            (lat, lon, altitude, timestamp),
                        )
                        results[(lat, lon, altitude, timestamp)] = None
                else:
                    results[(lat, lon, altitude, timestamp)] = None
            conn.commit()
        return results

    def clear_expired_data(self) -> None:
        """Remove all expired data from the cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM wind_data
                WHERE (timestamp + ttl) < ?
                """,
                (int(time.time()),),
            )
            conn.commit()

    def export_to_dataframe(self) -> pd.DataFrame:
        """Export all valid (non-expired) wind data to a pandas DataFrame."""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT lat, lon, altitude, timestamp, u_component, v_component
                FROM wind_data
                WHERE (timestamp + ttl) >= ?
            """
            df = pd.read_sql_query(query, conn, params=(int(time.time()),))
        return df

    def get_cache_stats(self) -> dict[str, int]:
        """Get statistics about the cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wind_data")
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM wind_data WHERE (timestamp + ttl) >= ?",
                (int(time.time()),),
            )
            valid = cursor.fetchone()[0]
        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
        }
