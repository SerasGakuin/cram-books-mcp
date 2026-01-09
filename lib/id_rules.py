"""
ID generation rules.
Ported from apps/gas/src/lib/id_rules.ts
"""
import re
from config import PREFIX_MAP


def decide_prefix(subject: str, title: str) -> str:
    """
    Determine the ID prefix based on subject and title.
    Returns a 2-character prefix like 'MB', 'EC', etc.
    """
    combined = f"{subject} {title}"
    for key, prefix in PREFIX_MAP.items():
        if key in combined:
            return prefix
    return "XX"  # Unknown


def next_id_for_prefix(prefix: str, existing_ids: list[str]) -> str:
    """
    Generate the next ID for a given prefix.
    Format: g{PREFIX}{3-digit-sequence}
    Example: gMB017, gEC003
    """
    # Ensure prefix starts with 'g' if not already
    if not prefix.startswith("g"):
        prefix = "g" + prefix

    # Find the maximum sequence number for this prefix
    max_seq = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")

    for id_str in existing_ids:
        if not id_str:
            continue
        id_str = str(id_str).strip()
        match = pattern.match(id_str)
        if match:
            try:
                seq = int(match.group(1))
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{max_seq + 1:03d}"


def extract_ids_from_values(values: list[list], id_col: int) -> list[str]:
    """
    Extract all non-empty IDs from a column in a 2D values array.
    Useful for passing to next_id_for_prefix.
    """
    ids = []
    for row in values:
        if id_col < len(row):
            val = row[id_col]
            if val and str(val).strip():
                ids.append(str(val).strip())
    return ids
