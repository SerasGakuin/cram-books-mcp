"""
Books handler class.
OOP-based implementation using BaseHandler.

Implements IDF-weighted search, chapter parsing, and CRUD operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from core.base_handler import BaseHandler
from sheets_client import SheetsClient
from config import BOOKS_MASTER_ID, BOOKS_SHEET, BOOK_COLUMNS
from lib.common import to_number_or_none
from lib.sheet_utils import parse_monthly_goal
from lib.id_rules import decide_prefix, next_id_for_prefix, extract_ids_from_values

from handlers.books.search import SearchMixin


# Type aliases
ChapterInfo = dict[str, Any]
BookDetails = dict[str, Any]


@dataclass
class BookMeta:
    """Book metadata (parent row data)."""
    id: str
    title: str
    subject: str
    monthly_goal_text: str = ""
    unit_load: int | None = None
    book_type: str = ""
    quiz_type: str = ""
    quiz_id: str = ""


class BooksHandler(BaseHandler, SearchMixin):
    """
    Handler for book-related operations.

    Extends BaseHandler with book-specific functionality:
    - IDF-weighted search (find) - via SearchMixin
    - Chapter parsing from child rows
    - Two-phase update/delete with preview confirmation
    """

    DEFAULT_FILE_ID: ClassVar[str] = BOOKS_MASTER_ID
    DEFAULT_SHEET_NAME: ClassVar[str] = BOOKS_SHEET

    COLUMN_SPEC: ClassVar[dict[str, list[str]]] = {
        "id": BOOK_COLUMNS["id"],
        "title": BOOK_COLUMNS["title"],
        "subject": BOOK_COLUMNS["subject"],
        "goal": BOOK_COLUMNS["monthly_goal"],
        "unit": BOOK_COLUMNS["unit_load"],
        "chap_idx": BOOK_COLUMNS["chap_idx"],
        "chap_name": BOOK_COLUMNS["chap_name"],
        "chap_begin": BOOK_COLUMNS["chap_begin"],
        "chap_end": BOOK_COLUMNS["chap_end"],
        "numbering": BOOK_COLUMNS["numbering"],
        "book_type": BOOK_COLUMNS["book_type"],
        "quiz_type": BOOK_COLUMNS["quiz_type"],
        "quiz_id": BOOK_COLUMNS["quiz_id"],
    }

    # Subject detection keywords (used by SearchMixin)
    SUBJECT_KEYS: ClassVar[list[str]] = [
        "現代文", "古文", "漢文", "英語", "数学",
        "化学", "物理", "生物", "日本史", "世界史", "地理"
    ]

    def __init__(
        self,
        sheets: SheetsClient,
        file_id: str | None = None,
        sheet_name: str | None = None,
    ) -> None:
        """Initialize BooksHandler with optional overrides."""
        super().__init__(sheets, file_id, sheet_name)
        self._preview_cache = self.get_preview_cache()

    # === Find (IDF Search) ===

    def find(
        self,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Find books by query using IDF-weighted search.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Response with candidates sorted by relevance score
        """
        if not query:
            return self._error("books.find", "BAD_REQUEST", "query が必要です")

        error = self.load_sheet("books.find")
        if error:
            return error

        if not self.values:
            return self._ok("books.find", {
                "query": query, "candidates": [], "top": None, "confidence": 0
            })

        if self.column_indices.get("id", -1) < 0:
            return self._error("books.find", "BAD_HEADER",
                             "必要な列（参考書ID/参考書名/教科）が見つかりません",
                             {"headers": self.headers})

        candidates = self._score_candidates(query)
        sliced = self._apply_gap_cutoff(candidates, limit)

        # Calculate confidence
        confidence = self._calculate_confidence(sliced)

        return self._ok("books.find", {
            "query": query,
            "candidates": sliced,
            "top": sliced[0] if sliced else None,
            "confidence": round(confidence, 4),
        })

    # === Get ===

    def get(self, book_id: str | None) -> dict[str, Any]:
        """
        Get book details by ID.

        Args:
            book_id: Book ID to retrieve

        Returns:
            Response with book details including chapters
        """
        if not book_id:
            return self._error("books.get", "BAD_REQUEST", "book_id が必要です")

        error = self.load_sheet("books.get")
        if error:
            return error

        if not self.values:
            return self._error("books.get", "EMPTY", "シートが空です")

        target_id = str(book_id).strip()
        meta, chapters = self._collect_book_data(target_id)

        if not meta:
            return self._error("books.get", "NOT_FOUND", f"book '{target_id}' not found")

        book = self._build_book_response(meta, chapters)
        return self._ok("books.get", {"book": book})

    def get_multiple(self, book_ids: list[str]) -> dict[str, Any]:
        """
        Get multiple books by IDs.

        Args:
            book_ids: List of book IDs to retrieve

        Returns:
            Response with list of book details
        """
        if not book_ids:
            return self._error("books.get", "BAD_REQUEST", "book_ids が必要です")

        error = self.load_sheet("books.get")
        if error:
            return error

        if not self.values:
            return self._error("books.get", "EMPTY", "シートが空です")

        target_ids = set(str(x).strip() for x in book_ids)
        books_map: dict[str, dict] = {id_: {"meta": None, "chapters": []} for id_ in target_ids}

        current_id = None
        for row in self.values[1:]:
            id_cell = str(self.get_cell(row, "id")).strip()
            if id_cell:
                current_id = id_cell
            if not current_id or current_id not in target_ids:
                continue

            bucket = books_map[current_id]

            # First row with ID is the parent
            if bucket["meta"] is None and id_cell:
                bucket["meta"] = self._parse_meta(row)

            # Parse chapter
            chapter = self._parse_chapter(row, len(bucket["chapters"]))
            if chapter:
                bucket["chapters"].append(chapter)

        books = [
            self._build_book_response(b["meta"], b["chapters"])
            for id_, b in books_map.items() if b["meta"]
        ]

        return self._ok("books.get", {"books": books})

    def _collect_book_data(self, target_id: str) -> tuple[BookMeta | None, list[ChapterInfo]]:
        """Collect meta and chapters for a single book."""
        meta = None
        chapters: list[ChapterInfo] = []
        current_id = None

        for row in self.values[1:]:
            id_cell = str(self.get_cell(row, "id")).strip()
            if id_cell:
                current_id = id_cell
            if current_id != target_id:
                continue

            if meta is None and id_cell:
                meta = self._parse_meta(row)

            chapter = self._parse_chapter(row, len(chapters))
            if chapter:
                chapters.append(chapter)

        return meta, chapters

    def _parse_meta(self, row: list[Any]) -> BookMeta:
        """Parse book metadata from a row."""
        return BookMeta(
            id=str(self.get_cell(row, "id")).strip(),
            title=str(self.get_cell(row, "title")),
            subject=str(self.get_cell(row, "subject")),
            monthly_goal_text=str(self.get_cell(row, "goal")),
            unit_load=to_number_or_none(self.get_cell(row, "unit")),
            book_type=str(self.get_cell(row, "book_type")),
            quiz_type=str(self.get_cell(row, "quiz_type")),
            quiz_id=str(self.get_cell(row, "quiz_id")),
        )

    def _parse_chapter(self, row: list[Any], chapter_count: int) -> ChapterInfo | None:
        """Parse chapter info from a row."""
        chap_name = str(self.get_cell(row, "chap_name")).strip()
        chap_begin = to_number_or_none(self.get_cell(row, "chap_begin"))
        chap_end = to_number_or_none(self.get_cell(row, "chap_end"))
        chap_idx = to_number_or_none(self.get_cell(row, "chap_idx"))
        numbering = str(self.get_cell(row, "numbering")).strip()

        if not chap_name and chap_begin is None and chap_end is None:
            return None

        return {
            "idx": chap_idx if chap_idx is not None else chapter_count + 1,
            "title": chap_name or None,
            "range": {"start": chap_begin, "end": chap_end}
                    if chap_begin is not None or chap_end is not None else None,
            "numbering": numbering or None,
        }

    def _build_book_response(self, meta: BookMeta, chapters: list[ChapterInfo]) -> BookDetails:
        """Build book response dict from meta and chapters."""
        goal = parse_monthly_goal(meta.monthly_goal_text)
        return {
            "id": meta.id,
            "title": meta.title,
            "subject": meta.subject,
            "monthly_goal": goal or {
                "text": meta.monthly_goal_text,
                "per_day_minutes": None,
                "days": None,
                "total_minutes_est": None,
            },
            "unit_load": meta.unit_load,
            "structure": {"chapters": chapters},
            "assessment": {
                "book_type": meta.book_type,
                "quiz_type": meta.quiz_type,
                "quiz_id": meta.quiz_id,
            },
        }

    # === Filter ===

    def filter(
        self,
        where: dict[str, str] | None = None,
        contains: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Filter books by conditions.

        Args:
            where: Exact match conditions (column -> value)
            contains: Partial match conditions (column -> value)
            limit: Maximum number of results

        Returns:
            Response with filtered books (grouped by book)
        """
        error = self.load_sheet("books.filter")
        if error:
            return error

        if not self.values:
            return self._ok("books.filter", {"books": [], "count": 0, "limit": limit})

        # Collect books with all their rows
        books_map = self._collect_all_books()

        # Filter and build results
        results = self._filter_books(books_map, where or {}, contains or {}, limit)

        return self._ok("books.filter", {
            "books": results,
            "count": len(results),
            "limit": limit if limit and limit > 0 else None,
        })

    def _collect_all_books(self) -> dict[str, dict]:
        """Collect all books with their rows."""
        from collections import defaultdict

        books_map: dict[str, dict] = {}
        current_id = None

        for row in self.values[1:]:
            id_cell = str(self.get_cell(row, "id")).strip()
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
                bucket["meta"] = self._parse_meta(row)

            chapter = self._parse_chapter(row, len(bucket["chapters"]))
            if chapter:
                bucket["chapters"].append(chapter)

            # Collect column values for filtering
            for ci in range(len(row)):
                raw = row[ci]
                if raw is not None and str(raw).strip():
                    bucket["cols"][ci].append(str(raw))

        return books_map

    def _filter_books(
        self,
        books_map: dict[str, dict],
        where: dict[str, str],
        contains: dict[str, str],
        limit: int | None,
    ) -> list[BookDetails]:
        """Filter books and build response list."""
        from lib.sheet_utils import norm_header
        from lib.common import normalize

        normalized_headers = [norm_header(h) for h in self.headers]

        def col_index_for(key: str) -> int:
            nk = norm_header(key)
            try:
                return normalized_headers.index(nk)
            except ValueError:
                return -1

        where_idx = [(col_index_for(k), str(v)) for k, v in where.items()]
        contains_idx = [(col_index_for(k), str(v)) for k, v in contains.items()]

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

        results: list[BookDetails] = []
        max_limit = limit if limit and limit > 0 else float("inf")

        for id_, b in books_map.items():
            if not b["meta"]:
                continue
            if not matches_book(b):
                continue

            results.append(self._build_book_response(b["meta"], b["chapters"]))

            if len(results) >= max_limit:
                break

        return results

    # === List ===

    def list(self, limit: int | None = None) -> dict[str, Any]:
        """
        List all books (ID, subject, title only).

        Args:
            limit: Maximum number of results

        Returns:
            Response with basic book info list
        """
        error = self.load_sheet("books.list")
        if error:
            return error

        if not self.values:
            return self._ok("books.list", {"books": [], "count": 0})

        seen: set[str] = set()
        books: list[dict[str, str]] = []

        for row in self.values[1:]:
            id_raw = str(self.get_cell(row, "id")).strip()
            if not id_raw or id_raw in seen:
                continue
            seen.add(id_raw)

            books.append({
                "id": id_raw,
                "title": str(self.get_cell(row, "title")),
                "subject": str(self.get_cell(row, "subject")),
            })

        if limit and limit > 0:
            books = books[:limit]

        return self._ok("books.list", {"books": books, "count": len(books)})

    # === Create ===

    def create(
        self,
        title: str,
        subject: str,
        unit_load: int | None = None,
        monthly_goal: str = "",
        chapters: list[dict] | None = None,
        id_prefix: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new book.

        Args:
            title: Book title
            subject: Subject name
            unit_load: Unit load value
            monthly_goal: Monthly goal text
            chapters: List of chapter dicts
            id_prefix: Custom ID prefix (overrides auto-generation)

        Returns:
            Response with new book ID and row count
        """
        if not title or not subject:
            return self._error("books.create", "BAD_REQUEST", "title と subject が必要です")

        error = self.load_sheet("books.create")
        if error:
            return error

        if not self.values:
            return self._error("books.create", "EMPTY", "シートが空です")

        # Generate ID
        sub_prefix = decide_prefix(subject, title)
        base_prefix = id_prefix.strip() if id_prefix else f"g{sub_prefix}"
        existing_ids = extract_ids_from_values(self.values, self.column_indices.get("id", -1))
        new_id = next_id_for_prefix(base_prefix, existing_ids)

        # Build rows
        rows = self._build_create_rows(new_id, title, subject, unit_load, monthly_goal, chapters)

        # Append rows
        self.sheets.append_rows(self.file_id, self.sheet_name, rows)

        return self._ok("books.create", {"id": new_id, "created_rows": len(rows)})

    def _build_create_rows(
        self,
        new_id: str,
        title: str,
        subject: str,
        unit_load: int | None,
        monthly_goal: str,
        chapters: list[dict] | None,
    ) -> list[list[Any]]:
        """Build rows for book creation."""
        idx = self.column_indices
        num_cols = len(self.headers)
        chapters = chapters or []
        rows: list[list[Any]] = []

        # Parent row
        parent = [""] * num_cols
        if idx.get("id", -1) >= 0:
            parent[idx["id"]] = new_id
        if idx.get("title", -1) >= 0:
            parent[idx["title"]] = title
        if idx.get("subject", -1) >= 0:
            parent[idx["subject"]] = subject
        if idx.get("goal", -1) >= 0:
            parent[idx["goal"]] = monthly_goal
        if idx.get("unit", -1) >= 0:
            parent[idx["unit"]] = unit_load if unit_load is not None else ""

        if chapters:
            # First chapter in parent row
            ch0 = chapters[0]
            if idx.get("chap_idx", -1) >= 0:
                parent[idx["chap_idx"]] = 1
            if idx.get("chap_name", -1) >= 0:
                parent[idx["chap_name"]] = ch0.get("title", "")
            if idx.get("chap_begin", -1) >= 0:
                parent[idx["chap_begin"]] = ch0.get("range", {}).get("start", "")
            if idx.get("chap_end", -1) >= 0:
                parent[idx["chap_end"]] = ch0.get("range", {}).get("end", "")
            if idx.get("numbering", -1) >= 0:
                parent[idx["numbering"]] = ch0.get("numbering", "")
            rows.append(parent)

            # Remaining chapters
            for i, ch in enumerate(chapters[1:], 2):
                child = [""] * num_cols
                if idx.get("chap_idx", -1) >= 0:
                    child[idx["chap_idx"]] = i
                if idx.get("chap_name", -1) >= 0:
                    child[idx["chap_name"]] = ch.get("title", "")
                if idx.get("chap_begin", -1) >= 0:
                    child[idx["chap_begin"]] = ch.get("range", {}).get("start", "")
                if idx.get("chap_end", -1) >= 0:
                    child[idx["chap_end"]] = ch.get("range", {}).get("end", "")
                if idx.get("numbering", -1) >= 0:
                    child[idx["numbering"]] = ch.get("numbering", "")
                rows.append(child)
        else:
            rows.append(parent)

        return rows

    # === Update (Two-phase) ===

    def update(
        self,
        book_id: str,
        updates: dict | None = None,
        confirm_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a book (two-phase: preview -> confirm).

        Args:
            book_id: Book ID to update
            updates: Field updates (preview mode)
            confirm_token: Confirmation token (confirm mode)

        Returns:
            Preview response or update confirmation
        """
        if not book_id:
            return self._error("books.update", "BAD_REQUEST", "book_id が必要です")

        error = self.load_sheet("books.update")
        if error:
            return error

        if not self.values:
            return self._error("books.update", "EMPTY", "シートが空です")

        # Find book block
        parent_row, end_row = self._find_book_block(str(book_id))

        if parent_row < 0:
            return self._error("books.update", "NOT_FOUND", f"book_id '{book_id}' が見つかりません")

        # Preview mode
        if not confirm_token:
            return self._update_preview(book_id, updates or {}, parent_row, end_row)

        # Confirm mode
        return self._update_confirm(book_id, confirm_token)

    def _find_book_block(self, target_id: str) -> tuple[int, int]:
        """Find parent row and end row for a book block."""
        parent_row = -1
        for i, row in enumerate(self.values[1:], 2):
            id_val = str(self.get_cell(row, "id")).strip()
            if id_val == target_id:
                parent_row = i
                break

        if parent_row < 0:
            return -1, -1

        # Find block end
        end_row = len(self.values) + 1
        for i in range(parent_row, len(self.values) + 1):
            if i > parent_row:
                if i <= len(self.values):
                    row = self.values[i - 1]
                    id_cell = str(self.get_cell(row, "id")).strip()
                    if id_cell:
                        end_row = i
                        break

        return parent_row, end_row

    def _update_preview(
        self,
        book_id: str,
        updates: dict,
        parent_row: int,
        end_row: int,
    ) -> dict[str, Any]:
        """Generate update preview."""
        current = self.values[parent_row - 1]
        idx = self.column_indices

        meta_changes = {}
        fields = [
            ("title", idx.get("title", -1)),
            ("subject", idx.get("subject", -1)),
            ("monthly_goal", idx.get("goal", -1)),
            ("unit_load", idx.get("unit", -1)),
        ]
        for key, col_idx in fields:
            if key in updates:
                from_val = self._get_cell_by_index(current, col_idx) if col_idx >= 0 else ""
                to_val = updates[key]
                if str(from_val) != str(to_val):
                    meta_changes[key] = {"from": from_val, "to": to_val}

        chapters_preview = None
        if "chapters" in updates and isinstance(updates["chapters"], list):
            existing_child_rows = max(0, end_row - parent_row)
            next_child_rows = max(0, len(updates["chapters"]) - 1)
            chapters_preview = {"from_count": existing_child_rows, "to_count": next_child_rows}

        token = self._preview_cache.store("upd", {
            "book_id": book_id,
            "updates": updates,
            "parent_row": parent_row,
            "end_row": end_row,
        })

        return self._ok("books.update", {
            "requires_confirmation": True,
            "preview": {
                "book_id": book_id,
                "meta_changes": meta_changes,
                "chapters": chapters_preview,
            },
            "confirm_token": token,
            "expires_in_seconds": self._preview_cache.ttl_seconds,
        })

    def _update_confirm(self, book_id: str, confirm_token: str) -> dict[str, Any]:
        """Apply confirmed update."""
        cached = self._preview_cache.pop("upd", confirm_token)
        if not cached:
            return self._error("books.update", "CONFIRM_EXPIRED",
                             "confirm_token が無効または期限切れです")

        if cached["book_id"] != book_id:
            return self._error("books.update", "CONFIRM_MISMATCH", "book_id が一致しません")

        # Apply updates
        updates_to_apply = cached["updates"]
        update_requests = []

        parent_row = cached["parent_row"]
        idx = self.column_indices
        field_map = {
            "title": idx.get("title", -1),
            "subject": idx.get("subject", -1),
            "monthly_goal": idx.get("goal", -1),
            "unit_load": idx.get("unit", -1),
        }

        for key, col_idx in field_map.items():
            if key in updates_to_apply and col_idx >= 0:
                from lib.sheet_utils import index_to_col_letter
                cell = f"{index_to_col_letter(col_idx)}{parent_row}"
                update_requests.append({"range": cell, "values": [[updates_to_apply[key]]]})

        if update_requests:
            self.sheets.batch_update(self.file_id, self.sheet_name, update_requests)

        return self._ok("books.update", {"book_id": book_id, "updated": True})

    # === Delete (Two-phase) ===

    def delete(
        self,
        book_id: str,
        confirm_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a book (two-phase: preview -> confirm).

        Args:
            book_id: Book ID to delete
            confirm_token: Confirmation token (confirm mode)

        Returns:
            Preview response or delete confirmation
        """
        if not book_id:
            return self._error("books.delete", "BAD_REQUEST", "book_id が必要です")

        error = self.load_sheet("books.delete")
        if error:
            return error

        if not self.values:
            return self._error("books.delete", "EMPTY", "シートが空です")

        # Find book block
        parent_row, end_row = self._find_book_block(str(book_id))

        if parent_row < 0:
            return self._error("books.delete", "NOT_FOUND", f"book_id '{book_id}' が見つかりません")

        # Preview mode
        if not confirm_token:
            token = self._preview_cache.store("del", {
                "book_id": book_id,
                "parent_row": parent_row,
                "end_row": end_row,
            })

            return self._ok("books.delete", {
                "requires_confirmation": True,
                "preview": {
                    "book_id": book_id,
                    "delete_rows": end_row - parent_row,
                    "range": {"start_row": parent_row, "end_row": end_row - 1},
                },
                "confirm_token": token,
                "expires_in_seconds": self._preview_cache.ttl_seconds,
            })

        # Confirm mode
        cached = self._preview_cache.pop("del", confirm_token)
        if not cached:
            return self._error("books.delete", "CONFIRM_EXPIRED",
                             "confirm_token が無効または期限切れです")

        if cached["book_id"] != book_id:
            return self._error("books.delete", "CONFIRM_MISMATCH", "book_id が一致しません")

        del_count = cached["end_row"] - cached["parent_row"]
        self.sheets.delete_rows(self.file_id, self.sheet_name, cached["parent_row"], del_count)

        return self._ok("books.delete", {"deleted_rows": del_count})
