# Involvex Browser — Rebrand Configuration

This fork rebrands Helium Browser for Android as **Involvex Browser**.

## Package identity

| Setting | Value |
|---------|-------|
| Android package | `app.involvex.browser` |
| GN arg | `chrome_public_manifest_package` in [`args.gn`](../args.gn) |
| Display name | Involvex Browser (applied via Vanadium string patches at build) |

## Build-time substitutions

[`build.sh`](../build.sh) and [`scripts/build-debug-wsl2.sh`](../scripts/build-debug-wsl2.sh) apply:

1. Vanadium → Helium string replacement in patches (upstream convention)
2. `io.github.jqssun.helium` → `app.involvex.browser` in patch contents

## Custom icons and strings

After the first Chromium sync, optional manual steps:

```bash
cd chromium/src
# App label (example — path may shift per Chromium version)
# Edit chrome/browser/ui/android/strings/android_chrome_strings.grd
python3 tools/grit/grit.py build -i ... -o ...
```

For production branding, add a dedicated Vanadium-format patch under
`vanadium/patches/` following the `0004-Vanadium-branding.patch` pattern.

## Verify rebrand

```bash
bash scripts/build-debug-wsl2.sh
aapt dump badging out/Default/apks/ChromePublic.apk | grep package
# Expect: package: name='app.involvex.browser'
```
