"""
Management command to display cache statistics.

This command shows Redis cache statistics including memory usage,
number of keys, and cache patterns.
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Display cache statistics and information"

    def handle(self, *args, **options):
        """Display cache statistics."""
        self.stdout.write(self.style.SUCCESS("Cache Statistics"))
        self.stdout.write("=" * 50)

        # Check if Redis backend is available
        if not hasattr(cache, "delete_pattern"):
            self.stdout.write(
                self.style.WARNING(
                    "Redis backend not available. Using fallback cache (DummyCache or similar)."
                )
            )
            self.stdout.write("Cache statistics are only available with Redis backend.")
            return

        # Get Redis client
        try:
            redis_client = cache._cache.get_client()

            # Get basic info
            info = redis_client.info()
            memory_info = redis_client.info("memory")

            # Display memory usage
            used_memory = memory_info.get("used_memory_human", "N/A")
            self.stdout.write(f"\nMemory Usage: {used_memory}")

            # Get number of keys by pattern
            patterns = {
                "Meal keys": "meal:*",
                "Meals keys": "meals:*",
                "Annual meal keys": "annual_meals:*",
                "Types menu keys": "types_menu:*",
                "JSON API keys": "json_api*",
                "School page keys": "school_page:*",
            }

            self.stdout.write("\nKey Counts by Pattern:")
            self.stdout.write("-" * 50)

            total_keys = 0
            for label, pattern in patterns.items():
                keys = list(redis_client.scan_iter(match=pattern))
                count = len(keys)
                total_keys += count
                self.stdout.write(f"  {label:25s}: {count:5d}")

            self.stdout.write("-" * 50)
            self.stdout.write(f"  {'Total cached keys':25s}: {total_keys:5d}")

            # Display cache backend info
            self.stdout.write("\nCache Backend Configuration:")
            self.stdout.write("-" * 50)
            self.stdout.write(f"  Backend: {cache.__class__.__name__}")

            # Get database info
            db_size = redis_client.dbsize()
            self.stdout.write(f"  Total keys in DB: {db_size}")

            # Hit rate (if available)
            keyspace_hits = info.get("keyspace_hits", 0)
            keyspace_misses = info.get("keyspace_misses", 0)
            total_ops = keyspace_hits + keyspace_misses

            if total_ops > 0:
                hit_rate = (keyspace_hits / total_ops) * 100
                self.stdout.write(f"\n  Cache Hit Rate: {hit_rate:.2f}%")
                self.stdout.write(f"  Cache Hits: {keyspace_hits}")
                self.stdout.write(f"  Cache Misses: {keyspace_misses}")

            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(
                self.style.SUCCESS("✓ Cache statistics displayed successfully")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error retrieving cache statistics: {e}")
            )
