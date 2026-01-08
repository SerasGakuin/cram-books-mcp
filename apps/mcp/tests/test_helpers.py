"""
Tests for helper functions in server.py
Pure functions that can be tested without mocking HTTP calls
"""
import os
import time
import hmac
import hashlib
import pytest
from unittest.mock import patch

# Import helpers from server module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    _strip_quotes,
    _coerce_str,
    _norm_header,
    _pick_col,
    _preview_put,
    _preview_get,
    _preview_pop,
    _normalize_key_for_sheet,
    _parse_where_like,
    _week_count_from_dates,
    _index_by_row,
    _PREVIEW_CACHE,
    _hmac_required,
    _hmac_secret,
    _verify_hmac,
)


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


class TestNormHeader:
    """Tests for _norm_header function"""

    def test_lowercase(self):
        assert _norm_header("HELLO") == "hello"

    def test_strips_whitespace(self):
        assert _norm_header("  hello  ") == "hello"

    def test_removes_regular_spaces(self):
        assert _norm_header("hello world") == "helloworld"

    def test_removes_fullwidth_spaces(self):
        assert _norm_header("hello\u3000world") == "helloworld"

    def test_mixed_input(self):
        assert _norm_header("  Hello\u3000World  ") == "helloworld"

    def test_empty_string(self):
        assert _norm_header("") == ""


class TestPickCol:
    """Tests for _pick_col function"""

    def test_finds_exact_match(self):
        headers = ["id", "name", "subject"]
        assert _pick_col(headers, ["name"]) == 1

    def test_finds_first_candidate(self):
        headers = ["id", "name", "subject"]
        assert _pick_col(headers, ["missing", "subject"]) == 2

    def test_case_insensitive(self):
        headers = ["ID", "NAME", "SUBJECT"]
        assert _pick_col(headers, ["name"]) == 1

    def test_ignores_spaces(self):
        headers = ["book id", "book name"]
        assert _pick_col(headers, ["bookid"]) == 0

    def test_returns_negative_one_when_not_found(self):
        headers = ["id", "name"]
        assert _pick_col(headers, ["missing"]) == -1

    def test_empty_headers(self):
        assert _pick_col([], ["name"]) == -1

    def test_empty_candidates(self):
        assert _pick_col(["id", "name"], []) == -1


