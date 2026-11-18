# Morning status — 2026-11-18

## Where things stand
**LineageOS 21 is installed on the Boox and boots by default.** It's a persistent DSU install: Lineage runs from its own images and its own 12 GB data area, and stock stays intact underneath. No firmware partitions were written.

- Build: bring-up 15 (`.local/builds/dsu-bringup15-20261117/`, sha256 `aa3af462…`).
- Reboots come back to Lineage (checked: 27 s, settings kept).
- Setup wizard done: no screen lock, Wi-Fi not joined (pick your network).
- Defaults set for e-ink and privacy:
  - Lineage stats collection **off**. It was on after setup, even though the page looked unchecked.
  - Location off.
  - Light theme.
  - All animations off.
  - Touch sounds and haptics off.
  - Time zone America/Los_Angeles.
- An empty `/sdcard/Books` folder is ready.

## What was fixed overnight
1. **`/data` mount** (bring-up 13): Lineage's fs_mgr didn't know stock's `dirsync` fstab flag.
2. **Panel never refreshing** (bring-ups 14–15). Reverse engineered with REA/Ghidra on the stock binaries:
   - The kernel only drives the panel from a single full-screen layer, so SurfaceFlinger now GPU-composes everything. Stock does the same ("h/w composer disabled").
   - The Onyx vendor composer only refreshes regions that SurfaceFlinger lists with each frame. The list goes in a custom command, `0x802`, with items `{left, top, right, bottom, mode}`. Lineage now sends one full-screen item per frame with mode 5, the same default stock SurfaceFlinger uses (`createSingleUpdate(…, 5)`).
   - Result: the e-ink controller's frame counter now moves on every screen change and stays put when idle. Before, it was stuck.

Details: `work/eink-display-path-2026-11-17.md`, `work/dsu-diagnostic-probe-2026-11-17.md`.

## Please check first (I couldn't see the panel)
- Does the screen follow what you do: launcher, opening Settings, scrolling?
- How bad are ghosting and flashing? If needed, try other modes live without rebuilding:
  - `adb shell setprop debug.booxos.epdc_mode 34` = GC16-style full refresh every frame (clean, flashes)
  - `adb shell setprop debug.booxos.epdc_mode 2` = GC16 partial
  - `adb shell setprop debug.booxos.epdc_mode 5` = auto (default)
  - `adb shell setprop debug.booxos.epdc_mode 1` = waveform 1 (probably DU, fast/black-and-white)

## Testing Readest and books
1. Join Wi-Fi: Settings → Network & internet.
2. Install Readest, either way:
   - From the Mac: download the Android APK from Readest's official release page, then `adb install <file>.apk`.
   - On the Boox: open the Jelly browser, download the APK, and allow "install unknown apps" for Jelly when asked.
   Android System WebView 156 is installed, which Readest needs.
3. Books:
   - `adb push book.epub /sdcard/Books/`
   - Or USB file transfer: pull down notifications → USB → File transfer.
   - Then import from Readest.
4. Page buttons send volume up/down. Enable "volume keys turn pages" in Readest if it offers it.

## Known issues
- **Front light:** the brightness slider does nothing. The light stays at stock's level, 16 of 32 (`/sys/class/backlight/onyx_bl_br`, world-writable; warmth is `onyx_bl_ct`). To set it by hand: `adb shell 'echo 24 > /sys/class/backlight/onyx_bl_br/brightness'`.
- **No ghosting cleanup yet:** there's no periodic full refresh (`ro.surface_flinger.booxos_epdc_full_every=0`). One-off clean (root): enable Developer options → Rooted debugging, then `adb root` and `adb shell cat /sys/devices/virtual/sepdc/debug/panel_clean`.
- **Debug build:** adb is open without authorization, and a debug probe runs at boot (it exits once boot completes). Fine for testing, not for daily use.
- **Pen:** the input device is present, but handwriting and fast-pen modes are Onyx framework features that aren't ported.

## Going back to stock
- Temporarily (next boot only): from Lineage, `adb shell gsi_tool disable` then `adb reboot`. Stock boots. `gsi_tool enable` brings Lineage back.
- Remove Lineage completely: on stock, `adb shell gsi_tool wipe`.
- If Lineage ever fails to boot, the DSU loader should fall back to stock by itself (gsid boot-attempt limit). Not tested here.
