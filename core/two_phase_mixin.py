"""
Two-Phase Operation Mixin.

Provides reusable two-phase (preview → confirm) operation pattern
for update and delete operations. Eliminates duplicate code between
BooksHandler and StudentsHandler.

Usage:
    class MyHandler(BaseHandler, TwoPhaseOperationMixin):
        def update(self, entity_id, updates=None, confirm_token=None):
            if not confirm_token:
                # Preview mode
                return self.store_preview(
                    op="my.update",
                    cache_prefix="upd",
                    entity_id=entity_id,
                    payload={"updates": updates, "row": row_index},
                    preview_data={"diffs": diffs},
                )
            # Confirm mode
            result = self.validate_confirm(
                op="my.update",
                cache_prefix="upd",
                entity_id=entity_id,
                confirm_token=confirm_token,
            )
            if not result["valid"]:
                return result["error"]
            # Execute update using result["payload"]
            ...
"""
from __future__ import annotations

from typing import Any, Callable, Protocol, TypedDict


class PreviewCacheProtocol(Protocol):
    """Protocol for preview cache interface."""

    ttl_seconds: int

    def store(self, prefix: str, data: dict) -> str:
        ...

    def pop(self, prefix: str, token: str) -> dict | None:
        ...


class ErrorInfo(TypedDict):
    """Error information for validation failures."""

    code: str
    message: str


class ValidateResult(TypedDict, total=False):
    """Result of confirm token validation."""

    valid: bool
    payload: dict[str, Any]
    error: ErrorInfo


class TwoPhaseOperationMixin:
    """
    Mixin for two-phase (preview → confirm) operations.

    Requires:
    - self._preview_cache: PreviewCache instance
    - self._ok(op, data): Success response builder
    - self._error(op, code, message): Error response builder
    """

    _preview_cache: PreviewCacheProtocol

    def _ok(self, op: str, data: dict[str, Any]) -> dict[str, Any]:
        """Override in subclass or inherit from BaseHandler."""
        raise NotImplementedError

    def _error(
        self, op: str, code: str, message: str, extra: dict | None = None
    ) -> dict[str, Any]:
        """Override in subclass or inherit from BaseHandler."""
        raise NotImplementedError

    # === Preview Phase ===

    def store_preview(
        self,
        op: str,
        cache_prefix: str,
        entity_id: str,
        payload: dict[str, Any],
        preview_data: dict[str, Any],
        entity_id_key: str = "entity_id",
    ) -> dict[str, Any]:
        """
        Store preview data and return confirmation response.

        Args:
            op: Operation name (e.g., "books.update")
            cache_prefix: Cache prefix for token storage
            entity_id: Entity ID (e.g., book_id, student_id)
            payload: Data to store for confirmation phase
            preview_data: Data to include in preview response
            entity_id_key: Key name for entity ID in cache (default: "entity_id")

        Returns:
            Response with requires_confirmation, confirm_token, preview
        """
        # Store payload with entity_id
        cache_data = {entity_id_key: entity_id, **payload}
        token = self._preview_cache.store(cache_prefix, cache_data)

        return self._ok(op, {
            "requires_confirmation": True,
            "preview": preview_data,
            "confirm_token": token,
            "expires_in_seconds": self._preview_cache.ttl_seconds,
        })

    # === Confirm Phase ===

    def validate_confirm(
        self,
        op: str,
        cache_prefix: str,
        entity_id: str,
        confirm_token: str,
        entity_id_key: str = "entity_id",
    ) -> ValidateResult:
        """
        Validate confirmation token and entity ID.

        Args:
            op: Operation name
            cache_prefix: Cache prefix for token retrieval
            entity_id: Expected entity ID
            confirm_token: Token from preview phase
            entity_id_key: Key name for entity ID in cache

        Returns:
            ValidateResult with valid=True and payload, or valid=False and error
        """
        cached = self._preview_cache.pop(cache_prefix, confirm_token)

        if not cached:
            return ValidateResult(
                valid=False,
                error=ErrorInfo(code="CONFIRM_EXPIRED", message="confirm_token is invalid or expired"),
            )

        cached_id = str(cached.get(entity_id_key, ""))
        if cached_id != str(entity_id):
            return ValidateResult(
                valid=False,
                error=ErrorInfo(code="CONFIRM_MISMATCH", message=f"{entity_id_key} mismatch"),
            )

        # Remove entity_id from payload before returning
        payload = {k: v for k, v in cached.items() if k != entity_id_key}

        return ValidateResult(valid=True, payload=payload)

    # === High-Level Orchestration ===

    def two_phase_update(
        self,
        op: str,
        cache_prefix: str,
        entity_id: str,
        confirm_token: str | None,
        build_preview: Callable[[], tuple[dict[str, Any], dict[str, Any]]],
        execute_update: Callable[[dict[str, Any]], dict[str, Any]],
        entity_id_key: str = "entity_id",
    ) -> dict[str, Any]:
        """
        Orchestrate two-phase update operation.

        Args:
            op: Operation name
            cache_prefix: Cache prefix
            entity_id: Entity ID
            confirm_token: Token (None for preview, string for confirm)
            build_preview: Callable returning (payload, preview_data)
            execute_update: Callable taking payload and returning result data
            entity_id_key: Key name for entity ID

        Returns:
            Preview response or update result
        """
        if not confirm_token:
            # Preview mode
            payload, preview_data = build_preview()
            return self.store_preview(
                op=op,
                cache_prefix=cache_prefix,
                entity_id=entity_id,
                payload=payload,
                preview_data=preview_data,
                entity_id_key=entity_id_key,
            )

        # Confirm mode
        result = self.validate_confirm(
            op=op,
            cache_prefix=cache_prefix,
            entity_id=entity_id,
            confirm_token=confirm_token,
            entity_id_key=entity_id_key,
        )

        if not result["valid"]:
            err = result["error"]
            return self._error(op, err["code"], err["message"])

        update_result = execute_update(result["payload"])
        return self._ok(op, update_result)

    def two_phase_delete(
        self,
        op: str,
        cache_prefix: str,
        entity_id: str,
        confirm_token: str | None,
        build_preview: Callable[[], tuple[dict[str, Any], dict[str, Any]]],
        execute_delete: Callable[[dict[str, Any]], dict[str, Any]],
        entity_id_key: str = "entity_id",
    ) -> dict[str, Any]:
        """
        Orchestrate two-phase delete operation.

        Same interface as two_phase_update for consistency.
        """
        return self.two_phase_update(
            op=op,
            cache_prefix=cache_prefix,
            entity_id=entity_id,
            confirm_token=confirm_token,
            build_preview=build_preview,
            execute_update=execute_delete,  # Same logic, different name
            entity_id_key=entity_id_key,
        )
