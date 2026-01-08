"""
Pytest configuration and fixtures for MCP server tests
"""
import os
import pytest
from typing import Any
from unittest.mock import patch

# Set test environment variables before importing server
os.environ.setdefault("EXEC_URL", "https://script.google.com/macros/s/TEST_DEPLOY_ID/exec")


@pytest.fixture
def mock_exec_url(monkeypatch):
    """Set EXEC_URL environment variable for tests"""
    monkeypatch.setenv("EXEC_URL", "https://script.google.com/macros/s/TEST/exec")


@pytest.fixture
def mock_hmac_secret(monkeypatch):
    """Set HMAC secret for authentication tests"""
    monkeypatch.setenv("MCP_HMAC_SECRET", "test-secret-key")
    monkeypatch.setenv("MCP_HMAC_REQUIRED", "true")


@pytest.fixture
def gas_responses():
    """Predefined GAS API response templates"""
    return {
        "books.find": {
            "ok": True,
            "op": "books.find",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "top": {"id": "gMB001", "title": "Test Book", "subject": "Math", "score": 1.0},
                "candidates": [
                    {"id": "gMB001", "title": "Test Book", "subject": "Math", "score": 1.0}
                ],
            },
        },
        "books.get": {
            "ok": True,
            "op": "books.get",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "book": {
                    "id": "gMB001",
                    "title": "Test Book",
                    "subject": "Math",
                    "monthly_goal": "1 hour/day",
                    "unit_load": 2,
                    "chapters": [
                        {"idx": 1, "title": "Chapter 1", "range": {"start": 1, "end": 10}}
                    ],
                }
            },
        },
        "books.filter": {
            "ok": True,
            "op": "books.filter",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "count": 1,
                "books": [{"id": "gMB001", "title": "Test Book", "subject": "Math"}],
            },
        },
        "books.create": {
            "ok": True,
            "op": "books.create",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"id": "gMB002", "created": True},
        },
        "books.update_preview": {
            "ok": True,
            "op": "books.update",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "confirm_token": "test-token-123",
                "preview": {"title": {"old": "Old Title", "new": "New Title"}},
            },
        },
        "books.update_confirm": {
            "ok": True,
            "op": "books.update",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"updated": True},
        },
        "books.delete_preview": {
            "ok": True,
            "op": "books.delete",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"confirm_token": "delete-token-456", "rows_to_delete": 2},
        },
        "books.delete_confirm": {
            "ok": True,
            "op": "books.delete",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"deleted": True},
        },
        "students.list": {
            "ok": True,
            "op": "students.list",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "count": 2,
                "students": [
                    {"id": "S001", "name": "Test Student 1", "grade": "高1"},
                    {"id": "S002", "name": "Test Student 2", "grade": "高2"},
                ],
            },
        },
        "planner.ids_list": {
            "ok": True,
            "op": "planner.ids_list",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "count": 2,
                "items": [
                    {"row": 4, "raw_code": "258gMB001", "month_code": 258, "book_id": "gMB001", "subject": "Math", "title": "", "guideline_note": ""},
                    {"row": 5, "raw_code": "258gEC001", "month_code": 258, "book_id": "gEC001", "subject": "English", "title": "", "guideline_note": ""},
                ],
            },
        },
        "planner.dates.get": {
            "ok": True,
            "op": "planner.dates.get",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"week_starts": ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25", ""]},
        },
        "planner.metrics.get": {
            "ok": True,
            "op": "planner.metrics.get",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "weeks": [
                    {
                        "week_index": 1,
                        "items": [
                            {"row": 4, "weekly_minutes": 120, "unit_load": 2, "guideline_amount": 240},
                        ],
                    }
                ]
            },
        },
        "planner.plan.get": {
            "ok": True,
            "op": "planner.plan.get",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {
                "weeks": [
                    {
                        "week_index": 1,
                        "items": [{"row": 4, "plan_text": "p1-10"}],
                    }
                ]
            },
        },
        "planner.plan.set": {
            "ok": True,
            "op": "planner.plan.set",
            "meta": {"ts": "2025-01-01T00:00:00Z"},
            "data": {"updated": True, "results": [{"ok": True, "cell": "H4"}]},
        },
        "error": {
            "ok": False,
            "op": "error",
            "error": {"code": "TEST_ERROR", "message": "Test error message"},
        },
    }


@pytest.fixture
def clear_preview_cache():
    """Clear the preview cache before and after tests"""
    from server import _PREVIEW_CACHE
    _PREVIEW_CACHE.clear()
    yield
    _PREVIEW_CACHE.clear()


@pytest.fixture
def mock_gas_api(httpx_mock, gas_responses):
    """
    Fixture to mock GAS API responses for tool tests.

    Usage:
        def test_books_find(mock_gas_api):
            mock_gas_api("books.find")
            # ... test code that calls GAS API
    """
    def _mock_api(response_key: str, method: str = "GET"):
        response = gas_responses.get(response_key, gas_responses["error"])
        if method.upper() == "GET":
            httpx_mock.add_response(json=response)
        else:
            httpx_mock.add_response(json=response)
    return _mock_api


@pytest.fixture
def mock_gas_sequence(httpx_mock, gas_responses):
    """
    Fixture to mock a sequence of GAS API responses.

    Usage:
        def test_two_phase_update(mock_gas_sequence):
            mock_gas_sequence(["books.update_preview", "books.update_confirm"])
            # ... test code that calls GAS API twice
    """
    def _mock_sequence(response_keys: list[str]):
        for key in response_keys:
            response = gas_responses.get(key, gas_responses["error"])
            httpx_mock.add_response(json=response)
    return _mock_sequence


@pytest.fixture
def mock_gas_error(httpx_mock):
    """
    Fixture to mock GAS API error response.

    Usage:
        def test_error_handling(mock_gas_error):
            mock_gas_error("NOT_FOUND", "Book not found")
            # ... test code
    """
    def _mock_error(code: str, message: str, op: str = "error"):
        httpx_mock.add_response(json={
            "ok": False,
            "op": op,
            "error": {"code": code, "message": message}
        })
    return _mock_error
