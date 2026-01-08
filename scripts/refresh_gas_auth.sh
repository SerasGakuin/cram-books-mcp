#!/usr/bin/env bash
set -euo pipefail

# GASの認証とデプロイを更新するスクリプト
# 定期的（週1回など）に実行することを推奨

cd "$(dirname "$0")/../apps/gas"

echo "🔄 GASの認証とデプロイを更新します..."

# 1. ビルド
echo "📦 ビルド中..."
npm run build

# 2. Push
echo "⬆️  Push中..."
clasp push

# 3. 既存デプロイIDで再デプロイ
DEPLOY_ID=$(cat .prod_deploy_id)
echo "🚀 デプロイ中 (ID: $DEPLOY_ID)..."
clasp deploy -i "$DEPLOY_ID" -d "Refresh deployment $(date +%Y-%m-%d)"

# 4. テスト
echo "✅ テスト中..."
DEPLOY_URL="https://script.google.com/macros/s/${DEPLOY_ID}/exec"
RESULT=$(curl -sS -L "${DEPLOY_URL}?op=ping")

if echo "$RESULT" | grep -q '"ok":true'; then
    echo "✅ GASは正常に動作しています"
    echo "$RESULT" | python3 -m json.tool
else
    echo "❌ GASのテストに失敗しました"
    echo "$RESULT"
    exit 1
fi

echo ""
echo "🎉 完了! 次回の実行は1週間後を推奨します"
