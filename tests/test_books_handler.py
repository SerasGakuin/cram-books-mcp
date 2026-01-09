"""
Tests for BooksHandler class.
TDD tests for the new OOP-based BooksHandler implementation.
"""
import pytest
from unittest.mock import MagicMock


class TestBooksHandlerInit:
    """Tests for BooksHandler initialization."""

    def test_init_uses_default_ids(self):
        """Should use default file_id and sheet_name from class variables."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        handler = BooksHandler(mock_sheets)

        # Should use class defaults
        assert handler.file_id is not None
        assert handler.sheet_name is not None

    def test_init_accepts_custom_ids(self):
        """Should accept custom file_id and sheet_name."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        handler = BooksHandler(mock_sheets, file_id="custom-file", sheet_name="CustomSheet")

        assert handler.file_id == "custom-file"
        assert handler.sheet_name == "CustomSheet"


class TestBooksHandlerColumnSpec:
    """Tests for COLUMN_SPEC configuration."""

    def test_column_spec_has_required_keys(self):
        """Should define all required column keys."""
        from handlers.books import BooksHandler

        required_keys = ["id", "title", "subject", "goal", "unit",
                         "chap_idx", "chap_name", "chap_begin", "chap_end",
                         "numbering", "book_type", "quiz_type", "quiz_id"]

        for key in required_keys:
            assert key in BooksHandler.COLUMN_SPEC, f"Missing key: {key}"


