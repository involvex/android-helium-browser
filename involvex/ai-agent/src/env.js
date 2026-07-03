let cached = null;

/// Loads an optional `.env` bundled with the (unpacked) extension.
///
/// Extension pages can fetch their own packaged files, so a `.env` pushed
/// alongside the extension is readable here. Missing file is not an error.
/// Format: `KEY=VALUE` per line, `#` comments and blank lines ignored.
export async function loadEnv() {
  if (cached) return cached;
  const out = {};
  try {
    const res = await fetch(chrome.runtime.getURL(".env"));
    if (res.ok) {
      const text = await res.text();
      for (const line of text.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const eq = trimmed.indexOf("=");
        if (eq === -1) continue;
        const key = trimmed.slice(0, eq).trim();
        let val = trimmed.slice(eq + 1).trim();
        if (
          (val.startsWith('"') && val.endsWith('"')) ||
          (val.startsWith("'") && val.endsWith("'"))
        ) {
          val = val.slice(1, -1);
        }
        if (key) out[key] = val;
      }
    }
  } catch (_) {
    // no .env present — that's fine
  }
  cached = out;
  return out;
}

/// GitHub token from any of the common key names.
export function envGistToken(env) {
  return env.GITHUB_TOKEN || env.GIST_TOKEN || env.GH_TOKEN || "";
}

export function envGistId(env) {
  return env.GIST_ID || env.GIST || "";
}
