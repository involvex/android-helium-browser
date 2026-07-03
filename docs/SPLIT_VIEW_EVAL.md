# Split Tab View — Evaluation

## Current status: **Not enabled** in Involvex/Helium Android builds

Split view exists in **paused** Helium patches, not in applied Vanadium patches.

## Source: `helium/patches/helium/core/split-view.patch`

Listed in [`helium/patches/series`](../helium/patches/series) line 149 — **not applied**
because the full Helium patch series (242 patches) is paused (GPLv2 vs Vanadium).

### What the patch enables

| Change | Effect |
|--------|--------|
| `kSideBySide` → `FEATURE_ENABLED_BY_DEFAULT` | Side-by-side tabs UI |
| `kSideBySideSessionRestore` enabled | Restore split layout on restart |
| Resize handle dimensions | Mobile-friendly splitter |
| `kSplitViewContentInset = 0` | Full-width split panes |
| Android/Java UI changes | Tab drag-drop split targets |

### Platform caveat

Upstream `kSideBySide` targets **desktop** `MultiContentsView` (views/ framework).
Android tab UI differs — the patch may require additional Android-specific glue
not fully covered in the Helium patch file (631 lines, mostly desktop C++).

## Options (ordered by effort)

### Option A — Wait for GPLv2 resolution (recommended)

Apply full `helium/patches/series` when upstream unblocks Helium layer.
Includes `split-view.patch` plus dependent UI patches.

**Effort:** Low (merge upstream) once legal path exists  
**Risk:** Medium — Android split UX may still need polish

### Option B — Cherry-pick upstream Chromium side-by-side flags only

Check M150 `chrome/browser/ui/ui_features.cc` for `kSideBySide` on Android:

```bash
cd chromium/src
git grep -n SideBySide chrome/browser/ui/android/
```

Enable via `chrome://flags` if upstream exposes Android split tabs.

**Effort:** 1–3 days investigation  
**Risk:** Feature may not exist on Android in M150

### Option C — Port Involvex Compose split-view (not recommended)

[`Involvex-Browser`](E:\repos\Involvex-Browser) implements split view in Compose around
**System WebView** — not compatible with Chromium's native tab model.

**Effort:** High rewrite inside Chromium Java UI  
**Risk:** Diverges from upstream; hard to maintain

## Recommendation

1. **Short term:** Document split view as roadmap item; users can use multi-window Android
2. **Medium term:** Track Helium GPLv2 issue; apply `split-view.patch` with Android QA
3. **Do not** port WebView split UI into Chromium fork

## Test plan (when enabled)

- [ ] Drag tab to split edge — second pane opens
- [ ] Resize divider between panes
- [ ] Close one pane — other survives
- [ ] Session restore after kill
- [ ] Extension popups in split context
- [ ] DevTools docked per pane (if supported)

## Related files

- [`helium/patches/helium/core/split-view.patch`](../helium/patches/helium/core/split-view.patch)
- [`helium/patches/series`](../helium/patches/series)
- [`README.md`](../README.md) — Helium patches paused notice
