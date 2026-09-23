from django.core.cache import cache
from django.test import override_settings

from contacts.rate_limit import is_rate_limited

# The test settings use DummyCache, which never actually stores anything, so
# rate-limiting can't be exercised without a real backend for these tests (#292).
LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class TestIsRateLimited:
    def setup_method(self):
        cache.clear()

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_allows_hits_within_the_limit(self):
        for _ in range(3):
            assert is_rate_limited("test-key", limit=3, window_seconds=60) is False

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_blocks_once_the_limit_is_exceeded(self):
        for _ in range(3):
            is_rate_limited("test-key", limit=3, window_seconds=60)

        assert is_rate_limited("test-key", limit=3, window_seconds=60) is True

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_keys_are_independent(self):
        for _ in range(3):
            is_rate_limited("key-a", limit=3, window_seconds=60)

        assert is_rate_limited("key-b", limit=3, window_seconds=60) is False

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_window_resets_after_expiry(self):
        for _ in range(3):
            is_rate_limited("test-key", limit=3, window_seconds=60)
        assert is_rate_limited("test-key", limit=3, window_seconds=60) is True

        cache.delete("test-key")  # simulate the window expiring

        assert is_rate_limited("test-key", limit=3, window_seconds=60) is False

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_handles_key_expiring_between_add_and_incr(self, monkeypatch):
        # Race guard: add() sees the key present (so it returns False), but the key
        # expires before incr() runs. Only reproducible on demand, hence the monkeypatch.
        cache.set("test-key", 1, 60)

        def raise_value_error(key):
            raise ValueError

        monkeypatch.setattr(cache, "incr", raise_value_error)

        assert is_rate_limited("test-key", limit=3, window_seconds=60) is False
