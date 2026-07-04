export const PROVIDERS = {
  gemini: {
    label: "Google Gemini",
    defaultModel: "gemini-2.0-flash",
    needsKey: true,
    knownModels: [
      "gemini-2.0-flash",
      "gemini-2.0-flash-lite",
      "gemini-1.5-flash",
      "gemini-1.5-pro",
    ],
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
    needsKey: true,
    knownModels: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "o4-mini"],
  },
  anthropic: {
    label: "Anthropic Claude",
    defaultModel: "claude-3-5-haiku-latest",
    needsKey: true,
    knownModels: [
      "claude-3-5-haiku-latest",
      "claude-3-5-sonnet-latest",
      "claude-3-7-sonnet-latest",
    ],
  },
  openrouter: {
    label: "OpenRouter",
    defaultModel: "openrouter/auto",
    needsKey: true,
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    knownModels: [
      "openrouter/auto",
      "deepseek/deepseek-chat",
      "google/gemini-2.0-flash-001",
      "anthropic/claude-3.5-haiku",
      "meta-llama/llama-3.3-70b-instruct",
      "qwen/qwen-2.5-72b-instruct",
    ],
  },
  opencode: {
    label: "OpenCode Zen",
    defaultModel: "mimo-v2.5-free",
    needsKey: true,
    defaultBaseUrl: "https://opencode.ai/zen/v1",
    knownModels: [
      "mimo-v2.5-free",
      "deepseek-v4-flash-free",
      "nemotron-3-ultra-free",
      "north-mini-code-free",
      "big-pickle",
      "claude-haiku-4-5",
      "claude-sonnet-5",
      "gemini-3-flash",
      "gpt-5-nano",
      "gpt-5.1-codex-mini",
      "deepseek-v4-flash",
      "glm-5",
      "kimi-k2.5",
      "qwen3.5-plus",
    ],
    hint: "OpenAI-compatible. Free models end with -free (e.g. mimo-v2.5-free).",
  },
  custom: {
    label: "Custom (OpenAI-compatible)",
    defaultModel: "",
    needsKey: false,
    defaultBaseUrl: "http://localhost:8080/v1",
    knownModels: [],
    hint: "For OpenCode, Kilo Code, LM Studio, vLLM, or any OpenAI-compatible server.",
  },
  ollama: {
    label: "Local (Ollama)",
    defaultModel: "qwen2.5:3b",
    needsKey: false,
    defaultBaseUrl: "http://localhost:11434",
    knownModels: ["qwen2.5:3b", "llama3.2:3b", "phi3.5", "gemma2:2b"],
  },
};

const DEFAULT_TIMEOUT_MS = 90000;

