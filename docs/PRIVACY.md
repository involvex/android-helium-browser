# Privacy Configuration

Involvex Browser inherits GrapheneOS Vanadium hardening plus Involvex-specific
DNS defaults.

## Active Vanadium privacy patches (verified in tree)

| Patch | Feature |
|-------|---------|
| `0199-enable-subresource-filter-on-all-sites` | Built-in ad/tracker blocking (SRF) on all sites |
| `0118-Make-HTTPS-only-mode-the-default` | HTTPS-Only mode default on |
| `0124` / client hints patches | Reduced fingerprinting surface |
| `0097-Disable-newer-privacy-sandbox-features` | Privacy Sandbox off by default |
| `0072-disable-metrics-by-default` | Metrics disabled |
| `0087` / Safe Browsing patches | Safe Browsing no-op without Play Services |
| `0065` / `0066` | Field trials / variations fetching disabled |
| `0102` | WebRTC IP handling — most private default |
| `0207`–`0211` | OS connectivity-check respected for DoH/probes |
| `0116-set-default-search-engine-to-DuckDuckGo` | Default search: DuckDuckGo |

## Involvex additions

| Change | Location |
|--------|----------|
| Remove Google Public DNS from DoH list | `involvex/patches/0282-default-cloudflare-doh-remove-google-dns.patch` |
| DoH probe host → `cloudflare-dns.com` | Same patch |
| Prefer secure DNS mode | `patch.sh` sed on `default_dns_over_https_config_source.cc` |

> Involvex patches live in `involvex/patches/` (parent-tracked) and are copied into
> `vanadium/patches/` by `build.sh` / `scripts/build-debug-wsl2.sh` before `git am`.
> This ensures they survive the `vanadium` submodule checkout in CI.

### User: enable Cloudflare DoH

Settings → Privacy and security → Use secure DNS → **Cloudflare** or custom:
`https://cloudflare-dns.com/dns-query`

### Ad blocking layers

1. **Engine:** Subresource Filter (always on)
2. **Extension:** Install uBlock Origin (MV2) from Chrome Web Store (Desktop site mode)

## Paused Helium (ungoogled) patches — GPLv2 blocker

242 patches under [`helium/patches/`](../helium/patches/) are **not applied** in
current builds due to licensing conflict between Vanadium and ungoogled-chromium.

### High-value patches to enable when legal path exists

| Patch | Benefit |
|-------|---------|
| `disable-gaia.patch` | Remove Google account integration |
| `disable-gcm.patch` | Remove Google Cloud Messaging |
| `block-trk-and-subdomains.patch` | Block `trk.*` tracking domains |
| `doh-changes.patch` | Further DoH hardening (sets off by default — merge carefully with 0282) |
| `ublock-install-as-component.patch` | Bundle uBO as component |

### Tracking status

Monitor upstream [android-helium-browser](https://github.com/jqssun/android-helium-browser)
and [Vanadium](https://github.com/GrapheneOS/Vanadium) for GPLv2 resolution before
enabling the Helium patch series via `helium/patches/series`.

## Custom search engines

Users can add engines in Settings → Search engine. To change the **default** at
build time, modify or replace `0116-set-default-search-engine-to-DuckDuckGo.patch`.

## Strict tracking protection checklist

- [x] SRF on all sites
- [x] Third-party cookies default off (`0079`)
- [x] DNT / reduced client hints
- [x] Privacy Sandbox disabled
- [x] Google DNS removed from DoH picker
- [ ] Helium `block-trk` (blocked on license)
- [ ] Custom referrer policy patches (Helium, blocked)
