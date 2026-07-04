# Involvex AI Agent (browser extension)

An on-tap AI assistant that reads — and, in Agent mode, acts on — the current
web page, plus private backup of your bookmarks and settings. Built as a
Manifest V3 extension so it runs in Involvex Browser (Helium/Kiwi fork) and in
desktop Chrome/Edge without rebuilding the browser.

## Features

- **On tap**: tap the toolbar button to open the AI chat for the current tab.
  The panel opens as a page/tab, so it works on Android too (the desktop-only
  `sidePanel` API is not used).
- **Reads the page**: summaries, Q&A, and answers grounded in the page content.
- **Selection actions**: right-click selected text → Explain / Translate / Rewrite.
- **Agent mode** (toggle): the model can `read_page`, `click`, `fill`,
  `navigate`, and `scroll` to complete multi-step tasks. Capped at 8 steps.
- **Multi-provider**: Google Gemini, OpenAI, Anthropic Claude, **OpenRouter**
  (hundreds of models, incl. free), **OpenCode Zen** (default `mimo-v2.5-free`),
  a **Custom OpenAI-compatible endpoint** (Kilo Code, LM Studio, vLLM, LiteLLM…),
  or a **local model via Ollama**. Keys are stored locally and sent straight to
  the provider — no Involvex server.
- **Model dropdown**: pick the model in Settings (with a **Load models** button
  that fetches the provider's live list) or switch quickly from the panel header.
- **Backup & Sync**: back up bookmarks + settings + installed-extension list to
  a **private GitHub Gist**. Serverless, free, and API keys are never included.
- **Export session as Markdown**: the ⤓ button saves the whole conversation
  (with the provider/model/mode header) to a `.md` file.

## Install (developer load)

### Desktop Chrome / Edge / Involvex desktop

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select this `involvex/ai-agent` folder.
4. Open **Details → Extension options** and set your provider + API key.
5. Tap the toolbar icon to open the side panel.

### Involvex Browser on Android

Extension loading is enabled in this fork. Open the browser's extensions page,
choose **Load unpacked** / install from a local `.zip` of this folder, then open
the extension's options to configure a provider.

## Configure a provider

Open the options page and pick one:

| Provider   | Needs key | Get a key                     | Example model              |
| ---------- | --------- | ----------------------------- | -------------------------- |
| Gemini     | yes       | aistudio.google.com/apikey    | `gemini-2.0-flash`         |
| OpenAI     | yes       | platform.openai.com/api-keys  | `gpt-4o-mini`              |
| Anthropic  | yes       | console.anthropic.com         | `claude-3-5-haiku-latest`  |
| OpenRouter | yes       | openrouter.ai/keys            | `openrouter/auto`          |
| OpenCode Zen | yes     | opencode.ai                   | `mimo-v2.5-free`           |
| Custom     | optional  | your own server               | server-defined             |
| Ollama     | no        | local install                 | `qwen2.5:3b`               |

Use **Load models** to fetch the live model list into the dropdown, then
**Test connection** to verify before chatting.

### OpenCode / Kilo Code / other OpenAI-compatible servers

Choose **Custom (OpenAI-compatible)** and set the Base URL to your server's
`/v1` endpoint (e.g. `http://localhost:8080/v1`), plus a key if it needs one.
Anything exposing `/v1/chat/completions` and `/v1/models` works.

## Backup & Sync (private GitHub Gist)

1. Create a GitHub token with only the **`gist`** scope at
   github.com/settings/tokens.
2. Open Settings → **Backup & Sync**, paste the token, click **Back up now**.
   A private (secret) Gist is created and its id is saved for future backups.
3. On another device, install the extension, paste the same token + Gist id,
   and click **Restore**. Bookmarks are added into a new "Involvex Restore"
   folder (existing bookmarks are never overwritten); non-secret settings are
   merged.

API keys and the Gist token itself are stripped from every backup, so secrets
never leave the device.

## Local small models (Ollama)

1. Install Ollama and pull a small model:
   ```bash
   ollama pull qwen2.5:3b
   ```
2. Let the extension reach Ollama (CORS). Start the server allowing the
   extension origin:
   ```bash
   OLLAMA_ORIGINS=* ollama serve
   ```
   (or set `OLLAMA_ORIGINS` to include `chrome-extension://*`).
3. In options choose **Local (Ollama)**, set base URL `http://localhost:11434`
   and the model name.

On Android, point the base URL at a reachable host running Ollama (e.g. your PC
on the LAN) since the phone itself won't run the server.

## How it works

- `manifest.json` — MV3 config (context menus, `scripting`, `bookmarks`).
- `src/background.js` — service worker: opens the panel as a tab, extracts page
  content and performs actions via `chrome.scripting.executeScript`, runs the
  ask flow and the agentic tool loop, routes chat over a `Port`, and handles
  backup requests.
- `src/providers.js` — unified `chat()` and `listModels()` across
  Gemini/OpenAI/Anthropic/OpenRouter/custom/Ollama.
- `src/backup.js` — private-Gist backup/restore of bookmarks + settings.
- `src/env.js` — optional `.env` loader for the Gist token.
- `src/panel.*` — the chat UI (on-tap surface, model dropdown, export, quick
  prompts, Agent toggle). Opens as a tab so it works on Android.
- `src/options.*` — provider settings, model picker, connection test, backup.
- `icons/` — extension icon set (16/32/48/128).
- `scripts/package-extension.*` — build a store-ready zip.

## Packaging

```bash
# from involvex/ai-agent
bash scripts/package-extension.sh          # -> dist/involvex-ai-agent-<version>.zip
```

```powershell
# Windows
pwsh scripts/package-extension.ps1
```

See `CHANGELOG.md` for release notes and `ROADMAP.md` for what's next.

The agent loop is provider-agnostic: the model requests one tool per turn as a
JSON block, the worker executes it in the page and feeds back the result until
the model calls `finish`. This avoids depending on any single vendor's
function-calling format.

## Safety notes

- Agent mode can click and submit forms. It is **off by default**; enable it per
  session with the **Agent** toggle. Navigation is restricted to `http(s)`.
- Page content is only sent to the provider you configured, when you send a
  message. Nothing is sent on page load.

## Roadmap

- Streaming responses.
- Per-site allow/deny list for Agent mode.
- Native toolbar button that opens this panel (deeper browser integration).
- Custom toolbar/PNG icon set.
