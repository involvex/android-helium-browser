# Changelog — Involvex AI Agent

All notable changes to the extension. Versions follow the `manifest.json`
`version` field.

## 0.4.0

- **Scheduled auto-backup** — daily or weekly Gist backup via `chrome.alarms`.
  Configure in Settings → Backup & Sync. Last backup date shown in the panel.
- **Streaming responses** — token-by-token rendering for Gemini and
  OpenAI-compatible providers (OpenAI, OpenRouter, OpenCode Zen, Custom) in Ask
  mode.
- **Provider quick-switch** — dropdown in the panel header to change provider
  without opening Settings.
- Docs: `adb-update.ps1` linked from README; CI 6-hour limit documented in
  `BUILD-WSL2.md`.

## 0.3.0

- **New provider: OpenCode Zen** (`https://opencode.ai/zen/v1`), OpenAI-compatible.
  Default model `mimo-v2.5-free`; free models end with `-free`. Use **Load
  models** for the full live list.
- **Custom icon set** (16/32/48/128) — blue→purple emblem, shown on the toolbar
  button and in the panel header.
- **Export session as Markdown** — new ⤓ button in the panel downloads the
  whole conversation (with provider/model/mode header) as a `.md` file.
- **New chat** — ＋ button clears the current session.
- Packaging: `scripts/package-extension.*` zips a store-ready build.

## 0.2.1

- Load the GitHub Gist token from a bundled `.env` (`GITHUB_TOKEN`, `GIST_ID`)
  so backups work without typing keys into Settings.

## 0.2.0

- **Android fix**: removed the desktop-only `sidePanel` API (was throwing
  "'sidePanel' is not allowed for specified platform"). The panel now opens as a
  normal tab and tracks the originating page tab, so it works on Android.
- **New providers**: OpenRouter and a Custom OpenAI-compatible endpoint
  (OpenCode, Kilo Code, LM Studio, vLLM, LiteLLM…).
- **Model dropdown** in Settings and in the panel header, with a **Load models**
  button that fetches the provider's live list.
- **Backup & Sync**: bookmarks + non-secret settings + installed-extension list
  to a private GitHub Gist. Secrets are stripped from every backup.

## 0.1.0

- Initial release: on-tap chat, page reading, selection actions (explain /
  translate / rewrite), Agent mode (read/click/fill/navigate/scroll), and
  providers Gemini / OpenAI / Anthropic / Ollama.
