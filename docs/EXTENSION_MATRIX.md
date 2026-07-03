# Extension Compatibility Matrix

Involvex Browser uses Chromium `is_desktop_android` with Manifest V2 re-enabled
(see [`patch.sh`](../patch.sh)). This is **not** desktop Chrome — expect partial API support.

## Test environment

| Item | Value |
|------|-------|
| Device | Physical Android 10+ recommended |
| Install | Chrome Web Store with **Desktop site** enabled |
| Build | Release APK (`build.sh` or CI) — debug may break extensions |
| Verify | `chrome://extensions` |

## Priority extensions

| Extension | ID | MV | Expected | Known issues |
|-----------|-----|-----|----------|--------------|
| uBlock Origin | `cjpalhdlnbpafiamejdnhcphjbkeiagm` | 2 | **Works** | Element picker opens in tab; page refresh quirks |
| Dark Reader | `eimadpbcbfnmbkopoojfekhnkhdbieeh` | 2 | **Works** | — |
| Tampermonkey | `dhdgffkkebhmkfjojejmpbldmpobfkfo` | 2/3 | **Partial** | Script sync via export, not Chrome sync |
| Stylus | `clngdbkpkpeebahjigkjmmbfbdggvcbj` | 2 | **Partial** | Theme injection site-dependent |
| Bitwarden | `nngceckbapebfimnndiiadpmaclajieg` | 3 | **Partial** | Autofill via Android framework preferred |
| Proton Pass | N/A (Android app) | — | **Via Autofill** | Use Proton Pass as system autofill provider |

## API limitations (all Android Chromium forks)

| API / behavior | Desktop | Involvex Android |
|----------------|---------|------------------|
| Extension popup | Overlay | Often opens as **new tab** |
| `chrome.windows` | Full | Broken / limited |
| `chrome.permissions.request` | Works | Often fails |
| Incognito-only extensions | Works | Unreliable |
| Native messaging | Works | Limited |
| MV3 service workers | Full | Lifecycle constrained on mobile |
| `.crx` sideload | Works | Unreliable — prefer Web Store |

## Test procedure

### 1. uBlock Origin

1. Enable Desktop site on [Chrome Web Store](https://chromewebstore.google.com/)
2. Install uBlock Origin
3. Pin to toolbar → open popup
4. Visit `https://ads-blocker.com/testing/` — confirm blocks
5. Log: popup behavior (tab vs overlay)

### 2. Tampermonkey

1. Install from Web Store
2. Add a test userscript (e.g. document title change)
3. Verify on target domain
4. Export scripts (Tampermonkey dashboard) for desktop sync

### 3. Dark Reader

1. Install and enable for all sites
2. Verify dark theme on `https://example.com`

### 4. Proton Pass autofill

1. Install [Proton Pass](https://play.google.com/store/apps/details?id=proton.android.pass) on device
2. Android Settings → Passwords & autofill → **Proton Pass**
3. In Involvex: Settings → Autofill and passwords → confirm autofill service
4. Test login on `https://example.com` form or your test site

### 5. DevTools

1. Open `chrome://chrome-urls`
2. Enable Android DevTools (enabled by default in this fork)
3. Context menu → Developer tools (if visible)
4. Alternative: `chrome://inspect` from desktop Chrome with USB debugging

## Recording results

Update this table after each release:

```markdown
| Extension | Version | Date | Result | Notes |
|-----------|---------|------|--------|-------|
| uBO | x.x.x | YYYY-MM-DD | PASS/FAIL | |
```

## Porting Kiwi fixes

If an extension fails here but worked on Kiwi, check
[kiwibrowser/chromium_extension_patches](https://github.com/kiwibrowser/chromium_extension_patches)
for surgical Android glue patches — cherry-pick only, do not rebase entire Kiwi tree.
