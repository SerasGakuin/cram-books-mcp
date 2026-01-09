"""
Base handler class for sheet-based operations.

Provides common functionality for all handlers:
- Sheet loading with error handling
- Column index mapping
- Cell access utilities
- Row finding and filtering
- Response helpers (ok/ng)
"""
from abc import ABC
from typing import Any, ClassVar

from sheets_client import SheetsClient
from lib.common import ok, ng, normalize
from lib.sheet_utils import pick_col, norm_header
from lib.preview_cache import PreviewCache


class BaseHandler(ABC):
    """
    Abstract base class for all sheet-based handlers.

    Subclasses must define:
    - DEFAULT_FILE_ID: Default spreadsheet ID
    - DEFAULT_SHEET_NAME: Default sheet name
    - COLUMN_SPEC: dict mapping column keys to candidate header names

    Example:
        class BooksHandler(BaseHandler):
            DEFAULT_FILE_ID = "abc123"
            DEFAULT_SHEET_NAME = "Books"
            COLUMN_SPEC = {
                "id": ["ID", "書籍ID"],
                "title": ["Title", "タイトル"],
            }
    """

    # Subclasses must override these
    DEFAULT_FILE_ID: ClassVar[str | None] = None
    DEFAULT_SHEET_NAME: ClassVar[str | None] = None
    COLUMN_SPEC: ClassVar[dict[str, list[str]]] = {}

    # Shared preview cache (class-level)
    _preview_cache: ClassVar[PreviewCache | None] = None

    def __init__(
        self,
        sheets: SheetsClient,
        file_id: str | None = None,
        sheet_name: str | None = None,
    ) -> None:
        """
        Initialize handler with sheets client and optional overrides.

        Args:
            sheets: SheetsClient instance
            file_id: Override default file ID
            sheet_name: Override default sheet name
        """
        self.sheets = sheets
        self.file_id = file_id or self.DEFAULT_FILE_ID
        self.sheet_name = sheet_name or self.DEFAULT_SHEET_NAME

        # Lazily loaded
        self._values: list[list[Any]] | None = None
        self._headers: list[str] | None = None
        self._column_indices: dict[str, int] | None = None

    # === Properties ===

    @property
    def values(self) -> list[list[Any]]:
        """Sheet values (all rows including header)."""
        return self._values or []

    @property
    def headers(self) -> list[str]:
        """Sheet headers (first row)."""
        return self._headers or []

    @property
    def column_indices(self) -> dict[str, int]:
        """Column index map (key -> 0-based index)."""
        return self._column_indices or {}

    @classmethod
    def get_preview_cache(cls) -> PreviewCache:
        """Get shared preview cache instance."""
        if cls._preview_cache is None:
            cls._preview_cache = PreviewCache()
        return cls._preview_cache

    # === Sheet Loading ===

    def load_sheet(self, op_name: str) -> dict | None:
        """
        Load sheet values with error handling.

        Args:
            op_name: Operation name for error messages

        Returns:
            Error dict if failed, None on success.
            On success, populates self._values, self._headers, self._column_indices.
        """
        try:
            self._values = self.sheets.get_all_values(self.file_id, self.sheet_name)
        except Exception as e:
            return self._error(op_name, "NOT_FOUND", f"sheet not found: {e}")

        if not self._values:
            return self._error(op_name, "EMPTY", "sheet is empty")

        self._headers = [str(h) for h in self._values[0]]
        self._build_column_indices()
        return None

    def _build_column_indices(self) -> None:
        """Build column index map using COLUMN_SPEC."""
        self._column_indices = {}
        for key, candidates in self.COLUMN_SPEC.items():
            self._column_indices[key] = pick_col(self._headers, candidates)

    # === Cell Access ===

    def get_cell(self, row: list[Any], col_key: str, default: Any = "") -> Any:
        """
        Get cell value from row using column key.

        Args:
            row: Row data
            col_key: Column key from COLUMN_SPEC
            default: Default value if column not found or cell empty

        Returns:
            Cell value or default
        """
        idx = self._column_indices.get(col_key, -1)
        return self._get_cell_by_index(row, idx, default)

    @staticmethod
    def _get_cell_by_index(row: list[Any], idx: int, default: Any = "") -> Any:
        """
        Get cell value by index with bounds checking.

        Args:
            row: Row data
            idx: Column index (0-based)
            default: Default value if index out of bounds or cell None

        Returns:
            Cell value or default
        """
        if 0 <= idx < len(row) and row[idx] is not None:
            return row[idx]
        return default

    # === Row Finding ===

    def find_row_by_id(self, id_col_key: str, target_id: str) -> int | None:
        """
        Find first row index where id_col matches target_id.

        Args:
            id_col_key: Column key for ID column
            target_id: Target ID value

        Returns:
            1-based row index or None if not found
        """
        idx = self._column_indices.get(id_col_key, -1)
        if idx < 0:
            return None

        target = str(target_id).strip()
        for i, row in enumerate(self.values[1:], 2):
            cell_val = str(self._get_cell_by_index(row, idx)).strip()
            if cell_val == target:
                return i
        return None

    def find_rows_by_ids(
        self,
        id_col_key: str,
        target_ids: list[str],
    ) -> dict[str, int]:
        """
        Find all rows matching any of target_ids.

        Args:
            id_col_key: Column key for ID column
            target_ids: List of target ID values

        Returns:
            dict mapping found IDs to 1-based row indices
        """
        idx = self._column_indices.get(id_col_key, -1)
        if idx < 0:
            return {}

        targets = {str(x).strip() for x in target_ids}
        result: dict[str, int] = {}

        for i, row in enumerate(self.values[1:], 2):
            cell_val = str(self._get_cell_by_index(row, idx)).strip()
            if cell_val in targets:
                result[cell_val] = i

        return result

    # === Filtering ===

    def filter_by_conditions(
        self,
        where: dict[str, str] | None = None,
        contains: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[tuple[int, list[Any]]]:
        """
        Filter rows by exact match (where) and partial match (contains).

        Args:
            where: dict of column -> value for exact match
            contains: dict of column -> value for partial match
            limit: Maximum number of results

        Returns:
            List of (row_index_1based, row) tuples
        """
        where = where or {}
        contains = contains or {}

        # Build normalized header index
        normalized_headers = [norm_header(h) for h in self.headers]

        def col_index_for(key: str) -> int:
            nk = norm_header(key)
            try:
                return normalized_headers.index(nk)
            except ValueError:
                return -1

        # Pre-compute column indices
        where_pairs = [(col_index_for(k), str(v)) for k, v in where.items()]
        contains_pairs = [(col_index_for(k), str(v)) for k, v in contains.items()]

        results: list[tuple[int, list[Any]]] = []
        max_results = limit if limit and limit > 0 else float("inf")

        for row_idx, row in enumerate(self.values[1:], 2):
            # Check where conditions (exact match)
            match = True
            for ci, v in where_pairs:
                if ci < 0:
                    match = False
                    break
                raw = str(row[ci]) if ci < len(row) else ""
                if normalize(raw) != normalize(v):
                    match = False
                    break

            if not match:
                continue

            # Check contains conditions (partial match)
            for ci, v in contains_pairs:
                if ci < 0:
                    match = False
                    break
                raw = str(row[ci]) if ci < len(row) else ""
                if normalize(v) not in normalize(raw):
                    match = False
                    break

            if match:
                results.append((row_idx, row))
                if len(results) >= max_results:
                    break

        return results

    # === Response Helpers ===

    def _ok(self, op: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Return success response.

        Args:
            op: Operation name
            data: Response data

        Returns:
            Success response dict
        """
        return ok(op, data or {})

    def _error(
        self,
        op: str,
        code: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Return error response.

        Args:
            op: Operation name
            code: Error code
            message: Error message
            extra: Additional error data

        Returns:
            Error response dict
        """
        return ng(op, code, message, extra)
