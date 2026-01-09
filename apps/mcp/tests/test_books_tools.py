"""
Tests for books tools in MCP server.
Tests books_find, books_get, books_filter, books_create, books_update, books_delete, books_list

Updated for direct Google Sheets API architecture.
"""
import pytest
from unittest.mock import patch, MagicMock

# Import the tool functions
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    async def test_find_book_success(self, mock_sheets_client, mock_handler_responses):
        """Should find books matching query"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_find", return_value=mock_handler_responses["books.find"]):
            result = await books_find(query="青チャート")
            assert result.get("ok") is True
            assert "candidates" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_find_requires_query(self):
        """Should return error when query is missing"""
        result = await books_find(query=None)
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_find_empty_query(self):
        """Should return error when query is empty"""
        result = await books_find(query="")
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_find_with_dict_input(self, mock_sheets_client, mock_handler_responses):
        """Should accept dict with query key"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_find", return_value=mock_handler_responses["books.find"]):
            result = await books_find(query={"query": "青チャート"})
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_find_handles_error(self, mock_sheets_client):
        """Should handle handler errors gracefully"""
        error_response = {"ok": False, "op": "books.find", "error": {"code": "NOT_FOUND", "message": "No books found"}}
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_find", return_value=error_response):
            result = await books_find(query="NonExistent")
            assert result.get("ok") is False


class TestBooksGet:
    """Tests for books_get tool"""

    @pytest.mark.asyncio
    async def test_get_single_book(self, mock_sheets_client, mock_handler_responses):
        """Should get single book by ID"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_get", return_value=mock_handler_responses["books.get"]):
            result = await books_get(book_id="gMB001")
            assert result.get("ok") is True
            assert "book" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_get_multiple_books(self, mock_sheets_client, mock_handler_responses):
        """Should get multiple books by IDs"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_get", return_value={"ok": True, "op": "books.get", "data": {"books": []}}):
            result = await books_get(book_ids=["gMB001", "gMB002"])
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_get_requires_id(self):
        """Should return error when no ID provided"""
        result = await books_get()
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_handles_not_found(self, mock_sheets_client):
        """Should handle book not found error"""
        error_response = {"ok": False, "op": "books.get", "error": {"code": "NOT_FOUND", "message": "Book not found"}}
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_get", return_value=error_response):
            result = await books_get(book_id="nonexistent")
            assert result.get("ok") is False


class TestBooksFilter:
    """Tests for books_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_subject(self, mock_sheets_client, mock_handler_responses):
        """Should filter books by subject"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_filter", return_value=mock_handler_responses["books.filter"]):
            result = await books_filter(where={"教科": "数学"})
            assert result.get("ok") is True
            assert "books" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_filter_by_contains(self, mock_sheets_client, mock_handler_responses):
        """Should filter books by partial match"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_filter", return_value=mock_handler_responses["books.filter"]):
            result = await books_filter(contains={"参考書名": "チャート"})
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_filter_with_limit(self, mock_sheets_client, mock_handler_responses):
        """Should respect limit parameter"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_filter", return_value=mock_handler_responses["books.filter"]):
            result = await books_filter(limit=10)
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_filter_no_params_returns_all(self, mock_sheets_client, mock_handler_responses):
        """Should return all books when no filter specified"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_filter", return_value=mock_handler_responses["books.filter"]):
            result = await books_filter()
            assert result.get("ok") is True


class TestBooksCreate:
    """Tests for books_create tool"""

    @pytest.mark.asyncio
    async def test_create_book(self, mock_sheets_client, mock_handler_responses):
        """Should create new book"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_create", return_value=mock_handler_responses["books.create"]):
            result = await books_create(title="New Book", subject="数学")
            assert result.get("ok") is True
            assert result.get("data", {}).get("id") is not None

    @pytest.mark.asyncio
    async def test_create_with_chapters(self, mock_sheets_client, mock_handler_responses):
        """Should create book with chapter information"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_create", return_value=mock_handler_responses["books.create"]):
            chapters = [{"title": "Chapter 1", "range": {"start": 1, "end": 50}}]
            result = await books_create(title="New Book", subject="数学", chapters=chapters)
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_create_with_custom_prefix(self, mock_sheets_client, mock_handler_responses):
        """Should use custom ID prefix"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_create", return_value=mock_handler_responses["books.create"]):
            result = await books_create(title="Custom", subject="英語", id_prefix="custom")
            assert result.get("ok") is True


class TestBooksUpdate:
    """Tests for books_update tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_update_preview(self, mock_sheets_client, mock_handler_responses):
        """Should return preview without confirm_token"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_update", return_value=mock_handler_responses["books.update_preview"]):
            result = await books_update(book_id="gMB001", updates={"参考書名": "Updated"})
            data = result.get("data", {})
            assert data.get("requires_confirmation") is True
            assert "confirm_token" in data

    @pytest.mark.asyncio
    async def test_update_confirm(self, mock_sheets_client, mock_handler_responses):
        """Should apply update with valid confirm_token"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_update", return_value=mock_handler_responses["books.update_confirm"]):
            result = await books_update(book_id="gMB001", confirm_token="valid-token")
            assert result.get("ok") is True
            assert result.get("data", {}).get("updated") is True

    @pytest.mark.asyncio
    async def test_update_requires_book_id(self):
        """Should require book_id"""
        result = await books_update(book_id=None, updates={"title": "New"})
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_invalid_token(self, mock_sheets_client):
        """Should handle invalid confirm_token"""
        error_response = {"ok": False, "op": "books.update", "error": {"code": "CONFIRM_EXPIRED", "message": "Token expired"}}
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_update", return_value=error_response):
            result = await books_update(book_id="gMB001", confirm_token="invalid")
            assert result.get("ok") is False


class TestBooksDelete:
    """Tests for books_delete tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_delete_preview(self, mock_sheets_client, mock_handler_responses):
        """Should return preview without confirm_token"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_delete", return_value=mock_handler_responses["books.delete_preview"]):
            result = await books_delete(book_id="gMB001")
            data = result.get("data", {})
            assert data.get("requires_confirmation") is True
            assert "confirm_token" in data

    @pytest.mark.asyncio
    async def test_delete_confirm(self, mock_sheets_client, mock_handler_responses):
        """Should delete with valid confirm_token"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_delete", return_value=mock_handler_responses["books.delete_confirm"]):
            result = await books_delete(book_id="gMB001", confirm_token="valid-token")
            assert result.get("ok") is True
            assert result.get("data", {}).get("deleted") is True

    @pytest.mark.asyncio
    async def test_delete_requires_book_id(self):
        """Should require book_id"""
        result = await books_delete(book_id=None)
        assert result.get("ok") is False
        assert "error" in result


class TestBooksList:
    """Tests for books_list tool"""

    @pytest.mark.asyncio
    async def test_list_all_books(self, mock_sheets_client, mock_handler_responses):
        """Should list all books"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_list", return_value=mock_handler_responses["books.list"]):
            result = await books_list()
            assert result.get("ok") is True
            assert "books" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_list_with_limit(self, mock_sheets_client, mock_handler_responses):
        """Should respect limit parameter"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("handlers.books.books_list", return_value=mock_handler_responses["books.list"]):
            result = await books_list(limit=5)
            assert result.get("ok") is True
