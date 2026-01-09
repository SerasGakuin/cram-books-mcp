"""
Tests for TwoPhaseOperationMixin.

TDD: Write tests first, then implement the mixin.
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from core.two_phase_mixin import TwoPhaseOperationMixin
from lib.preview_cache import PreviewCache


class MockHandler(TwoPhaseOperationMixin):
    """Mock handler for testing the mixin."""

    def __init__(self):
        self._preview_cache = PreviewCache(ttl_seconds=300)

    def _ok(self, op: str, data: dict) -> dict:
        return {"ok": True, "op": op, "data": data}

    def _error(self, op: str, code: str, message: str, extra: dict | None = None) -> dict:
        return {"ok": False, "op": op, "error": {"code": code, "message": message}}


class TestTwoPhasePreview:
    """Tests for preview phase functionality."""

    def test_store_preview_returns_confirmation_response(self):
        handler = MockHandler()
        response = handler.store_preview(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            payload={"field": "value"},
            preview_data={"changes": {"field": {"from": "old", "to": "new"}}},
        )

        assert response["ok"] is True
        assert response["op"] == "test.update"
        assert response["data"]["requires_confirmation"] is True
        assert "confirm_token" in response["data"]
        assert response["data"]["expires_in_seconds"] == 300
        assert response["data"]["preview"]["changes"]["field"]["from"] == "old"

    def test_store_preview_with_custom_preview_data(self):
        handler = MockHandler()
        response = handler.store_preview(
            op="books.delete",
            cache_prefix="del",
            entity_id="gMB001",
            payload={"parent_row": 5, "end_row": 8},
            preview_data={"delete_rows": 3, "book_id": "gMB001"},
        )

        assert response["data"]["preview"]["delete_rows"] == 3
        assert response["data"]["preview"]["book_id"] == "gMB001"


class TestTwoPhaseConfirm:
    """Tests for confirm phase functionality."""

    def test_validate_confirm_succeeds_with_valid_token(self):
        handler = MockHandler()
        # Store preview first
        store_response = handler.store_preview(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            payload={"key": "value"},
            preview_data={},
        )
        token = store_response["data"]["confirm_token"]

        # Validate confirm
        result = handler.validate_confirm(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            confirm_token=token,
        )

        assert result["valid"] is True
        assert result["payload"]["key"] == "value"
        assert "error" not in result

    def test_validate_confirm_fails_with_expired_token(self):
        handler = MockHandler()
        result = handler.validate_confirm(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            confirm_token="invalid_token",
        )

        assert result["valid"] is False
        assert result["error"]["code"] == "CONFIRM_EXPIRED"

    def test_validate_confirm_fails_with_mismatched_id(self):
        handler = MockHandler()
        # Store preview
        store_response = handler.store_preview(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            payload={},
            preview_data={},
        )
        token = store_response["data"]["confirm_token"]

        # Validate with different entity_id
        result = handler.validate_confirm(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e002",  # Different ID
            confirm_token=token,
        )

        assert result["valid"] is False
        assert result["error"]["code"] == "CONFIRM_MISMATCH"

    def test_validate_confirm_consumes_token(self):
        handler = MockHandler()
        # Store preview
        store_response = handler.store_preview(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            payload={},
            preview_data={},
        )
        token = store_response["data"]["confirm_token"]

        # First validation succeeds
        result1 = handler.validate_confirm(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            confirm_token=token,
        )
        assert result1["valid"] is True

        # Second validation fails (token consumed)
        result2 = handler.validate_confirm(
            op="test.update",
            cache_prefix="test_upd",
            entity_id="e001",
            confirm_token=token,
        )
        assert result2["valid"] is False
        assert result2["error"]["code"] == "CONFIRM_EXPIRED"


class TestTwoPhaseOrchestration:
    """Tests for two-phase operation orchestration."""

    def test_two_phase_update_preview_mode(self):
        handler = MockHandler()

        response = handler.two_phase_update(
            op="test.update",
            cache_prefix="upd",
            entity_id="e001",
            confirm_token=None,
            build_preview=lambda: ({"field": "new_value"}, {"changes": {"field": "new_value"}}),
            execute_update=lambda payload: {"updated": True},
        )

        assert response["ok"] is True
        assert response["data"]["requires_confirmation"] is True
        assert "confirm_token" in response["data"]

    def test_two_phase_update_confirm_mode(self):
        handler = MockHandler()

        # First: preview
        preview_response = handler.two_phase_update(
            op="test.update",
            cache_prefix="upd",
            entity_id="e001",
            confirm_token=None,
            build_preview=lambda: ({"field": "new_value"}, {"changes": {}}),
            execute_update=lambda payload: {"updated": True},
        )
        token = preview_response["data"]["confirm_token"]

        # Second: confirm
        confirm_response = handler.two_phase_update(
            op="test.update",
            cache_prefix="upd",
            entity_id="e001",
            confirm_token=token,
            build_preview=lambda: (None, None),  # Should not be called
            execute_update=lambda payload: {"updated": True, "field": payload["field"]},
        )

        assert confirm_response["ok"] is True
        assert confirm_response["data"]["updated"] is True
        assert confirm_response["data"]["field"] == "new_value"

    def test_two_phase_delete_preview_mode(self):
        handler = MockHandler()

        response = handler.two_phase_delete(
            op="test.delete",
            cache_prefix="del",
            entity_id="e001",
            confirm_token=None,
            build_preview=lambda: ({"row_index": 5}, {"row": 5}),
            execute_delete=lambda payload: {"deleted": True},
        )

        assert response["ok"] is True
        assert response["data"]["requires_confirmation"] is True
        assert response["data"]["preview"]["row"] == 5

    def test_two_phase_delete_confirm_mode(self):
        handler = MockHandler()

        # First: preview
        preview_response = handler.two_phase_delete(
            op="test.delete",
            cache_prefix="del",
            entity_id="e001",
            confirm_token=None,
            build_preview=lambda: ({"row_index": 5}, {"row": 5}),
            execute_delete=lambda payload: {"deleted": True, "rows": 1},
        )
        token = preview_response["data"]["confirm_token"]

        # Second: confirm
        confirm_response = handler.two_phase_delete(
            op="test.delete",
            cache_prefix="del",
            entity_id="e001",
            confirm_token=token,
            build_preview=lambda: (None, None),  # Should not be called
            execute_delete=lambda payload: {"deleted": True, "rows": 1},
        )

        assert confirm_response["ok"] is True
        assert confirm_response["data"]["deleted"] is True
        assert confirm_response["data"]["rows"] == 1


class TestEntityIdKey:
    """Tests for custom entity ID key handling."""

    def test_custom_entity_id_key(self):
        handler = MockHandler()

        # Store with book_id
        store_response = handler.store_preview(
            op="books.update",
            cache_prefix="upd",
            entity_id="gMB001",
            payload={"data": "value"},
            preview_data={},
            entity_id_key="book_id",
        )
        token = store_response["data"]["confirm_token"]

        # Validate with book_id
        result = handler.validate_confirm(
            op="books.update",
            cache_prefix="upd",
            entity_id="gMB001",
            confirm_token=token,
            entity_id_key="book_id",
        )

        assert result["valid"] is True

    def test_mismatched_id_key_fails(self):
        handler = MockHandler()

        # Store with default key
        store_response = handler.store_preview(
            op="test.update",
            cache_prefix="upd",
            entity_id="e001",
            payload={},
            preview_data={},
            entity_id_key="entity_id",
        )
        token = store_response["data"]["confirm_token"]

        # Validate with different ID
        result = handler.validate_confirm(
            op="test.update",
            cache_prefix="upd",
            entity_id="different_id",
            confirm_token=token,
            entity_id_key="entity_id",
        )

        assert result["valid"] is False
        assert result["error"]["code"] == "CONFIRM_MISMATCH"
