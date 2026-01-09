"""
Planner handler class.
OOP-based implementation combining weekly and monthly planner operations.

Provides reading and writing operations for planner sheets.
"""
from __future__ import annotations

import re
from typing import Any, NamedTuple

from sheets_client import SheetsClient
from config import (
    STUDENTS_MASTER_ID,
    STUDENTS_SHEET,
    STUDENT_COLUMNS,
    WEEKLY_SHEET_NAMES,
    MONTHLY_SHEET_NAME,
    MONTHPLAN_SHEET_NAME,
    MONTHPLAN_WEEK_COLUMNS,
    WEEK_METRICS_COLUMNS,
    WEEK_START_CELLS,
    PLANNER_START_ROW,
    PLANNER_END_ROW,
    PLAN_TEXT_MAX_LENGTH,
)
from lib.common import ok, ng, to_number_or_none
from lib.sheet_utils import pick_col, norm_header, extract_spreadsheet_id


class PlannerSheetResult(NamedTuple):
    """Result of resolving and opening a planner sheet."""
    file_id: str | None
    sheet_name: str | None
    error: dict | None


def _parse_book_code(raw: str) -> dict[str, Any]:
    """
    Parse A column code like '261gEC001' into month_code and book_id.

    Args:
        raw: Raw code string from A column

    Returns:
        Dict with month_code (int or None) and book_id (str)
    """
    s = str(raw or "").strip()
    if not s:
        return {"month_code": None, "book_id": ""}

    match = re.match(r"^(\d{3,4})(.+)$", s)
    if not match:
        return {"month_code": None, "book_id": s}

    code = int(match.group(1))
    book_id = match.group(2)
    return {"month_code": code, "book_id": book_id}


def _norm_year_2digit(year: Any) -> int | None:
    """Normalize year to 2-digit format (e.g., 2025 -> 25)."""
    try:
        n = int(str(year).strip())
        if n >= 2000:
            return n - 2000
        if 0 <= n <= 99:
            return n
        return None
    except (ValueError, TypeError):
        return None


