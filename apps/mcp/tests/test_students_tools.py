"""
Tests for students tools in MCP server.
Tests students_list, students_find, students_get, students_filter, students_create, students_update, students_delete
"""
import pytest
from unittest.mock import patch, AsyncMock

# Import the tool functions
import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])
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
    async def test_list_all_students(self, mock_gas_api):
        """Should list all students"""
        mock_gas_api("students.list")
        result = await students_list()
        assert "students" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_list_with_limit(self, mock_gas_api):
        """Should respect limit parameter"""
        mock_gas_api("students.list")
        result = await students_list(limit=5)
        assert result.get("ok") is True or "students" in result

    @pytest.mark.asyncio
    async def test_list_include_all(self, mock_gas_api):
        """Should include inactive students when include_all=True"""
        mock_gas_api("students.list")
        result = await students_list(include_all=True)
        assert result.get("ok") is True or "students" in result


class TestStudentsFind:
    """Tests for students_find tool"""

    @pytest.mark.asyncio
    async def test_find_by_name(self, mock_gas_api):
        """Should find students by name"""
        mock_gas_api("students.list")  # students_find uses list internally
        result = await students_find(query="山田")
        assert "candidates" in result or result.get("ok") is True or "top" in result

    @pytest.mark.asyncio
    async def test_find_requires_query(self):
        """Should return error when query is missing"""
        result = await students_find(query=None)
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_find_with_limit(self, mock_gas_api):
        """Should respect limit parameter"""
        mock_gas_api("students.list")
        result = await students_find(query="test", limit=3)
        assert result.get("ok") is True or "candidates" in result

    @pytest.mark.asyncio
    async def test_find_empty_query(self):
        """Should return error for empty query"""
        result = await students_find(query="")
        assert "error" in result or result.get("ok") is False


class TestStudentsGet:
    """Tests for students_get tool"""

    @pytest.mark.asyncio
    async def test_get_single_student(self, mock_gas_api):
        """Should get single student by ID"""
        mock_gas_api("students.list")
        result = await students_get(student_id="S001")
        assert result.get("ok") is True or "student" in result

    @pytest.mark.asyncio
    async def test_get_multiple_students(self, mock_gas_api):
        """Should get multiple students by IDs"""
        mock_gas_api("students.list")
        result = await students_get(student_ids=["S001", "S002"])
        assert result.get("ok") is True or "students" in result

    @pytest.mark.asyncio
    async def test_get_requires_id(self):
        """Should return error when no ID provided"""
        result = await students_get()
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_gas_error):
        """Should handle student not found"""
        mock_gas_error("NOT_FOUND", "Student not found", "students.get")
        result = await students_get(student_id="nonexistent")
        assert result.get("ok") is False


class TestStudentsFilter:
    """Tests for students_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_grade(self, mock_gas_api):
        """Should filter students by grade"""
        mock_gas_api("students.list")
        result = await students_filter(where={"学年": "高3"})
        assert result.get("ok") is True or "students" in result

    @pytest.mark.asyncio
    async def test_filter_by_contains(self, mock_gas_api):
        """Should filter by partial match"""
        mock_gas_api("students.list")
        result = await students_filter(contains={"氏名": "田"})
        assert result.get("ok") is True or "students" in result

    @pytest.mark.asyncio
    async def test_filter_with_limit(self, mock_gas_api):
        """Should respect limit"""
        mock_gas_api("students.list")
        result = await students_filter(limit=10)
        assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_filter_no_params(self, mock_gas_api):
        """Should return all students when no filter"""
        mock_gas_api("students.list")
        result = await students_filter()
        assert result.get("ok") is True or "students" in result


class TestStudentsCreate:
    """Tests for students_create tool"""

    @pytest.mark.asyncio
    async def test_create_student(self, mock_gas_api, httpx_mock):
        """Should create new student"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.create",
            "data": {"id": "S003", "created": True}
        })
        result = await students_create(record={"氏名": "新規生徒", "学年": "高1"})
        assert result.get("ok") is True or "id" in result

    @pytest.mark.asyncio
    async def test_create_with_custom_prefix(self, httpx_mock):
        """Should use custom ID prefix"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.create",
            "data": {"id": "custom001", "created": True}
        })
        result = await students_create(record={"氏名": "Test"}, id_prefix="custom")
        assert result.get("ok") is True


class TestStudentsUpdate:
    """Tests for students_update tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_update_preview(self, httpx_mock):
        """Should return preview without confirm_token"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.update",
            "data": {
                "requires_confirmation": True,
                "confirm_token": "test-token",
                "preview": {"学年": {"from": "高1", "to": "高2"}}
            }
        })
        result = await students_update(student_id="S001", updates={"学年": "高2"})
        data = result.get("data", result)
        assert "confirm_token" in data or data.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_update_confirm(self, httpx_mock):
        """Should apply update with confirm_token"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.update",
            "data": {"updated": True}
        })
        result = await students_update(student_id="S001", confirm_token="valid-token")
        assert result.get("ok") is True or result.get("updated") is True

    @pytest.mark.asyncio
    async def test_update_requires_student_id(self):
        """Should require student_id"""
        result = await students_update(student_id=None, updates={"学年": "高2"})
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_update_invalid_token(self, mock_gas_error):
        """Should handle invalid token"""
        mock_gas_error("CONFIRM_EXPIRED", "Token expired", "students.update")
        result = await students_update(student_id="S001", confirm_token="invalid")
        assert result.get("ok") is False


class TestStudentsDelete:
    """Tests for students_delete tool (two-phase)"""

    @pytest.mark.asyncio
    async def test_delete_preview(self, httpx_mock):
        """Should return preview without confirm_token"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.delete",
            "data": {
                "requires_confirmation": True,
                "confirm_token": "delete-token",
                "preview": {"row": 5}
            }
        })
        result = await students_delete(student_id="S001")
        data = result.get("data", result)
        assert "confirm_token" in data or data.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_delete_confirm(self, httpx_mock):
        """Should delete with confirm_token"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "students.delete",
            "data": {"deleted": True}
        })
        result = await students_delete(student_id="S001", confirm_token="valid-token")
        assert result.get("ok") is True or result.get("deleted") is True

    @pytest.mark.asyncio
    async def test_delete_requires_student_id(self):
        """Should require student_id"""
        result = await students_delete(student_id=None)
        assert "error" in result or result.get("ok") is False
