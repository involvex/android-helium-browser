#!/bin/bash
# Bootstrap Ubuntu (WSL2) for Chromium Android builds.
set -euo pipefail

echo "==> Installing build dependencies..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git python3 curl openjdk-17-jdk imagemagick libgcc-s1:i386 \
  build-essential ccache lsb-release file nano python3-pillow sudo

if [[ ! -d "${HOME}/depot_tools" ]]; then
  echo "==> Cloning depot_tools..."
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git \
    "${HOME}/depot_tools"
fi

MARKER='# involvex-browser depot_tools'
if ! grep -q "${MARKER}" "${HOME}/.bashrc" 2>/dev/null; then
  cat >>"${HOME}/.bashrc" <<EOF

${MARKER}
export PATH="\${HOME}/depot_tools:\${PATH}"
export CCACHE_DIR="\${HOME}/.ccache"
EOF
fi

export PATH="${HOME}/depot_tools:${PATH}"
ccache -M 20G 2>/dev/null || ccache -M 20G

echo "==> Setup complete."
echo "Run: source ~/.bashrc"
echo "Then: bash scripts/build-debug-wsl2.sh"
