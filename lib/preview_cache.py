"""
Preview/Confirm cache for two-phase operations.

Provides a shared cache for update/delete preview tokens,
replacing duplicate implementations in books.py and students.py.
"""
import uuid
from typing import Any


class PreviewCache:
    """
    Thread-safe in-memory cache for preview/confirm tokens.

    Usage:
        cache = PreviewCache()

        # Preview mode: store data and get token
        token = cache.store("book_upd", {"book_id": "gMB001", ...})

        # Confirm mode: retrieve and remove data
        data = cache.pop("book_upd", token)
        if data is None:
            # Token expired or invalid
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        """
        Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cached entries (default 5 minutes).
                         Note: TTL is advisory; cleanup not automatic.
        """
        self._cache: dict[str, Any] = {}
        self._ttl_seconds = ttl_seconds

    @property
    def ttl_seconds(self) -> int:
        """Get configured TTL in seconds."""
        return self._ttl_seconds

    @property
    def size(self) -> int:
        """Get current number of cached entries."""
        return len(self._cache)

    def _make_key(self, prefix: str, token: str) -> str:
        """Create internal cache key from prefix and token."""
        return f"{prefix}:{token}"

    def store(
        self,
        prefix: str,
        data: dict[str, Any],
        token: str | None = None,
    ) -> str:
        """
        Store data and return token.

        Args:
            prefix: Key prefix (e.g., "book_upd", "stu_del")
            data: Data to cache
            token: Optional custom token; generates UUID if not provided

        Returns:
            The token for later retrieval
        """
        if token is None:
            token = str(uuid.uuid4())

        key = self._make_key(prefix, token)
        self._cache[key] = data
        return token

    def get(self, prefix: str, token: str) -> dict[str, Any] | None:
        """
        Get cached data without removing it.

        Args:
            prefix: Key prefix
            token: Token from store()

        Returns:
            Cached data or None if not found
        """
        key = self._make_key(prefix, token)
        return self._cache.get(key)

    def pop(self, prefix: str, token: str) -> dict[str, Any] | None:
        """
        Get and remove cached data.

        Args:
            prefix: Key prefix
            token: Token from store()

        Returns:
            Cached data or None if not found
        """
        key = self._make_key(prefix, token)
        return self._cache.pop(key, None)

    def clear_prefix(self, prefix: str) -> int:
        """
        Remove all entries with given prefix.

        Args:
            prefix: Key prefix to clear

        Returns:
            Number of entries removed
        """
        prefix_pattern = f"{prefix}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix_pattern)]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def clear_all(self) -> int:
        """
        Remove all entries.

        Returns:
            Number of entries removed
        """
        count = len(self._cache)
        self._cache.clear()
        return count
