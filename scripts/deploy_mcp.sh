#!/usr/bin/env bash
set -euo pipefail

# Railway へ MCP をデプロイするユーティリティ。
# 使い方:
#   scripts/deploy_mcp.sh
#
# 事前準備:
#   1. Railway CLI をインストール: npm install -g @railway/cli
#   2. Railway にログイン: railway login
#   3. プロジェクトをリンク: railway link (apps/mcp ディレクトリで)
#
# 環境変数 (Railway Dashboard で設定):
#   - GOOGLE_CREDENTIALS_JSON: Service Account の JSON 内容

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT_DIR/apps/mcp"

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Railway CLI is not installed. Install with: npm install -g @railway/cli" >&2
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "Not logged in to Railway. Run: railway login" >&2
    exit 1
fi

echo "Deploying to Railway..." >&2
railway up

# Get service URL
echo ""
echo "Deployment complete. Check Railway dashboard for service URL." >&2
echo ""
echo "To set environment variables:" >&2
echo "  railway variables set GOOGLE_CREDENTIALS_JSON='\$(cat service-account.json)'" >&2
