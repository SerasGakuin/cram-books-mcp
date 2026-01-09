# CRAM Books MCP - 開発ガイド（簡潔版）

このプロジェクトは、学習塾で運用しているGoogleスプレッドシートを、LLM（Claude）から「提案→承認→実行」の安全な流れで操作する仕組みです。

## 開発原則（最重要）

1) DRYの徹底
- 重複コード禁止。1つだけをソースオブトゥルースにする
- 共通機能は適切に抽象化。冗長/未使用コードは即削除

2) コード品質・運用
- 必要最低限のファイルのみ。デバッグ用は使用後すぐ削除
- 簡潔で読みやすい実装。進捗・作業ログは `PROGRESS.md` に記録
- タスクは小さく分割→検証→クリーンアップ→意味ある単位でコミット

3) 禁止事項
- 冗長なコード/重複機能/不要なファイルの放置
- タスク完了の記録漏れ、ガイドの逸脱

## 目的と範囲

- 目的: 既存シートは変更せず、LLMから安全に操作
- コンセプト:
  1. LLMが呼びやすい小さなAPI群
  2. JSONで入出力を統一
  3. 承認付きの実行フロー
- 現在スコープ: 参考書データの検索・取得・登録・絞り込み、生徒管理、週間/月間計画管理

## 全体アーキテクチャ

```
[Claude (チャットUI)]
      │  (MCP over HTTP/SSE)
      ▼
[Railway 上の MCP サーバー]
      │  (Google Sheets API, Service Account認証)
      ▼
[Google スプレッドシート (参考書マスター / 生徒マスター / プランナー)]
```

> **Note**: 2026-01-09にGAS WebApp経由からGoogle Sheets API直接アクセスに移行しました。これによりGAS WebAppの「Access Denied」問題やCloud Runの課金問題を解消し、安定した運用が可能になりました。

## プロジェクト構造

```
cram-books-mcp/
├── apps/
│   └── mcp/                    # MCP Server (Python FastMCP + Google Sheets API)
│       ├── server.py           # MCPツール定義
│       ├── sheets_client.py    # Google Sheets APIラッパー
│       ├── config.py           # 定数定義（シートID、列マッピング等）
│       ├── env_loader.py       # 環境変数/クレデンシャル読み込み
│       ├── core/               # コア機能
│       │   ├── base_handler.py # BaseHandler（共通CRUD）
│       │   └── preview_cache.py
│       ├── handlers/           # ビジネスロジック（OOPハンドラー）
│       │   ├── books/          # BooksHandler + SearchMixin
│       │   ├── students/       # StudentsHandler
│       │   └── planner/        # PlannerHandler
│       ├── lib/                # 共通ユーティリティ
│       │   ├── common.py       # normalize, ok, ng等
│       │   ├── sheet_utils.py  # norm_header, pick_col, tokenize等
│       │   ├── id_rules.py     # decide_prefix, next_id_for_prefix
│       │   ├── input_parser.py # InputParser
│       │   └── preview_cache.py
│       ├── tests/              # pytest テスト（257件）
│       ├── Dockerfile
│       ├── railway.json        # Railway設定
│       └── Procfile
├── scripts/
│   └── deploy_mcp.sh           # Railway デプロイ
├── docs/
│   ├── ARCHITECTURE.md         # アーキテクチャ概要
│   ├── TESTING.md              # テストガイド
│   ├── speed_planner_weekly.md
│   └── planner_monthly.md
├── AGENTS.md, README.md, CLAUDE.md, CONTRIBUTING.md, PROGRESS.md
└── .gitignore
```

## セットアップ

### 前提条件
- Python 3.12+ / `uv`
- Railway CLI: `npm install -g @railway/cli`
- GCPプロジェクト（Service Account用）

### 1) Service Account設定（初回のみ）

1. **GCPコンソールにアクセス**: https://console.cloud.google.com/
2. **API有効化**: 「APIとサービス」→「ライブラリ」で以下を有効化
   - Google Sheets API
   - Google Drive API
3. **Service Account作成**: 「IAMと管理」→「サービスアカウント」→「作成」
   - 名前: `cram-books-mcp`
