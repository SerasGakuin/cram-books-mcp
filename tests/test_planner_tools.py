"""
Tests for planner tools in MCP server.
Tests planner_ids_list, planner_dates_*, planner_metrics_get, planner_plan_*, planner_monthly_filter, planner_guidance

Updated for direct Google Sheets API architecture.
"""
import pytest
from unittest.mock import patch, MagicMock

from server import (
    planner_ids_list,
    planner_dates_get,
    planner_dates_set,
    planner_metrics_get,
    planner_plan_get,
    planner_plan_set,
    planner_plan_create,
    planner_monthly_filter,
    planner_guidance,
)


class TestPlannerIdsList:
    """Tests for planner_ids_list tool"""

    @pytest.mark.asyncio
    async def test_list_ids_with_spreadsheet_id(self, mock_sheets_client, mock_handler_responses):
        """Should list planner IDs with spreadsheet_id"""
        mock_handler = MagicMock()
        mock_handler.ids_list.return_value = mock_handler_responses["planner.ids_list"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_ids_list(spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            assert "items" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_list_ids_with_student_id(self, mock_sheets_client, mock_handler_responses):
        """Should list planner IDs with student_id"""
        mock_handler = MagicMock()
        mock_handler.ids_list.return_value = mock_handler_responses["planner.ids_list"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_ids_list(student_id="S001")
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_list_ids_requires_identifier(self):
        """Should require student_id or spreadsheet_id"""
        result = await planner_ids_list()
        assert result.get("ok") is False
        assert "error" in result


class TestPlannerDatesGet:
    """Tests for planner_dates_get tool"""

    @pytest.mark.asyncio
    async def test_get_dates(self, mock_sheets_client, mock_handler_responses):
        """Should get week start dates"""
        mock_handler = MagicMock()
        mock_handler.dates_get.return_value = mock_handler_responses["planner.dates.get"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_dates_get(spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            assert "week_starts" in result.get("data", {})


class TestPlannerDatesSet:
    """Tests for planner_dates_set tool"""

    @pytest.mark.asyncio
    async def test_set_dates(self, mock_sheets_client):
        """Should set week start date"""
        response = {"ok": True, "op": "planner.dates.set", "data": {"updated": True}}
        mock_handler = MagicMock()
        mock_handler.dates_set.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_dates_set(
                start_date="2025-08-04",
                spreadsheet_id="test-sheet-id"
            )
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_set_dates_requires_start_date(self):
        """Should require start_date"""
        result = await planner_dates_set(
            start_date=None,
            spreadsheet_id="test-sheet-id"
        )
        assert result.get("ok") is False
        assert "error" in result


class TestPlannerMetricsGet:
    """Tests for planner_metrics_get tool"""

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_sheets_client, mock_handler_responses):
        """Should get planner metrics"""
        mock_handler = MagicMock()
        mock_handler.metrics_get.return_value = mock_handler_responses["planner.metrics.get"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_metrics_get(spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            assert "weeks" in result.get("data", {})


class TestPlannerPlanGet:
    """Tests for planner_plan_get tool"""

    @pytest.mark.asyncio
    async def test_get_plan(self, mock_sheets_client, mock_handler_responses):
        """Should get plan data with metrics"""
        mock_handler = MagicMock()
        mock_handler.plan_get.return_value = mock_handler_responses["planner.plan.get"]
        mock_handler.metrics_get.return_value = mock_handler_responses["planner.metrics.get"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_plan_get(spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            assert "weeks" in result.get("data", {})


class TestPlannerPlanSet:
    """Tests for planner_plan_set tool"""

    @pytest.mark.asyncio
    async def test_set_plan(self, mock_sheets_client, mock_handler_responses):
        """Should set plan entry"""
        mock_handler = MagicMock()
        mock_handler.plan_set.return_value = mock_handler_responses["planner.plan.set"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_plan_set(
                week_index=1,
                row=4,
                plan_text="p1-10",
                spreadsheet_id="test-sheet-id"
            )
            assert result.get("ok") is True


class TestPlannerPlanCreate:
    """Tests for planner_plan_create tool"""

    @pytest.mark.asyncio
    async def test_create_plan(self, mock_sheets_client, mock_handler_responses):
        """Should create plan entries"""
        mock_handler = MagicMock()
        mock_handler.dates_get.return_value = mock_handler_responses["planner.dates.get"]
        mock_handler.plan_set.return_value = mock_handler_responses["planner.plan.set"]
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            items = [{"week_index": 1, "row": 4, "plan_text": "p1-10"}]
            result = await planner_plan_create(items=items, spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_create_requires_items(self):
        """Should require items"""
        result = await planner_plan_create(items=None, spreadsheet_id="test-sheet-id")
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_empty_items(self):
        """Should handle empty items list"""
        result = await planner_plan_create(items=[], spreadsheet_id="test-sheet-id")
        assert result.get("ok") is False


class TestPlannerMonthlyFilter:
    """Tests for planner_monthly_filter tool"""

    @pytest.mark.asyncio
    async def test_filter_by_year_month(self, mock_sheets_client):
        """Should filter by year and month"""
        response = {
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
        }
        mock_handler = MagicMock()
        mock_handler.monthly_filter.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_monthly_filter(
                year=25,
                month=8,
                spreadsheet_id="test-sheet-id"
            )
            assert result.get("ok") is True
            assert "items" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_filter_normalizes_year(self, mock_sheets_client):
        """Should normalize 4-digit year to 2-digit"""
        response = {
            "ok": True,
            "op": "planner.monthly.filter",
            "data": {"year": 25, "month": 8, "count": 0, "items": []}
        }
        mock_handler = MagicMock()
        mock_handler.monthly_filter.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_monthly_filter(
                year=2025,
                month=8,
                spreadsheet_id="test-sheet-id"
            )
            assert result.get("ok") is True


class TestPlannerGuidance:
    """Tests for planner_guidance tool"""

    @pytest.mark.asyncio
    async def test_get_guidance(self):
        """Should return guidance data"""
        result = await planner_guidance()
        assert result.get("ok") is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_guidance_contains_structure(self):
        """Should contain sheet structure info"""
        result = await planner_guidance()
        data = result.get("data", {})
        assert "sheet" in data
        assert "policy" in data
        assert "format" in data
        assert "workflow" in data

    @pytest.mark.asyncio
    async def test_guidance_no_api_call(self):
        """Should not require API call - this is a static response"""
        # This should work without any mocking
        result = await planner_guidance()
        assert result is not None
        assert result.get("ok") is True
