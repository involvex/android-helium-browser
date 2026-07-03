const GIST_API = "https://api.github.com";
const BACKUP_FILE = "involvex-browser-backup.json";
const SECRET_KEYS = ["apiKey", "token", "gistToken"];

async function gh(path, token, { method = "GET", body } = {}) {
  const res = await fetch(`${GIST_API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`GitHub ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json();
}

/// Removes API keys / tokens so secrets never leave the device in a backup.
function stripSecrets(obj) {
  if (Array.isArray(obj)) return obj.map(stripSecrets);
  if (obj && typeof obj === "object") {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (SECRET_KEYS.includes(k)) continue;
      out[k] = stripSecrets(v);
    }
    return out;
  }
  return obj;
}

async function collectExtensions() {
  try {
    if (!chrome.management?.getAll) return null;
    const all = await chrome.management.getAll();
    return all
      .filter((e) => e.type === "extension" && e.id !== chrome.runtime.id)
      .map((e) => ({
        id: e.id,
        name: e.name,
        version: e.version,
        enabled: e.enabled,
        homepageUrl: e.homepageUrl || "",
        updateUrl: e.updateUrl || "",
      }));
  } catch (_) {
    return null;
  }
}

/// Builds the backup payload: bookmarks, non-secret settings, extension list.
export async function buildBackup() {
  const bookmarks = await chrome.bookmarks.getTree();
  const store = await chrome.storage.local.get(null);
  const settings = stripSecrets(store.settings || {});
  const extensions = await collectExtensions();
  return {
    schema: "involvex-backup/1",
    createdAt: new Date().toISOString(),
    bookmarks,
    settings,
    extensions,
  };
}

export async function pushBackup(token, gistId) {
  const payload = await buildBackup();
  const files = { [BACKUP_FILE]: { content: JSON.stringify(payload, null, 2) } };
  if (gistId) {
    const data = await gh(`/gists/${gistId}`, token, {
      method: "PATCH",
      body: { files },
    });
    return { gistId: data.id, updatedAt: payload.createdAt };
  }
  const data = await gh(`/gists`, token, {
    method: "POST",
    body: {
      description: "Involvex Browser backup (bookmarks + settings)",
      public: false,
      files,
    },
  });
  return { gistId: data.id, updatedAt: payload.createdAt };
}

export async function fetchBackup(token, gistId) {
  if (!gistId) throw new Error("No Gist id configured.");
  const data = await gh(`/gists/${gistId}`, token);
  const file = data.files?.[BACKUP_FILE];
  if (!file) throw new Error("Backup file not found in that Gist.");
  const content = file.truncated
    ? await (await fetch(file.raw_url)).text()
    : file.content;
  return JSON.parse(content);
}

function flattenBookmarks(nodes, acc = []) {
  for (const n of nodes) {
    if (n.url) acc.push({ title: n.title || n.url, url: n.url });
    if (n.children) flattenBookmarks(n.children, acc);
  }
  return acc;
}

/// Restores bookmarks into a dedicated folder (never clobbers existing ones)
/// and merges non-secret settings.
export async function restoreBackup(backup) {
  let bookmarksAdded = 0;
  if (backup.bookmarks) {
    const flat = flattenBookmarks(backup.bookmarks);
    const folder = await chrome.bookmarks.create({
      title: `Involvex Restore ${new Date().toISOString().slice(0, 10)}`,
    });
    for (const b of flat) {
      try {
        await chrome.bookmarks.create({
          parentId: folder.id,
          title: b.title,
          url: b.url,
        });
        bookmarksAdded++;
      } catch (_) {
        // skip invalid urls
      }
    }
  }
  if (backup.settings) {
    const { settings: current } = await chrome.storage.local.get("settings");
    const merged = { ...(backup.settings || {}) };
    // Keep existing secrets on this device.
    for (const [provider, cfg] of Object.entries(current || {})) {
      if (cfg && typeof cfg === "object") {
        merged[provider] = { ...(merged[provider] || {}) };
        for (const key of SECRET_KEYS) {
          if (cfg[key]) merged[provider][key] = cfg[key];
        }
      }
    }
    merged.provider = (current && current.provider) || merged.provider;
    await chrome.storage.local.set({ settings: merged });
  }
  return {
    bookmarksAdded,
    extensions: backup.extensions ? backup.extensions.length : 0,
  };
}
