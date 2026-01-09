"""
Tests for helper functions in lib modules.
Pure functions that can be tested without mocking Google Sheets.
"""
import os
import pytest

# Import helpers from lib modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.common import normalize, to_number_or_none, ok, ng
from lib.sheet_utils import norm_header, pick_col, tokenize, parse_monthly_goal, col_letter_to_index, extract_spreadsheet_id
from lib.id_rules import decide_prefix, next_id_for_prefix, extract_ids_from_values
from lib.input_parser import strip_quotes as _strip_quotes, coerce_str as _coerce_str, as_list as _as_list


class TestStripQuotes:
    """Tests for _strip_quotes function"""

    def test_removes_double_quotes(self):
        assert _strip_quotes('"hello"') == "hello"

    def test_removes_single_quotes(self):
        assert _strip_quotes("'hello'") == "hello"

    def test_strips_whitespace(self):
        assert _strip_quotes("  hello  ") == "hello"

    def test_no_quotes_unchanged(self):
        assert _strip_quotes("hello") == "hello"

    def test_mismatched_quotes_unchanged(self):
        assert _strip_quotes('"hello\'') == '"hello\''

    def test_empty_string(self):
        assert _strip_quotes("") == ""

    def test_only_quotes(self):
        assert _strip_quotes('""') == ""
        assert _strip_quotes("''") == ""

    def test_nested_quotes_outer_only(self):
        assert _strip_quotes('"\'inner\'"') == "'inner'"


class TestCoerceStr:
    """Tests for _coerce_str function"""

    def test_string_input(self):
        assert _coerce_str("hello") == "hello"

    def test_string_with_quotes(self):
        assert _coerce_str('"hello"') == "hello"

    def test_dict_with_matching_key(self):
        assert _coerce_str({"query": "test"}, ("query",)) == "test"

    def test_dict_with_second_key(self):
        assert _coerce_str({"id": "123"}, ("query", "id")) == "123"

    def test_dict_no_matching_key(self):
        assert _coerce_str({"other": "value"}, ("query",)) is None

    def test_empty_dict(self):
        assert _coerce_str({}, ("query",)) is None

    def test_none_input(self):
        assert _coerce_str(None) is None

    def test_number_input(self):
        assert _coerce_str(123) is None

    def test_list_input(self):
        assert _coerce_str(["a", "b"]) is None


class TestAsList:
    """Tests for _as_list function"""

    def test_none_returns_empty(self):
        assert _as_list(None) == []

    def test_string_returns_list(self):
        assert _as_list("item") == ["item"]

    def test_list_passthrough(self):
        assert _as_list(["a", "b"]) == ["a", "b"]

    def test_tuple_converts(self):
        assert _as_list(("a", "b")) == ["a", "b"]

    def test_strips_quotes(self):
        assert _as_list(['"a"', "'b'"]) == ["a", "b"]

    def test_dict_list_extracts_id(self):
        assert _as_list([{"id": "123"}, {"id": "456"}]) == ["123", "456"]

    def test_custom_id_key(self):
        assert _as_list([{"book_id": "b1"}, {"book_id": "b2"}], id_key="book_id") == ["b1", "b2"]


class TestNormalize:
    """Tests for normalize function (common.py)"""

    def test_lowercase(self):
        assert normalize("HELLO") == "hello"

    def test_strips_whitespace(self):
        assert normalize("  hello  ") == "hello"

    def test_preserves_internal_spaces(self):
        # normalize() does NFKC + lower + strip, but preserves internal spaces
        assert normalize("hello world") == "hello world"

    def test_nfkc_normalizes_fullwidth(self):
        # NFKC converts fullwidth to ASCII
        assert normalize("ＡＢＣ") == "abc"

    def test_empty_string(self):
        assert normalize("") == ""


class TestNormHeader:
    """Tests for norm_header function"""

    def test_lowercase(self):
        assert norm_header("HELLO") == "hello"

    def test_strips_whitespace(self):
        assert norm_header("  hello  ") == "hello"

    def test_removes_regular_spaces(self):
        assert norm_header("hello world") == "helloworld"

    def test_removes_fullwidth_spaces(self):
        assert norm_header("hello\u3000world") == "helloworld"

    def test_mixed_input(self):
        assert norm_header("  Hello\u3000World  ") == "helloworld"

    def test_empty_string(self):
        assert norm_header("") == ""


