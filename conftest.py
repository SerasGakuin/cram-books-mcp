"""
Pytest configuration and fixtures for MCP server tests.

Updated for direct Google Sheets API architecture (no GAS WebApp).
"""
import os
import pytest
from typing import Any
from unittest.mock import MagicMock, patch

# Set test environment variables before importing anything
os.environ.setdefault("GOOGLE_CREDENTIALS_JSON", '{"type": "service_account", "project_id": "test"}')


# ========== Response Assertion Helpers ==========

class ResponseAssertions:
    """Helper class for asserting API response structures."""

    @staticmethod
    def assert_success(response: dict, op: str | None = None) -> dict:
        """Assert response is successful and return data.

        Args:
            response: The response dict to check
            op: Optional operation name to verify

        Returns:
            The data dict from the response
        """
        assert response.get("ok") is True, f"Expected success, got: {response}"
        if op:
            assert response.get("op") == op, f"Expected op={op}, got {response.get('op')}"
        return response.get("data", {})

    @staticmethod
    def assert_error(response: dict, code: str, op: str | None = None) -> dict:
        """Assert response is an error with given code.

        Args:
            response: The response dict to check
            code: Expected error code
            op: Optional operation name to verify

        Returns:
            The error dict from the response
        """
        assert response.get("ok") is False, f"Expected error, got success: {response}"
        assert response.get("error", {}).get("code") == code, \
            f"Expected error code {code}, got {response.get('error', {}).get('code')}"
        if op:
            assert response.get("op") == op, f"Expected op={op}, got {response.get('op')}"
        return response.get("error", {})


@pytest.fixture
def assertions():
    """Fixture providing response assertion helpers."""
    return ResponseAssertions()


@pytest.fixture
def mock_sheets_client():
    """
    Mock SheetsClient for unit tests.
    Returns a MagicMock that can be configured per test.
    """
    mock = MagicMock()
    mock.get_all_values.return_value = []
    mock.get_range.return_value = []
    mock.open_by_id.return_value = MagicMock()
    return mock


@pytest.fixture
def sample_books_data():
    """Sample books data for testing"""
    return [
        ["参考書ID", "参考書名", "教科", "単位当たり処理量", "月間目標", "章立て", "章の名前", "章のはじめ", "章の終わり", "番号の数え方"],
        ["gMB001", "青チャート数学IA", "数学", "2", "1時間/日", "1", "第1章", "1", "50", "問"],
        ["gMB002", "青チャート数学IIB", "数学", "2", "1時間/日", "1", "第1章", "1", "60", "問"],
        ["gEC001", "英語長文問題集", "英語", "1", "30分/日", "1", "Chapter 1", "1", "20", "問"],
    ]


@pytest.fixture
def sample_students_data():
    """Sample students data for testing"""
    return [
        ["", "Comiru生徒番号", "姓", "名", "名前", "学年", "Status", "スプレッドシート", "スピードプランナーID", "ドキュメント", "タグ"],
        ["S001", "C001", "山田", "太郎", "山田太郎", "高1", "在塾", "https://docs.google.com/spreadsheets/d/sheet1", "", "", ""],
        ["S002", "C002", "鈴木", "花子", "鈴木花子", "高2", "在塾", "https://docs.google.com/spreadsheets/d/sheet2", "", "", ""],
        ["S003", "C003", "田中", "次郎", "田中次郎", "高3", "退塾", "https://docs.google.com/spreadsheets/d/sheet3", "", "", ""],
    ]


@pytest.fixture
def sample_planner_data():
    """Sample planner weekly data for testing"""
    return {
        "ids": [
            ["", "", "", ""],  # Row 1-3 are headers
            ["", "", "", ""],
            ["", "", "", ""],
            ["258gMB001", "25", "8", "gMB001", "数学", "青チャート", "週2時間"],  # Row 4
            ["258gEC001", "25", "8", "gEC001", "英語", "英語長文", "週1時間"],  # Row 5
        ],
        "dates": [
            ["2025-08-04", "", "", "", "", "", "", "", "", "", "", "2025-08-11", "", "", "", "", "", "", "", "2025-08-18", "", "", "", "", "", "", "", "2025-08-25", "", "", "", "", "", "", "", ""],
        ],
        "metrics": [
            ["", "", "", "", "120", "2", "240", "", "", "", "", "", "", "100", "2", "200", "", "", "", "", "", "", "80", "2", "160", "", "", "", "", "", "", "0", "2", "0", "", "", "", "", ""],  # Row 4
            ["", "", "", "", "60", "1", "60", "", "", "", "", "", "", "50", "1", "50", "", "", "", "", "", "", "40", "1", "40", "", "", "", "", "", "", "0", "1", "0", "", "", "", "", ""],  # Row 5
        ],
    }


