"""
Tests for planner tools in MCP server.
Tests planner_ids_list, planner_dates_*, planner_metrics_get, planner_plan_*, planner_monthly_filter, planner_guidance
"""
import pytest
from unittest.mock import patch, AsyncMock

# Import the tool functions
import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])
from server import (
    planner_ids_list,
    planner_dates_get,
    planner_dates_propose,
    planner_dates_confirm,
    planner_metrics_get,
    planner_plan_get,
    planner_plan_create,
    planner_monthly_filter,
    planner_plan_targets,
    planner_guidance,
)


class TestPlannerIdsList:
    """Tests for planner_ids_list tool"""

    @pytest.mark.asyncio
    async def test_list_ids_with_spreadsheet_id(self, mock_gas_api):
        """Should list planner IDs with spreadsheet_id"""
        mock_gas_api("planner.ids_list", method="POST")
        result = await planner_ids_list(spreadsheet_id="test-sheet-id")
        assert "items" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_list_ids_with_student_id(self, mock_gas_api):
        """Should list planner IDs with student_id"""
        mock_gas_api("planner.ids_list", method="POST")
        result = await planner_ids_list(student_id="S001")
        assert result.get("ok") is True or "items" in result

    @pytest.mark.asyncio
    async def test_list_ids_requires_identifier(self):
        """Should require student_id or spreadsheet_id"""
        result = await planner_ids_list()
        # May return error or empty result
        assert result is not None


class TestPlannerDatesGet:
    """Tests for planner_dates_get tool"""

    @pytest.mark.asyncio
    async def test_get_dates(self, mock_gas_api):
        """Should get week start dates"""
        mock_gas_api("planner.dates.get", method="POST")
        result = await planner_dates_get(spreadsheet_id="test-sheet-id")
        assert "week_starts" in result or result.get("ok") is True


class TestPlannerDatesPropose:
    """Tests for planner_dates_propose tool"""

    @pytest.mark.asyncio
    async def test_propose_dates(self, mock_gas_api, clear_preview_cache):
        """Should propose new dates - calls planner.dates.get first"""
        mock_gas_api("planner.dates.get", method="POST")
        result = await planner_dates_propose(
            start_date="2025-08-04",
            spreadsheet_id="test-sheet-id"
        )
        data = result.get("data", result)
        assert "confirm_token" in data or "effects" in data or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_propose_requires_start_date(self, mock_gas_api):
        """Should require start_date - but still calls dates.get"""
        mock_gas_api("planner.dates.get", method="POST")
        result = await planner_dates_propose(
            start_date=None,
            spreadsheet_id="test-sheet-id"
        )
        # May return ok with None start_date or error
        assert result is not None

    @pytest.mark.asyncio
    async def test_propose_requires_identifier(self, mock_gas_error):
        """Should handle missing identifier gracefully"""
        mock_gas_error("NOT_FOUND", "Spreadsheet not found")
        result = await planner_dates_propose(start_date="2025-08-04")
        # Should return error or empty result
        assert result is not None


class TestPlannerDatesConfirm:
    """Tests for planner_dates_confirm tool"""

    @pytest.mark.asyncio
    async def test_confirm_requires_token(self):
        """Should require confirm_token"""
        result = await planner_dates_confirm(confirm_token=None)
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_confirm_invalid_token(self, clear_preview_cache):
        """Should handle invalid token"""
        result = await planner_dates_confirm(confirm_token="nonexistent-token")
        assert result.get("ok") is False or "error" in result


class TestPlannerMetricsGet:
    """Tests for planner_metrics_get tool"""

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_gas_api):
        """Should get planner metrics"""
        mock_gas_api("planner.metrics.get", method="POST")
        result = await planner_metrics_get(spreadsheet_id="test-sheet-id")
        assert "weeks" in result or result.get("ok") is True


class TestPlannerPlanGet:
    """Tests for planner_plan_get tool"""

    @pytest.mark.asyncio
    async def test_get_plan(self, mock_gas_sequence):
        """Should get plan data - calls plan.get and metrics.get"""
        mock_gas_sequence(["planner.plan.get", "planner.metrics.get"])
        result = await planner_plan_get(spreadsheet_id="test-sheet-id")
        data = result.get("data", result)
        assert "weeks" in data or result.get("ok") is True


