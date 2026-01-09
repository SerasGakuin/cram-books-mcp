"""
Sheet utility functions.
Ported from apps/gas/src/lib/sheet_utils.ts
"""
import re
import math
import unicodedata
from typing import Any

# Stopwords for tokenization (common words that don't help with search)
STOPWORDS = {
    "問題集", "入試", "演習", "講座", "ノート",
    "完全", "総合", "実戦", "実践",
}


def norm_header(s: str) -> str:
    """
    Normalize a header string for matching.
    - NFKC normalization
    - Lowercase
    - Remove all whitespace
    """
    if not s:
        return ""
    result = str(s).strip().lower()
    result = unicodedata.normalize("NFKC", result)
    result = result.replace("\u3000", "").replace(" ", "")
    return result


def pick_col(headers: list[str], candidates: list[str]) -> int:
    """
    Find the column index for a header that matches any of the candidates.
    Returns -1 if not found.
    """
    normalized_headers = [norm_header(h) for h in headers]
    for c in candidates:
        key = norm_header(c)
        try:
            return normalized_headers.index(key)
        except ValueError:
            continue
    return -1


def tokenize(text: Any) -> list[str]:
    """
    Tokenize a string for search.
    - NFKC normalization
    - Handles Roman numerals and circled digits
    - Splits on non-word boundaries
    - Filters out stopwords and short tokens
    """
    if text is None:
        return []

    s = str(text)
    s = unicodedata.normalize("NFKC", s)

    # Roman numerals to digits
    replacements = [
        ("Ⅰ", "1"), ("Ⅱ", "2"), ("Ⅲ", "3"), ("Ⅳ", "4"), ("Ⅴ", "5"),
        ("Ⅵ", "6"), ("Ⅶ", "7"), ("Ⅷ", "8"), ("Ⅸ", "9"), ("Ⅹ", "10"),
        ("①", "1"), ("②", "2"), ("③", "3"), ("④", "4"), ("⑤", "5"),
        ("⑥", "6"), ("⑦", "7"), ("⑧", "8"), ("⑨", "9"), ("⑩", "10"),
        ("１", "1"), ("２", "2"), ("３", "3"), ("４", "4"), ("５", "5"),
        ("６", "6"), ("７", "7"), ("８", "8"), ("９", "9"), ("０", "0"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)

    # Split kanji-hiragana(1-2)-kanji patterns
    s = re.sub(r"([一-龯])[ぁ-ん]{1,2}([一-龯])", r"\1 \2", s)

    s = s.lower()

    # Split on non-word characters (keep Japanese characters)
    parts = re.split(r"[^\w一-龯ぁ-んァ-ン]+", s)

    tokens = []
    for p in parts:
        t = p.strip()
        if len(t) >= 2 and t not in STOPWORDS:
            tokens.append(t)

    return tokens


def calculate_idf(term: str, doc_freq: dict[str, int], total_docs: int) -> float:
    """
    Calculate IDF (Inverse Document Frequency) for a term.
    Uses BM25-style smoothing.
    """
    df = doc_freq.get(term, 0)
    return math.log(((total_docs - df + 0.5) / (df + 0.5)) + 1)


def parse_monthly_goal(text: Any) -> dict | None:
    """
    Parse a monthly goal text like "1時間" or "2.5時間".
    Returns dict with per_day_minutes, days, total_minutes_est, text.
    """
    if not text:
        return None

    s = str(text)
    match = re.search(r"(\d+(?:\.\d+)?)\s*時間", s)
    if match:
        hours = float(match.group(1))
        per_day_minutes = round(hours * 60)
        return {
            "per_day_minutes": per_day_minutes,
            "days": None,
            "total_minutes_est": None,
            "text": s,
        }

    return {
        "per_day_minutes": None,
        "days": None,
        "total_minutes_est": None,
        "text": s,
    }


def col_letter_to_index(letter: str) -> int:
    """
    Convert column letter(s) to 0-based index.
    A -> 0, B -> 1, ..., Z -> 25, AA -> 26, etc.
    """
    result = 0
    for char in letter.upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def index_to_col_letter(index: int) -> str:
    """
    Convert 0-based index to column letter(s).
    0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA, etc.
    """
    result = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def extract_spreadsheet_id(url: Any) -> str | None:
    """
    Extract spreadsheet ID from a Google Sheets URL or raw ID string.

    Args:
        url: A Google Sheets URL or raw spreadsheet ID

    Returns:
        The spreadsheet ID if found (at least 25 chars), None otherwise
    """
    if not url:
        return None
    match = re.search(r"[-\w]{25,}", str(url))
    return match.group(0) if match else None
