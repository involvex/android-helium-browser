import { PROVIDERS } from "./providers.js";

const messagesEl = document.getElementById("messages");
const emptyEl = document.getElementById("empty");
const inputEl = document.getElementById("input");
const formEl = document.getElementById("composer");
const sendBtn = document.getElementById("send");
const agentToggle = document.getElementById("agentToggle");
const settingsBtn = document.getElementById("settingsBtn");
const exportBtn = document.getElementById("exportBtn");
const newBtn = document.getElementById("newBtn");
const providerLine = document.getElementById("providerLine");
const modelSelect = document.getElementById("modelSelect");

const history = [];
let busy = false;
let statusEl = null;
let targetTabId = null;

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/// Renders a small, safe subset of markdown to HTML.
function renderMarkdown(src) {
  const blocks = src.split(/```/);
  let html = "";
  blocks.forEach((block, idx) => {
    if (idx % 2 === 1) {
      const nl = block.indexOf("\n");
      const code = nl >= 0 ? block.slice(nl + 1) : block;
      html += `<pre><code>${escapeHtml(code)}</code></pre>`;
      return;
    }
    let t = escapeHtml(block);
    t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
    t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    t = t.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    t = t.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>',
    );
    const lines = t.split("\n");
    let out = "";
    let inList = false;
    for (const line of lines) {
      const li = line.match(/^\s*[-*]\s+(.*)$/);
      if (li) {
        if (!inList) {
          out += "<ul>";
          inList = true;
        }
        out += `<li>${li[1]}</li>`;
      } else {
        if (inList) {
          out += "</ul>";
          inList = false;
        }
        if (line.trim()) out += `<p>${line}</p>`;
      }
    }
    if (inList) out += "</ul>";
    html += out;
  });
  return html;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addMessage(role, text, kind) {
  if (emptyEl && emptyEl.parentNode) emptyEl.remove();
  const el = document.createElement("div");
  el.className = `msg ${kind || role}`;
  if (role === "assistant" && kind !== "step" && kind !== "error") {
    el.innerHTML = renderMarkdown(text);
  } else {
    el.textContent = text;
  }
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function setStatus(text) {
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.className = "msg status";
    messagesEl.appendChild(statusEl);
  }
  statusEl.innerHTML = `<span class="blink">${escapeHtml(text)}</span>`;
  scrollToBottom();
}

function clearStatus() {
  if (statusEl) {
    statusEl.remove();
    statusEl = null;
  }
}

function setBusy(v) {
  busy = v;
  sendBtn.disabled = v;
  inputEl.disabled = v;
}

function send(text) {
  if (busy || !text.trim()) return;
  const mode = agentToggle.checked ? "agent" : "ask";
  addMessage("user", text);
  history.push({ role: "user", content: text });
  setBusy(true);
  setStatus("Connecting…");

  const port = chrome.runtime.connect({ name: "agent" });
  port.onMessage.addListener((m) => {
    if (m.event === "status") {
      setStatus(m.text);
    } else if (m.event === "step") {
      clearStatus();
      const args =
        m.args && Object.keys(m.args).length
          ? " " + JSON.stringify(m.args)
          : "";
      addMessage("assistant", `▸ ${m.action}${args}`, "step");
      if (m.thought) setStatus(m.thought);
    } else if (m.event === "assistant") {
      clearStatus();
      addMessage("assistant", m.text);
      history.push({ role: "assistant", content: m.text });
    } else if (m.event === "error") {
      clearStatus();
      addMessage("assistant", `Error: ${m.text}`, "error");
    } else if (m.event === "done") {
      clearStatus();
      setBusy(false);
      port.disconnect();
    }
  });
  port.onDisconnect.addListener(() => {
    clearStatus();
    setBusy(false);
  });
  port.postMessage({
    type: "chat",
    text,
    mode,
    tabId: targetTabId,
    history: history.slice(0, -1),
  });
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value;
  inputEl.value = "";
  inputEl.style.height = "auto";
  send(text);
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + "px";
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    formEl.requestSubmit();
  }
});

document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) send(chip.dataset.prompt);
});

settingsBtn.addEventListener("click", () => chrome.runtime.openOptionsPage());

/// Serializes the current session to Markdown and triggers a download.
function exportMarkdown() {
  if (!history.length) {
    addMessage("assistant", "Nothing to export yet — start a chat first.", "error");
    return;
  }
  const now = new Date();
  const lines = [
    `# Involvex AI — session`,
    "",
    `- Date: ${now.toLocaleString()}`,
    `- Provider/model: ${providerLine.textContent} · ${modelSelect.value}`,
    `- Mode: ${agentToggle.checked ? "Agent" : "Ask"}`,
    "",
    "---",
    "",
  ];
  for (const m of history) {
    const who = m.role === "user" ? "You" : "Assistant";
    lines.push(`## ${who}`, "", m.content, "");
  }
  const blob = new Blob([lines.join("\n")], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `involvex-ai-${now.toISOString().slice(0, 19).replace(/[:T]/g, "-")}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function newChat() {
  history.length = 0;
  messagesEl.innerHTML = "";
  const div = document.createElement("div");
  div.className = "empty";
  div.innerHTML =
    '<p class="empty-title">New chat</p>' +
    '<p class="empty-sub">Ask about this page, or turn on Agent mode to let me act on it.</p>';
  messagesEl.appendChild(div);
}

exportBtn.addEventListener("click", exportMarkdown);
newBtn.addEventListener("click", newChat);

agentToggle.addEventListener("change", () => {
  chrome.storage.local.set({ agentMode: agentToggle.checked });
});

// Quick model switch from the header, persisted to the active provider config.
modelSelect.addEventListener("change", async () => {
  const { settings } = await chrome.storage.local.get("settings");
  const s = settings || { provider: "gemini" };
  const p = s.provider;
  s[p] = { ...(s[p] || {}), model: modelSelect.value };
  await chrome.storage.local.set({ settings: s });
});

async function refreshHeader() {
  const { settings } = await chrome.storage.local.get("settings");
  const s = settings || { provider: "gemini" };
  const info = PROVIDERS[s.provider];
  const cfg = s[s.provider] || {};
  const currentModel = cfg.model || info?.defaultModel || "";

  const models = (cfg.models && cfg.models.length
    ? cfg.models
    : info?.knownModels || []
  ).slice();
  if (currentModel && !models.includes(currentModel)) models.unshift(currentModel);
  modelSelect.innerHTML = "";
  if (models.length === 0) {
    const opt = document.createElement("option");
    opt.textContent = currentModel || "(set model in Settings)";
    opt.value = currentModel;
    modelSelect.appendChild(opt);
  } else {
    for (const m of models) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m;
      if (m === currentModel) opt.selected = true;
      modelSelect.appendChild(opt);
    }
  }

  const missingKey = info?.needsKey && !cfg.apiKey;
  if (missingKey) {
    providerLine.textContent = `⚠ ${info.label}: no API key set — tap to open Settings`;
    providerLine.classList.add("warn");
    providerLine.onclick = () => chrome.runtime.openOptionsPage();
  } else {
    providerLine.textContent = `${info?.label || s.provider}`;
    providerLine.classList.remove("warn");
    providerLine.onclick = null;
  }
}

async function init() {
  const { agentMode, pendingPrompt, targetTabId: tid } =
    await chrome.storage.local.get(["agentMode", "pendingPrompt", "targetTabId"]);
  targetTabId = tid ?? null;
  agentToggle.checked = !!agentMode;
  await refreshHeader();
  if (pendingPrompt) {
    await chrome.storage.local.remove("pendingPrompt");
    send(pendingPrompt);
  }
  inputEl.focus();
}

// When the action is tapped again while the panel tab is already open, the
// background updates targetTabId and pings us to re-read it.
chrome.runtime.onMessage.addListener(async (msg) => {
  if (msg && msg.event === "panel-refocus") {
    const { pendingPrompt, targetTabId: tid } = await chrome.storage.local.get([
      "pendingPrompt",
      "targetTabId",
    ]);
    if (tid != null) targetTabId = tid;
    if (pendingPrompt) {
      await chrome.storage.local.remove("pendingPrompt");
      send(pendingPrompt);
    }
  }
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.settings) refreshHeader();
});

init();