4. **JSONキー取得**: サービスアカウント→「キー」タブ→「新しい鍵を作成」→JSON形式
5. **フォルダ共有**: 対象スプレッドシートのフォルダをService Accountメールアドレスと共有（編集者権限）

### 2) MCP サーバーセットアップ（ローカル）

```bash
cd apps/mcp

# .envファイルを作成
cp .env.example .env
# GOOGLE_CREDENTIALS_FILE にJSONキーのパスを設定

# 起動
uv run python server.py   # http://localhost:8080/mcp

# ヘルスチェック
curl http://localhost:8080/healthz
```

### 3) Railway デプロイ

```bash
# Railway CLIログイン＆プロジェクトリンク
railway login
cd apps/mcp
railway link

# 環境変数設定
railway variables set GOOGLE_CREDENTIALS_JSON="$(cat /path/to/service-account.json)"

# デプロイ
railway up
# または: scripts/deploy_mcp.sh
```

## MCP ツール一覧

### Books（参考書管理）

| ツール | 説明 | 主要引数 |
|--------|------|---------|
| `books_find` | 曖昧検索（IDF重み付き） | `query: string` |
| `books_get` | 詳細取得（単一/複数） | `book_id` または `book_ids[]` |
| `books_filter` | 条件絞り込み | `where?`, `contains?`, `limit?` |
| `books_list` | 親行一覧 | `limit?` |
| `books_create` | 新規作成（二段階） | `title`, `subject`, `chapters[]` |
| `books_update` | 更新（二段階） | `book_id`, `updates` |
| `books_delete` | 削除（二段階） | `book_id` |

### Students（生徒管理）

| ツール | 説明 | 主要引数 |
|--------|------|---------|
| `students_list` | 一覧（既定: 在塾のみ） | `limit?`, `include_all?` |
| `students_find` | 曖昧検索 | `query`, `limit?` |
| `students_get` | 詳細取得 | `student_id` または `student_ids[]` |
| `students_filter` | 条件絞り込み | `where?`, `contains?`, `limit?` |
| `students_create` | 新規作成 | `record` |
| `students_update` | 更新（二段階） | `student_id`, `updates` |
| `students_delete` | 削除（二段階） | `student_id` |

### Planner（週間管理）

| ツール | 説明 | 主要引数 |
|--------|------|---------|
| `planner_ids_list` | A〜D列の一覧取得 | `student_id` または `spreadsheet_id` |
| `planner_dates_get` | 週開始日の取得 | `student_id` または `spreadsheet_id` |
| `planner_dates_set` | 週開始日の設定 | `new_date`, `confirm_token?` |
| `planner_plan_get` | 計画+メトリクス取得 | `student_id` または `spreadsheet_id` |
| `planner_plan_targets` | 書込み候補の自動抽出 | `student_id` または `spreadsheet_id` |
| `planner_plan_create` | 一括作成 | `items[]` |
| `planner_guidance` | 計画作成ガイドライン | なし |

### Planner（月間管理）

| ツール | 説明 | 主要引数 |
|--------|------|---------|
| `planner_monthly_filter` | 指定年月の実績取得 | `year`, `month`, `student_id?` |

## 週間管理の最短フロー

1. **現状把握**: `planner_plan_get(student_id=...)`
   - weeks[].items[] に plan_text と metrics（weekly_minutes/unit_load/guideline_amount）が含まれます

2. **書込み候補の抽出**: `planner_plan_targets(...)`
   - A非空・週間時間非空・未入力のセルが targets[] として返されます
   - 各候補に `prev_range_hint` と `suggested_plan_text` が付加されます

3. **一括作成**: `planner_plan_create(items=[...])`
   - items は `{week_index, row|book_id, plan_text, overwrite?}` の配列
   - 応答に `guidance_digest` と `warnings` が含まれます

## 計画作成の原則（LLMが必ず守る）

- **収集→計画→書込みの順**:
  1. ids_list / dates_get / plan_get で現状把握
  2. 過去2-3ヶ月の実績（planner_monthly_filter）と TOC（books_get）を参照
  3. plan_targets → plan_create で一括反映

- **保守的な計画**: 過去の実績ペースとTOCに沿い、guideline_amount を守る

- **相談ポリシー（Ask-when-uncertain）**: 終端到達、重複/飛び、過不足の大きな逸脱など不確実な場合は必ずユーザーへ確認

