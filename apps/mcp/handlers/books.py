"""
Books handler.
Ported from apps/gas/src/handlers/books.ts

Implements IDF-weighted search, chapter parsing, and CRUD operations.
"""
import math
import re
from collections import defaultdict
from typing import Any

from sheets_client import SheetsClient
from config import BOOKS_MASTER_ID, BOOKS_SHEET, BOOK_COLUMNS
from lib.common import ok, ng, normalize, to_number_or_none
from lib.sheet_utils import pick_col, norm_header, tokenize, parse_monthly_goal
from lib.id_rules import decide_prefix, next_id_for_prefix, extract_ids_from_values
from lib.preview_cache import PreviewCache


# Type definitions
ChapterInfo = dict[str, Any]
BookDetails = dict[str, Any]


def _build_column_indices(headers: list[str]) -> dict[str, int]:
    """Build column index map from headers."""
    return {
        "id": pick_col(headers, BOOK_COLUMNS["id"]),
        "title": pick_col(headers, BOOK_COLUMNS["title"]),
        "subject": pick_col(headers, BOOK_COLUMNS["subject"]),
        "goal": pick_col(headers, BOOK_COLUMNS["monthly_goal"]),
        "unit": pick_col(headers, BOOK_COLUMNS["unit_load"]),
        "chap_idx": pick_col(headers, BOOK_COLUMNS["chap_idx"]),
        "chap_name": pick_col(headers, BOOK_COLUMNS["chap_name"]),
        "chap_begin": pick_col(headers, BOOK_COLUMNS["chap_begin"]),
        "chap_end": pick_col(headers, BOOK_COLUMNS["chap_end"]),
        "numbering": pick_col(headers, BOOK_COLUMNS["numbering"]),
        "book_type": pick_col(headers, BOOK_COLUMNS["book_type"]),
        "quiz_type": pick_col(headers, BOOK_COLUMNS["quiz_type"]),
        "quiz_id": pick_col(headers, BOOK_COLUMNS["quiz_id"]),
    }


def _get_cell(row: list, idx: int, default: Any = "") -> Any:
    """Safely get cell value from row."""
    if idx < 0 or idx >= len(row):
        return default
    return row[idx] if row[idx] is not None else default


def _parse_chapter(row: list, idx: dict[str, int], chapter_count: int) -> ChapterInfo | None:
    """Parse chapter info from a row."""
    chap_name = str(_get_cell(row, idx["chap_name"])).strip()
    chap_begin = to_number_or_none(_get_cell(row, idx["chap_begin"]))
    chap_end = to_number_or_none(_get_cell(row, idx["chap_end"]))
    chap_idx = to_number_or_none(_get_cell(row, idx["chap_idx"]))
    numbering = str(_get_cell(row, idx["numbering"])).strip()

    if not chap_name and chap_begin is None and chap_end is None:
        return None

    return {
        "idx": chap_idx if chap_idx is not None else chapter_count + 1,
        "title": chap_name or None,
        "range": {"start": chap_begin, "end": chap_end} if chap_begin is not None or chap_end is not None else None,
        "numbering": numbering or None,
    }


def _calculate_idf(term: str, doc_freq: dict[str, int], total_docs: int) -> float:
    """Calculate BM25-style IDF for a term."""
    df = doc_freq.get(term, 0)
    return math.log(((total_docs - df + 0.5) / (df + 0.5)) + 1)


