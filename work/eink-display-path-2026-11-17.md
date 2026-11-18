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