- **終端表記**: 終える週の末尾に「★完了！」、以降の週は「★相談」

- **週数遵守**: `week_count`（4/5）にない週は作成しない

- **表記と上限**: 52文字以内、範囲は「~」、複数は「,」または改行

## テスト

```bash
cd apps/mcp

# 全テスト実行
uv run pytest tests/

# カバレッジ付き
uv run pytest tests/ --cov=.

# 特定テストのみ
uv run pytest tests/test_books_tools.py -v
```

| テスト | 件数 |
|--------|------|
| helpers（lib/*） | 66 |
| books tools | 26 |
| students tools | 25 |
| planner tools | 24 |
| **合計** | 141 |

## トラブルシューティング

| 症状 | 原因 | 対処法 |
|------|------|--------|
| `/mcp` 直叩きで 406 | SSE必須の正常応答 | MCPクライアントで接続 |
| `GOOGLE_CREDENTIALS_JSON not set` | 環境変数未設定 | Railway環境変数またはローカル.envを確認 |
| `Permission denied` | Spreadsheet未共有 | Service AccountをSpreadsheetに共有 |
| APIレート制限 | Google Sheets API制限 | 100リクエスト/100秒/ユーザー |
| `healthz` タイムアウト | サーバー起動失敗 | Railwayログを確認 |

## デバッグ方法

```bash
# ローカルサーバー起動（ログ出力あり）
cd apps/mcp
uv run python server.py

# MCP Inspectorでテスト
npx @modelcontextprotocol/inspector
# URL: http://localhost:8080/mcp

# Railwayログ確認
railway logs
```

## Claude 接続

### カスタムコネクタの設定

1. Claude の設定画面を開く
2. 「カスタムコネクタ」を選択
3. 以下を設定:
   - **名前**: CRAM Books
   - **リモートMCPサーバーURL**: `https://<Railway Service URL>/mcp`
   - **認証**: なし
4. 有効化

### 使用例

```
Claude: 青チャートの数学の参考書を検索してください

> books_find を使用して検索します...
> 青チャートⅠ（新課程）が見つかりました

Claude: その参考書の詳細を教えてください

> books_get を使用して詳細を取得します...
> 章構成: 第1章 数と式（問1-43）...
```

## ChatGPT コネクタ対応

- 背景: ChatGPTのコネクタは MCP のうち `search` と `fetch` の2ツールのみを使用
- 方針: Claude向けの多機能MCP（本main）と、ChatGPT向け最小MCP（別ブランチ）を分離
- 制約: ChatGPTでは任意ツールは使えない。searchで広く拾い、fetchで詳細取得が基本

## CI/CD（GitHub Actions）

- **test.yml**: PR/push時に自動テスト（pytest）
- **deploy.yml**: 手動またはコミットメッセージトリガーでデプロイ
  - `[deploy-mcp]`: Railwayにデプロイ
  - 必要シークレット: `RAILWAY_TOKEN`

## ベストプラクティス

### Python (MCP)

1. **入力検証**
   ```python
   def _coerce_str(x: Any, keys: tuple[str, ...] = ()) -> str | None:
       if isinstance(x, str):
           return _strip_quotes(x)
       if isinstance(x, dict):
           for k in keys:
               v = x.get(k)
               if isinstance(v, str):
                   return _strip_quotes(v)
       return None
   ```

2. **ハンドラー呼び出しパターン**
   ```python
   @mcp.tool()
   async def books_find(query: Any) -> dict:
       q = _coerce_str(query, ("query", "q"))
       if not q:
           return {"ok": False, "error": {"code": "BAD_INPUT", "message": "query is required"}}
       return handlers.books.books_find(get_sheets_client(), q)
   ```

3. **エラーハンドリング**
   ```python
   try:
       result = handlers.books.books_get(sheets, book_id)
       return result
   except Exception as e:
       return {"ok": False, "error": {"code": "ERROR", "message": str(e)}}
   ```

## 参考リンク

- [Railway ドキュメント](https://docs.railway.app/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [gspread ライブラリ](https://docs.gspread.org/)
- [MCP (Model Context Protocol)](https://github.com/anthropics/mcp)
- [FastMCP](https://github.com/jlowin/fastmcp)