class TestPickCol:
    """Tests for pick_col function"""

    def test_finds_exact_match(self):
        headers = ["id", "name", "subject"]
        assert pick_col(headers, ["name"]) == 1

    def test_finds_first_candidate(self):
        headers = ["id", "name", "subject"]
        assert pick_col(headers, ["missing", "subject"]) == 2

    def test_case_insensitive(self):
        headers = ["ID", "NAME", "SUBJECT"]
        assert pick_col(headers, ["name"]) == 1

    def test_ignores_spaces(self):
        headers = ["book id", "book name"]
        assert pick_col(headers, ["bookid"]) == 0

    def test_returns_negative_one_when_not_found(self):
        headers = ["id", "name"]
        assert pick_col(headers, ["missing"]) == -1

    def test_empty_headers(self):
        assert pick_col([], ["name"]) == -1

    def test_empty_candidates(self):
        assert pick_col(["id", "name"], []) == -1


class TestTokenize:
    """Tests for tokenize function"""

    def test_splits_on_spaces(self):
        assert tokenize("hello world") == ["hello", "world"]

    def test_preserves_duplicates(self):
        # tokenize() doesn't remove duplicates
        assert tokenize("hello hello") == ["hello", "hello"]

    def test_filters_empty(self):
        assert tokenize("hello   world") == ["hello", "world"]

    def test_normalizes_case(self):
        assert tokenize("HELLO World") == ["hello", "world"]

    def test_filters_short_tokens(self):
        # Tokens shorter than 2 characters are filtered out
        assert tokenize("a bc def") == ["bc", "def"]


class TestParseMonthlyGoal:
    """Tests for parse_monthly_goal function"""

    def test_hours_per_day(self):
        result = parse_monthly_goal("1時間/日")
        assert result is not None
        assert result.get("per_day_minutes") == 60

    def test_decimal_hours(self):
        result = parse_monthly_goal("1.5時間/日")
        assert result is not None
        assert result.get("per_day_minutes") == 90

    def test_plain_hours(self):
        result = parse_monthly_goal("2時間")
        assert result is not None
        assert result.get("per_day_minutes") == 120

    def test_no_hours_returns_none_minutes(self):
        # If no 時間 pattern, per_day_minutes is None
        result = parse_monthly_goal("30分/日")
        assert result is not None
        assert result.get("per_day_minutes") is None

    def test_empty_string(self):
        assert parse_monthly_goal("") is None

    def test_none_input(self):
        assert parse_monthly_goal(None) is None


class TestColLetterToIndex:
    """Tests for col_letter_to_index function"""

    def test_single_letter(self):
        assert col_letter_to_index("A") == 0
        assert col_letter_to_index("B") == 1
        assert col_letter_to_index("Z") == 25

    def test_double_letter(self):
        assert col_letter_to_index("AA") == 26
        assert col_letter_to_index("AB") == 27
        assert col_letter_to_index("AZ") == 51

    def test_lowercase(self):
        assert col_letter_to_index("a") == 0
        assert col_letter_to_index("aa") == 26


class TestToNumberOrNone:
    """Tests for to_number_or_none function"""

    def test_integer_string(self):
        assert to_number_or_none("42") == 42

    def test_float_string(self):
        assert to_number_or_none("3.14") == 3.14

    def test_integer(self):
        assert to_number_or_none(42) == 42

    def test_float(self):
        assert to_number_or_none(3.14) == 3.14

    def test_none_returns_none(self):
        assert to_number_or_none(None) is None

    def test_empty_string(self):
        assert to_number_or_none("") is None

    def test_whitespace(self):
        assert to_number_or_none("  ") is None

    def test_invalid_string(self):
        assert to_number_or_none("not a number") is None


class TestOkNg:
    """Tests for ok/ng response builders"""

    def test_ok_basic(self):
        result = ok("test.op", {"key": "value"})
        assert result["ok"] is True
        assert result["op"] == "test.op"
        assert result["data"]["key"] == "value"

    def test_ng_basic(self):
        result = ng("test.op", "ERROR_CODE", "Error message")
        assert result["ok"] is False
        assert result["op"] == "test.op"
        assert result["error"]["code"] == "ERROR_CODE"
        assert result["error"]["message"] == "Error message"