class TestPreviewCache:
    """Tests for preview cache functions"""

    def setup_method(self):
        _PREVIEW_CACHE.clear()

    def teardown_method(self):
        _PREVIEW_CACHE.clear()

    def test_put_returns_token(self):
        token = _preview_put({"data": "test"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_get_returns_payload(self):
        payload = {"data": "test"}
        token = _preview_put(payload)
        assert _preview_get(token) == payload

    def test_get_missing_returns_none(self):
        assert _preview_get("nonexistent") is None

    def test_pop_returns_and_removes(self):
        payload = {"data": "test"}
        token = _preview_put(payload)
        assert _preview_pop(token) == payload
        assert _preview_get(token) is None

    def test_pop_missing_returns_none(self):
        assert _preview_pop("nonexistent") is None

    def test_multiple_entries(self):
        token1 = _preview_put({"id": 1})
        token2 = _preview_put({"id": 2})
        assert _preview_get(token1)["id"] == 1
        assert _preview_get(token2)["id"] == 2


class TestNormalizeKeyForSheet:
    """Tests for _normalize_key_for_sheet function"""

    def test_id_mappings(self):
        assert _normalize_key_for_sheet("id") == "参考書ID"
        assert _normalize_key_for_sheet("参考書id") == "参考書ID"
        assert _normalize_key_for_sheet("参考書ｉｄ") == "参考書ID"

    def test_title_mappings(self):
        assert _normalize_key_for_sheet("title") == "参考書名"
        assert _normalize_key_for_sheet("参考書名") == "参考書名"
        assert _normalize_key_for_sheet("書名") == "参考書名"

    def test_subject_mapping(self):
        assert _normalize_key_for_sheet("subject") == "教科"
        assert _normalize_key_for_sheet("教科") == "教科"

    def test_passthrough_unmapped(self):
        assert _normalize_key_for_sheet("unknown_key") == "unknown_key"

    def test_case_insensitive(self):
        assert _normalize_key_for_sheet("ID") == "参考書ID"
        assert _normalize_key_for_sheet("Title") == "参考書名"


class TestParseWhereLike:
    """Tests for _parse_where_like function"""

    def test_dict_input_passthrough(self):
        result = _parse_where_like({"教科": "数学"})
        assert result is not None
        assert result.get("教科") == "数学"

    def test_normalizes_keys(self):
        result = _parse_where_like({"subject": "数学"})
        assert result is not None
        assert "教科" in result

    def test_string_with_equals(self):
        result = _parse_where_like('subject = "数学"')
        assert result is not None
        assert result.get("教科") == "数学"

    def test_string_with_colon(self):
        result = _parse_where_like("title: 青チャート")
        assert result is not None
        assert result.get("参考書名") == "青チャート"

    def test_returns_none_for_invalid(self):
        assert _parse_where_like(None) is None
        assert _parse_where_like(123) is None
        assert _parse_where_like([]) is None

    def test_empty_dict(self):
        result = _parse_where_like({})
        assert result == {}


class TestWeekCountFromDates:
    """Tests for _week_count_from_dates function"""

    def test_four_weeks(self):
        dget = {"data": {"week_starts": ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25", ""]}}
        assert _week_count_from_dates(dget) == 4

    def test_five_weeks(self):
        dget = {"data": {"week_starts": ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25", "2025-09-01"]}}
        assert _week_count_from_dates(dget) == 5

    def test_no_data_defaults_to_five(self):
        dget = {}
        # When no data, function defaults to 5
        assert _week_count_from_dates(dget) == 5

    def test_empty_week_starts_returns_length(self):
        dget = {"data": {"week_starts": []}}
        # When empty list, returns len(ws) = 0 (edge case)
        assert _week_count_from_dates(dget) == 0


class TestIndexByRow:
    """Tests for _index_by_row function"""

    def test_indexes_by_row(self):
        items = [{"row": 4, "data": "a"}, {"row": 5, "data": "b"}]
        result = _index_by_row(items)
        assert result[4]["data"] == "a"
        assert result[5]["data"] == "b"

    def test_custom_key(self):
        items = [{"index": 1, "data": "a"}, {"index": 2, "data": "b"}]
        result = _index_by_row(items, key="index")
        assert result[1]["data"] == "a"

    def test_empty_list(self):
        assert _index_by_row([]) == {}

    def test_missing_key_skipped(self):
        items = [{"row": 4, "data": "a"}, {"data": "b"}]
        result = _index_by_row(items)
        assert 4 in result
        assert len(result) == 1


class TestHmacFunctions:
    """Tests for HMAC verification functions"""

    def test_hmac_required_defaults_false(self, monkeypatch):
        monkeypatch.delenv("MCP_HMAC_REQUIRED", raising=False)
        assert _hmac_required() is False

    def test_hmac_required_true(self, monkeypatch):
        monkeypatch.setenv("MCP_HMAC_REQUIRED", "true")
        assert _hmac_required() is True

    def test_hmac_required_various_values(self, monkeypatch):
        for val in ["1", "yes", "on", "true"]:
            monkeypatch.setenv("MCP_HMAC_REQUIRED", val)
            assert _hmac_required() is True

    def test_hmac_secret_returns_none_if_not_set(self, monkeypatch):
        monkeypatch.delenv("MCP_HMAC_SECRET", raising=False)
        assert _hmac_secret() is None

    def test_hmac_secret_returns_value(self, monkeypatch):
        monkeypatch.setenv("MCP_HMAC_SECRET", "my-secret")
        assert _hmac_secret() == "my-secret"


class TestVerifyHmac:
    """Tests for _verify_hmac function"""

    def test_no_secret_returns_ok(self, monkeypatch):
        monkeypatch.delenv("MCP_HMAC_SECRET", raising=False)
        ok, reason = _verify_hmac([], "GET", "/mcp")
        assert ok is True
        assert reason is None

    def test_valid_signature(self, monkeypatch):
        secret = "test-secret"
        monkeypatch.setenv("MCP_HMAC_SECRET", secret)
        ts = str(int(time.time()))
        method = "POST"
        path = "/mcp"
        mac = hmac.new(secret.encode(), f"{ts}.{method}.{path}".encode(), hashlib.sha256)
        sig = mac.hexdigest()
        headers = [
            (b"x-mcp-ts", ts.encode()),
            (b"x-mcp-sign", sig.encode()),
        ]
        ok, reason = _verify_hmac(headers, method, path)
        assert ok is True

    def test_invalid_signature(self, monkeypatch):
        monkeypatch.setenv("MCP_HMAC_SECRET", "test-secret")
        ts = str(int(time.time()))
        headers = [
            (b"x-mcp-ts", ts.encode()),
            (b"x-mcp-sign", b"invalid-signature"),
        ]
        ok, reason = _verify_hmac(headers, "POST", "/mcp")
        assert ok is False
        assert reason == "bad signature"

    def test_timestamp_skew(self, monkeypatch):
        secret = "test-secret"
        monkeypatch.setenv("MCP_HMAC_SECRET", secret)
        old_ts = str(int(time.time()) - 400)  # 400 seconds ago (> 300 threshold)
        method = "POST"
        path = "/mcp"
        mac = hmac.new(secret.encode(), f"{old_ts}.{method}.{path}".encode(), hashlib.sha256)
        sig = mac.hexdigest()
        headers = [
            (b"x-mcp-ts", old_ts.encode()),
            (b"x-mcp-sign", sig.encode()),
        ]
        ok, reason = _verify_hmac(headers, method, path)
        assert ok is False
        assert reason == "timestamp skew"

    def test_missing_headers_required(self, monkeypatch):
        monkeypatch.setenv("MCP_HMAC_SECRET", "test-secret")
        monkeypatch.setenv("MCP_HMAC_REQUIRED", "true")
        ok, reason = _verify_hmac([], "POST", "/mcp")
        assert ok is False
        assert reason == "missing headers"

    def test_missing_headers_optional(self, monkeypatch):
        monkeypatch.setenv("MCP_HMAC_SECRET", "test-secret")
        monkeypatch.setenv("MCP_HMAC_REQUIRED", "false")
        ok, reason = _verify_hmac([], "POST", "/mcp")
        assert ok is True
