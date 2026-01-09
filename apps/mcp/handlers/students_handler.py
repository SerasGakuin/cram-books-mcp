"""
Students handler class.
OOP-based implementation using BaseHandler.

Implements student CRUD operations with two-phase update/delete.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from core.base_handler import BaseHandler
from sheets_client import SheetsClient
from config import STUDENTS_MASTER_ID, STUDENTS_SHEET, STUDENT_COLUMNS
from lib.common import normalize
from lib.sheet_utils import norm_header, extract_spreadsheet_id
from lib.id_rules import next_id_for_prefix, extract_ids_from_values
from lib.preview_cache import PreviewCache


@dataclass
class StudentInfo:
    """Student data structure."""
    id: str
    name: str
    grade: str = ""
    status: str = ""
    planner_sheet_id: str = ""
    planner_link: str = ""
    meeting_doc: str = ""
    tags: str = ""


class StudentsHandler(BaseHandler):
    """
    Handler for student-related operations.

    Extends BaseHandler with student-specific functionality:
    - Simple fuzzy search (find)
    - Planner sheet ID extraction from links
    - Two-phase update/delete with preview confirmation
    """

    DEFAULT_FILE_ID: ClassVar[str] = STUDENTS_MASTER_ID
    DEFAULT_SHEET_NAME: ClassVar[str] = STUDENTS_SHEET

    COLUMN_SPEC: ClassVar[dict[str, list[str]]] = {
        "id": STUDENT_COLUMNS["id"],
        "name": STUDENT_COLUMNS["name"],
        "grade": STUDENT_COLUMNS["grade"],
        "status": STUDENT_COLUMNS["status"],
        "planner_link": STUDENT_COLUMNS["planner_link"],
        "planner_sheet_id": STUDENT_COLUMNS["planner_sheet_id"],
        "meeting_doc": STUDENT_COLUMNS["meeting_doc"],
        "tags": STUDENT_COLUMNS["tags"],
    }

    def __init__(
        self,
        sheets: SheetsClient,
        file_id: str | None = None,
        sheet_name: str | None = None,
    ) -> None:
        """Initialize StudentsHandler with optional overrides."""
        super().__init__(sheets, file_id, sheet_name)
        self._preview_cache = self.get_preview_cache()

    # === List ===

    def list(self, limit: int | None = None) -> dict[str, Any]:
        """
        List all students.

        Args:
            limit: Maximum number of results

        Returns:
            Response with student list
        """
        error = self.load_sheet("students.list")
        if error:
            return error

        if len(self.values) < 2:
            return self._ok("students.list", {"students": [], "count": 0})

        students: list[dict] = []
        for row in self.values[1:]:
            if not any(str(c).strip() for c in row):
                continue
            students.append(self._row_to_student(row))

        if limit and limit > 0:
            students = students[:limit]

        return self._ok("students.list", {"students": students, "count": len(students)})

    def _row_to_student(self, row: list[Any]) -> dict[str, Any]:
        """Convert a row to a student dict with planner ID extraction."""
        planner_link = str(self.get_cell(row, "planner_link"))
        planner_sheet_id = str(self.get_cell(row, "planner_sheet_id"))

        # Extract planner ID from link if not explicitly set
        if not planner_sheet_id and planner_link:
            planner_sheet_id = extract_spreadsheet_id(planner_link) or ""

        return {
            "id": str(self.get_cell(row, "id")).strip(),
            "name": str(self.get_cell(row, "name")),
            "grade": str(self.get_cell(row, "grade")),
            "status": str(self.get_cell(row, "status")),
            "planner_sheet_id": planner_sheet_id,
            "planner_link": planner_link,
            "meeting_doc": str(self.get_cell(row, "meeting_doc")),
            "tags": str(self.get_cell(row, "tags")),
        }

    # === Find ===

    def find(self, query: str, limit: int = 10) -> dict[str, Any]:
        """
        Find students by query (fuzzy match on name/ID).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Response with candidates sorted by score
        """
        if not query:
            return self._error("students.find", "BAD_REQUEST", "query is required")

        error = self.load_sheet("students.find")
        if error:
            return error

        if len(self.values) < 2:
            return self._ok("students.find", {
                "query": query, "candidates": [], "top": None, "confidence": 0
            })

        q = normalize(query)
        candidates = self._score_candidates_simple(q)

        candidates.sort(key=lambda x: -x["score"])
        if limit and limit > 0:
            candidates = candidates[:limit]

        return self._ok("students.find", {
            "query": query,
            "candidates": candidates,
            "top": candidates[0] if candidates else None,
            "confidence": candidates[0]["score"] if candidates else 0,
        })

    def _score_candidates_simple(self, query_normalized: str) -> list[dict[str, Any]]:
        """Score candidates with simple exact/partial matching."""
        candidates: list[dict] = []

        for row in self.values[1:]:
            id_val = str(self.get_cell(row, "id")).strip()
            name_val = str(self.get_cell(row, "name")).strip()

            if not id_val and not name_val:
                continue

            hay = [normalize(id_val), normalize(name_val)]
            score = 0.0
            reason = ""

            if any(h == query_normalized for h in hay):
                score = 1.0
                reason = "exact"
            elif any(query_normalized in h for h in hay):
                score = 0.9
                reason = "partial"

            if score > 0:
                candidates.append({
                    "student_id": id_val,
                    "name": name_val,
                    "score": score,
                    "reason": reason,
                })

        return candidates

    # === Get ===

    def get(self, student_id: str | None) -> dict[str, Any]:
        """
        Get student by ID.

        Args:
            student_id: Student ID to retrieve

        Returns:
            Response with student details
        """
        if not student_id:
            return self._error("students.get", "BAD_REQUEST",
                             "student_id or student_ids is required")

        error = self.load_sheet("students.get")
        if error:
            return error

        target = str(student_id).strip()

        for row in self.values[1:]:
            id_val = str(self.get_cell(row, "id")).strip()
            if id_val == target:
                return self._ok("students.get", {"student": self._row_to_student(row)})

        return self._error("students.get", "NOT_FOUND", f"student '{target}' not found")

    def get_multiple(self, student_ids: list[str]) -> dict[str, Any]:
        """
        Get multiple students by IDs.

        Args:
            student_ids: List of student IDs to retrieve

        Returns:
            Response with list of student details
        """
        if not student_ids:
            return self._error("students.get", "BAD_REQUEST",
                             "student_ids is required")

        error = self.load_sheet("students.get")
        if error:
            return error

        want = set(str(x).strip() for x in student_ids)
        results: list[dict] = []

        for row in self.values[1:]:
            id_val = str(self.get_cell(row, "id")).strip()
            if id_val and id_val in want:
                results.append(self._row_to_student(row))

        return self._ok("students.get", {"students": results})

    # === Filter ===

    def filter(
        self,
        where: dict[str, str] | None = None,
        contains: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Filter students by conditions.

        Args:
            where: Exact match conditions (column -> value)
            contains: Partial match conditions (column -> value)
            limit: Maximum number of results

        Returns:
            Response with filtered students
        """
        error = self.load_sheet("students.filter")
        if error:
            return error

        if len(self.values) < 2:
            return self._ok("students.filter", {"students": [], "count": 0})

        where = where or {}
        contains = contains or {}

        normalized_headers = [norm_header(h) for h in self.headers]

        def col_index_for(key: str) -> int:
            nk = norm_header(key)
            try:
                return normalized_headers.index(nk)
            except ValueError:
                return -1

        where_pairs = [(norm_header(k), str(v)) for k, v in where.items()]
        contains_pairs = [(norm_header(k), str(v)) for k, v in contains.items()]

        results: list[dict] = []
        for row in self.values[1:]:
            if not self._matches_conditions(row, where_pairs, contains_pairs, col_index_for):
                continue
            results.append(self._row_to_student(row))

        if limit and limit > 0:
            results = results[:limit]

        return self._ok("students.filter", {"students": results, "count": len(results)})

    def _matches_conditions(
        self,
        row: list[Any],
        where_pairs: list[tuple[str, str]],
        contains_pairs: list[tuple[str, str]],
        col_index_for: callable,
    ) -> bool:
        """Check if a row matches all filter conditions."""
        # Check where (exact match)
        for k, v in where_pairs:
            ci = col_index_for(k)
            if ci < 0:
                return False
            raw = str(row[ci]) if ci < len(row) else ""
            if norm_header(raw) != norm_header(v):
                return False

        # Check contains (partial match)
        for k, v in contains_pairs:
            ci = col_index_for(k)
            if ci < 0:
                return False
            raw = str(row[ci]) if ci < len(row) else ""
            if norm_header(v) not in norm_header(raw):
                return False

        return True

    # === Create ===

    def create(
        self,
        record: dict | None = None,
        id_prefix: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new student.

        Args:
            record: Student data dict
            id_prefix: Custom ID prefix (default: "s")

        Returns:
            Response with new student ID
        """
        error = self.load_sheet("students.create")
        if error:
            return error

        # Generate new ID
        prefix = id_prefix.strip() if id_prefix else "s"
        existing_ids = extract_ids_from_values(self.values, self.column_indices.get("id", -1))
        new_id = next_id_for_prefix(prefix, existing_ids)

        # Build new row
        new_row = self._build_create_row(new_id, record or {})

        # Append row
        self.sheets.append_rows(self.file_id, self.sheet_name, [new_row])

        return self._ok("students.create", {"id": new_id, "created": True})

    def _build_create_row(self, new_id: str, record: dict) -> list[Any]:
        """Build a new row for student creation."""
        new_row = [""] * len(self.headers)
        idx_id = self.column_indices.get("id", -1)
        if idx_id >= 0:
            new_row[idx_id] = new_id

        # Copy from record using normalized header matching
        norm_map = {norm_header(h): i for i, h in enumerate(self.headers)}
        for k, v in record.items():
            ci = norm_map.get(norm_header(k), -1)
            if ci >= 0:
                new_row[ci] = v

        return new_row

    # === Update (Two-phase) ===

    def update(
        self,
        student_id: str,
        updates: dict | None = None,
        confirm_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a student (two-phase: preview -> confirm).

        Args:
            student_id: Student ID to update
            updates: Field updates (preview mode)
            confirm_token: Confirmation token (confirm mode)

        Returns:
            Preview response or update confirmation
        """
        if not student_id:
            return self._error("students.update", "BAD_REQUEST", "student_id is required")

        error = self.load_sheet("students.update")
        if error:
            return error

        # Find student row
        row_index = self._find_student_row(str(student_id))
        if row_index < 0:
            return self._error("students.update", "NOT_FOUND",
                             f"student '{student_id}' not found")

        # Preview mode
        if not confirm_token:
            return self._update_preview(student_id, updates or {}, row_index)

        # Confirm mode
        return self._update_confirm(student_id, confirm_token)

    def _find_student_row(self, target_id: str) -> int:
        """Find the 1-based row index for a student."""
        for i, row in enumerate(self.values[1:], 2):
            id_val = str(self.get_cell(row, "id")).strip()
            if id_val == target_id:
                return i
        return -1

    def _update_preview(
        self,
        student_id: str,
        updates: dict,
        row_index: int,
    ) -> dict[str, Any]:
        """Generate update preview."""
        current_row = self.values[row_index - 1]  # 0-indexed
        diffs = {}
        norm_map = {norm_header(h): i for i, h in enumerate(self.headers)}

        for k, v in updates.items():
            ci = norm_map.get(norm_header(k), -1)
            if ci >= 0:
                from_val = current_row[ci] if ci < len(current_row) else ""
                to_val = v
                if str(from_val) != str(to_val):
                    diffs[self.headers[ci]] = {"from": from_val, "to": to_val}

        token = self._preview_cache.store("stu_upd", {
            "student_id": student_id,
            "updates": updates,
            "row_index": row_index,
        })

        return self._ok("students.update", {
            "requires_confirmation": True,
            "preview": {"diffs": diffs},
            "confirm_token": token,
            "expires_in_seconds": self._preview_cache.ttl_seconds,
        })

    def _update_confirm(self, student_id: str, confirm_token: str) -> dict[str, Any]:
        """Apply confirmed update."""
        cached = self._preview_cache.pop("stu_upd", confirm_token)
        if not cached:
            return self._error("students.update", "CONFIRM_EXPIRED",
                             "confirm_token is invalid or expired")

        if str(cached["student_id"]) != str(student_id):
            return self._error("students.update", "CONFIRM_MISMATCH", "student_id mismatch")

        # Apply updates
        updates_to_apply = cached["updates"]
        row_index = cached["row_index"]
        norm_map = {norm_header(h): i for i, h in enumerate(self.headers)}

        update_requests = []
        for k, v in updates_to_apply.items():
            ci = norm_map.get(norm_header(k), -1)
            if ci >= 0:
                cell = f"{chr(ord('A') + ci)}{row_index}"
                update_requests.append({"range": cell, "values": [[v]]})

        if update_requests:
            self.sheets.batch_update(self.file_id, self.sheet_name, update_requests)

        return self._ok("students.update", {"updated": True})

    # === Delete (Two-phase) ===

    def delete(
        self,
        student_id: str,
        confirm_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a student (two-phase: preview -> confirm).

        Args:
            student_id: Student ID to delete
            confirm_token: Confirmation token (confirm mode)

        Returns:
            Preview response or delete confirmation
        """
        if not student_id:
            return self._error("students.delete", "BAD_REQUEST", "student_id is required")

        error = self.load_sheet("students.delete")
        if error:
            return error

        # Find student row
        row_index = self._find_student_row(str(student_id))
        if row_index < 0:
            return self._error("students.delete", "NOT_FOUND",
                             f"student '{student_id}' not found")

        # Preview mode
        if not confirm_token:
            token = self._preview_cache.store("stu_del", {
                "student_id": student_id,
                "row_index": row_index,
            })

            return self._ok("students.delete", {
                "requires_confirmation": True,
                "preview": {"row": row_index},
                "confirm_token": token,
                "expires_in_seconds": self._preview_cache.ttl_seconds,
            })

        # Confirm mode
        cached = self._preview_cache.pop("stu_del", confirm_token)
        if not cached:
            return self._error("students.delete", "CONFIRM_EXPIRED",
                             "confirm_token is invalid or expired")

        if str(cached["student_id"]) != str(student_id):
            return self._error("students.delete", "CONFIRM_MISMATCH", "student_id mismatch")

        # Delete row
        self.sheets.delete_rows(self.file_id, self.sheet_name, cached["row_index"], 1)

        return self._ok("students.delete", {"deleted": True})
