import { chat } from "./providers.js";

const MAX_PAGE_CHARS = 12000;
const MAX_AGENT_STEPS = 8;

// ---- Functions injected into the page (must be self-contained) ----

function pageExtract(maxChars) {
  const clip = (s) => (s || "").replace(/\s+/g, " ").trim();
  const main =
    document.querySelector("main, article, [role=main]") || document.body;
  const text = clip(main.innerText).slice(0, maxChars);
  const interactives = [];
  const nodes = document.querySelectorAll(
    "a[href], button, input, textarea, select, [role=button]",
  );
  let i = 0;
  for (const el of nodes) {
    if (i >= 40) break;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    const label = clip(
      el.innerText ||
        el.value ||
        el.getAttribute("aria-label") ||
        el.getAttribute("placeholder") ||
        el.name ||
        "",
    );
    interactives.push({
      i,
      tag: el.tagName.toLowerCase(),
      type: el.type || "",
      label: label.slice(0, 80),
    });
    el.setAttribute("data-involvex-idx", String(i));
    i++;
  }
  return { title: document.title, url: location.href, text, interactives };
}

function pageGetSelection() {
  return { text: String(window.getSelection()) };
}

function pageClick(args) {
  let el = null;
  if (args.index != null)
    el = document.querySelector(`[data-involvex-idx="${args.index}"]`);
  if (!el && args.selector) el = document.querySelector(args.selector);
  if (!el && args.text) {
    const t = String(args.text).toLowerCase();
    const cands = document.querySelectorAll(
      "a,button,[role=button],input[type=submit],input[type=button]",
    );
    for (const c of cands) {
      if ((c.innerText || c.value || "").toLowerCase().includes(t)) {
        el = c;
        break;
      }
    }
  }
  if (!el) return { ok: false, error: "element not found" };
  el.scrollIntoView({ block: "center" });
  el.click();
  return { ok: true };
}

function pageFill(args) {
  let el = null;
  if (args.index != null)
    el = document.querySelector(`[data-involvex-idx="${args.index}"]`);
  if (!el && args.selector) el = document.querySelector(args.selector);
  if (!el) return { ok: false, error: "input not found" };
  el.focus();
  el.value = args.value != null ? args.value : "";
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true };
}

function pageScroll(args) {
  const amount = args.amount || window.innerHeight * 0.8;
  window.scrollBy({
    top: args.direction === "up" ? -amount : amount,
    behavior: "smooth",
  });
  return { ok: true, scrollY: window.scrollY };
}

// ---- Orchestration ----

async function loadSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return settings || { provider: "gemini" };
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({
    active: true,
    lastFocusedWindow: true,
  });
  return tab;
}

async function runInPage(tabId, func, args = []) {
  const [res] = await chrome.scripting.executeScript({
    target: { tabId },
    func,
    args,
  });
  return res?.result;
}

async function execTool(tab, action, args) {
  switch (action) {
    case "read_page":
      return await runInPage(tab.id, pageExtract, [MAX_PAGE_CHARS]);
    case "get_selection":
      return await runInPage(tab.id, pageGetSelection, []);
    case "click":
      return await runInPage(tab.id, pageClick, [args]);
    case "fill":
      return await runInPage(tab.id, pageFill, [args]);
    case "scroll":
      return await runInPage(tab.id, pageScroll, [args]);
    case "navigate":
      if (!/^https?:\/\//i.test(args.url || ""))
        return { ok: false, error: "only http(s) urls allowed" };
      await chrome.tabs.update(tab.id, { url: args.url });
      return { ok: true, navigatedTo: args.url };
    default:
      return { ok: false, error: `unknown tool ${action}` };
  }
}

function parseAction(raw) {
  let jsonStr = null;
  const fence = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) jsonStr = fence[1];
  else {
    const brace = raw.match(/\{[\s\S]*\}/);
    if (brace) jsonStr = brace[0];
  }
  if (!jsonStr) return null;
  try {
    const obj = JSON.parse(jsonStr.trim());
    if (obj && typeof obj.action === "string") return obj;
  } catch (_) {
    // not a tool call; treat as prose
  }
  return null;
}

async function runAsk(port, userText, history) {
  const settings = await loadSettings();
  const tab = await getActiveTab();
  let page = null;
  try {
    if (tab) page = await runInPage(tab.id, pageExtract, [MAX_PAGE_CHARS]);
  } catch (_) {
    // restricted page (chrome://, store, etc.) — continue without context
  }
  const ctx = page
    ? `PAGE TITLE: ${page.title}\nURL: ${page.url}\n\nPAGE CONTENT:\n${page.text}`
    : "(No page content is available for the current tab.)";
  const system =
    `You are Involvex AI, a helpful assistant embedded in a web browser. ` +
    `You can see the content of the user's current page below. Use it when ` +
    `relevant, cite specifics, and answer in concise markdown.\n\n${ctx}`;
  const messages = [
    { role: "system", content: system },
    ...history,
    { role: "user", content: userText },
  ];
  port.postMessage({ event: "status", text: "Thinking…" });
  const answer = await chat(settings, messages);
  port.postMessage({ event: "assistant", text: answer });
  port.postMessage({ event: "done" });
}