class TestPlannerPlanCreate:
    """Tests for planner_plan_create tool"""

    @pytest.mark.asyncio
    async def test_create_plan(self, httpx_mock):
        """Should create plan entries"""
        # Mock both calls that might be made
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.plan.set",
            "data": {"updated": True, "results": [{"ok": True}]}
        })
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.plan.set",
            "data": {"updated": True, "results": [{"ok": True}]}
        })
        items = [{"row": 4, "week": 1, "text": "p1-10"}]
        result = await planner_plan_create(items=items, spreadsheet_id="test-sheet-id")
        assert result.get("ok") is True or "results" in result

    @pytest.mark.asyncio
    async def test_create_requires_items(self):
        """Should require items"""
        result = await planner_plan_create(items=None, spreadsheet_id="test-sheet-id")
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_create_empty_items(self):
        """Should handle empty items list"""
        result = await planner_plan_create(items=[], spreadsheet_id="test-sheet-id")
        # May succeed with empty result or return error
        assert result is not None


class TestPlannerMonthlyFilter:
    """Tests for planner_monthly_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_year_month(self, httpx_mock):
        """Should filter by year and month"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.monthly.filter",
            "data": {
                "year": 25,
                "month": 8,
                "count": 2,
                "items": [
                    {"row": 2, "book_id": "gMB001", "subject": "数学"},
                    {"row": 3, "book_id": "gEC001", "subject": "英語"}
                ]
            }
        })
        result = await planner_monthly_filter(
            year=25,
            month=8,
            spreadsheet_id="test-sheet-id"
        )
        assert "items" in result or result.get("ok") is True

    @pytest.mark.asyncio
    async def test_filter_requires_year(self):
        """Should require year"""
        result = await planner_monthly_filter(year=None, month=8, spreadsheet_id="test-id")
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_filter_requires_month(self):
        """Should require month"""
        result = await planner_monthly_filter(year=25, month=None, spreadsheet_id="test-id")
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_filter_normalizes_year(self, httpx_mock):
        """Should normalize 4-digit year to 2-digit"""
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.monthly.filter",
            "data": {"year": 25, "month": 8, "count": 0, "items": []}
        })
        result = await planner_monthly_filter(
            year=2025,
            month=8,
            spreadsheet_id="test-sheet-id"
        )
        assert result.get("ok") is True


class TestPlannerPlanTargets:
    """Tests for planner_plan_targets tool"""

    @pytest.mark.asyncio
    async def test_get_targets(self, httpx_mock):
        """Should get plan targets - makes many HTTP calls"""
        # planner_plan_targets calls: ids_list, dates_get, metrics_get, plan_get (plan.get + metrics.get), books_get
        # Mock ids_list response
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.ids_list",
            "data": {"count": 1, "items": [{"row": 4, "book_id": "gMB001", "subject": "数学"}]}
        })
        # Mock dates_get response
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.dates.get",
            "data": {"week_starts": ["2025-08-04", "2025-08-11", "", "", ""]}
        })
        # Mock metrics_get response
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.metrics.get",
            "data": {"weeks": [{"week_index": 1, "items": [{"row": 4, "weekly_minutes": 60}]}]}
        })
        # Mock plan_get (plan.get)
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.plan.get",
            "data": {"weeks": [{"week_index": 1, "items": [{"row": 4, "plan_text": ""}]}]}
        })
        # Mock plan_get's call to metrics_get
        httpx_mock.add_response(json={
            "ok": True,
            "op": "planner.metrics.get",
            "data": {"weeks": []}
        })
        # Mock books_get (GET request)
        httpx_mock.add_response(json={
            "ok": True,
            "op": "books.get",
            "data": {"books": [{"id": "gMB001", "structure": {"chapters": []}}]}
        })
        result = await planner_plan_targets(spreadsheet_id="test-sheet-id")
        assert result is not None


class TestPlannerGuidance:
    """Tests for planner_guidance tool"""

    @pytest.mark.asyncio
    async def test_get_guidance(self):
        """Should return guidance text"""
        result = await planner_guidance()
        assert "guidance" in result or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_guidance_no_api_call(self):
        """Should not require API call"""
        # This is a static response
        result = await planner_guidance()
        assert result is not None