class PlannerHandler:
    """
    Handler for planner-related operations.

    Combines weekly and monthly planner functionality:
    - ids_list: List planner items (ABCD columns)
    - dates_get/set: Week start dates
    - metrics_get: Weekly time/units/guidelines
    - plan_get/set: Weekly plan text
    - monthly_filter: Monthly planner filtering
    """

    def __init__(self, sheets: SheetsClient) -> None:
        """Initialize PlannerHandler with a SheetsClient."""
        self.sheets = sheets

    # === Planner Resolution ===

    def resolve_planner(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
        op_name: str = "planner",
    ) -> PlannerSheetResult:
        """
        Resolve and open a planner sheet.

        Priority:
        1. spreadsheet_id if provided
        2. Look up student's planner_sheet_id from Students Master

        Args:
            student_id: Optional student ID to resolve
            spreadsheet_id: Optional direct spreadsheet ID
            op_name: Operation name for error messages

        Returns:
            PlannerSheetResult with (file_id, sheet_name, None) on success,
            or (None, None, error_dict) on failure.
        """
        resolved_id = self._resolve_spreadsheet_id(student_id, spreadsheet_id)
        if not resolved_id:
            return PlannerSheetResult(
                None,
                None,
                ng(op_name, "NOT_FOUND", "planner sheet not found (resolve by student_id or spreadsheet_id)"),
            )

        sheet_name = self._find_weekly_sheet(resolved_id)
        if not sheet_name:
            return PlannerSheetResult(
                None,
                None,
                ng(op_name, "NOT_FOUND", "planner sheet not found"),
            )

        return PlannerSheetResult(resolved_id, sheet_name, None)

    def _resolve_spreadsheet_id(
        self,
        student_id: str | None,
        spreadsheet_id: str | None,
    ) -> str | None:
        """Resolve the spreadsheet ID from direct ID or student lookup."""
        if spreadsheet_id:
            return str(spreadsheet_id)

        if not student_id:
            return None

        student_id = str(student_id).strip()

        try:
            values = self.sheets.get_all_values(STUDENTS_MASTER_ID, STUDENTS_SHEET)
            if len(values) < 2:
                return None

            headers = [str(h) for h in values[0]]
            idx_id = pick_col(headers, STUDENT_COLUMNS["id"])
            idx_planner = pick_col(headers, STUDENT_COLUMNS["planner_sheet_id"])
            idx_link = pick_col(headers, STUDENT_COLUMNS["planner_link"])

            # Fallback: search for columns containing planner keywords
            if idx_link < 0:
                normalized = [norm_header(h) for h in headers]
                for i, nh in enumerate(normalized):
                    if "スプレッドシート" in nh or "planner" in nh or "プランナー" in nh:
                        idx_link = i
                        break

            for row in values[1:]:
                id_val = str(row[idx_id]).strip() if idx_id >= 0 and idx_id < len(row) else ""
                if id_val != student_id:
                    continue

                # Try planner_sheet_id column
                if idx_planner >= 0 and idx_planner < len(row):
                    planner_id = str(row[idx_planner]).strip()
                    if planner_id:
                        return planner_id

                # Try link column
                if idx_link >= 0 and idx_link < len(row):
                    link = str(row[idx_link]).strip()
                    extracted = extract_spreadsheet_id(link)
                    if extracted:
                        return extracted

                return None

            return None
        except Exception:
            return None

    def _find_weekly_sheet(self, spreadsheet_id: str) -> str | None:
        """Find the weekly planner sheet name in a spreadsheet."""
        try:
            ss = self.sheets.open_by_id(spreadsheet_id)

            # Try known sheet names
            for name in WEEKLY_SHEET_NAMES:
                try:
                    ss.worksheet(name)
                    return name
                except Exception:
                    continue

            # Scan sheets for planner pattern (A4 matches month code + ID pattern)
            for ws in ss.worksheets():
                try:
                    a4 = ws.acell("A4").value
                    if a4 and re.match(r"^\d{3,4}.+", str(a4).strip()):
                        return ws.title
                except Exception:
                    continue

            return None
        except Exception:
            return None

    # === Weekly Operations ===

    def ids_list(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """
        List planner items (A/B/C/D columns).

        Returns raw codes, book IDs, subjects, titles, and guideline notes.
        """
        result = self.resolve_planner(student_id, spreadsheet_id, "planner.ids_list")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        try:
            abcd = self.sheets.get_range(fid, sname, "A4:D30")
        except Exception as e:
            return ng("planner.ids_list", "ERROR", str(e))

        items = []
        for i, row in enumerate(abcd):
            r = PLANNER_START_ROW + i
            a = str(row[0]).strip() if len(row) > 0 else ""
            if not a:
                break  # Stop at first empty A cell

            b = str(row[1]).strip() if len(row) > 1 else ""
            c = str(row[2]).strip() if len(row) > 2 else ""
            d = str(row[3]).strip() if len(row) > 3 else ""

            parsed = _parse_book_code(a)
            items.append({
                "row": r,
                "raw_code": a,
                "month_code": parsed["month_code"],
                "book_id": parsed["book_id"],
                "subject": b,
                "title": c,
                "guideline_note": d,
            })

        return ok("planner.ids_list", {"count": len(items), "items": items})

    def dates_get(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """Get week start dates (D1/L1/T1/AB1/AJ1)."""
        result = self.resolve_planner(student_id, spreadsheet_id, "planner.dates.get")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        try:
            week_starts = []
            for cell_addr in WEEK_START_CELLS:
                val = self.sheets.get_cell(fid, sname, cell_addr)
                week_starts.append(str(val) if val else "")

            return ok("planner.dates.get", {"week_starts": week_starts})
        except Exception as e:
            return ng("planner.dates.get", "ERROR", str(e))

    def dates_set(
        self,
        start_date: str,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """Set the first week start date (D1)."""
        if not start_date:
            return ng("planner.dates.set", "BAD_REQUEST", "start_date is required (YYYY-MM-DD)")

        result = self.resolve_planner(student_id, spreadsheet_id, "planner.dates.set")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        try:
            self.sheets.update_cell(fid, sname, "D1", start_date)
            return ok("planner.dates.set", {"updated": True})
        except Exception as e:
            return ng("planner.dates.set", "ERROR", str(e))

    def metrics_get(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """Get metrics for each week (weekly_minutes, unit_load, guideline_amount)."""
        result = self.resolve_planner(student_id, spreadsheet_id, "planner.metrics.get")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        try:
            weeks = []
            for week_idx in range(1, 6):
                cols = WEEK_METRICS_COLUMNS[week_idx]
                range_notation = f"{cols['time']}{PLANNER_START_ROW}:{cols['guide']}{PLANNER_END_ROW}"
                vals = self.sheets.get_range(fid, sname, range_notation)

                items = []
                for j, row in enumerate(vals):
                    r = PLANNER_START_ROW + j
                    items.append({
                        "row": r,
                        "weekly_minutes": to_number_or_none(row[0]) if len(row) > 0 else None,
                        "unit_load": to_number_or_none(row[1]) if len(row) > 1 else None,
                        "guideline_amount": to_number_or_none(row[2]) if len(row) > 2 else None,
                    })

                weeks.append({
                    "week_index": week_idx,
                    "column_time": cols["time"],
                    "column_unit": cols["unit"],
                    "column_guide": cols["guide"],
                    "items": items,
                })

            return ok("planner.metrics.get", {"weeks": weeks})
        except Exception as e:
            return ng("planner.metrics.get", "ERROR", str(e))

    def plan_get(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """Get plan text for each week (H/P/X/AF/AN columns)."""
        result = self.resolve_planner(student_id, spreadsheet_id, "planner.plan.get")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        try:
            weeks = []
            for week_idx in range(1, 6):
                col = WEEK_METRICS_COLUMNS[week_idx]["plan"]
                range_notation = f"{col}{PLANNER_START_ROW}:{col}{PLANNER_END_ROW}"
                vals = self.sheets.get_range(fid, sname, range_notation)

                items = []
                for j, row in enumerate(vals):
                    r = PLANNER_START_ROW + j
                    items.append({
                        "row": r,
                        "plan_text": str(row[0]).strip() if len(row) > 0 and row[0] else "",
                    })

                weeks.append({
                    "week_index": week_idx,
                    "column": col,
                    "items": items,
                })

            return ok("planner.plan.get", {"weeks": weeks})
        except Exception as e:
            return ng("planner.plan.get", "ERROR", str(e))

    def plan_set(
        self,
        week_index: int | None = None,
        plan_text: str | None = None,
        row: int | None = None,
        book_id: str | None = None,
        overwrite: bool = False,
        items: list[dict] | None = None,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Set plan text for a week.

        Can operate in single mode (week_index + row/book_id) or batch mode (items).
        """
        result = self.resolve_planner(student_id, spreadsheet_id, "planner.plan.set")
        if result.error:
            return result.error

        fid, sname = result.file_id, result.sheet_name

        # Read ABCD for book_id resolution
        try:
            abcd = self.sheets.get_range(fid, sname, "A4:D30")
        except Exception as e:
            return ng("planner.plan.set", "ERROR", str(e))

        # Build book_id -> row map
        book_row_map = self._build_book_row_map(abcd)

        # Single mode
        if items is None:
            return self._plan_set_single(fid, sname, week_index, plan_text, row, book_id, overwrite, book_row_map)

        # Batch mode
        return self._plan_set_batch(fid, sname, items, overwrite, book_row_map)

    def _build_book_row_map(self, abcd: list[list]) -> dict[str, int]:
        """Build a mapping from book_id to row number."""
        book_row_map = {}
        for i, abcd_row in enumerate(abcd):
            a = str(abcd_row[0]).strip() if len(abcd_row) > 0 else ""
            if not a:
                break
            parsed = _parse_book_code(a)
            if parsed["book_id"]:
                book_row_map[parsed["book_id"]] = PLANNER_START_ROW + i
        return book_row_map

    def _plan_set_single(
        self,
        fid: str,
        sname: str,
        week_index: int | None,
        plan_text: str | None,
        row: int | None,
        book_id: str | None,
        overwrite: bool,
        book_row_map: dict[str, int],
    ) -> dict[str, Any]:
        """Set plan text in single mode."""
        if not week_index or week_index < 1 or week_index > 5:
            return ng("planner.plan.set", "BAD_REQUEST", "week_index must be 1..5")

        text = str(plan_text or "")
        if len(text) > PLAN_TEXT_MAX_LENGTH:
            return ng("planner.plan.set", "TOO_LONG", f"plan_text must be <= {PLAN_TEXT_MAX_LENGTH} chars")

        # Resolve row
        target_row = row
        if not target_row and book_id:
            target_row = book_row_map.get(str(book_id))

        if not target_row:
            return ng("planner.plan.set", "ROW_NOT_FOUND", "row or book_id did not match any row")

        cols = WEEK_METRICS_COLUMNS[week_index]

        try:
            # Check preconditions
            a_val = self.sheets.get_cell(fid, sname, f"A{target_row}")
            if not str(a_val or "").strip():
                return ng("planner.plan.set", "PRECONDITION_A_EMPTY", "A[row] must not be empty")

            time_val = self.sheets.get_cell(fid, sname, f"{cols['time']}{target_row}")
            if not str(time_val or "").strip():
                return ng("planner.plan.set", "PRECONDITION_TIME_EMPTY",
                         f"weekly_minutes cell ({cols['time']}{target_row}) must not be empty")

            # Check existing
            plan_cell = f"{cols['plan']}{target_row}"
            current = str(self.sheets.get_cell(fid, sname, plan_cell) or "").strip()
            if not overwrite and current:
                return ng("planner.plan.set", "ALREADY_EXISTS", "cell already has text; set overwrite=true to replace")

            self.sheets.update_cell(fid, sname, plan_cell, text)
            return ok("planner.plan.set", {"updated": True, "cell": plan_cell})
        except Exception as e:
            return ng("planner.plan.set", "ERROR", str(e))

    def _plan_set_batch(
        self,
        fid: str,
        sname: str,
        items: list[dict],
        default_overwrite: bool,
        book_row_map: dict[str, int],
    ) -> dict[str, Any]:
        """Set plan text in batch mode."""
        results = []
        updates_by_col: dict[str, list[tuple[int, str]]] = {}

        for item in items:
            wk = item.get("week_index")
            txt = str(item.get("plan_text", ""))
            ow = item.get("overwrite", default_overwrite)

            if not wk or wk < 1 or wk > 5:
                results.append({"ok": False, "error": {"code": "BAD_WEEK", "message": "week_index must be 1..5"}})
                continue

            if len(txt) > PLAN_TEXT_MAX_LENGTH:
                results.append({"ok": False, "error": {"code": "TOO_LONG",
                               "message": f"plan_text must be <= {PLAN_TEXT_MAX_LENGTH} chars"}})
                continue

            # Resolve row
            target_row = item.get("row")
            if not target_row and item.get("book_id"):
                target_row = book_row_map.get(str(item["book_id"]))

            if not target_row:
                results.append({"ok": False, "error": {"code": "ROW_NOT_FOUND", "message": "row or book_id did not match"}})
                continue

            cols = WEEK_METRICS_COLUMNS[wk]
            cell_a1 = f"{cols['plan']}{target_row}"

            try:
                # Check preconditions
                a_val = self.sheets.get_cell(fid, sname, f"A{target_row}")
                if not str(a_val or "").strip():
                    results.append({"ok": False, "error": {"code": "PRECONDITION_A_EMPTY", "message": "A[row] must not be empty"}})
                    continue

                time_val = self.sheets.get_cell(fid, sname, f"{cols['time']}{target_row}")
                if not str(time_val or "").strip():
                    results.append({"ok": False, "error": {"code": "PRECONDITION_TIME_EMPTY", "message": "weekly_minutes cell empty"}})
                    continue

                current = str(self.sheets.get_cell(fid, sname, cell_a1) or "").strip()
                if not ow and current:
                    results.append({"ok": False, "cell": cell_a1, "error": {"code": "ALREADY_EXISTS", "message": "cell already has text"}})
                    continue

                # Add to updates
                col = cols["plan"]
                if col not in updates_by_col:
                    updates_by_col[col] = []
                updates_by_col[col].append((target_row, txt))
                results.append({"ok": True, "cell": cell_a1})
            except Exception as e:
                results.append({"ok": False, "error": {"code": "ERROR", "message": str(e)}})

        # Apply batch updates
        for col, row_vals in updates_by_col.items():
            for target_row, txt in row_vals:
                try:
                    self.sheets.update_cell(fid, sname, f"{col}{target_row}", txt)
                except Exception:
                    pass  # Already logged in results

        return ok("planner.plan.set", {"updated": True, "results": results})

    # === Monthly Operations ===

    def monthly_filter(
        self,
        year: int,
        month: int,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Filter monthly planner data by year and month.

        Args:
            year: Year (2-digit or 4-digit)
            month: Month (1-12)
            student_id: Student ID for resolving spreadsheet
            spreadsheet_id: Direct spreadsheet ID

        Returns:
            Items matching the specified year/month
        """
        yy = _norm_year_2digit(year)
        try:
            mm = int(str(month).strip())
            if mm < 1 or mm > 12:
                mm = None
        except (ValueError, TypeError):
            mm = None

        if yy is None or mm is None:
            return ng("planner.monthly.filter", "BAD_REQUEST", "year(2桁/4桁) と month(1..12) を指定してください")

        # Resolve spreadsheet
        resolved_id = self._resolve_spreadsheet_id(student_id, spreadsheet_id)
        if not resolved_id:
            return ng("planner.monthly.filter", "NOT_FOUND", "monthly sheet not found (月間管理)")

        try:
            ss = self.sheets.open_by_id(resolved_id)
            ws = ss.worksheet(MONTHLY_SHEET_NAME)
        except Exception as e:
            return ng("planner.monthly.filter", "NOT_FOUND", f"monthly sheet not found: {e}")

        try:
            all_values = ws.get_all_values()
            if len(all_values) <= 1:
                return ok("planner.monthly.filter", {"year": yy, "month": mm, "items": [], "count": 0})

            items = self._parse_monthly_rows(all_values[1:], yy, mm)

            return ok("planner.monthly.filter", {
                "year": yy,
                "month": mm,
                "items": items,
                "count": len(items),
            })
        except Exception as e:
            return ng("planner.monthly.filter", "ERROR", str(e))

    def _parse_monthly_rows(self, rows: list[list], target_year: int, target_month: int) -> list[dict]:
        """Parse monthly planner rows and filter by year/month."""
        items = []

        for i, row in enumerate(rows):
            r = i + 2  # Sheet row number

            a = str(row[0]) if len(row) > 0 else ""
            b = str(row[1]).strip() if len(row) > 1 else ""
            c = str(row[2]).strip() if len(row) > 2 else ""

            if not a and not b and not c:
                continue

            try:
                b_num = int(b) if b else None
                c_num = int(c) if c else None
            except ValueError:
                continue

            if b_num != target_year or c_num != target_month:
                continue

            # Extract additional columns (G-R)
            book_id = str(row[6]) if len(row) > 6 else ""
            subject = str(row[7]) if len(row) > 7 else ""
            title = str(row[8]) if len(row) > 8 else ""
            guideline_note = str(row[9]) if len(row) > 9 else ""
            unit_load = to_number_or_none(row[10]) if len(row) > 10 else None
            monthly_minutes = to_number_or_none(row[11]) if len(row) > 11 else None
            guideline_amount = to_number_or_none(row[12]) if len(row) > 12 else None

            # Week columns (N-R)
            weeks = []
            for j, col_idx in enumerate([13, 14, 15, 16, 17]):
                actual = str(row[col_idx]) if len(row) > col_idx else ""
                weeks.append({"index": j + 1, "actual": actual})

            # Calculate month code
            month_code = (b_num * 10 + c_num) if b_num is not None and c_num is not None else None

            items.append({
                "row": r,
                "raw_code": a,
                "month_code": month_code,
                "year": b_num,
                "month": c_num,
                "book_id": book_id,
                "subject": subject,
                "title": title,
                "guideline_note": guideline_note,
                "unit_load": unit_load,
                "monthly_minutes": monthly_minutes,
                "guideline_amount": guideline_amount,
                "weeks": weeks,
            })

        return items

    # === Monthplan Operations ===

    def _resolve_monthplan_sheet(
        self,
        student_id: str | None,
        spreadsheet_id: str | None,
        op_name: str,
    ) -> tuple[str | None, str | None, dict | None]:
        """
        Resolve the monthplan sheet.

        Returns:
            (file_id, sheet_name, error) - error is None on success
        """
        resolved_id = self._resolve_spreadsheet_id(student_id, spreadsheet_id)
        if not resolved_id:
            return None, None, ng(op_name, "NOT_FOUND", "monthplan sheet not found")

        try:
            ss = self.sheets.open_by_id(resolved_id)
            ss.worksheet(MONTHPLAN_SHEET_NAME)
            return resolved_id, MONTHPLAN_SHEET_NAME, None
        except Exception:
            return None, None, ng(op_name, "NOT_FOUND", f"sheet '{MONTHPLAN_SHEET_NAME}' not found")

    def monthplan_get(
        self,
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get the content of 「今月プラン」 sheet with summary statistics.

        Args:
            student_id: Student ID to resolve spreadsheet
            spreadsheet_id: Direct spreadsheet ID

        Returns:
            {
                "items": [
                    {
                        "row": 4,
                        "book_id": "gMA001",
                        "subject": "数学",
                        "title": "青チャート",
                        "weeks": {1: 3, 2: 2, 3: 4, 4: 3, 5: 2},
                        "row_total": 14
                    },
                    ...
                ],
                "week_totals": {1: 15, 2: 12, ...},
                "grand_total": 69,
                "count": 5
            }
        """
        op = "planner.monthplan.get"

        fid, sname, error = self._resolve_monthplan_sheet(student_id, spreadsheet_id, op)
        if error:
            return error

        try:
            # Read A4:H30
            data = self.sheets.get_range(fid, sname, "A4:H30")
        except Exception as e:
            return ng(op, "ERROR", str(e))

        items = []
        week_totals: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        grand_total = 0

        for i, row in enumerate(data):
            r = PLANNER_START_ROW + i

            # A column: book_id
            book_id = str(row[0]).strip() if len(row) > 0 else ""
            if not book_id:
                break  # Stop at first empty book_id

            # B column: subject
            subject = str(row[1]).strip() if len(row) > 1 else ""

            # C column: title
            title = str(row[2]).strip() if len(row) > 2 else ""

            # D-H columns: weekly hours
            weeks: dict[int, int] = {}
            row_total = 0
            for week_idx in range(1, 6):
                col_idx = 2 + week_idx  # D=3, E=4, F=5, G=6, H=7
                raw_val = row[col_idx] if len(row) > col_idx else ""
                hours = self._parse_hours(raw_val)
                weeks[week_idx] = hours
                row_total += hours
                week_totals[week_idx] += hours

            grand_total += row_total

            items.append({
                "row": r,
                "book_id": book_id,
                "subject": subject,
                "title": title,
                "weeks": weeks,
                "row_total": row_total,
            })

        return ok(op, {
            "items": items,
            "week_totals": week_totals,
            "grand_total": grand_total,
            "count": len(items),
        })

    def _parse_hours(self, raw: Any) -> int:
        """Parse hours value, returning 0 for empty/invalid values."""
        if raw is None or raw == "":
            return 0
        try:
            return int(str(raw).strip())
        except (ValueError, TypeError):
            return 0

    def monthplan_set(
        self,
        items: list[dict],
        student_id: str | None = None,
        spreadsheet_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Batch write weekly hours to 「今月プラン」 sheet.

        Args:
            items: List of {"row": int, "week": int (1-5), "hours": int}
            student_id: Student ID to resolve spreadsheet
            spreadsheet_id: Direct spreadsheet ID

        Returns:
            {"updated": True, "results": [{row, week, ok, error?}, ...]}
        """
        op = "planner.monthplan.set"

        if not items:
            return ng(op, "BAD_REQUEST", "items must not be empty")

        fid, sname, error = self._resolve_monthplan_sheet(student_id, spreadsheet_id, op)
        if error:
            return error

        results = []

        for item in items:
            row = item.get("row")
            week = item.get("week")
            hours = item.get("hours")

            # Validate row
            if row is None or row < PLANNER_START_ROW or row > PLANNER_END_ROW:
                results.append({
                    "row": row,
                    "week": week,
                    "ok": False,
                    "error": {"code": "BAD_ROW", "message": f"row must be {PLANNER_START_ROW}..{PLANNER_END_ROW}"},
                })
                continue

            # Validate week
            if week is None or week < 1 or week > 5:
                results.append({
                    "row": row,
                    "week": week,
                    "ok": False,
                    "error": {"code": "BAD_WEEK", "message": "week must be 1..5"},
                })
                continue

            # Validate hours
            try:
                hours_int = int(hours)
            except (ValueError, TypeError):
                results.append({
                    "row": row,
                    "week": week,
                    "ok": False,
                    "error": {"code": "BAD_HOURS", "message": "hours must be an integer"},
                })
                continue

            # Get column letter for this week
            col = MONTHPLAN_WEEK_COLUMNS[week]
            cell_a1 = f"{col}{row}"

            try:
                self.sheets.update_cell(fid, sname, cell_a1, hours_int)
                results.append({"row": row, "week": week, "ok": True, "cell": cell_a1})
            except Exception as e:
                results.append({
                    "row": row,
                    "week": week,
                    "ok": False,
                    "error": {"code": "ERROR", "message": str(e)},
                })

        return ok(op, {"updated": True, "results": results})
