# 進捗ログ

## 2025-08-31

- feat: POST 検証スクリプトを修正（`apps/gas/deploy_and_test.sh`）
  - 302/303 追従時に POST を維持しないよう `--post302/--post303` と `-X POST` を外し、`-L` + `-d` + `Content-Type: application/json` で安定化。
- docs: POST トラブルシュートに「curl 正しい使い方」を追記（`docs/POST_and_ExecutionAPI_Troubleshooting.md`）。
- docs: `AGENTS.md` の POST サンプルを更新（`-X` 不要化）。
- docs: `AGENTS.md` に「出力のチェック（GET/POSTの実例）」を追記（複数IDのPOST例含む）。
- feat: books.filter を「書籍単位のグルーピング応答」に変更（行→書籍）。
  - 仕様: where=完全一致, contains=部分一致を“書籍の全行”に対して評価し、合致した書籍のみ返却。
  - 応答形: { books: BookDetails[], count, limit }（books.getの複数形式に準拠）。
  - ドキュメント: AGENTS.md にレスポンス例と備考を追加。
- feat: books.create / books.update を実装（POST）。
  - create: id_prefix で採番、親行＋章行を末尾に追加、応答に新IDを返却。
  - update: 指定IDブロックを検出し、メタ更新＋章の完全置換に対応（必要なら行の挿入/削除）。
  - バグ修正: 空文字が数値0扱いになる不具合を修正（toNumberOrNull）。
  - E2E: 作成→取得→更新→再取得まで確認済み（固定デプロイID）。
- feat: 削除/更新を二段階化（プレビュー→confirm）。confirm_token を 5 分間 Cache に保存。
- chore: GASコード分割の下地追加（config.ts, lib/common.ts, lib/id_rules.ts, handlers/books.ts）。
- chore: MCP デプロイスクリプト追加（scripts/deploy_mcp.sh, scripts/gcloud_env.example）。
- docs: AGENTS.md に Cloud Run デプロイ手順と環境変数、POST運用の極小サマリ、コード配置マップを追記。
- docs: POST トラブルシュート文書を AGENTS へ要約移植したため削除。
- refactor: books.find/get/filter/create/update/delete を handlers/books.ts に移設。index.ts は薄いルーター化。
- fix(mcp): Dockerfile に uvicorn/fastmcp を追加し、`server.py` で `uvicorn.run` 起動。Cloud Run での PORT 待受エラーを解消。
 - docs(mcp): 各ツールに日本語ドキュメント（引数/例/返り値）を追加。文字列式 where/contains のサポートを実装（英語→シート見出しへ自動マッピング）。
 - chore(mcp): 実行API版ツール（books_find_exec/books_get_exec）を非公開化（@mcp.tool を外し、実験用として残置）。
 - feat(mcp): `books_list`（親行だけの id/subject/title 一覧）を追加。
 - feat(mcp): `tools_help`（公開ツールの簡易ヘルプ）を追加。

次の候補タスク:
- ローカル実行で `apps/gas/deploy_and_test.sh -d '{"op":"books.find","query":"青チャート"}'` を用い、`doPost` 到達と JSON 応答を確認。
- 確認後、`books.create/update/filter` の POST 実装とテストケースを追加。

## 2025-09-01

- feat(mcp): planner_plan_propose に早期警告を追加（`data.warnings`）。`week_index` 範囲外と `plan_text` 52文字超を検知。
- feat(mcp): planner_plan_targets を強化。Books TOCから `numbering_symbol`/`max_end` を把握し、`suggested_plan_text` を付与（prev_range_hint と guideline_amount から推定）。`end_of_book` を同梱。
- docs: tools_help/README/AGENTS を更新（targetsのサジェスト/ proposeのwarnings を明記）。
- chore: 作業ブランチ `feat/llm-ux-improvements` を作成。
- feat(gas): planner.plan.set に `items[]` を追加し、週列ごとに連続ブロックへバッチ書込み（単体互換維持）。
- feat(mcp): planner_plan_confirm が一括トークンを単一GASリクエスト（items[]）へ集約し、GAS側のバッチ書込みを活用。
- feat(mcp): 新ツール `planner_plan_create` を追加（提案/確定を統合）。週混在の一括作成を1コールで反映。応答に `guidance_digest` と `warnings` を同梱。
- docs: README/AGENTS/tools_help を `planner_plan_create` 中心に更新。旧 propose/confirm は deprecated と明記。
 - breaking(mcp docs): propose/confirm の実装は互換向けstubのみにし、ドキュメント上は完全廃止。今後は create に一本化。
