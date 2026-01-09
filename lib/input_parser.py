"""
Input parsing and validation utilities.

Functions for parsing and normalizing MCP tool inputs,
handling various input formats (strings, dicts, lists).
"""
from typing import Any


def strip_quotes(s: str) -> str:
    """
    Strip outer quotes from a string.

    Args:
        s: Input string

    Returns:
        String with leading/trailing quotes removed
    """
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def coerce_str(x: Any, keys: tuple[str, ...] = ()) -> str | None:
    """
    Extract a string from various input formats.

    Handles:
    - Direct string input
    - Dict with specified keys

    Args:
        x: Input value (string, dict, or other)
        keys: Tuple of keys to try in dict order

    Returns:
        Extracted string or None if not found
    """
    if isinstance(x, str):
        return strip_quotes(x)
    if isinstance(x, dict):
        for k in keys:
            v = x.get(k)
            if isinstance(v, str):
                return strip_quotes(v)
    return None


def as_list(x: Any, id_key: str = "id") -> list[str]:
    """
    Convert input to a list of string IDs.

    Handles:
    - None -> empty list
    - Single string -> list with one element
    - List/tuple of strings -> list of strings
    - List/tuple of dicts -> extract id_key from each

    Args:
        x: Input value
        id_key: Key to extract from dict items (default: "id")

    Returns:
        List of string IDs
    """
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        out = []
        for v in x:
            if isinstance(v, str):
                out.append(strip_quotes(v))
            elif isinstance(v, dict):
                s = coerce_str(v, (id_key, "id"))
                if s:
                    out.append(s)
        return out
    if isinstance(x, str):
        return [strip_quotes(x)]
    return []


def coerce_int(x: Any, keys: tuple[str, ...] = ()) -> int | None:
    """
    Extract an integer from various input formats.

    Args:
        x: Input value
        keys: Tuple of keys to try in dict order

    Returns:
        Extracted integer or None if not found/invalid
    """
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        try:
            return int(x)
        except ValueError:
            return None
    if isinstance(x, dict):
        for k in keys:
            v = x.get(k)
            result = coerce_int(v, ())
            if result is not None:
                return result
    return None


def coerce_bool(x: Any, keys: tuple[str, ...] = ()) -> bool | None:
    """
    Extract a boolean from various input formats.

    Args:
        x: Input value
        keys: Tuple of keys to try in dict order

    Returns:
        Extracted boolean or None if not found/invalid
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        lower = x.lower().strip()
        if lower in ("true", "1", "yes"):
            return True
        if lower in ("false", "0", "no"):
            return False
        return None
    if isinstance(x, dict):
        for k in keys:
            v = x.get(k)
            result = coerce_bool(v, ())
            if result is not None:
                return result
    return None


def resolve_entity_ids(
    single_id: Any,
    multi_ids: Any,
    single_keys: tuple[str, ...] = ("id",),
    multi_key: str = "id",
) -> tuple[str | None, list[str]]:
    """
    Resolve both single ID and multiple IDs from input.

    Handles the common pattern of accepting either:
    - A single ID (string or dict with id key)
    - Multiple IDs (list/tuple)
    - A single parameter that could be either

    Args:
        single_id: Primary single ID input
        multi_ids: Multiple IDs input
        single_keys: Keys to check in dict for single ID
        multi_key: Key to extract from list items

    Returns:
        Tuple of (single_id_str, list_of_ids)
    """
    single = coerce_str(single_id, single_keys)
    many = as_list(multi_ids, multi_key)

    # If multi_ids was empty, check if single_id was actually a list
    if not many and isinstance(single_id, (list, tuple)):
        many = as_list(single_id, multi_key)

    return single, many


def resolve_planner_context(
    student_id: Any,
    spreadsheet_id: Any,
) -> tuple[str | None, str | None]:
    """
    Resolve student_id and spreadsheet_id for planner tools.

    Args:
        student_id: Student ID input
        spreadsheet_id: Spreadsheet ID input

    Returns:
        Tuple of (student_id_str, spreadsheet_id_str)
    """
    sid = coerce_str(student_id, ("student_id", "id"))
    spid = coerce_str(spreadsheet_id, ("spreadsheet_id", "sheet_id", "id"))
    return sid, spid


# Aliases for backwards compatibility with server.py naming
_strip_quotes = strip_quotes
_coerce_str = coerce_str
_as_list = as_list
