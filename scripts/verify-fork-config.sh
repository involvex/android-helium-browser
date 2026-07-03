#!/bin/bash
# Verify Involvex fork configuration without a full Chromium compile.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERR=0

check() {
  if eval "$2"; then
    echo "[OK] $1"
  else
    echo "[FAIL] $1"
    ERR=1
  fi
}

check "Package is app.involvex.browser" \
  "grep -q 'app.involvex.browser' '${SCRIPT_DIR}/args.gn'"

check "is_desktop_android enabled" \
  "grep -q 'is_desktop_android = true' '${SCRIPT_DIR}/args.gn'"

check "Cloudflare DoH privacy tweaks in patch.sh" \
  "grep -q 'cloudflare-dns.com' '${SCRIPT_DIR}/patch.sh' && grep -q 'kDohProviderGoogle' '${SCRIPT_DIR}/patch.sh'"

check "Vanadium patch count" \
  "test \$(find '${SCRIPT_DIR}/vanadium/patches' -name '*.patch' | wc -l | tr -d ' ') -ge 280"

check "WSL2 or Linux environment" \
  "uname -s | grep -q Linux"

check "depot_tools in PATH or present" \
  "command -v gclient >/dev/null 2>&1 || test -d '${HOME}/depot_tools'"

if [[ ${ERR} -eq 0 ]]; then
  echo "All pre-build checks passed. Run: bash scripts/build-debug-wsl2.sh"
else
  echo "Some checks failed."
  exit 1
fi
