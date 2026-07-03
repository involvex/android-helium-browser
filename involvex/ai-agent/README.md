# Involvex AI Agent (browser extension)

An on-tap AI assistant that reads — and, in Agent mode, acts on — the current
web page. Built as a Manifest V3 extension so it runs in Involvex Browser
(Helium/Kiwi fork) and in desktop Chrome/Edge without rebuilding the browser.

## Features

- **On tap**: tap the toolbar button to open a chat side panel for the current tab.
- **Reads the page**: summaries, Q&A, and answers grounded in the page content.
- **Selection actions**: right-click selected text → Explain / Translate / Rewrite.
- **Agent mode** (toggle): the model can `read_page`, `click`, `fill`,
  `navigate`, and `scroll` to complete multi-step tasks. Capped at 8 steps.
- **Multi-provider**: Google Gemini, OpenAI, Anthropic Claude, or a **local
  model via Ollama**. Your API key is stored locally and sent straight to the
  provider — there is no Involvex server.

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

| Provider  | Needs key | Get a key                     | Example model              |
| --------- | --------- | ----------------------------- | -------------------------- |
| Gemini    | yes       | aistudio.google.com/apikey    | `gemini-2.0-flash`         |
| OpenAI    | yes       | platform.openai.com/api-keys  | `gpt-4o-mini`              |
| Anthropic | yes       | console.anthropic.com         | `claude-3-5-haiku-latest`  |
| Ollama    | no        | local install                 | `qwen2.5:3b`               |

Use **Test connection** to verify before chatting.

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

- `manifest.json` — MV3 config (side panel, context menus, `scripting`).
- `src/background.js` — service worker: extracts page content and performs
  actions via `chrome.scripting.executeScript`, runs the ask flow and the
  agentic tool loop, routes messages over a `Port`.
- `src/providers.js` — unified `chat()` across Gemini/OpenAI/Anthropic/Ollama.
- `src/sidepanel.*` — the chat UI (on-tap surface, quick prompts, Agent toggle).
- `src/options.*` — provider settings + connection test.

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
