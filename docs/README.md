# Involvex Browser Documentation

| Document | Description |
|----------|-------------|
| [BUILD-WSL2.md](BUILD-WSL2.md) | Windows WSL2 build environment and debug compile |
| [PRIVACY.md](PRIVACY.md) | Vanadium privacy patches + Cloudflare DoH |
| [EXTENSION_MATRIX.md](EXTENSION_MATRIX.md) | Chrome extension compatibility testing |
| [SYNC.md](SYNC.md) | Bookmark/history sync without cloud servers |
| [SPLIT_VIEW_EVAL.md](SPLIT_VIEW_EVAL.md) | Split tab view feasibility |

## Scripts

| Script | Purpose |
|--------|---------|
| `../scripts/setup-wsl2.sh` | Install Ubuntu build deps + depot_tools |
| `../scripts/build-debug-wsl2.sh` | Unsigned debug APK build |
| `../scripts/verify-fork-config.sh` | Pre-flight checks (no compile) |
| `../scripts/encrypt-backup.sh` | AES encrypt exports for Syncthing |

## Involvex fork

| Path | Purpose |
|------|---------|
| [../involvex/REBRAND.md](../involvex/REBRAND.md) | Package `app.involvex.browser` |
| [../involvex/UX_REFERENCE.md](../involvex/UX_REFERENCE.md) | WebView prototype reference |
