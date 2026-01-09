# Claude Code 開発ガイドライン

このドキュメントはClaude Codeを使った開発時のルールとワークフローを定義します。

## 基本方針

### 1. Pythonic & オブジェクト指向

すべてのPythonコードは以下の原則に従う:

- **PEP 8/20準拠**: Pythonの標準スタイルに従う
- **型ヒント必須**: 全public関数・メソッドに型ヒント（`T | None` 推奨）
- **dataclass/NamedTuple活用**: データ構造はクラスで表現
- **依存注入**: コンストラクタで依存を受け取る
- **コンポジション優先**: 継承より合成を選ぶ

```python
# Good: Pythonic & OOP
@dataclass
class BookMeta:
    id: str
    subject: str
    title: str

class BooksHandler:
    def __init__(self, sheets_client: SheetsClient) -> None:
        self._sheets = sheets_client

    def find(self, query: str) -> list[BookMeta]:
        return [BookMeta(**row) for row in self._search(query)]

# Bad: 手続き的
def books_find(query, sheets_client):
    result = []
    for row in search(query, sheets_client):
        result.append({"id": row[0], "subject": row[1], "title": row[2]})
    return result
```

### 2. TDD必須（リファクタリング時）

**すべてのリファクタリング作業はテスト駆動で行う**

## 開発ワークフロー

### 1. 計画フェーズ

1. plan modeで実装計画を作成
2. 不明点は質問して確認
3. PROGRESS.mdに計画を記録

### 2. 実装フェーズ

1. テスト先行で実装（TDD）
2. 小さな単位でコミット
3. 各コミット後にテスト実行

### 3. 検証フェーズ

1. 全テスト通過確認
2. ドキュメント更新
3. PROGRESS.mdに完了記録

## TDDルール

### 新機能追加

1. テストを先に書く（Red: 失敗する状態）
2. 最小限の実装でテスト通過（Green）
3. コード品質向上（Refactor）
4. コミット

### バグ修正

1. バグを再現するテストを先に書く
2. 修正してテスト通過
3. コミット

### リファクタリング（最重要）

1. **変更前に全テスト実行して通過確認**
2. 必要なら対象コードのテストを追加
3. 小さな変更単位で進める
4. **各変更後にテスト実行**
5. テスト失敗したら即座にロールバック
6. 全テスト通過を確認してコミット

```bash
# リファクタリング開始前（必須）
uv run pytest tests/ -v

# 各変更後（必須）
uv run pytest tests/ -v --tb=short

# 全完了後
uv run pytest tests/ --cov=. --cov-report=term-missing
```

## ドキュメント更新ルール

| 変更内容 | 更新対象 |
|---------|---------|
| 新ツール追加 | README.md のツール一覧 |
| API変更 | AGENTS.md |
| 大きな変更 | PROGRESS.md に記録 |
| 開発ルール変更 | このファイル（CLAUDE.md） |

## コード品質チェックリスト

実装完了時に確認:

- [ ] テスト通過（`uv run pytest tests/`）
- [ ] 型ヒント付与（全public関数）
- [ ] 重複コードなし（DRY原則）
- [ ] 入力検証あり
- [ ] エラーハンドリングあり
- [ ] ドキュメント更新

## コードスタイル

### 命名規約

| 種類 | スタイル | 例 |
|------|---------|-----|
| 関数/メソッド | snake_case | `books_find`, `_parse_chapter` |
| クラス | PascalCase | `BooksHandler`, `PreviewCache` |
| 定数 | UPPER_SNAKE | `BOOKS_MASTER_ID` |
| プライベート | `_` prefix | `_sheets`, `_cache` |

### Pythonicイディオム

- リスト内包表記を積極活用
- `enumerate`, `zip`, `any`, `all` を使う
- `with` 文でリソース管理
- ジェネレータで遅延評価
- f-stringで文字列フォーマット

### 関数サイズ

- 30行以下を目安
- 50行超は必ず分割
- ネスト3段以上は早期リターンで解消

## プロジェクト構造

```
cram-books-mcp/
├── server.py              # MCPサーバーエントリポイント
├── config.py              # 設定（シートID、列定義）
├── sheets_client.py       # Google Sheets APIクライアント
├── conftest.py            # pytest フィクスチャ
├── core/                  # コア機能
│   ├── base_handler.py    # BaseHandler（共通CRUD）
│   └── two_phase_mixin.py # TwoPhaseOperationMixin（プレビュー→確認）
├── handlers/              # ドメインハンドラー（OOP）
│   ├── __init__.py        # BooksHandler等のexport
│   ├── books/
│   │   ├── handler.py     # BooksHandler（CRUD + TwoPhase）
│   │   └── search.py      # SearchMixin（IDF検索）
│   ├── students/
│   │   └── handler.py     # StudentsHandler（CRUD + TwoPhase）
│   └── planner/
│       └── handler.py     # PlannerHandler（週間・月間）
├── lib/                   # ユーティリティ
│   ├── common.py          # ok/ng, normalize等
│   ├── types.py           # 型定義（Response, SheetValues等）
│   ├── errors.py          # エラーヘルパー（ErrorCode列挙）
│   ├── sheet_utils.py     # シート操作ヘルパー
│   ├── id_rules.py        # ID生成ルール
│   ├── input_parser.py    # 入力検証
│   └── preview_cache.py   # PreviewCache class
├── docs/                  # ドキュメント
│   ├── README.md          # ドキュメント一覧
│   ├── ARCHITECTURE.md    # アーキテクチャ概要
│   ├── TESTING.md         # テストガイド
│   ├── AGENTS.md          # LLMエージェント向けAPI仕様
│   ├── CLAUDE.md          # Claude Code開発ガイドライン
│   ├── CONTRIBUTING.md    # 貢献ガイド
│   ├── CHANGELOG.md       # 変更履歴
│   └── specs/             # 仕様書
└── tests/                 # テスト（291件）
    ├── conftest.py        # フィクスチャ
    ├── test_helpers.py    # lib/のテスト
    ├── test_two_phase_mixin.py  # Mixinテスト
    ├── test_*_handler.py  # ハンドラー単体テスト
    └── test_*_tools.py    # ツール統合テスト
```

## 新機能追加手順

1. `handlers/<domain>/` にハンドラークラスを追加（BaseHandler継承）
2. `handlers/__init__.py` でexport
3. `server.py` にMCPツールラッパーを追加
4. `tests/test_<domain>_handler.py` にハンドラーテストを追加
5. `tests/test_<domain>_tools.py` にツールテストを追加
6. ドキュメント更新（README.md, AGENTS.md）
7. PROGRESS.mdに記録

## よく使うコマンド

```bash
# テスト実行
uv run pytest tests/ -v

# カバレッジ付きテスト
uv run pytest tests/ --cov=. --cov-report=term-missing

# ローカルサーバー起動
uv run python server.py

# ヘルスチェック
curl http://localhost:8080/healthz
```
