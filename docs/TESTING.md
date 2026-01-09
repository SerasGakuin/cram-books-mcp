# Testing Guide

このドキュメントはcram-books-mcpプロジェクトのテスト基盤を説明します。

## 概要

| カテゴリ | テスト数 | 対象 |
|---------|---------|------|
| lib/（ヘルパー） | 66 | 純粋関数 |
| handlers（ハンドラー） | 96 | OOPハンドラークラス |
| tools（ツール） | 87 | MCPツール統合 |
| core（コア） | 8 | BaseHandler, PreviewCache |
| **合計** | **257** | ~85% カバレッジ |

## テスト実行

```bash
# 全テスト実行
uv run pytest tests/

# 詳細出力
uv run pytest tests/ -v

# カバレッジ付き
uv run pytest tests/ --cov=. --cov-report=term-missing

# 特定ファイルのみ
uv run pytest tests/test_books_handler.py -v

# 特定クラスのみ
uv run pytest tests/test_books_tools.py::TestBooksFind -v

# 特定テストのみ
uv run pytest tests/test_helpers.py::TestNormalize::test_basic_normalization -v
```

## テスト構成

```
tests/
├── conftest.py              # 共通フィクスチャ
├── test_helpers.py          # lib/のテスト (66件)
├── test_base_handler.py     # core/base_handler (15件)
├── test_preview_cache.py    # lib/preview_cache (8件)
├── test_books_handler.py    # handlers/books (30件)
├── test_books_tools.py      # books MCPツール (25件)
├── test_students_handler.py # handlers/students (31件)
├── test_students_tools.py   # students MCPツール (19件)
├── test_planner_handler.py  # handlers/planner (21件)
└── test_planner_tools.py    # planner MCPツール (17件)
```

## テスト階層

### 1. ハンドラーテスト（test_*_handler.py）

OOPハンドラークラスのロジックをテスト。sheets_clientをモックして独立テスト。

```python
# tests/test_books_handler.py
class TestBooksHandlerFind:
    def test_find_returns_candidates(self):
        from handlers.books import BooksHandler

        mock_sheets = MagicMock()
        mock_sheets.get_all_values.return_value = [
            ["書籍ID", "教科", "タイトル"],
            ["gMA001", "数学", "青チャート"],
        ]

        handler = BooksHandler(mock_sheets)
        result = handler.find("青チャート")

        assert result["ok"] is True
        assert len(result["data"]["candidates"]) >= 1
```

### 2. ツールテスト（test_*_tools.py）

MCPツール全体の統合テスト。ハンドラーをモックしてツール呼び出しをテスト。

```python
# tests/test_books_tools.py
class TestBooksFind:
    @pytest.mark.asyncio
    async def test_find_book_success(self):
        with patch("server.BooksHandler") as MockHandler:
            instance = MockHandler.return_value
            instance.find.return_value = {
                "ok": True,
                "data": {"candidates": [...]}
            }

            result = await books_find(query="青チャート")
            assert result["ok"] is True
```

### 3. ヘルパーテスト（test_helpers.py）

lib/の純粋関数をテスト。モック不要。

```python
# tests/test_helpers.py
class TestNormalize:
    def test_basic_normalization(self):
        from lib.common import normalize
        assert normalize("  Hello World  ") == "hello world"

    def test_fullwidth_conversion(self):
        from lib.common import normalize
        assert normalize("ＡＢＣ") == "abc"
```

### 4. コアテスト

core/の基盤機能をテスト。

```python
# tests/test_preview_cache.py
class TestPreviewCache:
    def test_store_and_get(self):
        from lib.preview_cache import PreviewCache

        cache = PreviewCache()
        token = cache.store("test", {"key": "value"})
        data = cache.get("test", token)

        assert data == {"key": "value"}
```

## テストカテゴリ詳細

### ヘルパーテスト（66件）

