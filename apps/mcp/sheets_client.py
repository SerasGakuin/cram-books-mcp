"""
Google Sheets API client using gspread.
Provides Service Account authentication and common sheet operations.
"""
import json
import gspread
from google.oauth2.service_account import Credentials
from typing import Any

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClient:
    """Wrapper around gspread for Google Sheets API access."""

    def __init__(self, credentials_json: str | dict):
        """
        Initialize the client with Service Account credentials.

        Args:
            credentials_json: Either a JSON string or dict containing
                             the Service Account credentials.
        """
        if isinstance(credentials_json, str):
            credentials_json = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self._spreadsheet_cache: dict[str, gspread.Spreadsheet] = {}

    def open_by_id(self, spreadsheet_id: str) -> gspread.Spreadsheet:
        """Open a spreadsheet by ID with caching."""
        if spreadsheet_id not in self._spreadsheet_cache:
            self._spreadsheet_cache[spreadsheet_id] = self.gc.open_by_key(spreadsheet_id)
        return self._spreadsheet_cache[spreadsheet_id]

    def get_worksheet(self, spreadsheet_id: str, sheet_name: str) -> gspread.Worksheet:
        """Get a worksheet by name from a spreadsheet."""
        ss = self.open_by_id(spreadsheet_id)
        return ss.worksheet(sheet_name)

    def get_all_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
        """Get all values from a worksheet as a 2D list."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        return ws.get_all_values()

    def get_range(self, spreadsheet_id: str, sheet_name: str, range_notation: str) -> list[list[Any]]:
        """Get values from a specific range (e.g., 'A1:D30')."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        return ws.get(range_notation)

    def get_cell(self, spreadsheet_id: str, sheet_name: str, cell: str) -> Any:
        """Get a single cell value."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        return ws.acell(cell).value

    def update_cell(self, spreadsheet_id: str, sheet_name: str, cell: str, value: Any) -> None:
        """Update a single cell."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.update_acell(cell, value)

    def update_range(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_notation: str,
        values: list[list[Any]],
    ) -> None:
        """Update a range of cells."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.update(range_notation, values)

    def batch_update(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        updates: list[dict],
    ) -> None:
        """
        Batch update multiple ranges.

        Args:
            updates: List of dicts with 'range' and 'values' keys.
                    e.g., [{'range': 'A1', 'values': [[1,2]]}, ...]
        """
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.batch_update(updates)

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: list[list[Any]],
    ) -> None:
        """Append rows to the end of a worksheet."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.append_rows(rows)

    def insert_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_index: int,
        num_rows: int = 1,
    ) -> None:
        """Insert empty rows at a specific index."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.insert_rows([[]] * num_rows, row=row_index)

    def delete_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_row: int,
        num_rows: int = 1,
    ) -> None:
        """Delete rows starting from start_row."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        ws.delete_rows(start_row, start_row + num_rows - 1)

    def get_row_count(self, spreadsheet_id: str, sheet_name: str) -> int:
        """Get the number of rows with data."""
        ws = self.get_worksheet(spreadsheet_id, sheet_name)
        return ws.row_count

    def clear_cache(self, spreadsheet_id: str | None = None) -> None:
        """Clear the spreadsheet cache (useful after modifications)."""
        if spreadsheet_id:
            self._spreadsheet_cache.pop(spreadsheet_id, None)
        else:
            self._spreadsheet_cache.clear()


# Singleton instance for the application
_sheets_client: SheetsClient | None = None


def get_sheets_client() -> SheetsClient:
    """
    Get the global SheetsClient instance.
    Initializes from environment variables on first call.
    """
    global _sheets_client
    if _sheets_client is None:
        from env_loader import get_google_credentials
        credentials = get_google_credentials()
        _sheets_client = SheetsClient(credentials)
    return _sheets_client


def reset_sheets_client() -> None:
    """Reset the global client (useful for testing)."""
    global _sheets_client
    _sheets_client = None
