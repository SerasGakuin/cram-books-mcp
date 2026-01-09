# アーキテクチャ概要

このドキュメントはMCPサーバーのアーキテクチャを説明します。

## レイヤー構成

```
┌─────────────────────────────────────────────────┐
│                  Tool Layer                      │
│               (server.py)                        │
│  - MCPツール定義（@mcp.tool()）                  │
│  - 入力パース・検証                              │
│  - ハンドラー呼び出し                            │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                Handler Layer                     │
│            (handlers/<domain>/)                  │
│  - BooksHandler / StudentsHandler / PlannerHandler│
│  - ビジネスロジック                              │
│  - CRUD操作                                      │
│  - エラーハンドリング                            │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                  Core Layer                      │
│                   (core/)                        │
│  - BaseHandler: 共通CRUD機能                     │
│  - PreviewCache: プレビュー/確認キャッシュ       │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               Library Layer                      │
│                   (lib/)                         │
│  - 純粋関数（normalize, tokenize等）             │
│  - sheet_utils: シート操作ヘルパー               │
│  - id_rules: ID生成ルール                        │
│  - input_parser: 入力検証                        │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              External Services                   │
│  - Google Sheets API (gspread + Service Account) │
└─────────────────────────────────────────────────┘
```

## ディレクトリ構成

```
apps/mcp/
├── server.py              # MCPサーバーエントリポイント
├── config.py              # 設定（シートID、列定義）
├── sheets_client.py       # Google Sheets APIクライアント
│
├── core/                  # コア機能
│   ├── base_handler.py    # BaseHandler（共通CRUD）
│   └── preview_cache.py   # プレビューキャッシュ
│
├── handlers/              # ドメインハンドラー（OOP）
│   ├── __init__.py        # Handler export
│   ├── books/
│   │   ├── __init__.py    # BooksHandler export
│   │   ├── handler.py     # BooksHandler class
│   │   └── search.py      # SearchMixin（IDF検索）
│   ├── students/
│   │   ├── __init__.py
│   │   └── handler.py     # StudentsHandler class
│   └── planner/
│       ├── __init__.py
│       └── handler.py     # PlannerHandler class
│
├── lib/                   # ユーティリティ
│   ├── common.py          # ok/ng, normalize等
│   ├── sheet_utils.py     # シート操作ヘルパー
│   ├── id_rules.py        # ID生成ルール
│   ├── input_parser.py    # 入力検証
│   └── preview_cache.py   # PreviewCache class
│
└── tests/                 # テスト（257件）
    ├── conftest.py        # フィクスチャ
    ├── test_helpers.py    # lib/のテスト
    ├── test_base_handler.py
    ├── test_preview_cache.py
    ├── test_books_handler.py
    ├── test_books_tools.py
    ├── test_students_handler.py
    ├── test_students_tools.py
    ├── test_planner_handler.py
    └── test_planner_tools.py
```

## コンポーネント詳細

### 1. Tool Layer (server.py)

MCPツールを定義し、ハンドラーを呼び出す薄いレイヤー。

```python
@mcp.tool()
async def books_find(query: str) -> dict:
    """参考書を検索"""
    return books_handler.find(query)
```

**責務**:
- MCPツール定義（デコレータ）
- 入力の簡易検証
- ハンドラーへの委譲

### 2. Handler Layer (handlers/)

ビジネスロジックを含むOOPハンドラー。

```python
class BooksHandler(BaseHandler, SearchMixin):
    """参考書ハンドラー"""

    def find(self, query: str) -> dict[str, Any]:
        """曖昧検索"""
        ...

    def get(self, book_id: str) -> dict[str, Any]:
        """詳細取得"""
        ...
```

**責務**:
- ドメインロジック
- シート操作
- エラーハンドリング
- レスポンス構築

### 3. Core Layer (core/)

ハンドラー間で共有される基盤機能。

#### BaseHandler

```python
class BaseHandler:
    """ハンドラー基底クラス"""

    def __init__(self, sheets_client: SheetsClient, file_id: str, sheet_name: str):
        self.sheets = sheets_client
        self.file_id = file_id
        self.sheet_name = sheet_name

    def _get_all_values(self) -> list[list[str]] | None:
        """シート全行取得"""
        ...

    def _build_column_indices(self, headers: list[str]) -> dict[str, int]:
        """列インデックスマップ作成"""
        ...
```

#### PreviewCache

