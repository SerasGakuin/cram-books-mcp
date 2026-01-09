"""
Common utility functions.
Ported from apps/gas/src/lib/common.ts
"""
import unicodedata
from typing import Any


def normalize(s: Any) -> str:
    """
    Normalize a string for comparison.
    - NFKC normalization
    - Lowercase
    - Strip whitespace
    """
    if s is None:
        return ""
    text = str(s).strip().lower()
    return unicodedata.normalize("NFKC", text)


def to_number_or_none(val: Any) -> int | float | None:
    """
    Convert a value to a number, or return None if not possible.
    Handles empty strings and None gracefully.
    """
    if val is None or val == "":
        return None
    try:
        # Try int first
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return val
        s = str(val).strip()
        if s == "":
            return None
        # Try to parse as float
        f = float(s)
        # Return int if it's a whole number
        if f == int(f):
            return int(f)
        return f
    except (ValueError, TypeError):
        return None


def ok(op: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a successful response."""
    return {"ok": True, "op": op, "data": data or {}}


def ng(op: str, code: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create an error response."""
    error: dict[str, Any] = {"code": code, "message": message}
    if extra:
        error.update(extra)
    return {"ok": False, "op": op, "error": error}