class TestDecidePrefix:
    """Tests for decide_prefix function"""

    def test_math_subject(self):
        assert decide_prefix("数学", "青チャート") == "MA"

    def test_math_b(self):
        assert decide_prefix("数学B", "問題集") == "MB"

    def test_english(self):
        assert decide_prefix("英語", "長文読解") == "EN"

    def test_english_writing(self):
        assert decide_prefix("英語ライティング", "作文") == "EW"

    def test_physics(self):
        assert decide_prefix("物理", "力学") == "PP"

    def test_unknown_subject(self):
        assert decide_prefix("未知の科目", "テスト") == "XX"


class TestNextIdForPrefix:
    """Tests for next_id_for_prefix function"""

    def test_first_id(self):
        result = next_id_for_prefix("MB", [])
        assert result == "gMB001"

    def test_increments_existing(self):
        existing = ["gMB001", "gMB002"]
        result = next_id_for_prefix("MB", existing)
        assert result == "gMB003"

    def test_handles_gaps(self):
        existing = ["gMB001", "gMB005"]
        result = next_id_for_prefix("MB", existing)
        assert result == "gMB006"

    def test_ignores_other_prefixes(self):
        existing = ["gEN001", "gEN002"]
        result = next_id_for_prefix("MB", existing)
        assert result == "gMB001"


class TestExtractIdsFromValues:
    """Tests for extract_ids_from_values function"""

    def test_extracts_from_column(self):
        values = [
            ["ID", "Name"],
            ["gMB001", "Book 1"],
            ["gMB002", "Book 2"],
        ]
        result = extract_ids_from_values(values, 0)
        assert "gMB001" in result
        assert "gMB002" in result

    def test_includes_all_rows(self):
        # extract_ids_from_values doesn't skip header - includes all non-empty values
        values = [
            ["ID", "Name"],
            ["gMB001", "Book 1"],
        ]
        result = extract_ids_from_values(values, 0)
        # Both "ID" (header) and "gMB001" are extracted
        assert "ID" in result
        assert "gMB001" in result

    def test_handles_empty_cells(self):
        values = [
            ["gMB001", "Book 1"],
            ["", "Empty"],
            ["gMB002", "Book 2"],
        ]
        result = extract_ids_from_values(values, 0)
        assert "" not in result
        # Only 2 non-empty values in column 0
        assert len(result) == 2
        assert "gMB001" in result
        assert "gMB002" in result

    def test_handles_missing_column(self):
        values = [
            ["gMB001"],
            ["gMB002"],
        ]
        # Accessing column 1 which doesn't exist
        result = extract_ids_from_values(values, 1)
        assert result == []


class TestExtractSpreadsheetId:
    """Tests for extract_spreadsheet_id function"""

    def test_extracts_from_full_url(self):
        url = "https://docs.google.com/spreadsheets/d/1abc-XYZ_123456789012345678901234567890/edit#gid=0"
        result = extract_spreadsheet_id(url)
        assert result == "1abc-XYZ_123456789012345678901234567890"

    def test_extracts_from_short_url(self):
        url = "https://docs.google.com/spreadsheets/d/1abcdefghijklmnopqrstuvwxyz/edit"
        result = extract_spreadsheet_id(url)
        assert result == "1abcdefghijklmnopqrstuvwxyz"

    def test_extracts_from_url_with_query_params(self):
        url = "https://docs.google.com/spreadsheets/d/1test123456789abcdefghijk/edit?usp=sharing"
        result = extract_spreadsheet_id(url)
        assert result == "1test123456789abcdefghijk"

    def test_returns_none_for_invalid_url(self):
        url = "https://example.com/not-a-spreadsheet"
        result = extract_spreadsheet_id(url)
        assert result is None

    def test_returns_none_for_short_id(self):
        # IDs must be at least 25 characters
        url = "https://docs.google.com/spreadsheets/d/short/edit"
        result = extract_spreadsheet_id(url)
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = extract_spreadsheet_id("")
        assert result is None

    def test_returns_none_for_none(self):
        result = extract_spreadsheet_id(None)  # type: ignore
        assert result is None

    def test_extracts_raw_id_string(self):
        # If given just an ID string (not a URL), should still work
        raw_id = "1abcdefghijklmnopqrstuvwxyz12345"
        result = extract_spreadsheet_id(raw_id)
        assert result == raw_id

    def test_handles_hyphen_and_underscore(self):
        # Real IDs contain hyphens and underscores
        url = "https://docs.google.com/spreadsheets/d/1abc-XYZ_123-456_789-abc_def/edit"
        result = extract_spreadsheet_id(url)
        assert result == "1abc-XYZ_123-456_789-abc_def"
