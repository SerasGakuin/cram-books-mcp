"""
Tests for students tools in MCP server.
Tests students_list, students_find, students_get, students_filter, students_create, students_update, students_delete

Updated for direct Google Sheets API architecture.
"""
import pytest
from unittest.mock import patch, MagicMock

# Import the tool functions
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    students_list,
    students_find,
    students_get,
    students_filter,
    students_create,
    students_update,
    students_delete,
)


class TestStudentsList:
    """Tests for students_list tool"""

    @pytest.mark.asyncio
    async def test_list_active_students(self, mock_sheets_client, mock_handler_responses):
        """Should list active students by default"""
        mock_handler = MagicMock()
        mock_handler.filter.return_value = mock_handler_responses["students.filter"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_list()
            assert result.get("ok") is True
            assert "students" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_list_all_students(self, mock_sheets_client, mock_handler_responses):
        """Should list all students when include_all=True"""
        mock_handler = MagicMock()
        mock_handler.list.return_value = mock_handler_responses["students.list"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_list(include_all=True)
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_list_with_limit(self, mock_sheets_client, mock_handler_responses):
        """Should respect limit parameter"""
        mock_handler = MagicMock()
        mock_handler.filter.return_value = mock_handler_responses["students.filter"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_list(limit=5)
            assert result.get("ok") is True


class TestStudentsFind:
    """Tests for students_find tool"""

    @pytest.mark.asyncio
    async def test_find_student_success(self, mock_sheets_client, mock_handler_responses):
        """Should find students matching query"""
        mock_handler = MagicMock()
        mock_handler.filter.return_value = mock_handler_responses["students.filter"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_find(query="山田")
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_find_requires_query(self):
        """Should return error when query is missing"""
        result = await students_find(query=None)
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_find_empty_query(self):
        """Should return error when query is empty"""
        result = await students_find(query="")
        assert result.get("ok") is False
        assert "error" in result


class TestStudentsGet:
    """Tests for students_get tool"""

    @pytest.mark.asyncio
    async def test_get_single_student(self, mock_sheets_client):
        """Should get single student by ID"""
        response = {"ok": True, "op": "students.get", "data": {"student": {"id": "S001", "name": "山田太郎"}}}
        mock_handler = MagicMock()
        mock_handler.get.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_get(student_id="S001")
            assert result.get("ok") is True
            assert "student" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_get_multiple_students(self, mock_sheets_client):
        """Should get multiple students by IDs"""
        response = {"ok": True, "op": "students.get", "data": {"students": []}}
        mock_handler = MagicMock()
        mock_handler.get_multiple.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_get(student_ids=["S001", "S002"])
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_get_requires_id(self, mock_sheets_client):
        """Should return error when no ID provided"""
        with patch("server.get_sheets_client", return_value=mock_sheets_client):
            result = await students_get()
            assert result.get("ok") is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_handles_not_found(self, mock_sheets_client):
        """Should handle student not found error"""
        error_response = {"ok": False, "op": "students.get", "error": {"code": "NOT_FOUND", "message": "Student not found"}}
        mock_handler = MagicMock()
        mock_handler.get.return_value = error_response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_get(student_id="nonexistent")
            assert result.get("ok") is False


class TestStudentsFilter:
    """Tests for students_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_grade(self, mock_sheets_client, mock_handler_responses):
        """Should filter students by grade"""
        mock_handler = MagicMock()
        mock_handler.filter.return_value = mock_handler_responses["students.filter"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_filter(where={"学年": "高1"})
            assert result.get("ok") is True
            assert "students" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_filter_by_contains(self, mock_sheets_client, mock_handler_responses):
        """Should filter students by partial match"""
        mock_handler = MagicMock()
        mock_handler.filter.return_value = mock_handler_responses["students.filter"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_filter(contains={"名前": "山田"})
            assert result.get("ok") is True


class TestStudentsCreate:
    """Tests for students_create tool"""

    @pytest.mark.asyncio
    async def test_create_student(self, mock_sheets_client):
        """Should create new student"""
        response = {"ok": True, "op": "students.create", "data": {"id": "S004", "created": True}}
        mock_handler = MagicMock()
        mock_handler.create.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_create(record={"名前": "新入生", "学年": "高1"})
            assert result.get("ok") is True
            assert result.get("data", {}).get("id") is not None


class TestStudentsUpdate:
    """Tests for students_update tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_update_preview(self, mock_sheets_client):
        """Should return preview without confirm_token"""
        response = {
            "ok": True,
            "op": "students.update",
            "data": {
                "requires_confirmation": True,
                "preview": {"diffs": {"名前": {"from": "旧名前", "to": "新名前"}}},
                "confirm_token": "test-token-123",
            },
        }
        mock_handler = MagicMock()
        mock_handler.update.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_update(student_id="S001", updates={"名前": "新名前"})
            data = result.get("data", {})
            assert data.get("requires_confirmation") is True
            assert "confirm_token" in data

    @pytest.mark.asyncio
    async def test_update_confirm(self, mock_sheets_client):
        """Should apply update with valid confirm_token"""
        response = {"ok": True, "op": "students.update", "data": {"updated": True}}
        mock_handler = MagicMock()
        mock_handler.update.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_update(student_id="S001", confirm_token="valid-token")
            assert result.get("ok") is True
            assert result.get("data", {}).get("updated") is True

    @pytest.mark.asyncio
    async def test_update_requires_student_id(self):
        """Should require student_id"""
        result = await students_update(student_id=None, updates={"名前": "New"})
        assert result.get("ok") is False
        assert "error" in result


class TestStudentsDelete:
    """Tests for students_delete tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_delete_preview(self, mock_sheets_client):
        """Should return preview without confirm_token"""
        response = {
            "ok": True,
            "op": "students.delete",
            "data": {
                "requires_confirmation": True,
                "preview": {"row": 5},
                "confirm_token": "delete-token-456",
            },
        }
        mock_handler = MagicMock()
        mock_handler.delete.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_delete(student_id="S001")
            data = result.get("data", {})
            assert data.get("requires_confirmation") is True
            assert "confirm_token" in data

    @pytest.mark.asyncio
    async def test_delete_confirm(self, mock_sheets_client):
        """Should delete with valid confirm_token"""
        response = {"ok": True, "op": "students.delete", "data": {"deleted": True}}
        mock_handler = MagicMock()
        mock_handler.delete.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.StudentsHandler", return_value=mock_handler):
            result = await students_delete(student_id="S001", confirm_token="valid-token")
            assert result.get("ok") is True
            assert result.get("data", {}).get("deleted") is True

    @pytest.mark.asyncio
    async def test_delete_requires_student_id(self):
        """Should require student_id"""
        result = await students_delete(student_id=None)
        assert result.get("ok") is False
        assert "error" in result
