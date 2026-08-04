#!/usr/bin/env bash
# Post-deploy smoke test: verify the deployed app is actually serving.
# Used by the CD workflow after a deploy, before declaring success.
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
echo "Smoke-testing ${BASE_URL} ..."

# 1. health endpoint returns 200 + status ok
status=$(curl -fsS "${BASE_URL}/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
[ "$status" = "ok" ] || { echo "❌ health check failed"; exit 1; }

# 2. core flow works: shorten then follow
slug=$(curl -fsS -X POST "${BASE_URL}/shorten" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['slug'])")
code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/${slug}")
[ "$code" = "302" ] || { echo "❌ redirect failed (got $code)"; exit 1; }

echo "✅ smoke test passed"
