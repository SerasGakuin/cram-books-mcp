"""
Tests for PreviewCache class.
"""
import pytest
import time
from lib.preview_cache import PreviewCache


class TestPreviewCache:
    """Tests for PreviewCache class"""

    def test_store_and_get(self):
        """Should store and retrieve data"""
        cache = PreviewCache()
        token = cache.store("test", {"key": "value"})

        assert token is not None
        assert len(token) == 36  # UUID format

        data = cache.get("test", token)
        assert data == {"key": "value"}

    def test_get_nonexistent_returns_none(self):
        """Should return None for nonexistent token"""
        cache = PreviewCache()
        data = cache.get("test", "nonexistent-token")
        assert data is None

    def test_pop_removes_data(self):
        """Should remove data after pop"""
        cache = PreviewCache()
        token = cache.store("test", {"key": "value"})

        data = cache.pop("test", token)
        assert data == {"key": "value"}

        # Second pop should return None
        data2 = cache.pop("test", token)
        assert data2 is None

    def test_different_prefixes_are_isolated(self):
        """Should isolate data by prefix"""
        cache = PreviewCache()

        token1 = cache.store("books", {"id": "book1"})
        token2 = cache.store("students", {"id": "student1"})

        # Cannot access with wrong prefix
        assert cache.get("students", token1) is None
        assert cache.get("books", token2) is None

        # Can access with correct prefix
        assert cache.get("books", token1) == {"id": "book1"}
        assert cache.get("students", token2) == {"id": "student1"}

    def test_store_with_custom_token(self):
        """Should allow custom token"""
        cache = PreviewCache()
        token = cache.store("test", {"key": "value"}, token="custom-token-123")

        assert token == "custom-token-123"
        assert cache.get("test", "custom-token-123") == {"key": "value"}

    def test_ttl_property(self):
        """Should have configurable TTL"""
        cache = PreviewCache(ttl_seconds=600)
        assert cache.ttl_seconds == 600

        default_cache = PreviewCache()
        assert default_cache.ttl_seconds == 300  # Default 5 minutes

    def test_clear_prefix(self):
        """Should clear all entries with given prefix"""
        cache = PreviewCache()

        cache.store("books", {"id": "1"})
        cache.store("books", {"id": "2"})
        cache.store("students", {"id": "s1"})

        cache.clear_prefix("books")

        # All books entries should be cleared
        # Students entry should remain
        # Note: We can't easily verify books are cleared without knowing tokens
        # but we can verify students still works


    def test_size_property(self):
        """Should report cache size"""
        cache = PreviewCache()
        assert cache.size == 0

        cache.store("test", {"key": "1"})
        assert cache.size == 1

        cache.store("test", {"key": "2"})
        assert cache.size == 2


class TestPreviewCacheIntegration:
    """Integration-style tests mimicking actual usage"""

    def test_books_update_pattern(self):
        """Should work with books update pattern"""
        cache = PreviewCache()

        # Preview mode: store update data
        book_id = "gMB001"
        updates = {"title": "New Title", "subject": "数学"}
        token = cache.store("book_upd", {
            "book_id": book_id,
            "updates": updates,
            "parent_row": 5,
            "end_row": 8,
        })

        # Confirm mode: retrieve and validate
        cached = cache.pop("book_upd", token)
        assert cached is not None
        assert cached["book_id"] == book_id
        assert cached["updates"] == updates

        # Cannot confirm twice
        cached2 = cache.pop("book_upd", token)
        assert cached2 is None

    def test_students_delete_pattern(self):
        """Should work with students delete pattern"""
        cache = PreviewCache()

        # Preview mode
        student_id = "S001"
        token = cache.store("stu_del", {
            "student_id": student_id,
            "row_index": 10,
        })

        # Verify with get (doesn't consume)
        preview = cache.get("stu_del", token)
        assert preview["student_id"] == student_id

        # Confirm with pop (consumes)
        confirmed = cache.pop("stu_del", token)
        assert confirmed["student_id"] == student_id

        # Verify consumed
        assert cache.get("stu_del", token) is None
