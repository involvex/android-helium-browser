# Roadmap — Involvex AI Agent

Status legend: ✅ done · 🚧 in progress · ⏭ next · 💡 idea

## Done ✅

- On-tap chat panel (tab-based, Android-safe)
- Page reading + grounded Q&A
- Selection actions (explain / translate / rewrite)
- Agent mode (read_page / click / fill / navigate / scroll, 8-step cap)
- Providers: Gemini, OpenAI, Anthropic, OpenRouter, OpenCode Zen, Custom
  (OpenAI-compatible), Ollama
- Model dropdown + live model listing
- Private-Gist backup/restore of bookmarks + settings + extension list
- `.env` token loading
- Custom icon set
- Export session as Markdown

## Next ⏭

1. **Scheduled auto-backup** — `chrome.alarms` timer calling the Gist push on an
   interval, with a "last synced" indicator.
2. **Streaming responses** — token-by-token rendering for OpenAI-compatible and
   Gemini endpoints (SSE) instead of waiting for the full reply.
3. **Per-provider quick switch in the panel** — a small dropdown next to the
   model select to change provider without opening Settings.
4. **Restore-with-merge for extensions** — offer install links from the
   backed-up extension list (open each `homepageUrl`/webstore entry).

## Ideas 💡

- Conversation history persistence (list of past sessions) with search.
- Prompt library / custom quick-prompt chips editable in Settings.
- Screenshot-to-vision for models that support image input.
- MEGA backend behind the same backup UI (needs the MEGA SDK; Gist is the
  default because it is serverless and free).
- Local RAG over the current page (chunk + embed with a small local model).

## Browser build (separate track)

The full Chromium/Android build cannot finish inside GitHub-hosted runners (they
hard-cancel at 6 hours; our build reached ~5h45m before cancellation). Options:

- **Recommended now**: ship a prebuilt Helium/Kiwi APK and load this extension
  into it — no multi-hour compile needed.
- **Self-hosted runner** (a beefy Linux box/VM) removes the 6-hour cap.
- **Local Linux/WSL2 build** with `ccache`/`reclient` for incremental rebuilds.
