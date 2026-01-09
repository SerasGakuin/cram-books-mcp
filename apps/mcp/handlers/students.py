"""
Students handler.
Ported from apps/gas/src/handlers/students.ts
"""
from typing import Any
import uuid

from sheets_client import SheetsClient
from config import STUDENTS_MASTER_ID, STUDENTS_SHEET, STUDENT_COLUMNS
from lib.common import ok, ng, normalize
from lib.sheet_utils import pick_col, norm_header
from lib.id_rules import next_id_for_prefix, extract_ids_from_values


def _extract_spreadsheet_id(url: str) -> str:
    """Extract spreadsheet ID from Google Sheets URL."""
    import re
    match = re.search(r"[-\w]{25,}", str(url))
    return match.group(0) if match else ""


def _row_to_student(headers: list[str], row: list) -> dict:
    """Convert a row to a student dict."""
    idx = lambda cands: pick_col(headers, cands)
    get = lambda i: str(row[i]).strip() if i >= 0 and i < len(row) else ""

    # Get planner link and extract ID
    planner_link = get(idx(STUDENT_COLUMNS["planner_link"]))
    planner_sheet_id = get(idx(STUDENT_COLUMNS["planner_sheet_id"]))
    if not planner_sheet_id and planner_link:
        planner_sheet_id = _extract_spreadsheet_id(planner_link)

    return {
        "id": get(idx(STUDENT_COLUMNS["id"])),
        "name": get(idx(STUDENT_COLUMNS["name"])),
        "grade": get(idx(STUDENT_COLUMNS["grade"])),
        "status": get(idx(STUDENT_COLUMNS["status"])),
        "planner_sheet_id": planner_sheet_id,
        "planner_link": planner_link,
        "meeting_doc": get(idx(STUDENT_COLUMNS["meeting_doc"])),
        "tags": get(idx(STUDENT_COLUMNS["tags"])),
    }


