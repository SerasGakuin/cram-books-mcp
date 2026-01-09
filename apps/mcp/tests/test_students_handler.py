"""
Tests for StudentsHandler class.
TDD tests for the new OOP-based StudentsHandler implementation.
"""
import pytest
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStudentsHandlerInit:
    """Tests for StudentsHandler initialization."""

    def test_init_uses_default_ids(self):
        """Should use default file_id and sheet_name from class variables."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets)

        assert handler.file_id is not None
        assert handler.sheet_name is not None

    def test_init_accepts_custom_ids(self):
        """Should accept custom file_id and sheet_name."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets, file_id="custom-file", sheet_name="CustomSheet")

        assert handler.file_id == "custom-file"
        assert handler.sheet_name == "CustomSheet"


class TestStudentsHandlerColumnSpec:
    """Tests for COLUMN_SPEC configuration."""

    def test_column_spec_has_required_keys(self):
        """Should define all required column keys."""
        from handlers.students_handler import StudentsHandler

        required_keys = ["id", "name", "grade", "status", "planner_link",
                         "planner_sheet_id", "meeting_doc", "tags"]

        for key in required_keys:
            assert key in StudentsHandler.COLUMN_SPEC, f"Missing key: {key}"


class TestStudentsHandlerList:
    """Tests for list method."""

    def test_list_returns_all_students(self):
        """Should return all students."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年", "ステータス"],
            ["s001", "田中太郎", "高3", "アクティブ"],
            ["s002", "鈴木花子", "高2", "アクティブ"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.list()

        assert result["ok"] is True
        assert len(result["data"]["students"]) == 2
        assert result["data"]["count"] == 2

    def test_list_respects_limit(self):
        """Should respect limit parameter."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
            ["s002", "鈴木花子", "高2"],
            ["s003", "佐藤次郎", "高1"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.list(limit=2)

        assert result["ok"] is True
        assert len(result["data"]["students"]) == 2

    def test_list_empty_sheet(self):
        """Should return empty list for empty sheet."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.list()

        assert result["ok"] is True
        assert result["data"]["students"] == []


class TestStudentsHandlerFind:
    """Tests for find method."""

    def test_find_requires_query(self):
        """Should return error when query is empty."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets)

        result = handler.find("")

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_find_returns_candidates(self):
        """Should return scored candidates for valid query."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
            ["s002", "田中花子", "高2"],
            ["s003", "鈴木次郎", "高1"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.find("田中")

        assert result["ok"] is True
        assert len(result["data"]["candidates"]) == 2

    def test_find_exact_match_highest_score(self):
        """Exact match should have the highest score."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
            ["s002", "田中", "高2"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.find("田中")

        assert result["ok"] is True
        candidates = result["data"]["candidates"]
        assert len(candidates) >= 1
        # Exact match should be first
        assert candidates[0]["name"] == "田中"

    def test_find_respects_limit(self):
        """Should respect the limit parameter."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中一郎", "高3"],
            ["s002", "田中二郎", "高2"],
            ["s003", "田中三郎", "高1"],
            ["s004", "田中四郎", "中3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.find("田中", limit=2)

        assert result["ok"] is True
        assert len(result["data"]["candidates"]) <= 2


class TestStudentsHandlerGet:
    """Tests for get method."""

    def test_get_requires_student_id(self):
        """Should return error when student_id is missing."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets)

        result = handler.get(None)

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_get_returns_student_details(self):
        """Should return student details."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年", "ステータス"],
            ["s001", "田中太郎", "高3", "アクティブ"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.get("s001")

        assert result["ok"] is True
        assert "student" in result["data"]
        student = result["data"]["student"]
        assert student["id"] == "s001"
        assert student["name"] == "田中太郎"

    def test_get_not_found(self):
        """Should return error for non-existent student."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.get("s999")

        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"

    def test_get_multiple_students(self):
        """Should return multiple students when student_ids list is provided."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
            ["s002", "鈴木花子", "高2"],
            ["s003", "佐藤次郎", "高1"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.get_multiple(["s001", "s003"])

        assert result["ok"] is True
        assert "students" in result["data"]
        assert len(result["data"]["students"]) == 2


class TestStudentsHandlerFilter:
    """Tests for filter method."""

    def test_filter_by_where(self):
        """Should filter by exact match (where)."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年", "ステータス"],
            ["s001", "田中太郎", "高3", "アクティブ"],
            ["s002", "鈴木花子", "高2", "休止"],
            ["s003", "佐藤次郎", "高3", "アクティブ"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.filter(where={"学年": "高3"})

        assert result["ok"] is True
        assert result["data"]["count"] == 2

    def test_filter_by_contains(self):
        """Should filter by partial match (contains)."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
            ["s002", "田中花子", "高2"],
            ["s003", "鈴木次郎", "高1"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.filter(contains={"名前": "田中"})

        assert result["ok"] is True
        assert result["data"]["count"] == 2

    def test_filter_with_limit(self):
        """Should respect limit parameter."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中一郎", "高3"],
            ["s002", "田中二郎", "高3"],
            ["s003", "田中三郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.filter(where={"学年": "高3"}, limit=2)

        assert result["ok"] is True
        assert len(result["data"]["students"]) <= 2


class TestStudentsHandlerCreate:
    """Tests for create method."""

    def test_create_generates_new_id(self):
        """Should generate new ID with prefix (format: g{prefix}{seq})."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["gs001", "既存の生徒", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.create(record={"名前": "新しい生徒", "学年": "高2"})

        assert result["ok"] is True
        # IDs have format g{prefix}{seq} - default prefix is "s" -> "gs002"
        assert result["data"]["id"].startswith("gs")
        assert result["data"]["id"] == "gs002"

    def test_create_with_custom_prefix(self):
        """Should use custom ID prefix (format: g{prefix}{seq})."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.create(record={"名前": "新入生"}, id_prefix="new")

        assert result["ok"] is True
        # IDs have format g{prefix}{seq} - custom prefix "new" -> "gnew001"
        assert result["data"]["id"].startswith("gnew")

    def test_create_appends_row(self):
        """Should append a row with student data."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.create(record={"名前": "新しい生徒", "学年": "高2"})

        assert result["ok"] is True
        mock_sheets.append_rows.assert_called_once()


class TestStudentsHandlerUpdate:
    """Tests for update method (two-phase)."""

    def test_update_requires_student_id(self):
        """Should return error when student_id is missing."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets)

        result = handler.update("", updates={"名前": "新名前"})

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_update_preview_mode(self):
        """Should return preview without confirm_token."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.update("s001", updates={"名前": "田中次郎"})

        assert result["ok"] is True
        assert result["data"]["requires_confirmation"] is True
        assert "confirm_token" in result["data"]
        assert "preview" in result["data"]

    def test_update_confirm_mode(self):
        """Should apply updates with valid confirm_token."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)

        # First call: get preview and token
        preview_result = handler.update("s001", updates={"名前": "田中次郎"})
        token = preview_result["data"]["confirm_token"]

        # Second call: confirm with token
        confirm_result = handler.update("s001", confirm_token=token)

        assert confirm_result["ok"] is True
        assert confirm_result["data"]["updated"] is True

    def test_update_expired_token(self):
        """Should reject expired/invalid token."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.update("s001", confirm_token="invalid-token")

        assert result["ok"] is False
        assert result["error"]["code"] == "CONFIRM_EXPIRED"

    def test_update_not_found(self):
        """Should return error for non-existent student."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.update("s999", updates={"名前": "新名前"})

        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"


class TestStudentsHandlerDelete:
    """Tests for delete method (two-phase)."""

    def test_delete_requires_student_id(self):
        """Should return error when student_id is missing."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        handler = StudentsHandler(mock_sheets)

        result = handler.delete("")

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_delete_preview_mode(self):
        """Should return preview without confirm_token."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.delete("s001")

        assert result["ok"] is True
        assert result["data"]["requires_confirmation"] is True
        assert "confirm_token" in result["data"]

    def test_delete_confirm_mode(self):
        """Should delete with valid confirm_token."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)

        # First call: get preview and token
        preview_result = handler.delete("s001")
        token = preview_result["data"]["confirm_token"]

        # Second call: confirm with token
        confirm_result = handler.delete("s001", confirm_token=token)

        assert confirm_result["ok"] is True
        assert confirm_result["data"]["deleted"] is True

    def test_delete_not_found(self):
        """Should return error for non-existent student."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "学年"],
            ["s001", "田中太郎", "高3"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.delete("s999")

        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"


class TestStudentsHandlerPlannerIdExtraction:
    """Tests for planner sheet ID extraction from links."""

    def test_extracts_planner_id_from_link(self):
        """Should extract planner sheet ID from Google Sheets URL."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "プランナーリンク", "プランナーシートID"],
            ["s001", "田中太郎", "https://docs.google.com/spreadsheets/d/1abc-XYZ_123456789012345678901234567890/edit", ""],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.get("s001")

        assert result["ok"] is True
        student = result["data"]["student"]
        assert student["planner_sheet_id"] == "1abc-XYZ_123456789012345678901234567890"

    def test_uses_existing_planner_id_if_present(self):
        """Should use existing planner sheet ID if already present."""
        from handlers.students_handler import StudentsHandler

        mock_sheets = MagicMock()
        # Use valid column names: "スピードプランナーID" is in STUDENT_COLUMNS["planner_sheet_id"]
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "スプレッドシート", "スピードプランナーID"],
            ["s001", "田中太郎", "https://docs.google.com/spreadsheets/d/xxx/edit", "explicit-id-12345678901234567890"],
        ]

        handler = StudentsHandler(mock_sheets)
        result = handler.get("s001")

        assert result["ok"] is True
        student = result["data"]["student"]
        assert student["planner_sheet_id"] == "explicit-id-12345678901234567890"