class TestBooksHandlerFind:
    """Tests for find method (IDF search)."""

    def test_find_requires_query(self):
        """Should return error when query is empty."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        handler = BooksHandler(mock_sheets)

        result = handler.find("")

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_find_returns_candidates(self):
        """Should return scored candidates for valid query."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科", "月間目標", "単元負荷"],
            ["gMA001", "青チャート数学IA", "数学", "1時間/日", 5],
            ["gMA002", "青チャート数学IIB", "数学", "1時間/日", 5],
            ["gEN001", "英語長文読解", "英語", "1時間/日", 3],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.find("青チャート")

        assert result["ok"] is True
        assert "candidates" in result["data"]
        assert len(result["data"]["candidates"]) >= 1

    def test_find_exact_match_highest_score(self):
        """Exact match should have the highest score."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
            ["gMA002", "青チャート数学II", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.find("青チャート")

        assert result["ok"] is True
        candidates = result["data"]["candidates"]
        assert len(candidates) >= 1
        # Exact match should be first
        assert candidates[0]["book_id"] == "gMA001"

    def test_find_respects_limit(self):
        """Should respect the limit parameter."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "数学問題集1", "数学"],
            ["gMA002", "数学問題集2", "数学"],
            ["gMA003", "数学問題集3", "数学"],
            ["gMA004", "数学問題集4", "数学"],
            ["gMA005", "数学問題集5", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.find("数学", limit=2)

        assert result["ok"] is True
        assert len(result["data"]["candidates"]) <= 2


class TestBooksHandlerGet:
    """Tests for get method."""

    def test_get_requires_book_id(self):
        """Should return error when book_id is missing."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        handler = BooksHandler(mock_sheets)

        result = handler.get(None)

        assert result["ok"] is False
        assert result["error"]["code"] == "BAD_REQUEST"

    def test_get_returns_book_details(self):
        """Should return book details with chapters."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科", "月間目標", "単元負荷", "章番号", "章名", "開始", "終了"],
            ["gMA001", "青チャート", "数学", "1時間/日", 5, 1, "第1章 数と式", 1, 50],
            ["", "", "", "", "", 2, "第2章 方程式", 51, 100],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.get("gMA001")

        assert result["ok"] is True
        assert "book" in result["data"]
        book = result["data"]["book"]
        assert book["id"] == "gMA001"
        assert book["title"] == "青チャート"
        assert len(book["structure"]["chapters"]) == 2

    def test_get_not_found(self):
        """Should return error for non-existent book."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.get("gXX999")

        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"

    def test_get_multiple_books(self):
        """Should return multiple books when book_ids list is provided."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
            ["gMA002", "赤チャート", "数学"],
            ["gEN001", "英語", "英語"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.get_multiple(["gMA001", "gEN001"])

        assert result["ok"] is True
        assert "books" in result["data"]
        assert len(result["data"]["books"]) == 2


class TestBooksHandlerFilter:
    """Tests for filter method."""

    def test_filter_by_where(self):
        """Should filter by exact match (where)."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
            ["gMA002", "赤チャート", "数学"],
            ["gEN001", "英語長文", "英語"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.filter(where={"教科": "数学"})

        assert result["ok"] is True
        assert result["data"]["count"] == 2

    def test_filter_by_contains(self):
        """Should filter by partial match (contains)."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート数学IA", "数学"],
            ["gMA002", "赤チャート数学IIB", "数学"],
            ["gEN001", "英語長文読解", "英語"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.filter(contains={"参考書名": "チャート"})

        assert result["ok"] is True
        assert result["data"]["count"] == 2

    def test_filter_with_limit(self):
        """Should respect limit parameter."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "数学1", "数学"],
            ["gMA002", "数学2", "数学"],
            ["gMA003", "数学3", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.filter(where={"教科": "数学"}, limit=2)

        assert result["ok"] is True
        assert len(result["data"]["books"]) <= 2


class TestBooksHandlerList:
    """Tests for list method."""

    def test_list_returns_all_books(self):
        """Should return all books with basic info."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
            ["gMA002", "赤チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.list()

        assert result["ok"] is True
        assert len(result["data"]["books"]) == 2
        # Should only include basic info
        for book in result["data"]["books"]:
            assert "id" in book
            assert "title" in book
            assert "subject" in book

    def test_list_respects_limit(self):
        """Should respect limit parameter."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "数学1", "数学"],
            ["gMA002", "数学2", "数学"],
            ["gMA003", "数学3", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.list(limit=2)

        assert result["ok"] is True
        assert len(result["data"]["books"]) == 2


class TestBooksHandlerCreate:
    """Tests for create method."""

    def test_create_requires_title_and_subject(self):
        """Should return error when title or subject is missing."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
        ]
        handler = BooksHandler(mock_sheets)

        result = handler.create(title="", subject="数学")
        assert result["ok"] is False

        result = handler.create(title="テスト", subject="")
        assert result["ok"] is False

    def test_create_generates_new_id(self):
        """Should generate new ID based on subject."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "既存の本", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.create(title="新しい本", subject="数学")

        assert result["ok"] is True
        assert result["data"]["id"].startswith("gMA")
        # Should be gMA002 (next after gMA001)
        assert result["data"]["id"] == "gMA002"

    def test_create_appends_rows(self):
        """Should append rows for parent and chapters."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科", "章番号", "章名", "開始", "終了"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.create(
            title="新しい本",
            subject="数学",
            chapters=[
                {"title": "第1章", "range": {"start": 1, "end": 50}},
                {"title": "第2章", "range": {"start": 51, "end": 100}},
            ]
        )

        assert result["ok"] is True
        # Should have called append_rows
        mock_sheets.append_rows.assert_called_once()
        # Should have created 2 rows (parent with first chapter, then second chapter)
        call_args = mock_sheets.append_rows.call_args
        rows = call_args[0][2]  # Third positional argument
        assert len(rows) == 2


class TestBooksHandlerUpdate:
    """Tests for update method (two-phase)."""

    def test_update_preview_mode(self):
        """Should return preview without confirm_token."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.update("gMA001", updates={"title": "新タイトル"})

        assert result["ok"] is True
        assert result["data"]["requires_confirmation"] is True
        assert "confirm_token" in result["data"]
        assert "preview" in result["data"]

    def test_update_confirm_mode(self):
        """Should apply updates with valid confirm_token."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)

        # First call: get preview and token
        preview_result = handler.update("gMA001", updates={"title": "新タイトル"})
        token = preview_result["data"]["confirm_token"]

        # Second call: confirm with token
        confirm_result = handler.update("gMA001", confirm_token=token)

        assert confirm_result["ok"] is True
        assert confirm_result["data"]["updated"] is True

    def test_update_expired_token(self):
        """Should reject expired/invalid token."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.update("gMA001", confirm_token="invalid-token")

        assert result["ok"] is False
        assert result["error"]["code"] == "CONFIRM_EXPIRED"


class TestBooksHandlerDelete:
    """Tests for delete method (two-phase)."""

    def test_delete_preview_mode(self):
        """Should return preview without confirm_token."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.delete("gMA001")

        assert result["ok"] is True
        assert result["data"]["requires_confirmation"] is True
        assert "confirm_token" in result["data"]

    def test_delete_confirm_mode(self):
        """Should delete with valid confirm_token."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)

        # First call: get preview and token
        preview_result = handler.delete("gMA001")
        token = preview_result["data"]["confirm_token"]

        # Second call: confirm with token
        confirm_result = handler.delete("gMA001", confirm_token=token)

        assert confirm_result["ok"] is True
        assert "deleted_rows" in confirm_result["data"]

    def test_delete_not_found(self):
        """Should return error for non-existent book."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "青チャート", "数学"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.delete("gXX999")

        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"


class TestBooksHandlerChapterParsing:
    """Tests for chapter parsing logic."""

    def test_parses_chapters_from_child_rows(self):
        """Should parse chapters from child rows (rows without ID)."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科", "章番号", "章名", "開始", "終了", "ナンバリング"],
            ["gMA001", "青チャート", "数学", 1, "第1章", 1, 50, "例題1-50"],
            ["", "", "", 2, "第2章", 51, 100, "例題51-100"],
            ["", "", "", 3, "第3章", 101, 150, "例題101-150"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.get("gMA001")

        assert result["ok"] is True
        chapters = result["data"]["book"]["structure"]["chapters"]
        assert len(chapters) == 3

        # First chapter
        assert chapters[0]["title"] == "第1章"
        assert chapters[0]["range"]["start"] == 1
        assert chapters[0]["range"]["end"] == 50

        # Third chapter
        assert chapters[2]["title"] == "第3章"
        assert chapters[2]["range"]["start"] == 101

    def test_handles_missing_chapter_fields(self):
        """Should handle rows with missing chapter fields gracefully."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科", "章番号", "章名", "開始", "終了"],
            ["gMA001", "青チャート", "数学", 1, "第1章", "", ""],  # No range
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.get("gMA001")

        assert result["ok"] is True
        chapters = result["data"]["book"]["structure"]["chapters"]
        assert len(chapters) == 1
        # Range should be None or have None values
        ch = chapters[0]
        assert ch["title"] == "第1章"


