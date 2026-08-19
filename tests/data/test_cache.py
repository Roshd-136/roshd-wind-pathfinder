"""
Tests for the WindDataCache class.
"""

import os
import tempfile
import time
import unittest

from data.cache import WindDataCache


class TestWindDataCache(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.cache = WindDataCache(db_path=self.temp_db)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_store_and_retrieve(self):
        """Test storing and retrieving wind data."""
        self.cache.store_wind_data(
            lat=35.7, lon=51.4, altitude=1000, timestamp=int(time.time()),
            u_component=5.0, v_component=2.0
        )
        result = self.cache.get_wind_data(35.7, 51.4, 1000, int(time.time()))
        self.assertIsNotNone(result)
        self.assertEqual(result, (5.0, 2.0))

    def test_data_expiration(self):
        """Test that expired data is not returned."""
        # Store data with 1 second TTL
        self.cache._set_ttl("wind", 1)
        expired_timestamp = int(time.time()) - 2  # 2 seconds ago
        self.cache.store_wind_data(
            lat=35.7, lon=51.4, altitude=1000, timestamp=expired_timestamp,
            u_component=5.0, v_component=2.0, ttl=1
        )
        result = self.cache.get_wind_data(35.7, 51.4, 1000, expired_timestamp)
        self.assertIsNone(result)

    def test_batch_retrieval(self):
        """Test retrieving multiple data points at once."""
        coords = [
            (35.7, 51.4, 1000.0, int(time.time())),
            (35.8, 51.5, 1500.0, int(time.time())),
            (35.9, 51.6, 2000.0, int(time.time())),
        ]
        for lat, lon, alt, ts in coords:
            self.cache.store_wind_data(lat, lon, alt, ts, 5.0, 2.0)

        results = self.cache.get_wind_data_batch(coords)
        for coord in coords:
            self.assertEqual(results[coord], (5.0, 2.0))

    def test_clear_expired_data(self):
        """Test that clear_expired_data removes only expired entries."""
        # Store valid data
        self.cache.store_wind_data(35.7, 51.4, 1000, int(time.time()), 5.0, 2.0)
        # Store expired data
        self.cache._set_ttl("wind", 1)
        expired_timestamp = int(time.time()) - 2
        self.cache.store_wind_data(
            35.8, 51.5, 1500, expired_timestamp, 3.0, 1.0, ttl=1
        )

        # Before clearing
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["valid_entries"], 1)

        # Clear expired
        self.cache.clear_expired_data()

        # After clearing
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_entries"], 1)
        self.assertEqual(stats["valid_entries"], 1)

    def test_export_to_dataframe(self):
        """Test exporting cache data to pandas DataFrame."""
        # Skip this test if pandas is not available
        try:
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("pandas not available")

        self.cache.store_wind_data(35.7, 51.4, 1000, int(time.time()), 5.0, 2.0)
        self.cache.store_wind_data(35.8, 51.5, 1500, int(time.time()), 3.0, 1.0)

        df = self.cache.export_to_dataframe()
        self.assertEqual(len(df), 2)
        self.assertIn("lat", df.columns)
        self.assertIn("u_component", df.columns)

    def test_custom_ttl(self):
        """Test setting custom TTL."""
        self.cache._set_ttl("wind", 3600)  # 1 hour
        ttl = self.cache._get_ttl("wind")
        self.assertEqual(ttl, 3600)


if __name__ == "__main__":
    unittest.main()