2025-09-05
- Hardening MCP service
  - Added tuned HTTP client with retries (3x) and explicit connect/read/write timeouts.
  - Added `/healthz` endpoint and 406 hint at `/` (SSE endpoint remains `/mcp`).
  - Updated Cloud Run deploy defaults: `--timeout=3600`, `--concurrency=5`, `--min-instances=1`.
  - No functional API changes. SSE endpoint unchanged.

## 2026-01-08

### feat: Comprehensive TDD Implementation

#### GAS Test Infrastructure (Vitest)
- Added Vitest test framework with v8 coverage
- Created `vitest.config.ts` with 90% coverage thresholds
- Created `src/__mocks__/gas-stubs.ts` for SpreadsheetApp/CacheService/ContentService mocks
- 88 unit tests for lib/ pure functions:
  - `common.test.ts`: normalize, toNumberOrNull, ok, ng
  - `id_rules.test.ts`: decidePrefix, nextIdForPrefix
  - `sheet_utils.test.ts`: headerKey, pickCol, parseMonthlyGoal
- lib/ coverage: 97.95%

#### GAS Refactoring (DRY + Testability)
- New `src/interfaces/spreadsheet.ts`: ISheet, IRange, ISpreadsheet, ISpreadsheetService, ICacheService interfaces
- New `src/services/factory.ts`: Service factory for dependency injection
- New `src/types/domain.ts`: Strong type definitions (BookMeta, Student, PlannerItem, etc.)
- New `src/lib/student_resolver.ts`: Extracted resolveSpreadsheetIdByStudent (DRY fix)
- New `src/lib/columns.ts`: Centralized column name definitions
- Updated `handlers/planner.ts` and `handlers/planner_monthly.ts` to use shared modules

#### MCP Test Infrastructure (pytest)
- Added pytest, pytest-asyncio, pytest-cov, pytest-httpx dependencies
- Created `conftest.py` with fixtures and GAS response templates
- 66 unit tests for helper functions:
  - `test_helpers.py`: _strip_quotes, _coerce_str, _norm_header, _pick_col, _verify_hmac, etc.
- All pure function tests pass

#### CI/CD (GitHub Actions)
- New `.github/workflows/test.yml`: Automated testing on push/PR
  - GAS tests with Vitest and coverage upload
  - MCP tests with pytest and coverage upload
  - Build validation
- New `.github/workflows/deploy.yml`: Manual/triggered deployment
  - GAS deployment via clasp
  - MCP deployment to Cloud Run
  - Triggered by `[deploy-gas]` or `[deploy-mcp]` in commit message

#### Documentation
- Updated README.md with testing and CI/CD sections
- Updated section numbering (2.5 Testing, 2.6 CI/CD, 2.7 Claude/ChatGPT, 2.8 Troubleshooting)

### feat: TDD Phase 2 - Handler & Tool Tests

#### GAS Handler Tests (111 tests)
- `handlers/__tests__/books.test.ts`: 35 tests (find, get, filter, create, update, delete)
- `handlers/__tests__/students.test.ts`: 34 tests (list, find, get, filter, create, update, delete)
- `handlers/__tests__/planner.test.ts`: 24 tests (ids_list, dates_get/set, metrics_get, plan_get/set)
- `handlers/__tests__/planner_monthly.test.ts`: 18 tests (filter with year normalization)
- Coverage: 88.45% handlers, 85.7% overall

