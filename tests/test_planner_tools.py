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
    monthplan_get,
    monthplan_set,
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


class TestPlannerMonthlyFilterMultiple:
    """Tests for planner_monthly_filter with year_months parameter"""

    @pytest.mark.asyncio
    async def test_multiple_year_months(self, mock_sheets_client):
        """Should pass year_months to handler"""
        response = {
            "ok": True,
            "op": "planner.monthly.filter",
            "data": {
                "year_months": [{"year": 25, "month": 6}, {"year": 25, "month": 7}],
                "items": [{"book_id": "gMA001"}, {"book_id": "gEN001"}],
                "count": 2,
                "by_month": {
                    "25-06": [{"book_id": "gMA001"}],
                    "25-07": [{"book_id": "gEN001"}],
                }
            }
        }
        mock_handler = MagicMock()
        mock_handler.monthly_filter.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await planner_monthly_filter(
                year_months=[
                    {"year": 2025, "month": 6},
                    {"year": 2025, "month": 7},
                ],
                spreadsheet_id="test-sheet-id"
            )
            assert result.get("ok") is True
            assert "year_months" in result.get("data", {})
            assert "by_month" in result.get("data", {})

    @pytest.mark.asyncio
    async def test_year_months_passed_to_handler(self, mock_sheets_client):
        """Should correctly pass year_months parameter to handler"""
        mock_handler = MagicMock()
        mock_handler.monthly_filter.return_value = {"ok": True, "data": {}}
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            await planner_monthly_filter(
                year_months=[{"year": 2025, "month": 8}],
                spreadsheet_id="test-id"
            )
            # Verify handler was called with year_months
            mock_handler.monthly_filter.assert_called_once()
            call_kwargs = mock_handler.monthly_filter.call_args.kwargs
            assert "year_months" in call_kwargs
            assert call_kwargs["year_months"] == [{"year": 2025, "month": 8}]

    @pytest.mark.asyncio
    async def test_backward_compatible_single_month(self, mock_sheets_client):
        """Should still work with year/month params"""
        response = {
            "ok": True,
            "op": "planner.monthly.filter",
            "data": {"year": 25, "month": 8, "items": [], "count": 0}
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
            # Should have single month response format
            assert result.get("data", {}).get("year") == 25


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


class TestMonthplanGet:
    """Tests for monthplan_get tool"""

    @pytest.mark.asyncio
    async def test_get_monthplan_with_spreadsheet_id(self, mock_sheets_client):
        """Should get monthplan data with spreadsheet_id"""
        response = {
            "ok": True,
            "op": "planner.monthplan.get",
            "data": {
                "items": [
                    {
                        "row": 4,
                        "book_id": "gMA001",
                        "subject": "数学",
                        "title": "青チャート",
                        "weeks": {1: 3, 2: 2, 3: 4, 4: 3, 5: 2},
                        "row_total": 14,
                    }
                ],
                "week_totals": {1: 3, 2: 2, 3: 4, 4: 3, 5: 2},
                "grand_total": 14,
                "count": 1,
            }
        }
        mock_handler = MagicMock()
        mock_handler.monthplan_get.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await monthplan_get(spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            data = result.get("data", {})
            assert "items" in data
            assert "week_totals" in data
            assert "grand_total" in data

    @pytest.mark.asyncio
    async def test_get_monthplan_with_student_id(self, mock_sheets_client):
        """Should get monthplan data with student_id"""
        response = {
            "ok": True,
            "op": "planner.monthplan.get",
            "data": {"items": [], "week_totals": {}, "grand_total": 0, "count": 0}
        }
        mock_handler = MagicMock()
        mock_handler.monthplan_get.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            result = await monthplan_get(student_id="S001")
            assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_get_monthplan_requires_identifier(self):
        """Should require student_id or spreadsheet_id"""
        result = await monthplan_get()
        assert result.get("ok") is False
        assert "error" in result


class TestMonthplanSet:
    """Tests for monthplan_set tool"""

    @pytest.mark.asyncio
    async def test_set_monthplan(self, mock_sheets_client):
        """Should set monthplan hours"""
        response = {
            "ok": True,
            "op": "planner.monthplan.set",
            "data": {
                "updated": True,
                "results": [
                    {"row": 4, "week": 1, "ok": True, "cell": "D4"},
                    {"row": 4, "week": 2, "ok": True, "cell": "E4"},
                ]
            }
        }
        mock_handler = MagicMock()
        mock_handler.monthplan_set.return_value = response
        with patch("server.get_sheets_client", return_value=mock_sheets_client), \
             patch("server.PlannerHandler", return_value=mock_handler):
            items = [
                {"row": 4, "week": 1, "hours": 3},
                {"row": 4, "week": 2, "hours": 2},
            ]
            result = await monthplan_set(items=items, spreadsheet_id="test-sheet-id")
            assert result.get("ok") is True
            assert result.get("data", {}).get("updated") is True

    @pytest.mark.asyncio
    async def test_set_monthplan_requires_identifier(self):
        """Should require student_id or spreadsheet_id"""
        result = await monthplan_set(items=[{"row": 4, "week": 1, "hours": 3}])
        assert result.get("ok") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_set_monthplan_requires_items_list(self):
        """Should require items to be a list"""
        result = await monthplan_set(items="invalid", spreadsheet_id="test-sheet-id")
        assert result.get("ok") is False
        assert "error" in result
