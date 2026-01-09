"""
Type definitions for the MCP server.
Provides type safety for responses, sheet data, and common structures.
"""
from typing import TypedDict, Any


class ErrorDetail(TypedDict):
    """Error detail structure."""
    code: str
    message: str


class SuccessResponse(TypedDict):
    """Successful API response."""
    ok: bool
    op: str
    data: dict[str, Any]


class ErrorResponse(TypedDict):
    """Error API response."""
    ok: bool
    op: str
    error: ErrorDetail


# Union type for all API responses
Response = SuccessResponse | ErrorResponse

# Sheet data types
SheetRow = list[Any]
SheetValues = list[SheetRow]

# Column mapping type
ColumnSpec = dict[str, list[str]]