async function runAgent(port, userText, history) {
  const settings = await loadSettings();
  const tab = await getActiveTab();
  if (!tab) throw new Error("No active tab to act on.");
  const toolDoc =
    `You can control the current browser page with tools. To use a tool, ` +
    `reply with ONLY one fenced json block:\n` +
    "```json\n" +
    `{"thought":"why","action":"<name>","args":{...}}\n` +
    "```\n" +
    `Tools:\n` +
    `- read_page {} -> page title, url, text, and up to 40 interactive elements each with an index "i".\n` +
    `- get_selection {} -> currently selected text.\n` +
    `- click {"index":n} | {"selector":"css"} | {"text":"visible text"} -> click an element.\n` +
    `- fill {"index":n|"selector":"css","value":"text"} -> fill an input.\n` +
    `- navigate {"url":"https://..."} -> load a URL in the current tab.\n` +
    `- scroll {"direction":"down"|"up"} -> scroll the page.\n` +
    `- finish {"answer":"final markdown answer"} -> end the task.\n` +
    `Rules: exactly one tool per reply. read_page before acting if you have ` +
    `not seen the page. Prefer element index from read_page. When done or no ` +
    `action is needed, use finish.`;
  const system = `You are Involvex AI Agent, operating inside a web browser on behalf of the user. ${toolDoc}`;
  const convo = [
    { role: "system", content: system },
    ...history,
    { role: "user", content: userText },
  ];

  for (let step = 0; step < MAX_AGENT_STEPS; step++) {
    port.postMessage({ event: "status", text: `Planning (step ${step + 1})…` });
    const raw = await chat(settings, convo);
    const parsed = parseAction(raw);
    if (!parsed) {
      port.postMessage({ event: "assistant", text: raw });
      port.postMessage({ event: "done" });
      return;
    }
    convo.push({ role: "assistant", content: raw });
    if (parsed.action === "finish") {
      port.postMessage({
        event: "assistant",
        text: parsed.args?.answer || "Done.",
      });
      port.postMessage({ event: "done" });
      return;
    }
    port.postMessage({
      event: "step",
      action: parsed.action,
      args: parsed.args || {},
      thought: parsed.thought || "",
    });
    let result;
    try {
      result = await execTool(tab, parsed.action, parsed.args || {});
    } catch (e) {
      result = { ok: false, error: String((e && e.message) || e) };
    }
    convo.push({
      role: "user",
      content: `TOOL RESULT (${parsed.action}):\n${JSON.stringify(result).slice(0, 8000)}`,
    });
  }
  port.postMessage({
    event: "assistant",
    text: "Stopped after the step limit. Ask me to continue if needed.",
  });
  port.postMessage({ event: "done" });
}

// ---- Wiring ----

function enablePanelOnActionClick() {
  chrome.sidePanel
    ?.setPanelBehavior({ openPanelOnActionClick: true })
    .catch(() => {});
}

chrome.runtime.onInstalled.addListener(() => {
  enablePanelOnActionClick();
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "involvex-summarize-page",
      title: "Involvex AI: Summarize page",
      contexts: ["page"],
    });
    chrome.contextMenus.create({
      id: "involvex-explain",
      title: "Involvex AI: Explain selection",
      contexts: ["selection"],
    });
    chrome.contextMenus.create({
      id: "involvex-translate",
      title: "Involvex AI: Translate selection",
      contexts: ["selection"],
    });
    chrome.contextMenus.create({
      id: "involvex-rewrite",
      title: "Involvex AI: Rewrite selection",
      contexts: ["selection"],
    });
  });
});

chrome.runtime.onStartup?.addListener(enablePanelOnActionClick);

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const sel = info.selectionText || "";
  let prompt = "";
  switch (info.menuItemId) {
    case "involvex-summarize-page":
      prompt = "Summarize the current page as a few concise bullet points.";
      break;
    case "involvex-explain":
      prompt = `Explain this clearly:\n\n"""${sel}"""`;
      break;
    case "involvex-translate":
      prompt = `Translate this. If it is already English, translate to German; otherwise translate to English:\n\n"""${sel}"""`;
      break;
    case "involvex-rewrite":
      prompt = `Rewrite this to be clearer and more concise, keeping the meaning:\n\n"""${sel}"""`;
      break;
    default:
      return;
  }
  await chrome.storage.local.set({ pendingPrompt: prompt });
  try {
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch (_) {
    // side panel open may be unavailable on some pages
  }
});

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "agent") return;
  port.onMessage.addListener(async (msg) => {
    try {
      if (msg.type === "chat") {
        if (msg.mode === "agent") {
          await runAgent(port, msg.text, msg.history || []);
        } else {
          await runAsk(port, msg.text, msg.history || []);
        }
      }
    } catch (e) {
      port.postMessage({ event: "error", text: String((e && e.message) || e) });
    }
  });
});