def books_find(
    sheets: SheetsClient,
    query: str,
    limit: int = 20,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """
    Find books by query using IDF-weighted search.

    Returns candidates sorted by relevance score.
    """
    if not query:
        return ng("books.find", "BAD_REQUEST", "query が必要です")

    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.find", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ok("books.find", {"query": query, "candidates": [], "top": None, "confidence": 0})

    headers = [str(h).strip() for h in values[0]]
    idx = _build_column_indices(headers)

    if idx["id"] < 0 or idx["title"] < 0 or idx["subject"] < 0:
        return ng("books.find", "BAD_HEADER", "必要な列（参考書ID/参考書名/教科）が見つかりません", {"headers": headers})

    # Normalize query
    q_normalized = normalize(query)
    q_tokens = tokenize(query)

    # Subject detection
    SUBJECT_KEYS = ["現代文", "古文", "漢文", "英語", "数学", "化学", "物理", "生物", "日本史", "世界史", "地理"]
    query_subject = next((k for k in SUBJECT_KEYS if k.lower() in [t.lower() for t in q_tokens]), None)

    # Build document frequency and collect parent rows
    seen = set()
    doc_freq: dict[str, int] = defaultdict(int)
    parent_rows: list[dict] = []

    for row in values[1:]:
        id_raw = str(_get_cell(row, idx["id"])).strip()
        title_raw = str(_get_cell(row, idx["title"])).strip()
        subject_raw = str(_get_cell(row, idx["subject"])).strip()

        if not id_raw and not title_raw and not subject_raw:
            continue
        if not id_raw:  # Child row (chapter)
            continue
        if id_raw in seen:
            continue
        seen.add(id_raw)

        parent_rows.append({
            "id": id_raw,
            "title": title_raw,
            "subject": subject_raw,
        })

        # Count document frequency
        tok_set = set(tokenize(title_raw))
        for t in tok_set:
            doc_freq[t] += 1

    total_docs = len(parent_rows) or 1

    # Calculate IDF for query tokens
    unique_q_tokens = list(set(q_tokens))
    sum_idf_q = sum(_calculate_idf(t, doc_freq, total_docs) for t in unique_q_tokens) or 1

    # Score candidates
    candidates = []
    for r in parent_rows:
        hay = [normalize(r["id"]), normalize(r["title"]), normalize(r["subject"])]
        hay = [h for h in hay if h and len(h) >= 2]

        combined_norm = normalize(r["title"])
        title_tok_set = set(tokenize(r["title"]))

        # Calculate IDF coverage
        idf_hit_fwd = sum(_calculate_idf(t, doc_freq, total_docs) for t in unique_q_tokens if t in title_tok_set)
        cov_idf_fwd = idf_hit_fwd / sum_idf_q

        # Scoring
        score = 0
        reason = ""

        if any(h == q_normalized for h in hay):
            score = 1.0
            reason = "exact"
        elif q_normalized in combined_norm:
            score = 0.95
            reason = "phrase"
        elif any(q_normalized in h for h in hay):
            score = 0.90
            reason = "partial_target"
        elif cov_idf_fwd > 0:
            score = 0.80
            reason = "coverage_q_in_title"
        else:
            short = q_normalized[:3] if len(q_normalized) >= 3 else ""
            if short and any(short in h for h in hay):
                score = 0.72
                reason = "fuzzy3"

        # Bonus
        bonus = 0
        if cov_idf_fwd > 0:
            bonus += min(0.12, 0.12 * cov_idf_fwd)
        if combined_norm.startswith(q_normalized):
            bonus += 0.02
        if query_subject and normalize(query_subject) == normalize(r["subject"]):
            bonus += 0.02

        final_score = min(1, score + bonus)

        if final_score > 0:
            candidates.append({
                "book_id": r["id"],
                "title": r["title"],
                "subject": r["subject"],
                "score": round(final_score, 4),
                "reason": reason,
            })

    candidates.sort(key=lambda x: -x["score"])

    # Apply score gap cutoff
    min_gap = 0.05
    cut_index = len(candidates)
    for i in range(len(candidates) - 1):
        if candidates[i]["score"] - candidates[i + 1]["score"] >= min_gap:
            cut_index = i + 1
            break

    sliced = candidates[:min(limit, cut_index)]

    # Calculate confidence
    confidence = 0
    if sliced:
        s1 = sliced[0]["score"]
        s2 = sliced[1]["score"] if len(sliced) > 1 else 0
        confidence = max(0, min(1, s1 - 0.25 * s2))

    return ok("books.find", {
        "query": query,
        "candidates": sliced,
        "top": sliced[0] if sliced else None,
        "confidence": round(confidence, 4),
    })


def books_get(
    sheets: SheetsClient,
    book_id: str | None = None,
    book_ids: list[str] | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """
    Get book details by ID(s).

    Includes chapter information from child rows.
    """
    list_param = book_ids if book_ids else ([book_id] if isinstance(book_id, list) else None)

    if not book_id and not list_param:
        return ng("books.get", "BAD_REQUEST", "book_id または book_ids が必要です")

    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.get", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ng("books.get", "EMPTY", "シートが空です")

    headers = [str(h) for h in values[0]]
    idx = _build_column_indices(headers)

    if idx["id"] < 0 or idx["title"] < 0 or idx["subject"] < 0:
        return ng("books.get", "BAD_HEADER", "必要な列が見つかりません", {"headers": headers})

    # Multiple IDs
    if list_param and len(list_param) > 0:
        target_ids = set(str(x).strip() for x in list_param)
        books_map: dict[str, dict] = {id_: {"meta": None, "chapters": []} for id_ in target_ids}

        current_id = None
        for row in values[1:]:
            id_cell = str(_get_cell(row, idx["id"])).strip()
            if id_cell:
                current_id = id_cell
            if not current_id or current_id not in target_ids:
                continue

            bucket = books_map[current_id]

            # First row with ID is the parent
            if bucket["meta"] is None and id_cell:
                bucket["meta"] = {
                    "id": current_id,
                    "title": str(_get_cell(row, idx["title"])),
                    "subject": str(_get_cell(row, idx["subject"])),
                    "monthly_goal_text": str(_get_cell(row, idx["goal"])),
                    "unit_load": to_number_or_none(_get_cell(row, idx["unit"])),
                    "book_type": str(_get_cell(row, idx["book_type"])),
                    "quiz_type": str(_get_cell(row, idx["quiz_type"])),
                    "quiz_id": str(_get_cell(row, idx["quiz_id"])),
                }

            # Parse chapter
            chapter = _parse_chapter(row, idx, len(bucket["chapters"]))
            if chapter:
                bucket["chapters"].append(chapter)

        books = []
        for id_ in target_ids:
            b = books_map[id_]
            if not b["meta"]:
                continue
            goal = parse_monthly_goal(b["meta"]["monthly_goal_text"])
            books.append({
                "id": b["meta"]["id"],
                "title": b["meta"]["title"],
                "subject": b["meta"]["subject"],
                "monthly_goal": goal or {"text": b["meta"]["monthly_goal_text"], "per_day_minutes": None, "days": None, "total_minutes_est": None},
                "unit_load": b["meta"]["unit_load"],
                "structure": {"chapters": b["chapters"]},
                "assessment": {
                    "book_type": b["meta"]["book_type"],
                    "quiz_type": b["meta"]["quiz_type"],
                    "quiz_id": b["meta"]["quiz_id"],
                },
            })

        return ok("books.get", {"books": books})

    # Single ID
    target_id = str(book_id).strip()
    meta = None
    chapters = []
    current_id = None

    for row in values[1:]:
        id_cell = str(_get_cell(row, idx["id"])).strip()
        if id_cell:
            current_id = id_cell
        if current_id != target_id:
            continue

        if meta is None and id_cell:
            meta = {
                "id": current_id,
                "title": str(_get_cell(row, idx["title"])),
                "subject": str(_get_cell(row, idx["subject"])),
                "monthly_goal_text": str(_get_cell(row, idx["goal"])),
                "unit_load": to_number_or_none(_get_cell(row, idx["unit"])),
                "book_type": str(_get_cell(row, idx["book_type"])),
                "quiz_type": str(_get_cell(row, idx["quiz_type"])),
                "quiz_id": str(_get_cell(row, idx["quiz_id"])),
            }

        chapter = _parse_chapter(row, idx, len(chapters))
        if chapter:
            chapters.append(chapter)

    if not meta:
        return ng("books.get", "NOT_FOUND", f"book '{target_id}' not found")

    goal = parse_monthly_goal(meta["monthly_goal_text"])
    book = {
        "id": meta["id"],
        "title": meta["title"],
        "subject": meta["subject"],
        "monthly_goal": goal or {"text": meta["monthly_goal_text"], "per_day_minutes": None, "days": None, "total_minutes_est": None},
        "unit_load": meta["unit_load"],
        "structure": {"chapters": chapters},
        "assessment": {
            "book_type": meta["book_type"],
            "quiz_type": meta["quiz_type"],
            "quiz_id": meta["quiz_id"],
        },
    }

    return ok("books.get", {"book": book})


def books_filter(
    sheets: SheetsClient,
    where: dict | None = None,
    contains: dict | None = None,
    limit: int | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """
    Filter books by conditions.

    Groups results by book (not row).
    """
    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.filter", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ok("books.filter", {"books": [], "count": 0, "limit": limit})

    headers = [str(h).strip() for h in values[0]]
    idx = _build_column_indices(headers)
    normalized_headers = [norm_header(h) for h in headers]

    where = where or {}
    contains = contains or {}

    # Build condition indices
    def col_index_for(key: str) -> int:
        nk = norm_header(key)
        try:
            return normalized_headers.index(nk)
        except ValueError:
            return -1

    where_idx = [(col_index_for(k), str(v)) for k, v in where.items()]
    contains_idx = [(col_index_for(k), str(v)) for k, v in contains.items()]

    # Collect books with all their rows
    books_map: dict[str, dict] = {}
    current_id = None

    for row in values[1:]:
        id_cell = str(_get_cell(row, idx["id"])).strip() if idx["id"] >= 0 else ""
        if id_cell:
            current_id = id_cell
        if not current_id:
            continue

        if current_id not in books_map:
            books_map[current_id] = {
                "meta": None,
                "chapters": [],
                "cols": defaultdict(list),
            }

        bucket = books_map[current_id]

        if bucket["meta"] is None and id_cell:
            bucket["meta"] = {
                "id": current_id,
                "title": str(_get_cell(row, idx["title"])),
                "subject": str(_get_cell(row, idx["subject"])),
                "monthly_goal_text": str(_get_cell(row, idx["goal"])),
                "unit_load": to_number_or_none(_get_cell(row, idx["unit"])),
                "book_type": str(_get_cell(row, idx["book_type"])),
                "quiz_type": str(_get_cell(row, idx["quiz_type"])),
                "quiz_id": str(_get_cell(row, idx["quiz_id"])),
            }

        chapter = _parse_chapter(row, idx, len(bucket["chapters"]))
        if chapter:
            bucket["chapters"].append(chapter)

        # Collect column values for filtering
        for ci, _ in where_idx + contains_idx:
            if ci >= 0 and ci < len(row):
                raw = row[ci]
                if raw is not None and str(raw).strip():
                    bucket["cols"][ci].append(str(raw))

    # Filter books
    def matches_book(b: dict) -> bool:
        for ci, v in where_idx:
            if ci < 0:
                return False
            vals = b["cols"].get(ci, [])
            if not any(normalize(x) == normalize(v) for x in vals):
                return False
        for ci, v in contains_idx:
            if ci < 0:
                return False
            vals = b["cols"].get(ci, [])
            if not any(normalize(v) in normalize(x) for x in vals):
                return False
        return True

    results = []
    max_limit = limit if limit and limit > 0 else float("inf")

    for id_, b in books_map.items():
        if not b["meta"]:
            continue
        if not matches_book(b):
            continue

        results.append({
            "id": b["meta"]["id"],
            "title": b["meta"]["title"],
            "subject": b["meta"]["subject"],
            "monthly_goal": {
                "text": b["meta"]["monthly_goal_text"],
                "per_day_minutes": None,
                "days": None,
                "total_minutes_est": None,
            },
            "unit_load": b["meta"]["unit_load"],
            "structure": {"chapters": b["chapters"]},
            "assessment": {
                "book_type": b["meta"]["book_type"],
                "quiz_type": b["meta"]["quiz_type"],
                "quiz_id": b["meta"]["quiz_id"],
            },
        })

        if len(results) >= max_limit:
            break

    return ok("books.filter", {
        "books": results,
        "count": len(results),
        "limit": limit if limit and limit > 0 else None,
    })


def books_list(
    sheets: SheetsClient,
    limit: int | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """
    List all books (ID, subject, title only).

    Lighter than books_filter for simple lookups.
    """
    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.list", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ok("books.list", {"books": [], "count": 0})

    headers = [str(h).strip() for h in values[0]]
    idx = _build_column_indices(headers)

    seen = set()
    books = []

    for row in values[1:]:
        id_raw = str(_get_cell(row, idx["id"])).strip()
        if not id_raw or id_raw in seen:
            continue
        seen.add(id_raw)

        books.append({
            "id": id_raw,
            "title": str(_get_cell(row, idx["title"])),
            "subject": str(_get_cell(row, idx["subject"])),
        })

    if limit and limit > 0:
        books = books[:limit]

    return ok("books.list", {"books": books, "count": len(books)})


# Shared preview cache for update/delete operations
_preview_cache = PreviewCache()


def books_create(
    sheets: SheetsClient,
    title: str,
    subject: str,
    unit_load: int | None = None,
    monthly_goal: str = "",
    chapters: list[dict] | None = None,
    id_prefix: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Create a new book."""
    if not title or not subject:
        return ng("books.create", "BAD_REQUEST", "title と subject が必要です")

    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.create", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ng("books.create", "EMPTY", "シートが空です")

    headers = [str(h) for h in values[0]]
    idx = _build_column_indices(headers)

    # Generate ID
    sub_prefix = decide_prefix(subject, title)
    base_prefix = id_prefix.strip() if id_prefix else f"g{sub_prefix}"
    existing_ids = extract_ids_from_values(values, idx["id"])
    new_id = next_id_for_prefix(base_prefix, existing_ids)

    # Build rows
    chapters = chapters or []
    rows = []

    # Parent row
    parent = [""] * len(headers)
    if idx["id"] >= 0:
        parent[idx["id"]] = new_id
    if idx["title"] >= 0:
        parent[idx["title"]] = title
    if idx["subject"] >= 0:
        parent[idx["subject"]] = subject
    if idx["goal"] >= 0:
        parent[idx["goal"]] = monthly_goal
    if idx["unit"] >= 0:
        parent[idx["unit"]] = unit_load if unit_load is not None else ""

    if chapters:
        # First chapter in parent row
        ch0 = chapters[0]
        if idx["chap_idx"] >= 0:
            parent[idx["chap_idx"]] = 1
        if idx["chap_name"] >= 0:
            parent[idx["chap_name"]] = ch0.get("title", "")
        if idx["chap_begin"] >= 0:
            parent[idx["chap_begin"]] = ch0.get("range", {}).get("start", "")
        if idx["chap_end"] >= 0:
            parent[idx["chap_end"]] = ch0.get("range", {}).get("end", "")
        if idx["numbering"] >= 0:
            parent[idx["numbering"]] = ch0.get("numbering", "")
        rows.append(parent)

        # Remaining chapters
        for i, ch in enumerate(chapters[1:], 2):
            child = [""] * len(headers)
            if idx["chap_idx"] >= 0:
                child[idx["chap_idx"]] = i
            if idx["chap_name"] >= 0:
                child[idx["chap_name"]] = ch.get("title", "")
            if idx["chap_begin"] >= 0:
                child[idx["chap_begin"]] = ch.get("range", {}).get("start", "")
            if idx["chap_end"] >= 0:
                child[idx["chap_end"]] = ch.get("range", {}).get("end", "")
            if idx["numbering"] >= 0:
                child[idx["numbering"]] = ch.get("numbering", "")
            rows.append(child)
    else:
        rows.append(parent)

    # Append rows
    sheets.append_rows(fid, sname, rows)

    return ok("books.create", {"id": new_id, "created_rows": len(rows)})


def books_update(
    sheets: SheetsClient,
    book_id: str,
    updates: dict | None = None,
    confirm_token: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Update a book (two-phase: preview -> confirm)."""
    if not book_id:
        return ng("books.update", "BAD_REQUEST", "book_id が必要です")

    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.update", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ng("books.update", "EMPTY", "シートが空です")

    headers = [str(h) for h in values[0]]
    idx = _build_column_indices(headers)

    # Find book block
    parent_row = -1
    for i, row in enumerate(values[1:], 2):
        id_val = str(_get_cell(row, idx["id"])).strip()
        if id_val == str(book_id):
            parent_row = i
            break

    if parent_row < 0:
        return ng("books.update", "NOT_FOUND", f"book_id '{book_id}' が見つかりません")

    # Find block end
    end_row = len(values)
    for i in range(parent_row, len(values)):
        if i > parent_row - 1:
            row = values[i]
            id_cell = str(_get_cell(row, idx["id"])).strip()
            if id_cell:
                end_row = i
                break

    # Preview mode
    if not confirm_token:
        updates = updates or {}
        current = values[parent_row - 1]

        meta_changes = {}
        fields = [("title", idx["title"]), ("subject", idx["subject"]), ("monthly_goal", idx["goal"]), ("unit_load", idx["unit"])]
        for key, col_idx in fields:
            if key in updates:
                from_val = _get_cell(current, col_idx) if col_idx >= 0 else ""
                to_val = updates[key]
                if str(from_val) != str(to_val):
                    meta_changes[key] = {"from": from_val, "to": to_val}

        chapters_preview = None
        if "chapters" in updates and isinstance(updates["chapters"], list):
            existing_child_rows = max(0, end_row - parent_row)
            next_child_rows = max(0, len(updates["chapters"]) - 1)
            chapters_preview = {"from_count": existing_child_rows, "to_count": next_child_rows}

        token = _preview_cache.store("upd", {
            "book_id": book_id,
            "updates": updates,
            "parent_row": parent_row,
            "end_row": end_row,
        })

        return ok("books.update", {
            "requires_confirmation": True,
            "preview": {"book_id": book_id, "meta_changes": meta_changes, "chapters": chapters_preview},
            "confirm_token": token,
            "expires_in_seconds": _preview_cache.ttl_seconds,
        })

    # Confirm mode
    cached = _preview_cache.pop("upd", confirm_token)
    if not cached:
        return ng("books.update", "CONFIRM_EXPIRED", "confirm_token が無効または期限切れです")

    if cached["book_id"] != book_id:
        return ng("books.update", "CONFIRM_MISMATCH", "book_id が一致しません")

    # Apply updates (simplified - full implementation would need row operations)
    updates_to_apply = cached["updates"]
    update_requests = []

    parent_row = cached["parent_row"]
    field_map = {"title": idx["title"], "subject": idx["subject"], "monthly_goal": idx["goal"], "unit_load": idx["unit"]}

    for key, col_idx in field_map.items():
        if key in updates_to_apply and col_idx >= 0:
            from lib.sheet_utils import index_to_col_letter
            cell = f"{index_to_col_letter(col_idx)}{parent_row}"
            update_requests.append({"range": cell, "values": [[updates_to_apply[key]]]})

    if update_requests:
        sheets.batch_update(fid, sname, update_requests)

    return ok("books.update", {"book_id": book_id, "updated": True})


def books_delete(
    sheets: SheetsClient,
    book_id: str,
    confirm_token: str | None = None,
    file_id: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    """Delete a book (two-phase: preview -> confirm)."""
    if not book_id:
        return ng("books.delete", "BAD_REQUEST", "book_id が必要です")

    fid = file_id or BOOKS_MASTER_ID
    sname = sheet_name or BOOKS_SHEET

    try:
        values = sheets.get_all_values(fid, sname)
    except Exception as e:
        return ng("books.delete", "NOT_FOUND", f"sheet not found: {e}")

    if not values:
        return ng("books.delete", "EMPTY", "シートが空です")

    headers = [str(h) for h in values[0]]
    idx = _build_column_indices(headers)

    # Find book block
    parent_row = -1
    for i, row in enumerate(values[1:], 2):
        id_val = str(_get_cell(row, idx["id"])).strip()
        if id_val == str(book_id):
            parent_row = i
            break

    if parent_row < 0:
        return ng("books.delete", "NOT_FOUND", f"book_id '{book_id}' が見つかりません")

    # Find block end
    end_row = len(values) + 1
    for i in range(parent_row, len(values) + 1):
        if i > parent_row:
            if i <= len(values):
                row = values[i - 1]
                id_cell = str(_get_cell(row, idx["id"])).strip()
                if id_cell:
                    end_row = i
                    break

    # Preview mode
    if not confirm_token:
        token = _preview_cache.store("del", {
            "book_id": book_id,
            "parent_row": parent_row,
            "end_row": end_row,
        })

        return ok("books.delete", {
            "requires_confirmation": True,
            "preview": {
                "book_id": book_id,
                "delete_rows": end_row - parent_row,
                "range": {"start_row": parent_row, "end_row": end_row - 1},
            },
            "confirm_token": token,
            "expires_in_seconds": _preview_cache.ttl_seconds,
        })

    # Confirm mode
    cached = _preview_cache.pop("del", confirm_token)
    if not cached:
        return ng("books.delete", "CONFIRM_EXPIRED", "confirm_token が無効または期限切れです")

    if cached["book_id"] != book_id:
        return ng("books.delete", "CONFIRM_MISMATCH", "book_id が一致しません")

    del_count = cached["end_row"] - cached["parent_row"]
    sheets.delete_rows(fid, sname, cached["parent_row"], del_count)

    return ok("books.delete", {"deleted_rows": del_count})