def students_list(
    sheets: SheetsClient,
    limit: int | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """List all students."""
    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.list", "NOT_FOUND", f"students sheet not found: {e}")

    if len(values) < 2:
        return ok("students.list", {"students": [], "count": 0})

    headers = [str(h) for h in values[0]]
    students = []

    for row in values[1:]:
        if not any(str(c).strip() for c in row):
            continue
        students.append(_row_to_student(headers, row))

    if limit and limit > 0:
        students = students[:limit]

    return ok("students.list", {"students": students, "count": len(students)})


def students_find(
    sheets: SheetsClient,
    query: str,
    limit: int | None = 10,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Find students by query (fuzzy match on name/ID)."""
    if not query:
        return ng("students.find", "BAD_REQUEST", "query is required")

    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.find", "NOT_FOUND", f"students sheet not found: {e}")

    if len(values) < 2:
        return ok("students.find", {"query": query, "candidates": [], "top": None, "confidence": 0})

    headers = [str(h) for h in values[0]]
    idx_name = pick_col(headers, STUDENT_COLUMNS["name"])
    idx_id = pick_col(headers, STUDENT_COLUMNS["id"])

    q = normalize(query)
    candidates = []

    for row in values[1:]:
        id_val = str(row[idx_id]).strip() if idx_id >= 0 else ""
        name_val = str(row[idx_name]).strip() if idx_name >= 0 else ""

        if not id_val and not name_val:
            continue

        hay = [normalize(id_val), normalize(name_val)]
        score = 0
        reason = ""

        if any(h == q for h in hay):
            score = 1.0
            reason = "exact"
        elif any(q in h for h in hay):
            score = 0.9
            reason = "partial"

        if score > 0:
            candidates.append({
                "student_id": id_val,
                "name": name_val,
                "score": score,
                "reason": reason,
            })

    candidates.sort(key=lambda x: -x["score"])
    if limit and limit > 0:
        candidates = candidates[:limit]

    return ok("students.find", {
        "query": query,
        "candidates": candidates,
        "top": candidates[0] if candidates else None,
        "confidence": candidates[0]["score"] if candidates else 0,
    })


def students_get(
    sheets: SheetsClient,
    student_id: str | None = None,
    student_ids: list[str] | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Get student(s) by ID."""
    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.get", "NOT_FOUND", f"students sheet not found: {e}")

    headers = [str(h) for h in values[0]]
    idx_id = pick_col(headers, STUDENT_COLUMNS["id"])

    # Multiple IDs
    if student_ids and len(student_ids) > 0:
        want = set(str(x).strip() for x in student_ids)
        results = []
        for row in values[1:]:
            id_val = str(row[idx_id]).strip() if idx_id >= 0 else ""
            if id_val and id_val in want:
                results.append(_row_to_student(headers, row))
        return ok("students.get", {"students": results})

    # Single ID
    single = str(student_id or "").strip()
    if not single:
        return ng("students.get", "BAD_REQUEST", "student_id or student_ids is required")

    for row in values[1:]:
        id_val = str(row[idx_id]).strip() if idx_id >= 0 else ""
        if id_val == single:
            return ok("students.get", {"student": _row_to_student(headers, row)})

    return ng("students.get", "NOT_FOUND", f"student '{single}' not found")


def students_filter(
    sheets: SheetsClient,
    where: dict | None = None,
    contains: dict | None = None,
    limit: int | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Filter students by conditions."""
    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.filter", "NOT_FOUND", f"students sheet not found: {e}")

    if len(values) < 2:
        return ok("students.filter", {"students": [], "count": 0})

    headers = [str(h) for h in values[0]]
    normalized_headers = [norm_header(h) for h in headers]

    where = where or {}
    contains = contains or {}

    where_pairs = [(norm_header(k), str(v)) for k, v in where.items()]
    contains_pairs = [(norm_header(k), str(v)) for k, v in contains.items()]

    def col_index_for(k_norm: str) -> int:
        try:
            return normalized_headers.index(k_norm)
        except ValueError:
            return -1

    results = []
    for row in values[1:]:
        ok_all = True

        # Check where (exact match)
        for k, v in where_pairs:
            ci = col_index_for(k)
            if ci < 0:
                ok_all = False
                break
            raw = str(row[ci]) if ci < len(row) else ""
            if norm_header(raw) != norm_header(v):
                ok_all = False
                break

        if not ok_all:
            continue

        # Check contains (partial match)
        for k, v in contains_pairs:
            ci = col_index_for(k)
            if ci < 0:
                ok_all = False
                break
            raw = str(row[ci]) if ci < len(row) else ""
            if norm_header(v) not in norm_header(raw):
                ok_all = False
                break

        if ok_all:
            results.append(_row_to_student(headers, row))

    if limit and limit > 0:
        results = results[:limit]

    return ok("students.filter", {"students": results, "count": len(results)})


# In-memory cache for confirm tokens (preview -> confirm pattern)
_PREVIEW_CACHE: dict[str, dict] = {}


def students_create(
    sheets: SheetsClient,
    record: dict | None = None,
    id_prefix: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Create a new student."""
    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.create", "NOT_FOUND", f"students sheet not found: {e}")

    headers = [str(h) for h in values[0]]
    idx_id = pick_col(headers, STUDENT_COLUMNS["id"])

    # Generate new ID
    prefix = id_prefix.strip() if id_prefix else "s"
    existing_ids = extract_ids_from_values(values, idx_id)
    new_id = next_id_for_prefix(prefix, existing_ids)

    # Build new row
    new_row = [""] * len(headers)
    if idx_id >= 0:
        new_row[idx_id] = new_id

    # Copy from record
    record = record or {}
    norm_map = {norm_header(h): i for i, h in enumerate(headers)}
    for k, v in record.items():
        ci = norm_map.get(norm_header(k), -1)
        if ci >= 0:
            new_row[ci] = v

    # Append row
    sheets.append_rows(fid, sname, [new_row])

    return ok("students.create", {"id": new_id, "created": True})


def students_update(
    sheets: SheetsClient,
    student_id: str,
    updates: dict | None = None,
    confirm_token: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Update a student (two-phase: preview -> confirm)."""
    if not student_id:
        return ng("students.update", "BAD_REQUEST", "student_id is required")

    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.update", "NOT_FOUND", f"students sheet not found: {e}")

    headers = [str(h) for h in values[0]]
    idx_id = pick_col(headers, STUDENT_COLUMNS["id"])

    # Find student row
    row_index = -1
    for i, row in enumerate(values[1:], 2):  # 1-indexed, starting from row 2
        id_val = str(row[idx_id]).strip() if idx_id >= 0 and idx_id < len(row) else ""
        if id_val == str(student_id):
            row_index = i
            break

    if row_index < 0:
        return ng("students.update", "NOT_FOUND", f"student '{student_id}' not found")

    # Preview mode
    if not confirm_token:
        updates = updates or {}
        current_row = values[row_index - 1]  # 0-indexed
        diffs = {}
        norm_map = {norm_header(h): i for i, h in enumerate(headers)}

        for k, v in updates.items():
            ci = norm_map.get(norm_header(k), -1)
            if ci >= 0:
                from_val = current_row[ci] if ci < len(current_row) else ""
                to_val = v
                if str(from_val) != str(to_val):
                    diffs[headers[ci]] = {"from": from_val, "to": to_val}

        token = str(uuid.uuid4())
        _PREVIEW_CACHE[f"stu_upd:{token}"] = {
            "student_id": student_id,
            "updates": updates,
            "row_index": row_index,
        }

        return ok("students.update", {
            "requires_confirmation": True,
            "preview": {"diffs": diffs},
            "confirm_token": token,
            "expires_in_seconds": 300,
        })

    # Confirm mode
    cached = _PREVIEW_CACHE.pop(f"stu_upd:{confirm_token}", None)
    if not cached:
        return ng("students.update", "CONFIRM_EXPIRED", "confirm_token is invalid or expired")

    if str(cached["student_id"]) != str(student_id):
        return ng("students.update", "CONFIRM_MISMATCH", "student_id mismatch")

    # Apply updates
    updates_to_apply = cached["updates"]
    norm_map = {norm_header(h): i for i, h in enumerate(headers)}

    update_requests = []
    for k, v in updates_to_apply.items():
        ci = norm_map.get(norm_header(k), -1)
        if ci >= 0:
            cell = f"{chr(ord('A') + ci)}{row_index}"
            update_requests.append({"range": cell, "values": [[v]]})

    if update_requests:
        sheets.batch_update(fid, sname, update_requests)

    return ok("students.update", {"updated": True})


def students_delete(
    sheets: SheetsClient,
    student_id: str,
    confirm_token: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Delete a student (two-phase: preview -> confirm)."""
    if not student_id:
        return ng("students.delete", "BAD_REQUEST", "student_id is required")

    fid = file_id or STUDENTS_MASTER_ID
    sname = sheet_name or STUDENTS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("students.delete", "NOT_FOUND", f"students sheet not found: {e}")

    headers = [str(h) for h in values[0]]
    idx_id = pick_col(headers, STUDENT_COLUMNS["id"])

    # Find student row
    row_index = -1
    for i, row in enumerate(values[1:], 2):
        id_val = str(row[idx_id]).strip() if idx_id >= 0 and idx_id < len(row) else ""
        if id_val == str(student_id):
            row_index = i
            break

    if row_index < 0:
        return ng("students.delete", "NOT_FOUND", f"student '{student_id}' not found")

    # Preview mode
    if not confirm_token:
        token = str(uuid.uuid4())
        _PREVIEW_CACHE[f"stu_del:{token}"] = {
            "student_id": student_id,
            "row_index": row_index,
        }

        return ok("students.delete", {
            "requires_confirmation": True,
            "preview": {"row": row_index},
            "confirm_token": token,
            "expires_in_seconds": 300,
        })

    # Confirm mode
    cached = _PREVIEW_CACHE.pop(f"stu_del:{confirm_token}", None)
    if not cached:
        return ng("students.delete", "CONFIRM_EXPIRED", "confirm_token is invalid or expired")

    if str(cached["student_id"]) != str(student_id):
        return ng("students.delete", "CONFIRM_MISMATCH", "student_id mismatch")

    # Delete row
    sheets.delete_rows(fid, sname, cached["row_index"], 1)

    return ok("students.delete", {"deleted": True})
