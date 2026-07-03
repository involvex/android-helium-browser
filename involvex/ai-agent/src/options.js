import { PROVIDERS, chat } from "./providers.js";

const providerSel = document.getElementById("provider");
const statusEl = document.getElementById("status");

const FIELDS = {
  gemini: ["apiKey", "model"],
  openai: ["apiKey", "model"],
  anthropic: ["apiKey", "model"],
  ollama: ["baseUrl", "model"],
};

function el(provider, field) {
  return document.getElementById(`${provider}-${field}`);
}

function showActiveCard() {
  const active = providerSel.value;
  document.querySelectorAll(".card").forEach((c) => {
    c.classList.toggle("active", c.dataset.provider === active);
  });
}

function collectSettings() {
  const settings = { provider: providerSel.value };
  for (const [provider, fields] of Object.entries(FIELDS)) {
    const cfg = {};
    for (const f of fields) {
      const v = el(provider, f).value.trim();
      if (v) cfg[f] = v;
    }
    settings[provider] = cfg;
  }
  return settings;
}

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = `status ${kind || ""}`;
}

async function load() {
  const { settings } = await chrome.storage.local.get("settings");
  const s = settings || { provider: "gemini" };
  providerSel.value = s.provider || "gemini";
  for (const [provider, fields] of Object.entries(FIELDS)) {
    const cfg = s[provider] || {};
    for (const f of fields) {
      el(provider, f).value = cfg[f] || "";
    }
    if (!(s[provider] && s[provider].model)) {
      el(provider, "model").placeholder = PROVIDERS[provider].defaultModel;
    }
  }
  if (!s.ollama || !s.ollama.baseUrl) {
    el("ollama", "baseUrl").placeholder = PROVIDERS.ollama.defaultBaseUrl;
  }
  showActiveCard();
}

async function save() {
  await chrome.storage.local.set({ settings: collectSettings() });
  setStatus("Saved.", "ok");
}

async function test() {
  setStatus("Testing…", "");
  try {
    const settings = collectSettings();
    const reply = await chat(settings, [
      { role: "user", content: "Reply with exactly: OK" },
    ]);
    if (reply) setStatus(`Connected. Model said: ${reply.slice(0, 40)}`, "ok");
    else setStatus("Connected but got an empty reply.", "err");
  } catch (e) {
    setStatus(`Failed: ${String((e && e.message) || e)}`, "err");
  }
}

providerSel.addEventListener("change", showActiveCard);
document.getElementById("save").addEventListener("click", save);
document.getElementById("test").addEventListener("click", async () => {
  await save();
  await test();
});

load();