| カテゴリ | 関数 |
|---------|------|
| Common | normalize, ok, ng, to_number_or_none |
| Sheet Utils | norm_header, pick_col, tokenize, parse_monthly_goal, extract_spreadsheet_id |
| ID Rules | decide_prefix, next_id_for_prefix, extract_ids_from_values |

### ハンドラーテスト（96件）

| ファイル | テスト内容 |
|---------|-----------|
| test_books_handler.py | BooksHandler CRUD、IDF検索、スコアリング |
| test_students_handler.py | StudentsHandler CRUD、フィルタ、プランナーID解決 |
| test_planner_handler.py | PlannerHandler 週間/月間計画、メトリクス |
| test_base_handler.py | BaseHandler 共通機能 |

### ツールテスト（87件）

| ファイル | ツール |
|---------|--------|
| test_books_tools.py | books_find, books_get, books_filter, books_list, books_create, books_update, books_delete |
| test_students_tools.py | students_list, students_find, students_get, students_filter, students_create, students_update, students_delete |
| test_planner_tools.py | planner_ids_list, planner_dates_get/set, planner_plan_get/create, planner_monthly_filter, planner_guidance |

## フィクスチャ

### conftest.py

```python
@pytest.fixture
def mock_sheets_client():
    """Mock Google Sheets client"""
    mock = MagicMock()
    mock.get_all_values.return_value = []
    return mock

@pytest.fixture
def sample_books_data():
    """サンプル参考書データ"""
    return [
        ["書籍ID", "教科", "タイトル", "レベル"],
        ["gMA001", "数学", "青チャート", "3"],
        ["gEN001", "英語", "長文読解", "2"],
    ]
```

## モックパターン

### ハンドラーモック

```python
# ハンドラーをモック
with patch("server.BooksHandler") as MockHandler:
    instance = MockHandler.return_value
    instance.find.return_value = {"ok": True, "data": {...}}
```

### sheets_clientモック

```python
# sheets_clientをモック
mock_sheets = MagicMock()
mock_sheets.get_all_values.return_value = [...]
mock_sheets.open_by_id.return_value = MagicMock()

handler = BooksHandler(mock_sheets)
```

## CI/CD

GitHub Actionsで自動テスト実行:

- **トリガー**: Push / PR to main
- **ワークフロー**: `.github/workflows/test.yml`
- **ステップ**:
  1. Python 3.12セットアップ
  2. uv で依存関係インストール
  3. pytest 実行（カバレッジ付き）
  4. 結果レポート

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: uv run pytest tests/ --cov=. --cov-report=term-missing
```

## トラブルシューティング

### 1. ImportError

```bash
# リポジトリルートで実行しているか確認
uv sync  # 依存関係再インストール
```

### 2. モックが期待通り動かない

```python
# パッチ対象のパスを確認
# BAD: patch("handlers.books.BooksHandler")
# GOOD: patch("server.BooksHandler")  # インポート先でパッチ
```

### 3. 非同期テストエラー

```python
# pytest-asyncio デコレータを確認
@pytest.mark.asyncio
async def test_async_function():
    ...
```

### 4. 特定テストのデバッグ

```bash
# 出力を表示
uv run pytest tests/test_helpers.py -v -s

# 最初の失敗で停止
uv run pytest tests/ -x

# 失敗したテストのみ再実行
uv run pytest tests/ --lf
```

## TDDワークフロー

### 新機能追加

1. **Red**: 失敗するテストを書く
2. **Green**: 最小限の実装でテスト通過
3. **Refactor**: コード品質向上
4. **Commit**: テスト通過を確認してコミット

### リファクタリング

1. 変更前に全テスト通過を確認
2. 小さな変更単位で進める
3. 各変更後にテスト実行
4. 失敗したら即座にロールバック

```bash
# リファクタリング開始前（必須）
uv run pytest tests/ -v

# 各変更後
uv run pytest tests/ -v --tb=short
```
