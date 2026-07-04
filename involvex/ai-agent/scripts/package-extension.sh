#!/usr/bin/env bash
# Packages the Involvex AI Agent extension into a store-ready zip.
# Excludes local secrets (.env), scripts, and source assets.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

VERSION="$(grep -o '"version": *"[^"]*"' manifest.json | head -1 | sed 's/.*"\([0-9.]*\)"/\1/')"
OUT="dist/involvex-ai-agent-${VERSION}.zip"
mkdir -p dist
rm -f "$OUT"

zip -r "$OUT" \
  manifest.json \
  src \
  icons \
  README.md \
  CHANGELOG.md \
  -x "*/.env" ".env" "*.map" >/dev/null

echo "Built $OUT"
