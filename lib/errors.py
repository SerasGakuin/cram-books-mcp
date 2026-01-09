"""
Standardized error handling for the MCP server.
Provides consistent error codes and response helpers.
"""
from enum import Enum
from typing import Any

from lib.common import ng


class ErrorCode(str, Enum):
    """Standardized error codes used across the MCP server."""
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    EMPTY = "EMPTY"
    CONFIRM_EXPIRED = "CONFIRM_EXPIRED"
    CONFIRM_MISMATCH = "CONFIRM_MISMATCH"
    SHEET_ERROR = "SHEET_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def bad_request(op: str, message: str) -> dict[str, Any]:
    """Create a BAD_REQUEST error response."""
    return ng(op, ErrorCode.BAD_REQUEST, message)


def not_found(op: str, message: str) -> dict[str, Any]:
    """Create a NOT_FOUND error response."""
    return ng(op, ErrorCode.NOT_FOUND, message)


def empty_sheet(op: str, message: str = "シートが空です") -> dict[str, Any]:
    """Create an EMPTY error response for empty sheets."""
    return ng(op, ErrorCode.EMPTY, message)


def confirm_expired(op: str, message: str = "確認トークンが無効または期限切れ") -> dict[str, Any]:
    """Create a CONFIRM_EXPIRED error response."""
    return ng(op, ErrorCode.CONFIRM_EXPIRED, message)


def confirm_mismatch(op: str, message: str) -> dict[str, Any]:
    """Create a CONFIRM_MISMATCH error response."""
    return ng(op, ErrorCode.CONFIRM_MISMATCH, message)


def sheet_error(op: str, message: str) -> dict[str, Any]:
    """Create a SHEET_ERROR error response."""
    return ng(op, ErrorCode.SHEET_ERROR, message)


def internal_error(op: str, message: str) -> dict[str, Any]:
    """Create an INTERNAL_ERROR error response."""
    return ng(op, ErrorCode.INTERNAL_ERROR, message)
