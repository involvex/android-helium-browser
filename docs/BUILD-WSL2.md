# Building Involvex Browser (Helium/Vanadium fork) on Windows via WSL2

This guide covers local Android APK builds on Windows 11 without Docker. Chromium Android
compilation requires a Linux toolchain; WSL2 is the supported path on Windows.

## Hardware requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 16 GB | 32 GB |
| Disk (Linux filesystem) | 150 GB free | 250+ GB on NVMe |
| CPU | 4 cores | 8+ cores |

GPU (e.g. AMD RX 6600) does not accelerate the Chromium compile; CPU and RAM dominate.

## 1. Install WSL2

In PowerShell (Administrator):

```powershell
wsl --install -d Ubuntu-24.04
```

Reboot if prompted, then open **Ubuntu 24.04** and create your Linux user.

### WSL memory limit (optional)

Create or edit `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=24GB
processors=8
swap=16GB
```

Restart WSL: `wsl --shutdown`

## 2. Bootstrap the build environment

From Ubuntu, run the setup script shipped with this repo:

```bash
cd ~/src
git clone <your-fork-url> android-helium-browser
cd android-helium-browser
bash scripts/setup-wsl2.sh
source ~/.bashrc
```

Or install manually:

```bash
sudo apt update
sudo apt install -y git python3 curl openjdk-17-jdk imagemagick \
  libgcc-s1:i386 build-essential ccache lsb-release file nano \
  python3-pillow sudo

git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git ~/depot_tools
echo 'export PATH="$HOME/depot_tools:$PATH"' >> ~/.bashrc
echo 'export CCACHE_DIR="$HOME/.ccache"' >> ~/.bashrc
source ~/.bashrc
ccache -M 20G
```

## 3. Clone location

**Always build inside the Linux filesystem** (`~/src/...`), not under `/mnt/e/` or
`/mnt/c/`. NTFS mounts are 5–10× slower for Chromium’s 400k+ files and can cause
subtle build failures.

To access Windows repos from WSL:

```bash
mkdir -p ~/src
cp -a /mnt/e/repos/android-helium-browser ~/src/android-helium-browser
cd ~/src/android-helium-browser
```

## 4. Debug build (no signing keys)

For a first compile without GitHub signing secrets:

```bash
bash scripts/build-debug-wsl2.sh
```

Output APK:

```
chromium/src/out/Default/apks/ChromePublic.apk
```

Install on a device:

```bash
adb install -r chromium/src/out/Default/apks/ChromePublic.apk
```

## 5. Release build (signed)

Set base64-encoded keystore secrets (same as CI):

```bash
export LOCAL_TEST_JKS="$(base64 -w0 keys/local.properties)"
export STORE_TEST_JKS="$(base64 -w0 keys/test.jks)"
bash build.sh
```

Signed APKs appear under `chromium/src/out/release/`.

## 6. Incremental rebuilds

After the first full sync:

```bash
cd ~/src/android-helium-browser/chromium/src
source ../../patch.sh   # only if patch.sh changed
gn gen out/Default
autoninja -C out/Default chrome_public_apk
```

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `git am` patch failures after Vanadium update | Update `vanadium` submodule; check patch conflicts |
| OOM during link | Reduce parallel jobs: `autoninja -j4 -C out/Default ...` |
| Slow I/O | Move tree to `~/src`, enable ccache |
| Missing `install-build-deps` packages | Re-run `./build/install-build-deps.sh --no-prompt` |
| WSL clock skew | `sudo hwclock -s` on Windows host |

## 8. Chromium version

The target tag is defined in [`vanadium/args.gn`](../vanadium/args.gn)
(`android_default_version_name`, e.g. `150.0.7871.63`).

## Related docs

- [PRIVACY.md](PRIVACY.md) — privacy patches and Cloudflare DoH
- [EXTENSION_MATRIX.md](EXTENSION_MATRIX.md) — extension compatibility testing
- [SYNC.md](SYNC.md) — bookmark/history sync without servers
- [SPLIT_VIEW_EVAL.md](SPLIT_VIEW_EVAL.md) — split tab view status
- [Agents.md](../Agents.md) — developer reference
