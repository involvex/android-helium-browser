#!/bin/bash
# Debug Chromium Android build without APK signing secrets.
#
# Storage: a full Chromium Android checkout + build is ~120-150 GB.
# Set BUILD_ROOT to place the heavy chromium/ tree on a specific drive/path,
# e.g. BUILD_ROOT=/mnt/i/chromium-build to keep it off the M.2.
# If unset, the tree lives in ./chromium next to this repo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${SCRIPT_DIR}"  # common.sh clobbers SCRIPT_DIR via $0; keep the real repo root
export VERSION
VERSION="$(grep -m1 -o '[0-9]\+\(\.[0-9]\+\)\{3\}' "${SCRIPT_DIR}/vanadium/args.gn")"
export CHROMIUM_SOURCE=https://chromium.googlesource.com/chromium/src.git
export DEBIAN_FRONTEND=noninteractive

# --- Ensure depot_tools is on PATH (works on non-interactive re-runs) ---
for dt in "${DEPOT_TOOLS:-}" "${HOME}/depot_tools" "${SCRIPT_DIR}/depot_tools"; do
  if [[ -n "${dt}" && -x "${dt}/gclient" ]]; then
    export PATH="${dt}:${PATH}"
    break
  fi
done

if ! command -v gclient >/dev/null 2>&1 || ! command -v gn >/dev/null 2>&1; then
  echo "ERROR: depot_tools (gclient/gn) not found."
  echo "Install: git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git ~/depot_tools"
  echo "Or set DEPOT_TOOLS=/path/to/depot_tools and re-run."
  exit 1
fi
echo "==> depot_tools: $(command -v gn)"

cd "${SCRIPT_DIR}"

# --- Relocate heavy chromium/ tree to BUILD_ROOT if requested ---
if [[ -n "${BUILD_ROOT:-}" ]]; then
  mkdir -p "${BUILD_ROOT}/chromium"
  # If ./chromium exists and is not already the symlink, move/remove it.
  if [[ -e chromium && ! -L chromium ]]; then
    if [[ -z "$(ls -A chromium 2>/dev/null)" ]]; then
      rmdir chromium
    else
      echo "==> Moving existing ./chromium into ${BUILD_ROOT}/chromium ..."
      cp -a chromium/. "${BUILD_ROOT}/chromium/" && rm -rf chromium
    fi
  fi
  [[ -L chromium ]] && rm -f chromium
  ln -s "${BUILD_ROOT}/chromium" chromium
  echo "==> chromium tree -> ${BUILD_ROOT}/chromium (via symlink)"
fi

# --- Detect a usable existing checkout, else (re)fetch cleanly ---
NEED_FETCH=0
if [[ ! -f chromium/.gclient || ! -d chromium/src/.git ]]; then
  NEED_FETCH=1
fi

if [[ "${NEED_FETCH}" -eq 1 ]]; then
  echo "==> First-time / clean Chromium fetch (this takes a long time)..."

  # Remove any partial/corrupt tree to avoid git init conflicts.
  if [[ -e chromium && ! -L chromium ]]; then
    rm -rf chromium
  elif [[ -L chromium ]]; then
    rm -rf "$(readlink -f chromium)"/* "$(readlink -f chromium)"/.[!.]* 2>/dev/null || true
  fi

  sudo apt-get update
  sudo apt-get install -y sudo lsb-release file nano git curl python3 \
    python3-pillow imagemagick

  mkdir -p chromium/src/out/Default
  cd chromium
  gclient root
  cd src
  git init
  git remote add origin "${CHROMIUM_SOURCE}"
  git fetch --depth 1 "${CHROMIUM_SOURCE}" "+refs/tags/${VERSION}:chromium_${VERSION}"
  git checkout "${VERSION}"
  COMMIT="$(git show-ref -s "${VERSION}" | head -n1)"
  cat >../.gclient <<EOF
solutions = [
  {
    "name": "src",
    "url": "${CHROMIUM_SOURCE}@${COMMIT}",
    "deps_file": "DEPS",
    "managed": False,
    "custom_vars": {
      "checkout_android_prebuilts_build_tools": True,
      "checkout_pgo_profiles": True,
      "checkout_telemetry_dependencies": False,
      "codesearch": "Debug",
    },
  },
]
target_os = ["android"]
EOF
  git submodule foreach git config -f ./.git/config submodule.\$name.ignore all
  git config --add remote.origin.fetch '+refs/tags/*:refs/tags/*'
  # git am needs a committer identity (CI runners have none)
  git config user.email "ci@involvex.browser"
  git config user.name "involvex-ci"

  source "${SCRIPT_DIR}/common.sh"
  SCRIPT_DIR="${REPO_DIR}"  # restore: common.sh reset it relative to the changed CWD
  rm -rf "${SCRIPT_DIR}"/vanadium/patches/*trichrome-{apk-build-targets,browser-apk-targets}.patch
  rm -rf "${SCRIPT_DIR}"/vanadium/patches/*{detailed,supported}-language*.patch
  rm -rf "${SCRIPT_DIR}"/vanadium/patches/*component-updates.patch
  replace "${SCRIPT_DIR}/vanadium/patches" "VANADIUM" "HELIUM"
  replace "${SCRIPT_DIR}/vanadium/patches" "Vanadium" "Helium"
  replace "${SCRIPT_DIR}/vanadium/patches" "vanadium" "helium"
  replace "${SCRIPT_DIR}/vanadium/patches" "io.github.jqssun.helium" "app.involvex.browser"
  # Involvex-specific patches (parent-tracked, survive submodule checkout in CI)
  if compgen -G "${SCRIPT_DIR}/involvex/patches/*.patch" >/dev/null; then
    cp "${SCRIPT_DIR}"/involvex/patches/*.patch "${SCRIPT_DIR}/vanadium/patches/"
  fi
  git am --whitespace=nowarn --keep-non-patch "${SCRIPT_DIR}"/vanadium/patches/*.patch

  gclient sync -D --no-history --nohooks
  gclient runhooks
  rm -rf third_party/angle/third_party/VK-GL-CTS/
  ./build/install-build-deps.sh --no-prompt
else
  echo "==> Existing checkout detected; skipping fetch."
  cd chromium/src
fi

source "${SCRIPT_DIR}/patch.sh"
cp "${SCRIPT_DIR}/args.gn" out/Default/args.gn
sudo dpkg --add-architecture i386 2>/dev/null || true
sudo apt-get update
sudo apt-get install -y libgcc-s1:i386
gn gen out/Default
autoninja -C out/Default chrome_public_apk

echo "==> Debug APK:"
find out/Default/apks -name 'Chrome*.apk' -print