#### MCP Tool Tests (71 tests)
- `tests/test_books_tools.py`: 26 tests (find, get, filter, create, update, delete, list)
- `tests/test_students_tools.py`: 25 tests (list, find, get, filter, create, update, delete)
- `tests/test_planner_tools.py`: 20 tests (ids_list, dates_*, metrics, plan_*, guidance)
- Added httpx mock fixtures to `conftest.py`
- Coverage: ~72% server.py

#### Coverage Configuration
- Updated `vitest.config.ts` to include handlers/
- Thresholds: 80% lines, 60% branches, 90% functions

#### Documentation
- Created `docs/TESTING.md` with comprehensive testing guide
- Updated README.md test section with coverage table and link to TESTING.md

#### Total Test Count: 338
- GAS: 201 tests (90 lib + 111 handlers)
- MCP: 137 tests (66 helpers + 71 tools)

## 2026-01-09

### refactor: GAS WebApp廃止 → Google Sheets API直接アクセス + Railway移行

#### 背景と課題
- GAS WebApp: 頻繁に「Access Denied」になり、手動で再設定が必要
- Cloud Run: 課金無効化でサービス停止、手動介入が必要
- 本番運用に適さない不安定なアーキテクチャ

#### 新アーキテクチャ
```
[Claude/LLM]
   │  (MCP over HTTP/SSE)
   ▼
[Railway: MCP Server]
   │  (Google Sheets API, Service Account認証)
   ▼
[Google Sheets: Books / Students / Planner]
```

#### 実装内容

**Phase 1-2: Service Account設定（ユーザー作業完了）**
- GCPでService Account作成（cram-book-mcp@cram-books-mcp-0830）
- Google Sheets/Drive API有効化
- フォルダ共有でSpreadsheetへのアクセス権限付与

**Phase 3: MCP Server書き換え**
- 新規ファイル作成:
  - `env_loader.py`: .env/環境変数からのクレデンシャル読み込み
  - `sheets_client.py`: gspreadラッパー（Service Account認証）
  - `config.py`: 定数定義（シートID、列マッピング等）
  - `lib/common.py`: normalize, ok, ng等の共通関数
  - `lib/sheet_utils.py`: norm_header, pick_col, tokenize等
  - `lib/id_rules.py`: decide_prefix, next_id_for_prefix
  - `handlers/books.py`: books_* ツール群（IDF検索含む）
  - `handlers/students.py`: students_* ツール群
  - `handlers/planner.py`: planner_* 週間管理ツール群
  - `handlers/planner_monthly.py`: planner_monthly_* 月間管理ツール群
- `server.py`完全書き換え:
  - HTTP呼び出し（_get/_post）を廃止
  - handlers直接呼び出しパターンに変更
  - 全23ツールを新アーキテクチャに対応
- `Dockerfile`更新: google-auth, gspread, python-dotenv追加

**Phase 3-4: テスト更新（141テスト）**
- `conftest.py`: 新fixtures（mock_sheets_client, mock_handler_responses等）
- `test_books_tools.py`: ハンドラーモックに対応
- `test_students_tools.py`: 新アーキテクチャ対応
- `test_planner_tools.py`: 新ツール名（planner_dates_set等）対応
- `test_helpers.py`: libモジュール関数のテスト

**Phase 4: Railway設定**
- `railway.json`: Railway設定ファイル作成
- `Procfile`: プロセス定義
- `scripts/deploy_mcp.sh`: Railway CLIデプロイスクリプト

**Phase 5: ドキュメント更新（完了）**
- README.md: 新アーキテクチャに更新
- AGENTS.md: 全面改訂（993行 → 346行に簡素化）

#### 残タスク（ユーザー作業）
- Phase 5-3: Railwayデプロイ
  1. Railway CLIインストール: `npm install -g @railway/cli`
  2. ログイン: `railway login`
  3. プロジェクト作成＆リンク: `cd apps/mcp && railway link`
  4. 環境変数設定: `railway variables set GOOGLE_CREDENTIALS_JSON="$(cat service-account.json)"`
  5. デプロイ: `railway up` または `scripts/deploy_mcp.sh`
  6. MCP接続テスト
