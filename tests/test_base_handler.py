"""
Tests for BaseHandler abstract class.
"""
import pytest
from unittest.mock import MagicMock, patch

from core.base_handler import BaseHandler


class ConcreteHandler(BaseHandler):
    """Concrete implementation for testing."""

    DEFAULT_FILE_ID = "test-file-id"
    DEFAULT_SHEET_NAME = "TestSheet"
    COLUMN_SPEC = {
        "id": ["ID", "Id"],
        "name": ["Name", "名前"],
        "status": ["Status", "ステータス"],
    }


class TestBaseHandlerInit:
    """Tests for BaseHandler initialization."""

    def test_init_with_defaults(self):
        """Should use default file_id and sheet_name."""
        mock_sheets = MagicMock()
        handler = ConcreteHandler(mock_sheets)

        assert handler.sheets == mock_sheets
        assert handler.file_id == "test-file-id"
        assert handler.sheet_name == "TestSheet"

    def test_init_with_custom_ids(self):
        """Should use provided file_id and sheet_name."""
        mock_sheets = MagicMock()
        handler = ConcreteHandler(
            mock_sheets,
            file_id="custom-file",
            sheet_name="CustomSheet",
        )

        assert handler.file_id == "custom-file"
        assert handler.sheet_name == "CustomSheet"


class TestBaseHandlerLoadSheet:
    """Tests for load_sheet method."""

    def test_load_sheet_success(self):
        """Should load sheet and build column indices."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001", "Alice", "Active"],
            ["002", "Bob", "Inactive"],
        ]

        handler = ConcreteHandler(mock_sheets)
        result = handler.load_sheet("test.op")

        assert result is None  # No error
        assert handler.headers == ["ID", "Name", "Status"]
        assert len(handler.values) == 3
        assert handler.column_indices["id"] == 0
        assert handler.column_indices["name"] == 1
        assert handler.column_indices["status"] == 2

    def test_load_sheet_empty_returns_error(self):
        """Should return error for empty sheet."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = []

        handler = ConcreteHandler(mock_sheets)
        result = handler.load_sheet("test.op")

        assert result is not None
        assert result["ok"] is False
        assert result["error"]["code"] == "EMPTY"

    def test_load_sheet_exception_returns_error(self):
        """Should return error on exception."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.side_effect = Exception("Connection failed")

        handler = ConcreteHandler(mock_sheets)
        result = handler.load_sheet("test.op")

        assert result is not None
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        assert "Connection failed" in result["error"]["message"]


class TestBaseHandlerCellAccess:
    """Tests for cell access methods."""

    def test_get_cell_by_key(self):
        """Should get cell value by column key."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001", "Alice", "Active"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        row = handler.values[1]
        assert handler.get_cell(row, "id") == "001"
        assert handler.get_cell(row, "name") == "Alice"
        assert handler.get_cell(row, "status") == "Active"

    def test_get_cell_with_default(self):
        """Should return default for missing column."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name"],
            ["001", "Alice"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        row = handler.values[1]
        assert handler.get_cell(row, "status", "N/A") == "N/A"

    def test_get_cell_short_row(self):
        """Should handle row shorter than expected."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001"],  # Short row
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        row = handler.values[1]
        assert handler.get_cell(row, "id") == "001"
        assert handler.get_cell(row, "name", "default") == "default"


class TestBaseHandlerFindRow:
    """Tests for row finding methods."""

    def test_find_row_by_id(self):
        """Should find row by ID."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name"],
            ["001", "Alice"],
            ["002", "Bob"],
            ["003", "Charlie"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        assert handler.find_row_by_id("id", "001") == 2
        assert handler.find_row_by_id("id", "002") == 3
        assert handler.find_row_by_id("id", "003") == 4
        assert handler.find_row_by_id("id", "999") is None

    def test_find_rows_by_ids(self):
        """Should find multiple rows by IDs."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name"],
            ["001", "Alice"],
            ["002", "Bob"],
            ["003", "Charlie"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        result = handler.find_rows_by_ids("id", ["001", "003", "999"])
        assert result == {"001": 2, "003": 4}


class TestBaseHandlerFilter:
    """Tests for filter_by_conditions method."""

    def test_filter_by_where(self):
        """Should filter by exact match."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001", "Alice", "Active"],
            ["002", "Bob", "Inactive"],
            ["003", "Charlie", "Active"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        results = handler.filter_by_conditions(where={"Status": "Active"})
        assert len(results) == 2
        assert results[0][0] == 2  # Row index
        assert results[0][1][1] == "Alice"
        assert results[1][0] == 4
        assert results[1][1][1] == "Charlie"

    def test_filter_by_contains(self):
        """Should filter by partial match."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001", "Alice Smith", "Active"],
            ["002", "Bob Jones", "Active"],
            ["003", "Alice Brown", "Inactive"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        results = handler.filter_by_conditions(contains={"Name": "Alice"})
        assert len(results) == 2
        assert results[0][1][1] == "Alice Smith"
        assert results[1][1][1] == "Alice Brown"

    def test_filter_with_limit(self):
        """Should respect limit parameter."""
        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["ID", "Name", "Status"],
            ["001", "Alice", "Active"],
            ["002", "Bob", "Active"],
            ["003", "Charlie", "Active"],
        ]

        handler = ConcreteHandler(mock_sheets)
        handler.load_sheet("test.op")

        results = handler.filter_by_conditions(
            where={"Status": "Active"},
            limit=2,
        )
        assert len(results) == 2


class TestBaseHandlerResponses:
    """Tests for response helper methods."""

    def test_ok_response(self):
        """Should return success response."""
        mock_sheets = MagicMock()
        handler = ConcreteHandler(mock_sheets)

        result = handler._ok("test.op", {"key": "value"})
        assert result["ok"] is True
        assert result["op"] == "test.op"
        assert result["data"]["key"] == "value"

    def test_error_response(self):
        """Should return error response."""
        mock_sheets = MagicMock()
        handler = ConcreteHandler(mock_sheets)

        result = handler._error("test.op", "BAD_REQUEST", "Invalid input")
        assert result["ok"] is False
        assert result["op"] == "test.op"
        assert result["error"]["code"] == "BAD_REQUEST"
        assert result["error"]["message"] == "Invalid input"
