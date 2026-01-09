"""
Planner (monthly) handler.
Ported from apps/gas/src/handlers/planner_monthly.ts

Provides reading operations for monthly planner sheets.
"""
from typing import Any

from sheets_client import SheetsClient
from config import MONTHLY_SHEET_NAME
from lib.common import ok, ng, to_number_or_none
from .planner import resolve_planner_sheet_id


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


def planner_monthly_filter(
    sheets: SheetsClient,
    year: int,
    month: int,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
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

    resolved_id = resolve_planner_sheet_id(sheets, student_id, spreadsheet_id)
    if not resolved_id:
        return ng("planner.monthly.filter", "NOT_FOUND", "monthly sheet not found (月間管理)")

    try:
        ss = sheets.open_by_id(resolved_id)
        ws = ss.worksheet(MONTHLY_SHEET_NAME)
    except Exception as e:
        return ng("planner.monthly.filter", "NOT_FOUND", f"monthly sheet not found: {e}")

    try:
        # Read from row 2 to the end, columns A to R (18 columns)
        all_values = ws.get_all_values()
        if len(all_values) <= 1:
            return ok("planner.monthly.filter", {"year": yy, "month": mm, "items": [], "count": 0})

        values = all_values[1:]  # Skip header row

        items = []
        for i, row in enumerate(values):
            r = i + 2  # Sheet row number

            # Extract basic columns
            a = str(row[0]) if len(row) > 0 else ""
            b = str(row[1]).strip() if len(row) > 1 else ""
            c = str(row[2]).strip() if len(row) > 2 else ""

            if not a and not b and not c:
                continue  # Skip empty rows

            # Parse year/month from B/C columns
            try:
                b_num = int(b) if b else None
                c_num = int(c) if c else None
            except ValueError:
                continue

            if b_num != yy or c_num != mm:
                continue

            # Extract additional columns (G-R)
            book_id = str(row[6]) if len(row) > 6 else ""      # G
            subject = str(row[7]) if len(row) > 7 else ""      # H
            title = str(row[8]) if len(row) > 8 else ""        # I
            guideline_note = str(row[9]) if len(row) > 9 else ""  # J
            unit_load = to_number_or_none(row[10]) if len(row) > 10 else None  # K
            monthly_minutes = to_number_or_none(row[11]) if len(row) > 11 else None  # L
            guideline_amount = to_number_or_none(row[12]) if len(row) > 12 else None  # M

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

        return ok("planner.monthly.filter", {
            "year": yy,
            "month": mm,
            "items": items,
            "count": len(items),
        })
    except Exception as e:
        return ng("planner.monthly.filter", "ERROR", str(e))
