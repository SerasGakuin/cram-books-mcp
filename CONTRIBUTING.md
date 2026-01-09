# Contribution Guide

このプロジェクトへの貢献ガイドです。

## ブランチ戦略

- `main`: 本番環境（Railway自動デプロイ）
- `feat/*`: 機能開発
- `fix/*`: バグ修正
- `refactor/*`: リファクタリング

## PRプロセス

1. `feat/*` ブランチで開発
2. テスト通過を確認（`cd apps/mcp && uv run pytest tests/`）
3. PR作成 → レビュー → mainマージ
4. Railway自動デプロイ

## コミット規約

[Conventional Commits](https://www.conventionalcommits.org/) に従う:

- `feat`: 新機能
- `fix`: バグ修正
- `refactor`: リファクタリング
- `docs`: ドキュメント
- `test`: テスト追加/修正
- `chore`: その他（CI、依存関係など）

### 例

```
feat(books): add bulk update support
fix(planner): resolve incorrect date calculation
refactor(handlers): extract common validation logic
docs(readme): update installation instructions
test(students): add filter edge cases
```

### スコープ

- `books`: 参考書関連
- `students`: 生徒関連
- `planner`: プランナー関連
- `mcp`: MCPサーバー全般
- `gas`: GAS関連（アーカイブ）

## コード品質

### 必須チェックリスト

- [ ] テスト通過（`uv run pytest tests/`）
- [ ] 型ヒント付与（全public関数）
- [ ] 重複コードなし（DRY原則）
- [ ] エラーハンドリングあり

### Pythonスタイル

- PEP 8 準拠
- 型ヒント必須（Python 3.10+ スタイル: `T | None` など）
- dataclass/NamedTuple を積極活用
- 関数は30行以下を目安

## テスト

```bash
cd apps/mcp

# 全テスト実行
uv run pytest tests/ -v

# カバレッジ付き
uv run pytest tests/ --cov=. --cov-report=term-missing

# 特定テストのみ
uv run pytest tests/test_books_tools.py -v
```

## ローカル開発

```bash
cd apps/mcp

# 依存関係インストール
uv sync

# ローカルサーバー起動
uv run python server.py

# ヘルスチェック
curl http://localhost:8080/healthz
```

## 環境変数

開発時は `.env` ファイルを作成:

```bash
GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
```

## 問い合わせ

- 質問や議論: GitHub Issues
- バグ報告: GitHub Issues（再現手順を含めてください）
