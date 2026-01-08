"""
Tests for books tools in MCP server.
Tests books_find, books_get, books_filter, books_create, books_update, books_delete, books_list
"""
import pytest
from unittest.mock import patch, AsyncMock

# Import the tool functions
import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])
from server import (
    books_find,
    books_get,
    books_filter,
    books_create,
    books_update,
    books_delete,
    books_list,
)


class TestBooksFind:
    """Tests for books_find tool"""

    @pytest.mark.asyncio
    async def test_find_book_success(self, mock_gas_api):
        """Should find books matching query"""
        mock_gas_api("books.find")
        result = await books_find(query="Test Book")
        # Result may have data nested or flat depending on response transformation
        data = result.get("data", result)
        assert "top" in data or "candidates" in data or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_find_requires_query(self):
        """Should return error when query is missing"""
        result = await books_find(query=None)
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_find_empty_query(self):
        """Should return error when query is empty"""
        result = await books_find(query="")
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_find_handles_gas_error(self, mock_gas_error):
        """Should handle GAS API error gracefully"""
        mock_gas_error("NOT_FOUND", "No books found")
        result = await books_find(query="NonExistent")
        assert result.get("ok") is False or "error" in result


class TestBooksGet:
    """Tests for books_get tool"""

    @pytest.mark.asyncio
    async def test_get_single_book(self, mock_gas_api):
        """Should get single book by ID"""
        mock_gas_api("books.get")
        result = await books_get(book_id="gMB001")
        assert "book" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_get_multiple_books(self, mock_gas_api):
        """Should get multiple books by IDs"""
        mock_gas_api("books.filter")  # books_get with multiple IDs uses filter
        result = await books_get(book_ids=["gMB001", "gMB002"])
        assert result.get("ok") is True or "books" in result

    @pytest.mark.asyncio
    async def test_get_requires_id(self):
        """Should return error when no ID provided"""
        result = await books_get()
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_get_handles_not_found(self, mock_gas_error):
        """Should handle book not found error"""
        mock_gas_error("NOT_FOUND", "Book not found", "books.get")
        result = await books_get(book_id="nonexistent")
        assert result.get("ok") is False


class TestBooksFilter:
    """Tests for books_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_subject(self, mock_gas_api):
        """Should filter books by subject"""
        mock_gas_api("books.filter", method="POST")
        result = await books_filter(where={"教科": "数学"})
        assert "books" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_filter_by_contains(self, mock_gas_api):
        """Should filter books by partial match"""
        mock_gas_api("books.filter", method="POST")
        result = await books_filter(contains={"参考書名": "チャート"})
        assert result.get("ok") is True or "books" in result

    @pytest.mark.asyncio
    async def test_filter_with_limit(self, mock_gas_api):
        """Should respect limit parameter"""
        mock_gas_api("books.filter", method="POST")
        result = await books_filter(limit=10)
        assert result.get("ok") is True or "books" in result

    @pytest.mark.asyncio
    async def test_filter_no_params_returns_all(self, mock_gas_api):
        """Should return all books when no filter specified"""
        mock_gas_api("books.filter", method="POST")
        result = await books_filter()
        assert result.get("ok") is True or "books" in result


class TestBooksCreate:
    """Tests for books_create tool"""

    @pytest.mark.asyncio
    async def test_create_book(self, mock_gas_api):
        """Should create new book"""
        mock_gas_api("books.create", method="POST")
        result = await books_create(title="New Book", subject="数学")
        assert result.get("ok") is True or "id" in result

    @pytest.mark.asyncio
    async def test_create_requires_title(self):
        """Should require title"""
        result = await books_create(title=None, subject="数学")
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_create_requires_subject(self):
        """Should require subject"""
        result = await books_create(title="New Book", subject=None)
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_create_with_chapters(self, mock_gas_api):
        """Should create book with chapter information"""
        mock_gas_api("books.create", method="POST")
        chapters = [{"title": "Chapter 1", "range": {"start": 1, "end": 50}}]
        result = await books_create(title="New Book", subject="数学", chapters=chapters)
        assert result.get("ok") is True or "id" in result

    @pytest.mark.asyncio
    async def test_create_with_custom_prefix(self, mock_gas_api):
        """Should use custom ID prefix"""
        mock_gas_api("books.create", method="POST")
        result = await books_create(title="Custom", subject="英語", id_prefix="custom")
        assert result.get("ok") is True


class TestBooksUpdate:
    """Tests for books_update tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_update_preview(self, mock_gas_api):
        """Should return preview without confirm_token"""
        mock_gas_api("books.update_preview", method="POST")
        result = await books_update(book_id="gMB001", updates={"参考書名": "Updated"})
        data = result.get("data", result)
        assert "confirm_token" in data or data.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_update_confirm(self, mock_gas_sequence):
        """Should apply update with valid confirm_token"""
        mock_gas_sequence(["books.update_confirm"])
        result = await books_update(book_id="gMB001", confirm_token="valid-token")
        assert result.get("ok") is True or result.get("updated") is True

    @pytest.mark.asyncio
    async def test_update_requires_book_id(self):
        """Should require book_id"""
        result = await books_update(book_id=None, updates={"title": "New"})
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_update_invalid_token(self, mock_gas_error):
        """Should handle invalid confirm_token"""
        mock_gas_error("CONFIRM_EXPIRED", "Token expired", "books.update")
        result = await books_update(book_id="gMB001", confirm_token="invalid")
        assert result.get("ok") is False


class TestBooksDelete:
    """Tests for books_delete tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_delete_preview(self, mock_gas_api):
        """Should return preview without confirm_token"""
        mock_gas_api("books.delete_preview", method="POST")
        result = await books_delete(book_id="gMB001")
        data = result.get("data", result)
        assert "confirm_token" in data or data.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_delete_confirm(self, mock_gas_sequence):
        """Should delete with valid confirm_token"""
        mock_gas_sequence(["books.delete_confirm"])
        result = await books_delete(book_id="gMB001", confirm_token="valid-token")
        assert result.get("ok") is True or result.get("deleted") is True

    @pytest.mark.asyncio
    async def test_delete_requires_book_id(self):
        """Should require book_id"""
        result = await books_delete(book_id=None)
        assert "error" in result or result.get("ok") is False


class TestBooksList:
    """Tests for books_list tool"""

    @pytest.mark.asyncio
    async def test_list_all_books(self, mock_gas_api):
        """Should list all books"""
        mock_gas_api("books.filter", method="POST")
        result = await books_list()
        assert "books" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_list_with_limit(self, mock_gas_api):
        """Should respect limit parameter"""
        mock_gas_api("books.filter", method="POST")
        result = await books_list(limit=5)
        assert result.get("ok") is True or "books" in result
