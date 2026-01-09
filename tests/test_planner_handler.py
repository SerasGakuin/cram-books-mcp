"""
Tests for PlannerHandler class.
TDD tests for the new OOP-based PlannerHandler implementation.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestPlannerHandlerInit:
    """Tests for PlannerHandler initialization."""

    def test_init_accepts_sheets_client(self):
        """Should accept a SheetsClient instance."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        handler = PlannerHandler(mock_sheets)

        assert handler.sheets == mock_sheets


class TestPlannerHandlerResolve:
    """Tests for planner sheet resolution."""

    def test_resolve_with_direct_spreadsheet_id(self):
        """Should use direct spreadsheet_id if provided."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()

        handler = PlannerHandler(mock_sheets)
        result = handler.resolve_planner(spreadsheet_id="direct-id-12345")

        assert result.file_id == "direct-id-12345"
        assert result.error is None

    def test_resolve_from_student_id(self):
        """Should resolve spreadsheet_id from student's planner link."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前", "スプレッドシート"],
            ["s001", "田中太郎", "https://docs.google.com/spreadsheets/d/1abc-XYZ_123456789012345678901234567890/edit"],
        ]
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()

        handler = PlannerHandler(mock_sheets)
        result = handler.resolve_planner(student_id="s001")

        assert result.file_id == "1abc-XYZ_123456789012345678901234567890"

    def test_resolve_not_found(self):
        """Should return error when planner not found."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["生徒ID", "名前"],
            ["s001", "田中太郎"],
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.resolve_planner(student_id="s999")

        assert result.error is not None


class TestPlannerHandlerIdsList:
    """Tests for ids_list method."""

    def test_ids_list_returns_items(self):
        """Should return planner items from ABCD columns."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [
            ["261gMA001", "数学", "青チャート", "1日2問"],
            ["261gEN001", "英語", "長文読解", "1日1題"],
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.ids_list(spreadsheet_id="test-id")

        assert result["ok"] is True
        assert len(result["data"]["items"]) == 2
        assert result["data"]["items"][0]["book_id"] == "gMA001"
        assert result["data"]["items"][0]["subject"] == "数学"


