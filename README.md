# BooxOS

An experimental, telemetry-free Android for the **BOOX Go Color 7 Gen II**
(`GoColor7_2`), built on **LineageOS 21 (Android 14)** and tuned for e-ink reading.

The idea: a quiet e-reader OS. It has no metrics or data collection, no
pre-installed clutter, an app store for your reading app, and an e-ink refresh
policy that keeps the screen smooth and readable.

> **Status: experimental bring-up.** It runs on real hardware as a
> [Dynamic System Update (DSU)](https://source.android.com/docs/core/ota/dynamic-system-updates)
> guest. Stock firmware stays installed underneath, and nothing is flashed. It is
> not affiliated with or endorsed by Onyx, and it is not an official LineageOS
> build. Use it at your own risk.

## Is this a fork of LineageOS?

No. BooxOS is a **LineageOS device port plus customizations**. This repository
doesn't contain LineageOS's or AOSP's source code. The build downloads the
unmodified LineageOS 21 source separately, as every LineageOS device port does,
and adds this repo on top. LineageOS and AOSP do the heavy lifting; credit for
the operating system itself goes to them.

What this repo adds:
- **A device tree** for the Go Color 7 Gen II (`device/onyx/GoColor7_2`), plus
  overlays, a small Quick Settings app, SELinux policy and init scripts for this
  hardware. All written for this project.
- **Patch files** with our changes to AOSP's SurfaceFlinger and fs_mgr
  (`tools/build-host/patches/`). They are diffs against unmodified upstream
  files, which remain under their original Apache-2.0 license.
- **Build scripts, tools and research notes.**

## What works

| Area | State |
|---|---|
| Boot | Boots as a persistent DSU in about 30–50 s. Reboots return to it; stock is one command away. |
| E-ink display | Panel updates driven through the Onyx composer (reverse-engineered, see below). Smooth A2 updates, gentle cleanup after app switches. |
| Touch | Works. A boot-time controller reset works around the vendor driver leaving its interrupt off. |
| Front light | The system brightness slider drives the light (minimum = off). Warmth is set from a Quick Settings tile. |
| B&W / Color | A Quick Settings tile switches between black-and-white (full 300 ppi) and color (150 ppi Kaleido). |
| Text | Density 320, with bold and high-contrast text by default (tested for crispness on the panel). |
| Wi-Fi, page buttons | Work. The page buttons send volume up/down, which most readers can use to turn pages. |
| Apps | Aurora Store (Play Store apps without a Google account), F-Droid, and Readest preinstalled. |
| Privacy defaults | Lineage stats off, location off, no lock screen, animations off. No Google apps. |

**Not done yet:**
- Pen and handwriting (Onyx framework features)
- A proper flash/install path, rather than DSU
- A non-debug release build: bring-up builds have open adb
- Per-app refresh settings

## How the e-ink display works here

The interesting part of this project. Found by reverse engineering the stock
vendor composer and SurfaceFlinger with Ghidra:

- **SurfaceFlinger must GPU-compose everything** into one full-screen layer. The
  kernel's EPDC hook only accepts a single plane.
- **The Onyx composer only refreshes the panel for regions listed with each
  frame**, via a custom HWC command (`0x802`). Each item is
  `{left, top, right, bottom, mode}`. The mode word picks the waveform: low nibble
  = waveform, bit 5 = full update, bit 8 = dithering, and other bits are driver
  flags. Stock Android sends these from its Onyx-patched SurfaceFlinger; we patch
  Lineage's `HidlComposer` to send them.
- **Refresh policy**, tuned live on the device:
  - Every frame uses **A2 + dithering** (mode `260`): fast, no flashing,
    smooth scrolling and page turns.
  - When the set of visible apps changes (an app switch), the screen gets one
    **cleanup redraw** once things are quiet. It covers only the area changed since
    the last cleanup. It is gentle (mode `35`) normally and a full GC16 flash
    (mode `34`) every 4th time.
  - Every knob is a system property. You can tune it live without rebuilding:

    ```bash
    adb shell setprop debug.booxos.epdc_mode 260        # waveform for every update
    adb shell setprop debug.booxos.epdc_hard_every 4    # every Nth cleanup is a full flash
    adb shell setprop debug.booxos.epdc_clean_pct 400   # also clean after N% of the screen changed (0 = off)
    ```

Details and the experiments behind these choices:
`work/eink-display-path-2026-11-17.md` and `work/eink-live-experiments-2026-11-18.md`.

## Repository layout

```
device/onyx/GoColor7_2/   LineageOS device tree
  lineage_GoColor7_2.mk     product config, e-ink policy defaults
  overlay/                  home screen, settings/privacy defaults, Quick Settings
  apps/BooxosDisplay/       Light + B&W Quick Settings tiles, first-boot text defaults
  prebuilt/apps/            Aurora Store, F-Droid, Readest (APKs fetched, not in git)
  sepolicy/                 sysfs labels and properties for light/touch
  init/                     touch-controller reset, warmth trigger
  bringup/                  debug-only boot probe (bring-up builds)
tools/build-host/         build scripts and platform patches
  kpc_build.sh              builds the images and the DSU zip
  patches/                  frameworks/native patch (EPDC update list, refresh policy,
                            front light) and its generator
tools/fetch_store_apks.sh download the bundled APKs, verified against pinned SHA-256
work/                     investigation notes, status reports, experiment logs
```

## Building

You need a LineageOS 21 source tree and a Linux build host with plenty of disk
(the scripts here run the build in a container). Roughly:

1. Sync LineageOS 21 and place `device/onyx/GoColor7_2` in the tree.
2. Provide the stock prebuilts the device tree expects. They are extracted from
   the matching stock firmware and are not in this repo: see
   `device/onyx/GoColor7_2/README.md`.
3. Fetch the bundled apps: `tools/fetch_store_apks.sh`.
4. Copy `tools/build-host/patches/` to `booxos-patches/` in the tree, then run
   `tools/build-host/kpc_build.sh`. It applies the platform patches (fs_mgr
   `dirsync`, forced GPU composition, the EPDC policy) and builds `system`,
   `system_ext` and `product`. With `BOOXOS_BRINGUP=1` it also builds a DSU zip.

## Installing (DSU)

On the **stock** firmware, with USB debugging on and the unit's bootloader unlocked:

```bash
adb push booxos-dsu-bringup.zip /storage/emulated/0/Download/
adb shell am start-activity \
  -n com.android.dynsystem/com.android.dynsystem.VerificationActivity \
  -a android.os.image.action.START_INSTALL \
  -d file:///storage/emulated/0/Download/booxos-dsu-bringup.zip \
  --el KEY_USERDATA_SIZE 12884901888
```

When the install finishes:

```bash
adb shell gsi_tool enable
```

```bash
adb reboot
```

`gsi_tool enable --single-boot` boots it just once, for a trial.

**Back to stock:** from BooxOS, run `adb shell gsi_tool disable` and then `adb reboot`.
To remove BooxOS completely, run `adb shell gsi_tool wipe` from stock.

Installing a new build replaces BooxOS's data partition, so you sign in to
apps again.

## Credits and licenses

- [LineageOS](https://lineageos.org) and the
  [Android Open Source Project](https://source.android.com): the operating
  system (Apache-2.0 and others). The patches here modify AOSP files and stay
  under their licenses.
- [go7-lineage](https://github.com/go7-lineage) (the LineageOS port for the
  monochrome BOOX Go 7) was studied as prior art for e-ink support on Onyx
  devices. None of its code is included or used here.
- Bundled apps, unmodified and with their original signatures:
  - [Aurora Store](https://gitlab.com/AuroraOSS/AuroraStore) (GPL-3.0)
  - [F-Droid](https://f-droid.org) (GPL-3.0)
  - [Readest](https://github.com/readest/readest) (AGPL-3.0)
- Vendor blobs and stock images are Onyx's and are **not** distributed here.
- BOOX is a trademark of Onyx International. This project is independent.