@pytest.fixture
def mock_handler_responses():
    """Predefined handler response templates"""
    return {
        "books.find": {
            "ok": True,
            "op": "books.find",
            "data": {
                "query": "青チャート",
                "top": {"book_id": "gMB001", "title": "青チャート数学IA", "subject": "数学", "score": 1.0},
                "candidates": [
                    {"book_id": "gMB001", "title": "青チャート数学IA", "subject": "数学", "score": 1.0},
                    {"book_id": "gMB002", "title": "青チャート数学IIB", "subject": "数学", "score": 0.9},
                ],
                "confidence": 1.0,
            },
        },
        "books.get": {
            "ok": True,
            "op": "books.get",
            "data": {
                "book": {
                    "id": "gMB001",
                    "title": "青チャート数学IA",
                    "subject": "数学",
                    "unit_load": 2,
                    "monthly_goal": "1時間/日",
                    "structure": {
                        "chapters": [{"idx": 1, "title": "第1章", "range": {"start": 1, "end": 50}}]
                    },
                }
            },
        },
        "books.filter": {
            "ok": True,
            "op": "books.filter",
            "data": {
                "count": 2,
                "books": [
                    {"id": "gMB001", "title": "青チャート数学IA", "subject": "数学"},
                    {"id": "gMB002", "title": "青チャート数学IIB", "subject": "数学"},
                ],
            },
        },
        "books.list": {
            "ok": True,
            "op": "books.list",
            "data": {
                "count": 3,
                "books": [
                    {"id": "gMB001", "subject": "数学", "title": "青チャート数学IA"},
                    {"id": "gMB002", "subject": "数学", "title": "青チャート数学IIB"},
                    {"id": "gEC001", "subject": "英語", "title": "英語長文問題集"},
                ],
            },
        },
        "books.create": {
            "ok": True,
            "op": "books.create",
            "data": {"id": "gMB003", "created": True},
        },
        "books.update_preview": {
            "ok": True,
            "op": "books.update",
            "data": {
                "requires_confirmation": True,
                "preview": {"diffs": {"参考書名": {"from": "Old Title", "to": "New Title"}}},
                "confirm_token": "test-token-123",
                "expires_in_seconds": 300,
            },
        },
        "books.update_confirm": {
            "ok": True,
            "op": "books.update",
            "data": {"updated": True},
        },
        "books.delete_preview": {
            "ok": True,
            "op": "books.delete",
            "data": {
                "requires_confirmation": True,
                "preview": {"rows_to_delete": 2},
                "confirm_token": "delete-token-456",
                "expires_in_seconds": 300,
            },
        },
        "books.delete_confirm": {
            "ok": True,
            "op": "books.delete",
            "data": {"deleted": True},
        },
        "students.list": {
            "ok": True,
            "op": "students.list",
            "data": {
                "count": 2,
                "students": [
                    {"id": "S001", "name": "山田太郎", "grade": "高1", "status": "在塾"},
                    {"id": "S002", "name": "鈴木花子", "grade": "高2", "status": "在塾"},
                ],
            },
        },
        "students.filter": {
            "ok": True,
            "op": "students.filter",
            "data": {
                "count": 2,
                "students": [
                    {"id": "S001", "name": "山田太郎", "grade": "高1", "status": "在塾"},
                    {"id": "S002", "name": "鈴木花子", "grade": "高2", "status": "在塾"},
                ],
            },
        },
        "planner.ids_list": {
            "ok": True,
            "op": "planner.ids_list",
            "data": {
                "count": 2,
                "items": [
                    {"row": 4, "raw_code": "258gMB001", "month_code": 258, "book_id": "gMB001", "subject": "数学", "title": "青チャート"},
                    {"row": 5, "raw_code": "258gEC001", "month_code": 258, "book_id": "gEC001", "subject": "英語", "title": "英語長文"},
                ],
            },
        },
        "planner.dates.get": {
            "ok": True,
            "op": "planner.dates.get",
            "data": {"week_starts": ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25", ""]},
        },
        "planner.metrics.get": {
            "ok": True,
            "op": "planner.metrics.get",
            "data": {
                "weeks": [
                    {
                        "week_index": 1,
                        "items": [{"row": 4, "weekly_minutes": 120, "unit_load": 2, "guideline_amount": 240}],
                    }
                ]
            },
        },
        "planner.plan.get": {
            "ok": True,
            "op": "planner.plan.get",
            "data": {
                "weeks": [
                    {"week_index": 1, "items": [{"row": 4, "plan_text": "p1-10"}]},
                ]
            },
        },
        "planner.plan.set": {
            "ok": True,
            "op": "planner.plan.set",
            "data": {"updated": True, "results": [{"ok": True, "cell": "H4"}]},
        },
    }


@pytest.fixture
def mock_books_handler(mock_handler_responses):
    """
    Fixture to mock books handler for tool tests.

    Usage:
        def test_books_find(mock_books_handler):
            with mock_books_handler("find", mock_handler_responses["books.find"]):
                result = await books_find(query="青チャート")
    """
    def _mock(func_name: str, response: dict):
        return patch(f"handlers.books.books_{func_name}", return_value=response)
    return _mock


@pytest.fixture
def mock_students_handler(mock_handler_responses):
    """Fixture to mock students handler for tool tests."""
    def _mock(func_name: str, response: dict):
        return patch(f"handlers.students.students_{func_name}", return_value=response)
    return _mock


@pytest.fixture
def mock_planner_handler(mock_handler_responses):
    """Fixture to mock planner handler for tool tests."""
    def _mock(func_name: str, response: dict):
        return patch(f"handlers.planner.planner_{func_name}", return_value=response)
    return _mock