class TestPlannerHandlerDates:
    """Tests for dates_get and dates_set methods."""

    def test_dates_get_returns_week_starts(self):
        """Should return week start dates from header row."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_cell.side_effect = ["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27", "2025-02-03"]

        handler = PlannerHandler(mock_sheets)
        result = handler.dates_get(spreadsheet_id="test-id")

        assert result["ok"] is True
        assert len(result["data"]["week_starts"]) == 5
        assert result["data"]["week_starts"][0] == "2025-01-06"

    def test_dates_set_requires_start_date(self):
        """Should return error when start_date is missing."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        handler = PlannerHandler(mock_sheets)

        result = handler.dates_set("", spreadsheet_id="test-id")

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_dates_set_updates_cell(self):
        """Should update the first week start date cell."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()

        handler = PlannerHandler(mock_sheets)
        result = handler.dates_set("2025-01-06", spreadsheet_id="test-id")

        assert result["ok"] is True
        assert result["data"]["updated"] is True
        mock_sheets.update_cell.assert_called()


class TestPlannerHandlerMetrics:
    """Tests for metrics_get method."""

    def test_metrics_get_returns_weeks(self):
        """Should return metrics for each week."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        # Return mock data for each week's range
        mock_sheets.get_range.return_value = [
            ["60", "5", "10"],  # Row 4: 60 min, 5 units, 10 guideline
            ["30", "3", "5"],   # Row 5
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.metrics_get(spreadsheet_id="test-id")

        assert result["ok"] is True
        assert len(result["data"]["weeks"]) == 5


class TestPlannerHandlerPlanGet:
    """Tests for plan_get method."""

    def test_plan_get_returns_weeks(self):
        """Should return plan text for each week."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [
            ["1-10"],  # Row 4
            ["11-20"], # Row 5
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.plan_get(spreadsheet_id="test-id")

        assert result["ok"] is True
        assert len(result["data"]["weeks"]) == 5


class TestPlannerHandlerPlanSet:
    """Tests for plan_set method."""

    def test_plan_set_single_mode(self):
        """Should set plan text in single mode."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [["261gMA001", "数学", "青チャート", ""]]
        mock_sheets.get_cell.side_effect = ["261gMA001", "60", ""]  # A, time, plan

        handler = PlannerHandler(mock_sheets)
        result = handler.plan_set(
            week_index=1,
            plan_text="1-10",
            row=4,
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        assert result["data"]["updated"] is True

    def test_plan_set_rejects_too_long(self):
        """Should reject plan_text that exceeds max length."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [["261gMA001", "数学", "青チャート", ""]]

        handler = PlannerHandler(mock_sheets)
        result = handler.plan_set(
            week_index=1,
            plan_text="x" * 100,  # Too long
            row=4,
            spreadsheet_id="test-id"
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "TOO_LONG"

    def test_plan_set_validates_week_index(self):
        """Should validate week_index is 1-5."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [["261gMA001", "数学", "青チャート", ""]]

        handler = PlannerHandler(mock_sheets)
        result = handler.plan_set(
            week_index=6,  # Invalid
            plan_text="1-10",
            row=4,
            spreadsheet_id="test-id"
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_plan_set_batch_mode(self):
        """Should set multiple plan texts in batch mode."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = MagicMock()
        mock_sheets.get_range.return_value = [["261gMA001", "数学", "青チャート", ""]]
        mock_sheets.get_cell.side_effect = ["261gMA001", "60", ""] * 3  # Repeated for multiple items

        handler = PlannerHandler(mock_sheets)
        result = handler.plan_set(
            items=[
                {"week_index": 1, "row": 4, "plan_text": "1-10"},
                {"week_index": 2, "row": 4, "plan_text": "11-20"},
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True


class TestPlannerHandlerMonthlyFilter:
    """Tests for monthly_filter method."""

    def test_monthly_filter_by_year_month(self):
        """Should filter monthly planner by year and month."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_ws = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        # monthly_filter directly opens the monthly sheet by name
        mock_ss.worksheet.return_value = mock_ws
        mock_ws.get_all_values.return_value = [
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "25", "1", "", "", "", "gMA001", "数学", "青チャート", "note", "5", "60", "10", "A", "B", "C", "D", "E"],
            ["code2", "25", "2", "", "", "", "gEN001", "英語", "長文", "note", "3", "30", "5", "X", "Y", "Z", "", ""],
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(year=2025, month=1, spreadsheet_id="test-id")

        assert result["ok"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["items"][0]["book_id"] == "gMA001"

    def test_monthly_filter_normalizes_year(self):
        """Should normalize 4-digit year to 2-digit."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_ws = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        # monthly_filter directly opens the monthly sheet by name
        mock_ss.worksheet.return_value = mock_ws
        mock_ws.get_all_values.return_value = [
            ["ID", "年", "月"],
            ["code1", "25", "1"],
        ]

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(year=2025, month=1, spreadsheet_id="test-id")

        assert result["ok"] is True
        assert result["data"]["year"] == 25

    def test_monthly_filter_validates_month(self):
        """Should validate month is 1-12."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        handler = PlannerHandler(mock_sheets)

        result = handler.monthly_filter(year=2025, month=13, spreadsheet_id="test-id")

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"


class TestPlannerHandlerBookCodeParsing:
    """Tests for book code parsing logic."""

    def test_parse_book_code_with_valid_format(self):
        """Should parse month code and book ID from A column."""
        from handlers.planner import _parse_book_code

        result = _parse_book_code("261gMA001")

        assert result["month_code"] == 261
        assert result["book_id"] == "gMA001"

    def test_parse_book_code_with_4digit_month(self):
        """Should handle 4-digit month codes."""
        from handlers.planner import _parse_book_code

        result = _parse_book_code("2512gMA001")

        assert result["month_code"] == 2512
        assert result["book_id"] == "gMA001"

    def test_parse_book_code_empty(self):
        """Should handle empty input."""
        from handlers.planner import _parse_book_code

        result = _parse_book_code("")

        assert result["month_code"] is None
        assert result["book_id"] == ""

    def test_parse_book_code_no_prefix(self):
        """Should handle input without month code prefix."""
        from handlers.planner import _parse_book_code

        result = _parse_book_code("gMA001")

        assert result["month_code"] is None
        assert result["book_id"] == "gMA001"


class TestPlannerHandlerMonthlyFilterMultiple:
    """Tests for multiple year-months batch retrieval."""

    def _make_mock_sheets_with_data(self, data: list[list]):
        """Helper to create mock sheets with monthly data."""
        mock_sheets = MagicMock()
        mock_ss = MagicMock()
        mock_ws = MagicMock()
        mock_sheets.open_by_id.return_value = mock_ss
        mock_ss.worksheet.return_value = mock_ws
        mock_ws.get_all_values.return_value = data
        return mock_sheets

    def test_multiple_year_months_returns_combined_items(self):
        """Should return combined items from multiple months."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "25", "6", "", "", "", "gMA001", "数学", "青チャート", "note", "5", "60", "10", "A", "B", "C", "D", "E"],
            ["code2", "25", "7", "", "", "", "gEN001", "英語", "長文", "note", "3", "30", "5", "X", "Y", "Z", "", ""],
            ["code3", "25", "8", "", "", "", "gPH001", "物理", "力学", "note", "4", "45", "8", "1", "2", "3", "4", "5"],
        ])

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(
            year_months=[
                {"year": 2025, "month": 6},
                {"year": 2025, "month": 7},
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        assert result["data"]["count"] == 2
        # Items from both months
        book_ids = [item["book_id"] for item in result["data"]["items"]]
        assert "gMA001" in book_ids
        assert "gEN001" in book_ids
        assert "gPH001" not in book_ids  # Month 8 not requested

    def test_multiple_year_months_includes_by_month(self):
        """Should include by_month dict for easy access."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "25", "6", "", "", "", "gMA001", "数学", "青チャート", "", "", "", "", "", "", "", "", ""],
            ["code2", "25", "7", "", "", "", "gEN001", "英語", "長文", "", "", "", "", "", "", "", "", ""],
        ])

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(
            year_months=[
                {"year": 2025, "month": 6},
                {"year": 2025, "month": 7},
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        assert "by_month" in result["data"]
        assert "25-06" in result["data"]["by_month"]
        assert "25-07" in result["data"]["by_month"]
        assert len(result["data"]["by_month"]["25-06"]) == 1
        assert len(result["data"]["by_month"]["25-07"]) == 1

    def test_multiple_year_months_includes_year_months_in_response(self):
        """Should include requested year_months in response."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月"],
            ["code1", "25", "6"],
        ])

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(
            year_months=[
                {"year": 2025, "month": 6},
                {"year": 2025, "month": 7},
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        assert "year_months" in result["data"]
        assert len(result["data"]["year_months"]) == 2
        assert {"year": 25, "month": 6} in result["data"]["year_months"]
        assert {"year": 25, "month": 7} in result["data"]["year_months"]

    def test_empty_year_months_returns_error(self):
        """Should return error when year_months is empty list."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        handler = PlannerHandler(mock_sheets)

        result = handler.monthly_filter(
            year_months=[],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_invalid_year_month_in_list_returns_error(self):
        """Should return error when year_months contains invalid entry."""
        from handlers.planner import PlannerHandler

        mock_sheets = MagicMock()
        handler = PlannerHandler(mock_sheets)

        result = handler.monthly_filter(
            year_months=[
                {"year": 2025, "month": 13},  # Invalid month
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_backward_compatible_single_month(self):
        """Should maintain backward compatibility with year/month params."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "25", "6", "", "", "", "gMA001", "数学", "青チャート", "", "", "", "", "", "", "", "", ""],
        ])

        handler = PlannerHandler(mock_sheets)
        # Use old-style parameters
        result = handler.monthly_filter(year=2025, month=6, spreadsheet_id="test-id")

        assert result["ok"] is True
        assert result["data"]["year"] == 25
        assert result["data"]["month"] == 6
        assert result["data"]["count"] == 1

    def test_year_months_takes_precedence_over_year_month(self):
        """When both year_months and year/month provided, year_months wins."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "25", "6", "", "", "", "gMA001", "数学", "青チャート", "", "", "", "", "", "", "", "", ""],
            ["code2", "25", "7", "", "", "", "gEN001", "英語", "長文", "", "", "", "", "", "", "", "", ""],
        ])

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(
            year=2025,
            month=6,
            year_months=[{"year": 2025, "month": 7}],  # Should use this
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        # Should have year_months in response (multi-month mode)
        assert "year_months" in result["data"]
        assert result["data"]["count"] == 1
        assert result["data"]["items"][0]["book_id"] == "gEN001"  # Month 7

    def test_cross_year_retrieval(self):
        """Should handle retrieval across different years."""
        from handlers.planner import PlannerHandler

        mock_sheets = self._make_mock_sheets_with_data([
            ["ID", "年", "月", "D", "E", "F", "書籍ID", "教科", "タイトル", "備考", "負荷", "月時間", "目安量", "W1", "W2", "W3", "W4", "W5"],
            ["code1", "24", "12", "", "", "", "gMA001", "数学", "青チャート", "", "", "", "", "", "", "", "", ""],
            ["code2", "25", "1", "", "", "", "gEN001", "英語", "長文", "", "", "", "", "", "", "", "", ""],
        ])

        handler = PlannerHandler(mock_sheets)
        result = handler.monthly_filter(
            year_months=[
                {"year": 2024, "month": 12},
                {"year": 2025, "month": 1},
            ],
            spreadsheet_id="test-id"
        )

        assert result["ok"] is True
        assert result["data"]["count"] == 2
        assert "24-12" in result["data"]["by_month"]
        assert "25-01" in result["data"]["by_month"]