```python
class PreviewCache:
    """プレビュー/確認操作のキャッシュ"""

    def store(self, prefix: str, data: Any) -> str:
        """データを保存しトークンを返す"""
        ...

    def pop(self, prefix: str, token: str) -> Any | None:
        """トークンでデータを取得し削除"""
        ...
```

### 4. Library Layer (lib/)

純粋関数とユーティリティ。

| モジュール | 機能 |
|-----------|------|
| common.py | ok/ng レスポンス, normalize, to_number_or_none |
| sheet_utils.py | norm_header, pick_col, tokenize, extract_spreadsheet_id |
| id_rules.py | decide_prefix, next_id_for_prefix |
| input_parser.py | InputParser（入力検証） |

## データフロー

### 1. 検索フロー（books_find）

```
[Client] → books_find(query="青チャート")
    │
    ▼
[server.py] → BooksHandler.find(query)
    │
    ▼
[BooksHandler] → SearchMixin._score_candidates(query)
    │           → _build_doc_freq() → sheets.get_all_values()
    │           → IDF計算 → スコアリング
    │
    ▼
[BooksHandler] → ok(data={candidates: [...]})
    │
    ▼
[Client] ← {ok: true, data: {candidates: [...]}}
```

### 2. 更新フロー（books_update）

```
[Client] → books_update(book_id, changes, confirm_token=None)
    │
    ▼
[server.py] → BooksHandler.update(book_id, changes, None)
    │
    ▼ (プレビューモード)
[BooksHandler] → 変更差分計算
    │           → PreviewCache.store("books_update", diff)
    │           → ok(data={preview: diff, confirm_token: "xxx"})
    │
    ▼
[Client] ← {ok: true, data: {preview: {...}, confirm_token: "xxx"}}
    │
    ▼
[Client] → books_update(book_id, changes, confirm_token="xxx")
    │
    ▼ (確定モード)
[BooksHandler] → PreviewCache.pop("books_update", "xxx")
    │           → sheets.update_cell(...)
    │           → ok(data={updated: true})
    │
    ▼
[Client] ← {ok: true, data: {updated: true}}
```

## 設計原則

### 1. OOP & 依存注入

```python
# コンストラクタで依存を注入
class BooksHandler(BaseHandler, SearchMixin):
    def __init__(self, sheets_client: SheetsClient):
        super().__init__(sheets_client, BOOKS_MASTER_ID, "参考書マスター")
```

### 2. コンポジション優先

```python
# Mixinで機能を合成
class BooksHandler(BaseHandler, SearchMixin):
    # SearchMixin から検索機能を継承
    # BaseHandler から CRUD 機能を継承
    pass
```

### 3. 単一責任

- **server.py**: ツール定義のみ
- **Handler**: ドメインロジックのみ
- **lib/**: 純粋関数のみ

### 4. DRY原則

- 共通コードは core/ または lib/ に抽出
- PreviewCache は全ハンドラーで共有
- extract_spreadsheet_id は lib/sheet_utils.py に統一

## テスト戦略

### テスト階層

| レイヤー | テストファイル | テスト対象 |
|---------|---------------|-----------|
| Handler | test_*_handler.py | ハンドラーロジック（モック） |
| Tool | test_*_tools.py | MCPツール統合 |
| Lib | test_helpers.py | 純粋関数 |
| Core | test_base_handler.py, test_preview_cache.py | 基盤機能 |

### テスト数（257件）

| カテゴリ | 件数 |
|---------|------|
| lib/テスト | 66 |
| ハンドラーテスト | 96 |
| ツールテスト | 87 |
| コアテスト | 8 |

## 新機能追加手順

1. **ハンドラー作成**
   ```
   handlers/<domain>/
   ├── __init__.py     # export
   └── handler.py      # Handler class (BaseHandler継承)
   ```

2. **handlers/__init__.py でexport**
   ```python
   from handlers.<domain> import <Domain>Handler
   ```

3. **server.py にツール追加**
   ```python
   <domain>_handler = <Domain>Handler(sheets_client)

   @mcp.tool()
   async def <domain>_find(query: str) -> dict:
       return <domain>_handler.find(query)
   ```

4. **テスト追加**
   - tests/test_<domain>_handler.py（ハンドラー単体）
   - tests/test_<domain>_tools.py（ツール統合）

5. **ドキュメント更新**
   - README.md: ツール一覧
   - AGENTS.md: 詳細API仕様
