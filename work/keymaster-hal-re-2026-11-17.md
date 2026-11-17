# Stock Keymaster HAL reverse engineering (REA + Ghidra) — 2026-11-17

Why: probe v2 showed the DSU guest's `/data` never mounts (keystore2 crash downstream). The device uses hardware-wrapped keys (`wrappedkey_v0` for FBE and metadata encryption), so the guest's Android 14 vold depends on stock's Keymaster.

## Setup
- REA `rea-agents` 6.9.0 CLI (npx cache), Ghidra 12.2 (Homebrew formula `ghidra`, pulls `openjdk@25`). Env: `GHIDRA_INSTALL_DIR=/opt/homebrew/opt/ghidra/libexec`, `JAVA_HOME=/opt/homebrew/opt/openjdk@25`.
- REA's Claude Code MCP registration did not complete (no entry in `~/.claude.json`); CLI used directly.
- Inputs extracted with `debugfs` from the **stock** OTA `vendor.img` (sha256 `147fe58e…`), not the derivative prebuilt (`0de3bb…`). adb shell can't read `/vendor` binaries (SELinux).

## Stock Keymaster
- VINTF: `android.hardware.keymaster@4.1::IKeymasterDevice/default`; service `vendor.keymaster-4-1` (`/vendor/bin/hw/android.hardware.keymaster@4.1-service-qti`, class `early_hal`), lib `libqtikeymaster4.so` (sha256 `63b7a42f…`), TA client via `libQSEEComAPI.so`.
- Implements `exportKey`, `importWrappedKey`, `upgradeKey`, `deleteAllKeys`, 4.1 `earlyBootEnded`. `export_key` (0x111aa8) just serializes to the TA, with no HAL-side storage-key gating.

## Key finding: HAL startup (`Keymaster4Device` ctor, 0x10d014)
Pseudocode: `work/re/libqtikeymaster4-Keymaster4Device-ctor-0x10d014.c`.
1. `WaitForPropertyCreation(…, INT64_MAX)` on `ro.build.version.security_patch`, `ro.vendor.build.security_patch`, `ro.build.version.release` → hangs forever if any is missing.
2. `get_date_support`; failure → abort ("get_date_support failed").
3. `configure({OS_VERSION 0x2c1 = GetOsVersion(release), OS_PATCHLEVEL 0x2c2 = GetPatchlevel(security_patch), VENDOR_PATCHLEVEL 0x2ce})`; non-zero → `__android_log_assert("Configure failed")` → **HAL aborts**.

In the DSU guest the vendor HAL reads the guest's properties: release 14, security_patch 2026-10-01 (stock: 13 / 2026-04-01; vendor 2025-10-01). The guest's patch level is newer, so not a classic rollback rejection; whether the QSEE TA accepts it is unknown.

## Hypothesis for the guest `/data` failure
Keymaster HAL aborts at configure (or hangs on a property) → no usable Keymaster → vold can't create/unwrap the `wrappedkey_v0` metadata key → `/data` not mounted → keystore2 "failed to attach database persistent", adbd never registered, zygote restarting.

## How to confirm (next probe)
Report `init.svc.vendor.keymaster-4-1` (+ init exit code/signal, death count) and whether logcat contains "Configure failed" / "get_date_support failed" / "Android property not present", plus the first vold `E` line.
