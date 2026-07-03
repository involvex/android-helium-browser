export const PROVIDERS = {
  gemini: {
    label: "Google Gemini",
    defaultModel: "gemini-2.0-flash",
    needsKey: true,
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
    needsKey: true,
  },
  anthropic: {
    label: "Anthropic Claude",
    defaultModel: "claude-3-5-haiku-latest",
    needsKey: true,
  },
  ollama: {
    label: "Local (Ollama)",
    defaultModel: "qwen2.5:3b",
    needsKey: false,
    defaultBaseUrl: "http://localhost:11434",
  },
};

const DEFAULT_TIMEOUT_MS = 90000;

async function postJson(url, headers, body, signal) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${detail}`.trim());
  }
  return res.json();
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
      case "anthropic":
        return await chatAnthropic(
          cfg.apiKey,
          model,
          messages,
          controller.signal,
        );
      case "ollama": {
        const base = (cfg.baseUrl || PROVIDERS.ollama.defaultBaseUrl).replace(
          /\/$/,
          "",
        );
        return await chatOllama(base, model, messages, controller.signal);
      }
      default:
        throw new Error(`Unknown provider: ${provider}`);
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
  const data = await postJson(url, {}, body, signal);
  const parts = data?.candidates?.[0]?.content?.parts || [];
  return parts.map((p) => p.text || "").join("").trim();
}

async function chatOpenAiCompatible(url, apiKey, model, messages, signal) {
  if (!apiKey) throw new Error("OpenAI API key not set (open Options).");
  const body = { model, messages, temperature: 0.3 };
  const data = await postJson(
    url,
    { Authorization: `Bearer ${apiKey}` },
    body,
    signal,
  );
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
  const data = await postJson(
    "https://api.anthropic.com/v1/messages",
    {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body,
    signal,
  );
  const blocks = data?.content || [];
  return blocks
    .map((b) => (b.type === "text" ? b.text : ""))
    .join("")
    .trim();
}

async function chatOllama(base, model, messages, signal) {
  const body = { model, messages, stream: false };
  const data = await postJson(`${base}/api/chat`, {}, body, signal);
  return (data?.message?.content || "").trim();
}
