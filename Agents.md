# Helium Browser for Android - Agent Instructions

This document provides instructions and guidelines for AI agents working with the Helium Browser for Android codebase.

## Project Overview

Helium Browser is an experimental, fully open-source Chromium-based web browser for Android with extensions support. It is based on:
- [Vanadium](https://github.com/GrapheneOS/Vanadium) by GrapheneOS
- [Helium](https://github.com/imputnet/helium) by imputnet

**Key Technologies:**
- **Language:** C++, Java, Kotlin, Python, JavaScript
- **Build System:** GN (Generate Ninja), Ninja, depot_tools
- **Platform:** Android (arm, arm64)
- **Source:** Chromium base with privacy/security patches

---

## Directory Structure

```
android-helium-browser/
├── .github/                  # GitHub workflows and issue templates
│   └── workflows/
│       └── build.yml         # CI/CD build workflow
├── helium/                   # Helium-specific utilities and patches
│   ├── devutils/            # Development utilities (linting, testing, validation)
│   ├── utils/               # Core utilities (patching, domain substitution, etc.)
│   └── resources/           # Helium resources (branding, generate_resources.txt)
├── vanadium/                # Vanadium patches and configuration
│   ├── patches/             # All Vanadium patches (0001-0101+)
│   └── args.gn             # Vanadium-specific GN build arguments
├── chromium/               # Chromium source tree (after sync)
│   └── src/                # Main Chromium source
├── args.gn                 # Main GN build arguments
├── build.sh                # Main build script
├── patch.sh                # Additional patching script
└── common.sh               # Shared build functions (signing, replace, etc.)
```

---

## Build System Overview

### GN Configuration

The project uses GN (Generate Ninja) for build configuration. Key files:
- `args.gn` - Main build arguments for Helium
- `vanadium/args.gn` - Vanadium build arguments (defines version, branding)

### Build Process

1. **Clone Chromium** via `depot_tools` (handled by `build.sh`)
2. **Apply Vanadium patches** via `git am`
3. **Apply Helium substitutions** (name replacement, resource generation)
4. **Apply custom patches** via `patch.sh`
5. **Generate build files** with `gn gen`
6. **Build APKs** with `autoninja`
7. **Sign APKs** using apksigner/jarsigner

---

## Useful Commands

### Building

#### Windows (WSL2)

See [docs/BUILD-WSL2.md](docs/BUILD-WSL2.md) for the full WSL2 setup guide.

```bash
bash scripts/setup-wsl2.sh
bash scripts/build-debug-wsl2.sh
```

#### Linux

```bash
# Full build (requires secrets setup)
./build.sh

# Apply patches only
./patch.sh

# Generate GN build files
gn gen out/Default

# Build specific target
autoninja -C out/Default chrome_public_apk

# Build for different architectures
# Edit args.gn: target_cpu = "arm" or "arm64"

# Sign APK
apksigner sign -verbose -ks keys/test.jks --ks-pass pass:$password --out output.apk input.apk

# Verify APK signature
apksigner verify -verbose input.apk
```

### Development Utilities

```bash
# Run linting checks
./helium/devutils/check_all_code.sh

# Run code formatting (YAPF)
./helium/devutils/run_devutils_yapf.sh
./helium/devutils/run_utils_yapf.sh
./helium/devutils/run_other_yapf.sh

# Run tests
./helium/devutils/run_devutils_tests.sh
./helium/devutils/run_utils_tests.sh

# Validate patches
python3 helium/devutils/validate_patches.py
python3 helium/devutils/validate_config.py

# Check patch files
python3 helium/devutils/check_patch_files.py
```

### Patch Management

```bash
# Apply quilt-format patches
python3 -m helium.utils.patches apply <target_dir> <patches_dir>

# Generate patches list from series
python3 -m helium.utils.patches generate_patches_from_series <patches_dir>

# Name substitution (Chrome -> Helium)
python3 helium/utils/name_substitution.py --sub -t <tree_path>

# Domain substitution
python3 helium/utils/domain_substitution.py
```

### GitHub Actions

```bash
# Verify build attestations
gh attestation verify *.apk -R jqssun/android-helium-browser
```

---

## Technologies

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Browser Engine | Chromium | Web rendering, JavaScript engine (V8) |
| Build System | GN + Ninja | Fast, scalable builds |
| Source Management | depot_tools | Chromium's build tool suite |
| Android Integration | Java/Kotlin | Android-specific features |
| Patching | Python + shell scripts | Custom modifications |
| CI/CD | GitHub Actions | Automated builds/releases |

### Key Libraries & Tools

- **depot_tools**: `gclient`, `gn`, `ninja`, `git cl`
- **Android SDK**: Build tools, platform tools, apksigner
- **Python 3**: Build automation, patching scripts
- **ImageMagick**: Icon processing
- **JDK**: Java compilation (current: `third_party/jdk/current/bin/`)

### Build Dependencies (Ubuntu)

```bash
sudo apt-get install -y sudo lsb-release file nano git curl python3 python3-pillow imagemagick
# Plus Android SDK and depot_tools
```

---

## Best Practices & Guidelines

### General Development

1. **Always read existing code** before making changes
2. **Follow the existing code style** ( Chromium style guides)
3. **Test changes thoroughly** - especially for Android-specific modifications
4. **Keep patches focused** - one logical change per patch
5. **Use descriptive patch names** following the Vanadium convention (`XXXX-description.patch`)

### Patch Management

1. **Vanadium patches are upstream** - do not modify unless necessary
2. **Patch order matters** - follow the series file order
3. **Test patches with `--dry-run`** before applying
4. **Use quilt format** for new patches (unified diff with series file)
5. **Keep patches reversible** when possible

### Build Configuration

1. **Never commit secrets** - use environment variables or GitHub secrets
2. **Use `is_debug = false` and `is_official_build = true`** for release builds
3. **Match Vanadium version** when syncing new Chromium releases
4. **Disable metrics and reporting** in default builds

### Code Changes

1. **String replacements**: Use the provided substitution utilities
2. **Resource modifications**: Follow Chromium's resource handling conventions
3. **Feature flags**: Use `BASE_FEATURE` macro with appropriate defaults
4. **Incognito improvements**: Test thoroughly - security-critical code

### Security Considerations

1. **Privacy by default** - disable telemetry, metrics, reporting
2. **No Google API keys** - use placeholder values in builds
3. **Keep Safe Browsing off** unless explicitly needed
4. **WebRTC IP handling** - default to hidden IPs

### Common Patterns

#### Adding a new patch:
```bash
# 1. Create the patch file in vanadium/patches/
# 2. Add to series file in order
# 3. Test with: patch --dry-run -p1 -i new.patch
# 4. Apply and verify build
```

#### Modifying build arguments:
```bash
# Edit args.gn, then regenerate:
gn args out/Default  # Interactive
# OR
gn gen out/Default   # Regenerate from args.gn
```

#### Debugging build issues:
```bash
# Verbose build output
autoninja -C out/Default -v chrome_public_apk

# Check gn args
gn args out/Default --list | grep <pattern>

# Clean rebuild
rm -rf out/Default && gn gen out/Default && autoninja -C out/Default chrome_public_apk
```

---

## Project-Specific Notes

### Extension Support (MV2)

Helium supports Manifest V2 extensions (including uBlock Origin). Key configurations:
- `extensions/common/extension_features.cc` - MV2 features enabled
- `extensions/browser/manifest_v2_experiment_manager.cc` - MV2 testing enabled

### Branding

- Package name: `app.involvex.browser` (Involvex fork; upstream: `io.github.jqssun.helium`)
- WebView package: Configured in `args.gn`
- String replacement via `name_substitution.py`

### Version Management

- Version defined in `vanadium/args.gn` (`android_default_version_name`, `android_default_version_code`)
- Helium version is derived from Vanadium version

### Known Issues

1. Some patches depend on specific Chromium versions
2. Secondary ABI builds may require additional configuration
3. Trichrome library patches need careful handling

---

## Resources

- [Vanadium GitHub](https://github.com/GrapheneOS/Vanadium)
- [Helium GitHub](https://github.com/imputnet/helium)
- [Chromium Development](https://www.chromium.org/)
- [GrapheneOS Build Guide](https://grapheneos.org/build#browser-and-webview)
- [GN Build Configuration](https://gn.googlesource.com/gn/+/main/docs.md)
- [depot_tools](https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools.html)

---

## Quick Reference

| Action | Command |
|--------|---------|
| Full build | `./build.sh` |
| Apply patches | `./patch.sh` |
| Generate build files | `gn gen out/Default` |
| Build APK | `autoninja -C out/Default chrome_public_apk` |
| Sign APK | `apksigner sign -ks keys/test.jks --out output.apk input.apk` |
| Run tests | `./helium/devutils/run_devutils_tests.sh` |
| Lint code | `./helium/devutils/check_all_code.sh` |

---

*Last updated: 2026-07-03*