async function request(url, { method = "POST", headers = {}, body, signal }) {
  const res = await fetch(url, {
    method,
    headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${detail}`.trim());
  }
  return res.json();
}

function baseUrlFor(provider, cfg) {
  return (cfg.baseUrl || PROVIDERS[provider].defaultBaseUrl || "").replace(
    /\/$/,
    "",
  );
}

/// Sends a chat completion to the configured provider and returns plain text.
///
/// `messages` is a list of `{ role: "system"|"user"|"assistant", content }`.
export async function chat(settings, messages) {
  const provider = settings.provider;
  const cfg = settings[provider] || {};
  const model = cfg.model || PROVIDERS[provider].defaultModel;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  try {
    switch (provider) {
      case "gemini":
        return await chatGemini(cfg.apiKey, model, messages, controller.signal);
      case "openai":
        return await chatOpenAiCompatible(
          "https://api.openai.com/v1/chat/completions",
          cfg.apiKey,
          model,
          messages,
          controller.signal,
        );
      case "openrouter":
        return await chatOpenAiCompatible(
          `${baseUrlFor("openrouter", cfg)}/chat/completions`,
          cfg.apiKey,
          model,
          messages,
          controller.signal,
          { "HTTP-Referer": "https://involvex.browser", "X-Title": "Involvex AI" },
        );
      case "opencode":
        return await chatOpenAiCompatible(
          `${baseUrlFor("opencode", cfg)}/chat/completions`,
          cfg.apiKey,
          model,
          messages,
          controller.signal,
        );
      case "custom":
        return await chatOpenAiCompatible(
          `${baseUrlFor("custom", cfg)}/chat/completions`,
          cfg.apiKey,
          model,
          messages,
          controller.signal,
        );
      case "anthropic":
        return await chatAnthropic(
          cfg.apiKey,
          model,
          messages,
          controller.signal,
        );
      case "ollama":
        return await chatOllama(
          baseUrlFor("ollama", cfg),
          model,
          messages,
          controller.signal,
        );
      default:
        throw new Error(`Unknown provider: ${provider}`);
    }
  } finally {
    clearTimeout(timer);
  }
}

/// Fetches the list of available model ids from the provider, when supported.
export async function listModels(settings) {
  const provider = settings.provider;
  const cfg = settings[provider] || {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    switch (provider) {
      case "gemini": {
        if (!cfg.apiKey) throw new Error("Set the Gemini API key first.");
        const data = await request(
          `https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(cfg.apiKey)}`,
          { method: "GET", signal: controller.signal },
        );
        return (data.models || [])
          .filter((m) =>
            (m.supportedGenerationMethods || []).includes("generateContent"),
          )
          .map((m) => m.name.replace(/^models\//, ""));
      }
      case "openai": {
        if (!cfg.apiKey) throw new Error("Set the OpenAI API key first.");
        const data = await request("https://api.openai.com/v1/models", {
          method: "GET",
          headers: { Authorization: `Bearer ${cfg.apiKey}` },
          signal: controller.signal,
        });
        return (data.data || []).map((m) => m.id).sort();
      }
      case "openrouter": {
        const data = await request(
          `${baseUrlFor("openrouter", cfg)}/models`,
          { method: "GET", signal: controller.signal },
        );
        return (data.data || []).map((m) => m.id).sort();
      }
      case "opencode": {
        const headers = cfg.apiKey
          ? { Authorization: `Bearer ${cfg.apiKey}` }
          : {};
        const data = await request(`${baseUrlFor("opencode", cfg)}/models`, {
          method: "GET",
          headers,
          signal: controller.signal,
        });
        return (data.data || []).map((m) => m.id);
      }
      case "custom": {
        const headers = cfg.apiKey
          ? { Authorization: `Bearer ${cfg.apiKey}` }
          : {};
        const data = await request(`${baseUrlFor("custom", cfg)}/models`, {
          method: "GET",
          headers,
          signal: controller.signal,
        });
        return (data.data || []).map((m) => m.id).sort();
      }
      case "ollama": {
        const data = await request(`${baseUrlFor("ollama", cfg)}/api/tags`, {
          method: "GET",
          signal: controller.signal,
        });
        return (data.models || []).map((m) => m.name).sort();
      }
      case "anthropic":
      default:
        return PROVIDERS[provider].knownModels.slice();
    }
  } finally {
    clearTimeout(timer);
  }
}

function splitSystem(messages) {
  const system = messages
    .filter((m) => m.role === "system")
    .map((m) => m.content)
    .join("\n\n");
  const rest = messages.filter((m) => m.role !== "system");
  return { system, rest };
}

async function chatGemini(apiKey, model, messages, signal) {
  if (!apiKey) throw new Error("Gemini API key not set (open Options).");
  const { system, rest } = splitSystem(messages);
  const contents = rest.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));
  const body = { contents };
  if (system) body.systemInstruction = { parts: [{ text: system }] };
  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/` +
    `${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const data = await request(url, { body, signal });
  const parts = data?.candidates?.[0]?.content?.parts || [];
  return parts.map((p) => p.text || "").join("").trim();
}

async function chatOpenAiCompatible(
  url,
  apiKey,
  model,
  messages,
  signal,
  extraHeaders = {},
) {
  const headers = { ...extraHeaders };
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  const body = { model, messages, temperature: 0.3 };
  const data = await request(url, { headers, body, signal });
  return (data?.choices?.[0]?.message?.content || "").trim();
}

async function chatAnthropic(apiKey, model, messages, signal) {
  if (!apiKey) throw new Error("Anthropic API key not set (open Options).");
  const { system, rest } = splitSystem(messages);
  const body = {
    model,
    max_tokens: 2048,
    messages: rest.map((m) => ({ role: m.role, content: m.content })),
  };
  if (system) body.system = system;
  const data = await request("https://api.anthropic.com/v1/messages", {
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body,
    signal,
  });
  const blocks = data?.content || [];
  return blocks.map((b) => (b.type === "text" ? b.text : "")).join("").trim();
}

async function chatOllama(base, model, messages, signal) {
  const body = { model, messages, stream: false };
  const data = await request(`${base}/api/chat`, { body, signal });
  return (data?.message?.content || "").trim();
}
