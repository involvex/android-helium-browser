# Involvex UX Reference (WebView prototype)

The Jetpack Compose prototype lives at `E:\repos\Involvex-Browser` (sibling repo).

Use it as a **design reference only** — not as the browser engine.

## Patterns worth porting to Chromium

| Prototype feature | File | Chromium target |
|-------------------|------|-----------------|
| Split-view layout | `BrowserMainScreen.kt` | `split-view.patch` (when GPLv2 unblocked) |
| Settings organization | `BrowserSettings.kt` | Android Chrome settings Java |
| Encrypted backup UX | `BrowserViewModel.kt` | Bookmark export + `scripts/encrypt-backup.sh` |
| Custom homepage | `BrowserHomepage.kt` | New tab page override patch |
| QR config transfer | `QrScannerScreen.kt` | Optional settings import |

## Do not port

- WebView wrapper (`BrowserWebView.kt`) — use Chromium content layer
- User-script “extensions” — use real MV2 via Web Store
- Fake incognito / DoH toggles — use Vanadium prefs

See [Involvex-Browser README](E:\repos\Involvex-Browser\README.md).
