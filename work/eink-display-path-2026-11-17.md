# E-ink display path in the Lineage 21 DSU guest (2026-11-17)

Bring-up 13 boots to `sys.boot_completed=1`, but the panel kept the old image (user-confirmed), while `screencap` showed the Lineage setup wizard.

## Findings (guest, adb root via Developer options → Rooted debugging)
- Nothing opens `/dev/ebc` (`root:root 0600`, `ebc_device`). DRM `/dev/dri/card0` is opened only by the stock vendor `vendor.qti.hardware.display.composer-service` (and `feature_enabler_client`).
- The kernel's SDE DRM driver feeds the EPD from atomic commits: dmesg is flooded with
  `__sde_plane_atomic_update_epdc(): error! … width[1264] height[53] …` and `… height[189] …` —
  the status-bar and nav-bar overlay planes. The EPDC hook rejects non-full-screen planes.
- EPDC debug sysfs: `/sys/devices/virtual/sepdc/debug/{status,update_disable,submit_upd_work,update_snapshot,panel_clean,…}`; `waveform_version` = `onyx waveform sg`. `status` showed `frame[87:87:87]`, `update_disable 0`, `update_err 0`.
- Stock bugreport (`.local/captures/precheck-bugreport-20261117`): SurfaceFlinger reports **`h/w composer disabled`**, and all layers (`com.onyx.reader…MainActivity`, `StatusBar`) are `CLIENT` composited into one full-screen client target.

## Experiment
`service call SurfaceFlinger 1008 i32 1` (Developer option "Disable HW overlays", forced GPU composition) on the running guest:
- The plane errors stopped; the EPDC frame counter went 87 → 120.
- **User confirmed the panel now shows Lineage.** Stock kernel and vendor HWC drive e-ink fine when SurfaceFlinger hands them one full-screen layer.

## Fix (next build)
Make forced client composition the boot default instead of a runtime toggle:
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` constructor (next to `debug.sf.showupdates`, ~L487):
  `mDebugDisableHWC = base::GetBoolProperty("ro.surface_flinger.booxos_force_client_composition"s, false);`
  (`ro.surface_flinger.` prefix is labeled `surfaceflinger_prop`, so SF can read it.)
- Device: `PRODUCT_SYSTEM_PROPERTIES += ro.surface_flinger.booxos_force_client_composition=true`.

## Also noted (not yet acted on)
- Stock sets `vendor.display.*` (e.g. `disable_excl_rect_partial_fb=1`, `comp_mask=0`, `enable_optimize_refresh=1`, `lcd_density=300`) and `ro.hardware.egl=adreno`; none exist in the guest, so stock sets them from its system side. They may matter for refresh quality later.
- Refresh mode, waveform selection, and A2/fast modes are the Onyx framework's job (EpdController-style); the next phase is REA on stock system pieces.

Captures: `.local/captures/guest-bringup13-20261117/epd-guest-*.txt`.

## Update (night of 2026-11-17): forced GPU composition alone is not enough

Bring-up 14 (forced client composition at boot) had no plane errors, but the panel only refreshed on explicit requests. Reading `sepdc/debug/panel_init` / `panel_clean` **triggers** a panel init / full clean (side-effect reads). The bring-up 13 refresh was a one-off.

### How stock drives the panel (REA/Ghidra on stock binaries)
- Stock **system** is Onyx-patched: `libgui` (`Surface::transferEpdc`, `EpdcWrapper`, `hwc_epdc_llist`) and `surfaceflinger` (`EpdcManager`, `EpdcSchemaManager`, "add full screen epdc"). Apps pass update regions and modes through `View.invalidateWithUpdateMode` / `EpdController`.
- Stock **vendor** composer (`vendor.qti.hardware.display.composer-service`, unchanged in the guest):
  - `QtiComposerClient::CommandReader::parse` @0x13cd50 handles opcode **0x802** (`0x8020000|len`): word0 = item count, then 5-word items `{left, top, right, bottom, mode}` (count must equal (len-1)/5).
  - `CommandReader::presentDisplay` @0x145ebc turns items into `onyx_epdc_update_to_display` entries (max 8 per present): rect clamped to the display; `mode & 0xf` selects the waveform (1→1, 2→2, 3→3, 4→4, **5→0xff auto**, 6→5 (+flag 0x8000 if bit12), 7→0xf, 8→8, 9→0x10, 0xb, 0xc, 0xd); **bit 5 → update_mode** (full); bits 6/8/19/20-21/22/28 → driver flags.
  - `libsdedrm` sets DRM plane props `EPDC_UPDATE_CNT` / `EPDC_UPDATE_PARMS_ADDR`; the kernel's `__sde_plane_atomic_update_epdc` acts only on those.
- Lineage sent no 0x802, so the kernel never got update parameters.

### Fix (bring-up 15, `tools/build-host/patches/frameworks_native-0001-epdc-update-list.patch`)
`HidlComposer` writes one full-screen 0x802 item before every `presentDisplay`/`presentOrValidateDisplay`. Mode word: `debug.booxos.epdc_mode` (live), else `ro.surface_flinger.booxos_epdc_mode` (=5); optional periodic full refresh `ro.surface_flinger.booxos_epdc_full_every` (=0, off) with `..._full_mode` (=34 = 2|0x20).

Result on device: EPDC frame counter advances with every screen change (87 stuck → 2553 → 2695 → 2907 … ; idle = no change); `epdc_update`/`epdc_power` wakeup sources active. Panel not visually confirmed yet (overnight, user asleep).

### Other hardware in the guest
Touch `onyx_ts_istaric` (raw 0–1263 × 0–1679, rotation 0, matches panel), pen `onyx_emp_istaric_pen`, keys (`gpio-keys` volume up/down = page buttons, `qpnp_pon` power, `onyx-hall` cover → KEY_POWER), battery OK, Wi-Fi `wlan0` scans, audio HAL up, WebView 156.
**Not working:** brightness slider → front light (`onyx_bl_br` 0–32 stays at 16; Android reports display brightness unsupported).