- Phase 6: 旧インフラ廃止
  - Claude設定更新（MCP URLをRailwayに変更）
  - GAS WebAppアーカイブ（任意）
  - Cloud Run削除（任意）

### refactor: Phase 1 コード構造改善

#### 重複コードの統合

**A. スプレッドシートID抽出の統一**
- `lib/sheet_utils.py`に`extract_spreadsheet_id()`関数を追加
- `handlers/students.py`と`handlers/planner.py`の重複関数を削除
- 9件の新規テスト追加（`test_helpers.py::TestExtractSpreadsheetId`）

**B. Planner解決パターンの抽出**
- `handlers/planner.py`に`resolve_and_open_planner()`ヘルパー追加
- `PlannerSheetResult` NamedTupleでPythonicな戻り値を実現
- 6関数（ids_list, dates_get/set, metrics_get, plan_get/set）をリファクタリング
- 各関数で約8行 → 4行に削減

#### 開発ガイドライン整備

- `CONTRIBUTING.md`: ブランチ戦略、コミット規約、コード品質チェックリスト
- `CLAUDE.md`: Claude Code開発ワークフロー、TDDルール、Pythonicスタイルガイド

#### テスト

- 全150テスト通過（141 + 9新規）
- TDDに従い、テスト先行でリファクタリング実施

### refactor: Phase 2 共通モジュール化

#### PreviewCacheクラスの作成
- `lib/preview_cache.py`: 共通キャッシュクラス
  - トークン生成・格納・取得・削除を一元化
  - prefix分離でbooks/students独立管理
  - 10件のテスト追加（`test_preview_cache.py`）
- `handlers/books.py`: PreviewCache使用に移行
- `handlers/students.py`: PreviewCache使用に移行
- 未使用のuuidインポートを削除

#### 入力検証の統一
- `lib/input_parser.py`: 入力パース関数を集約
  - `strip_quotes()`: 引用符除去
  - `coerce_str()`: 文字列抽出
  - `as_list()`: リスト変換
  - `coerce_int()`, `coerce_bool()`: 追加ヘルパー
- `server.py`から関数を削除、lib/input_parserからインポート
- テストのインポートも更新

#### テスト
- 全160テスト通過

### refactor: Phase 3 OOP Handler Classes (TDD)

#### BaseHandler抽象クラス
- `core/base_handler.py`: 全ハンドラー共通の抽象基底クラス
  - シート読み込みとエラーハンドリング
  - COLUMN_SPECによる列インデックスマッピング
  - セルアクセスと行検索ユーティリティ
  - filter_by_conditions (where/contains)
  - レスポンスヘルパー (_ok/_error)
  - PreviewCacheの共有管理
- `core/__init__.py`: BaseHandlerのエクスポート
- 15件のテスト追加（`test_base_handler.py`）

#### BooksHandler
- `handlers/books_handler.py`: BaseHandlerパターンを活用
  - IDF重み付き検索（教科ボーナス付き）
  - 子行からの章パース
  - 二段階CRUD操作（preview/confirm）
- 30件のテスト追加（`test_books_handler.py`）

#### StudentsHandler
- `handlers/students_handler.py`: 生徒操作用ハンドラー
  - シンプルなファジー検索
  - プランナーシートIDのリンクからの抽出
  - 二段階CRUD操作
- 31件のテスト追加（`test_students_handler.py`）

#### PlannerHandler
- `handlers/planner_handler.py`: プランナー操作用ハンドラー
  - 週間プランナー操作（ids, dates, metrics, plan）
  - 月間プランナーフィルタリング
  - 書籍コードパース（month_code + book_id）
- 21件のテスト追加（`test_planner_handler.py`）

#### テスト
- 新規97テスト追加
- 全257テスト通過
- TDD（テスト駆動開発）で実装

#### 次のステップ
- server.pyをハンドラー登録パターンに更新（オプション）
- 既存関数を新クラスにルーティング

