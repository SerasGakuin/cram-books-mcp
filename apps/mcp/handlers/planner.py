"""
Planner (weekly) handler.
Ported from apps/gas/src/handlers/planner.ts

Provides reading and writing operations for weekly planner sheets.
"""
import re
from typing import Any, NamedTuple

from sheets_client import SheetsClient
from config import (
    STUDENTS_MASTER_ID,
    STUDENTS_SHEET,
    STUDENT_COLUMNS,
    WEEKLY_SHEET_NAMES,
    WEEK_METRICS_COLUMNS,
    WEEK_START_CELLS,
    PLANNER_START_ROW,
    PLANNER_END_ROW,
    PLAN_TEXT_MAX_LENGTH,
)
from lib.common import ok, ng, to_number_or_none
from lib.sheet_utils import pick_col, norm_header, extract_spreadsheet_id


def resolve_planner_sheet_id(
    sheets: SheetsClient,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> str | None:
    """
    Resolve planner spreadsheet ID.

    Priority:
    1. spreadsheet_id if provided
    2. Look up student's planner_sheet_id from Students Master
    """
    if spreadsheet_id:
        return str(spreadsheet_id)

    if not student_id:
        return None

    student_id = str(student_id).strip()

    try:
        values = sheets.get_all_values(STUDENTS_MASTER_ID, STUDENTS_SHEET)
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


def _open_planner_sheet(sheets: SheetsClient, spreadsheet_id: str) -> tuple[str, str] | None:
    """
    Find the weekly planner sheet in a spreadsheet.

    Returns (spreadsheet_id, sheet_name) or None.
    """
    try:
        ss = sheets.open_by_id(spreadsheet_id)

        # Try known sheet names
        for name in WEEKLY_SHEET_NAMES:
            try:
                ss.worksheet(name)
                return (spreadsheet_id, name)
            except Exception:
                continue

        # Scan sheets for planner pattern (A4 matches month code + ID pattern)
        for ws in ss.worksheets():
            try:
                a4 = ws.acell("A4").value
                if a4 and re.match(r"^\d{3,4}.+", str(a4).strip()):
                    return (spreadsheet_id, ws.title)
            except Exception:
                continue

        return None
    except Exception:
        return None


class PlannerSheetResult(NamedTuple):
    """Result of resolving and opening a planner sheet."""

    file_id: str | None
    sheet_name: str | None
    error: dict | None


def resolve_and_open_planner(
    sheets: SheetsClient,
    op_name: str,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> PlannerSheetResult:
    """
    Resolve and open a planner sheet in one step.

    Args:
        sheets: SheetsClient instance
        op_name: Operation name for error messages (e.g., "planner.ids_list")
        student_id: Optional student ID to resolve
        spreadsheet_id: Optional direct spreadsheet ID

    Returns:
        PlannerSheetResult with (file_id, sheet_name, None) on success,
        or (None, None, error_dict) on failure.
    """
    resolved_id = resolve_planner_sheet_id(sheets, student_id, spreadsheet_id)
    if not resolved_id:
        return PlannerSheetResult(
            None,
            None,
            ng(op_name, "NOT_FOUND", "planner sheet not found (resolve by student_id or spreadsheet_id)"),
        )

    sheet_info = _open_planner_sheet(sheets, resolved_id)
    if not sheet_info:
        return PlannerSheetResult(
            None,
            None,
            ng(op_name, "NOT_FOUND", "planner sheet not found"),
        )

    return PlannerSheetResult(sheet_info[0], sheet_info[1], None)


def _parse_book_code(raw: str) -> dict:
    """Parse A column code like '261gEC001' into month_code and book_id."""
    s = str(raw or "").strip()
    if not s:
        return {"month_code": None, "book_id": ""}

    match = re.match(r"^(\d{3,4})(.+)$", s)
    if not match:
        return {"month_code": None, "book_id": s}

    code = int(match.group(1))
    book_id = match.group(2)
    return {"month_code": code, "book_id": book_id}


def _read_abcd(sheets: SheetsClient, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
    """Read A4:D30 range (ABCD columns for rows 4-30)."""
    return sheets.get_range(spreadsheet_id, sheet_name, "A4:D30")


def planner_ids_list(
    sheets: SheetsClient,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """
    List planner items (A/B/C/D columns).

    Returns raw codes, book IDs, subjects, titles, and guideline notes.
    """
    result = resolve_and_open_planner(sheets, "planner.ids_list", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    try:
        abcd = _read_abcd(sheets, fid, sname)
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


def planner_dates_get(
    sheets: SheetsClient,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """Get week start dates (D1/L1/T1/AB1/AJ1)."""
    result = resolve_and_open_planner(sheets, "planner.dates.get", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    try:
        week_starts = []
        for cell_addr in WEEK_START_CELLS:
            val = sheets.get_cell(fid, sname, cell_addr)
            week_starts.append(str(val) if val else "")

        return ok("planner.dates.get", {"week_starts": week_starts})
    except Exception as e:
        return ng("planner.dates.get", "ERROR", str(e))


def planner_dates_set(
    sheets: SheetsClient,
    start_date: str,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """Set the first week start date (D1)."""
    if not start_date:
        return ng("planner.dates.set", "BAD_REQUEST", "start_date is required (YYYY-MM-DD)")

    result = resolve_and_open_planner(sheets, "planner.dates.set", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    try:
        sheets.update_cell(fid, sname, "D1", start_date)
        return ok("planner.dates.set", {"updated": True})
    except Exception as e:
        return ng("planner.dates.set", "ERROR", str(e))


def planner_metrics_get(
    sheets: SheetsClient,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """
    Get metrics for each week (weekly_minutes, unit_load, guideline_amount).
    """
    result = resolve_and_open_planner(sheets, "planner.metrics.get", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    try:
        weeks = []
        for week_idx in range(1, 6):
            cols = WEEK_METRICS_COLUMNS[week_idx]
            range_notation = f"{cols['time']}{PLANNER_START_ROW}:{cols['guide']}{PLANNER_END_ROW}"
            vals = sheets.get_range(fid, sname, range_notation)

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


def planner_plan_get(
    sheets: SheetsClient,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """
    Get plan text for each week (H/P/X/AF/AN columns).
    """
    result = resolve_and_open_planner(sheets, "planner.plan.get", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    try:
        weeks = []
        for week_idx in range(1, 6):
            col = WEEK_METRICS_COLUMNS[week_idx]["plan"]
            range_notation = f"{col}{PLANNER_START_ROW}:{col}{PLANNER_END_ROW}"
            vals = sheets.get_range(fid, sname, range_notation)

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


def planner_plan_set(
    sheets: SheetsClient,
    week_index: int | None = None,
    plan_text: str | None = None,
    row: int | None = None,
    book_id: str | None = None,
    overwrite: bool = False,
    items: list[dict] | None = None,
    student_id: str | None = None,
    spreadsheet_id: str | None = None,
) -> dict:
    """
    Set plan text for a week.

    Can operate in single mode (week_index + row/book_id) or batch mode (items).
    """
    result = resolve_and_open_planner(sheets, "planner.plan.set", student_id, spreadsheet_id)
    if result.error:
        return result.error

    fid, sname = result.file_id, result.sheet_name

    # Read ABCD for book_id resolution
    try:
        abcd = _read_abcd(sheets, fid, sname)
    except Exception as e:
        return ng("planner.plan.set", "ERROR", str(e))

    # Build book_id -> row map
    book_row_map = {}
    for i, abcd_row in enumerate(abcd):
        a = str(abcd_row[0]).strip() if len(abcd_row) > 0 else ""
        if not a:
            break
        parsed = _parse_book_code(a)
        if parsed["book_id"]:
            book_row_map[parsed["book_id"]] = PLANNER_START_ROW + i

    # Single mode
    if items is None:
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

        # Check preconditions
        try:
            a_val = sheets.get_cell(fid, sname, f"A{target_row}")
            if not str(a_val or "").strip():
                return ng("planner.plan.set", "PRECONDITION_A_EMPTY", "A[row] must not be empty")

            time_val = sheets.get_cell(fid, sname, f"{cols['time']}{target_row}")
            if not str(time_val or "").strip():
                return ng("planner.plan.set", "PRECONDITION_TIME_EMPTY", f"weekly_minutes cell ({cols['time']}{target_row}) must not be empty")

            # Check existing
            plan_cell = f"{cols['plan']}{target_row}"
            current = str(sheets.get_cell(fid, sname, plan_cell) or "").strip()
            if not overwrite and current:
                return ng("planner.plan.set", "ALREADY_EXISTS", "cell already has text; set overwrite=true to replace")

            sheets.update_cell(fid, sname, plan_cell, text)
            return ok("planner.plan.set", {"updated": True, "cell": plan_cell})
        except Exception as e:
            return ng("planner.plan.set", "ERROR", str(e))

    # Batch mode
    results = []
    updates_by_col: dict[str, list[tuple[int, str]]] = {}

    for item in items:
        wk = item.get("week_index")
        txt = str(item.get("plan_text", ""))
        ow = item.get("overwrite", overwrite)

        if not wk or wk < 1 or wk > 5:
            results.append({"ok": False, "error": {"code": "BAD_WEEK", "message": "week_index must be 1..5"}})
            continue

        if len(txt) > PLAN_TEXT_MAX_LENGTH:
            results.append({"ok": False, "error": {"code": "TOO_LONG", "message": f"plan_text must be <= {PLAN_TEXT_MAX_LENGTH} chars"}})
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

        # Check preconditions
        try:
            a_val = sheets.get_cell(fid, sname, f"A{target_row}")
            if not str(a_val or "").strip():
                results.append({"ok": False, "error": {"code": "PRECONDITION_A_EMPTY", "message": "A[row] must not be empty"}})
                continue

            time_val = sheets.get_cell(fid, sname, f"{cols['time']}{target_row}")
            if not str(time_val or "").strip():
                results.append({"ok": False, "error": {"code": "PRECONDITION_TIME_EMPTY", "message": f"weekly_minutes cell empty"}})
                continue

            current = str(sheets.get_cell(fid, sname, cell_a1) or "").strip()
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
                sheets.update_cell(fid, sname, f"{col}{target_row}", txt)
            except Exception:
                pass  # Already logged in results

    return ok("planner.plan.set", {"updated": True, "results": results})