class TestBooksHandlerIdfScoring:
    """Tests for IDF scoring algorithm."""

    def test_idf_term_in_single_doc_gets_high_weight(self):
        """Term appearing in single document should get high IDF weight."""
        from handlers.books import BooksHandler, _calculate_idf

        # Term appears in 1 out of 100 documents
        doc_freq = {"rare_term": 1}
        total_docs = 100

        idf = _calculate_idf("rare_term", doc_freq, total_docs)

        # Should be high (around 4.6 for 1/100)
        assert idf > 4.0

    def test_idf_common_term_gets_low_weight(self):
        """Term appearing in many documents should get low IDF weight."""
        from handlers.books import BooksHandler, _calculate_idf

        # Term appears in 90 out of 100 documents
        doc_freq = {"common_term": 90}
        total_docs = 100

        idf = _calculate_idf("common_term", doc_freq, total_docs)

        # Should be low (close to 0)
        assert idf < 0.5

    def test_subject_bonus_applies(self):
        """Subject match should boost relevance score."""
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["参考書ID", "参考書名", "教科"],
            ["gMA001", "問題集", "数学"],
            ["gEN001", "問題集", "英語"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.find("数学 問題集")

        assert result["ok"] is True
        candidates = result["data"]["candidates"]
        # Math book should score higher due to subject bonus
        assert candidates[0]["book_id"] == "gMA001"
