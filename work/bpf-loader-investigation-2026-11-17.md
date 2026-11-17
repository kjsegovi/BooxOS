# BPF loader failure in the DSU guest — offline investigation

2026-11-17. Source and stock-image analysis only; no device actions in this step. Context: [dsu-phase2-first-boot-2026-11-17.json](dsu-phase2-first-boot-2026-11-17.json).

## Symptom

- Bring-up 1: guest reached second-stage init, then rebooted to stock with `reboot,bpfloader-failed`.
- Bring-up 2 (`reboot_on_failure` commented out): guest never enumerated on USB in 20 min.

## Kernel is not the obvious problem

Stock kernel `4.19.157` config (extracted from the validated stock `boot.img` ikconfig, sha256 `681af35e…`) has Android's 4.19 BPF set: `BPF_SYSCALL`, `BPF_JIT` + `BPF_JIT_ALWAYS_ON`, `CGROUP_BPF`, `SOCK_CGROUP_DATA`, `NET_CLS_BPF`, `NET_CLS_ACT`, `NET_SCH_INGRESS`, `NETFILTER_XT_MATCH_BPF`, `INET_DIAG_DESTROY`, `BPF_EVENTS`. Android 14's netbpfload only *warns* below 4.14 and only hard-requires 4.19 from Android 15 (`NetBpfLoad.cpp`).

## Where netbpfload / bpfloader can fail (Lineage 21 source)

`/system/bin/netbpfload` (platform) → execs `/apex/com.android.tethering/bin/netbpfload` → loads network programs → execs `/system/bin/bpfloader` → loads `/system/etc/bpf/*.o` → sets `bpf.progs_loaded=1`.

Fatal exits:
1. Init-script sanity: exactly one of `bpfloader.rc` / `netbpfload.rc`. **Checked: only `netbpfload.rc` is in the image — passes.**
2. sysctl writes `bpf_jit_enable` / `bpf_jit_kallsyms` must succeed on ≥4.14.
3. Creating `/sys/fs/bpf/<subdirs>` (SELinux/genfscon-sensitive with an Android 11 vendor policy).
4. Any non-optional program/map failing to load ("CRITICAL FAILURE LOADING BPF PROGRAMS", sleeps 20 s, returns 2).

Platform programs in the image: `bpfRingbufProg`, `bpfMemEvents` (ringbuf, guarded `KVER(5,8,0)` → should be skipped), `gpuMem`, `gpuWork`, `timeInState`, `fuseMedia`, `uprobestats`. The same Android 14 programs shipped on 4.19 phones (e.g. Pixel 5), so a failure here would point at Onyx-kernel differences from the Android common kernel, or SELinux. Can't be settled statically.

## Why bring-up 2 went silent

`init.rc`: `trigger post-fs-data` → `trigger load_bpf_programs` → `trigger zygote-start` … then `boot`, which is where USB/adbd come up. `netbpfload.rc` runs `exec_start bpfloader`, which **blocks init with no timeout** until the loader exits. Nothing else waits on `bpf.progs_loaded` in init. So a loader that hangs (rather than exits) holds the device before USB exists. Netbpfload logs go to the kernel log (`KernelLogger`), unreachable without adb.

## Debug build change (bring-up 3, debug-only)

`tools/build-host/kpc_build.sh` with `BOOXOS_BRINGUP=1` now also changes `exec_start bpfloader` → `start bpfloader` in `netbpfload.rc`, so init continues to `boot` and adb comes up regardless. Standard builds restore both rc files from git first.

Expected outcomes of the next DSU boot:
- **adb appears** → `adb root`, `dmesg | grep -i -E "bpf|NetBpfLoad"` and `logcat` give the exact failing step/program.
- **still no adb** → BPF is not what blocks; look earlier (vold/userdata, SELinux, vendor init).

Security note: these bring-up changes disable a fail-safe and ADB auth. They exist only for diagnosis and must never ship.

## Bring-up 3 build

Passed 2026-11-17 (incremental). `system/etc/init/netbpfload.rc` line 18: `start bpfloader  # BOOXOS_BRINGUP: was exec_start`; `reboot_on_failure` commented in both rc files; `ro.adb.secure=0`. DSU zip sha256 `6a0c2f864fdc21753c51eb7f819add7f488af6799549642ac297436e3dec6fe0`, on the Mac at `.local/builds/dsu-bringup3-20261117/booxos-dsu-bringup.zip`. Not yet run on the device.

## Bring-up 3 result and the real blocker (2026-11-17)

Bring-up 3 (loader non-blocking) **also** hung with no USB for ~17 min; owner held Power, back on stock. So BPF was not what kept USB down.

Cause found in source: guest `init.rc` `on zygote-start` → `wait_for_prop odsign.verification.done 1`. `odsign_main.cpp` runs `compileArtifacts()` (odrefresh) **synchronously** when artifacts are missing and only sets `odsign.verification.done` via a scope guard on exit. Our builds used `WITH_DEXPREOPT=false`, so there are no precompiled ART artifacts: first boot compiles the whole boot classpath + system_server on-device while init's action queue is frozen before `early-boot`/`boot` (where USB/adbd start). Stock vendor `late-fs` waits (`hwservicemanager.ready`, `wait_for_keymaster`) run before post-fs-data and were already passed in attempt 1.

Fix: `WITH_DEXPREOPT` override removed from `kpc_build.sh` (both flavors) and `build_color_target.py`. Bring-up 4 launched with dexpreopt on and the BPF debug changes still in place. The BPF failure itself is still unexplained and should show up in `dmesg` once adb works.

## Bring-up 4 result; switch to early adb (2026-11-17)

First bring-up 4 build was a no-op: `device/onyx/GoColor7_2/lineage_GoColor7_2.mk` itself set `WITH_DEXPREOPT := false` ("lower build-memory pressure", from the Mac-build era). Removed; rebuilt in 8 min with `system/framework/arm64/boot-*.{art,oat,vdex}` present, system.img 836 → 943 MB, zip `f0dca938…`.

Bring-up 4 on device: **still no USB for ~19 min**, back on stock after Power hold. So missing dexpreopt was not the (only) blocker. Two plausible causes ruled out without logs; stopping the guessing.

Bring-up 5 (debug-only, `BOOXOS_BRINGUP=1` → `device/onyx/GoColor7_2/bringup/`): a `post-fs-data`-started oneshot service (`seclabel u:r:su:s0`, permissive on userdebug) runs `/product/etc/booxos-earlyadb.sh`, which builds the adb USB gadget by hand (configfs g1 + ffs.adb, VID/PID 18d1:4ee7, functionfs at /dev/usb-ffs/adb, `ctl.start adbd`, UDC `ro.boot.usbcontroller`), mirroring stock `init.qcom.usb.rc`, and writes dmesg/logcat/getprop/ps (with WCHAN) to `/data/local/tmp/booxos/` every 3 s. Attempt 1 proved post-fs-data completes, and the script runs as a background service, so later blocking stages can't stop it. The `ps` WCHAN column should show exactly which process init is waiting on.

## Bring-up 5 result (2026-11-17, paused here)

Zip `023dbf82…` installed and enabled from the Mac; `adb reboot` 12:55:38. No USB enumeration (early-adb gadget did not appear). Owner force-restarted after ~2 min; back on stock, guest installed/disabled. Stock DropBox has no `SYSTEM_LAST_KMSG` entry for the guest boot (only SYSTEM_BOOT / system_server_wtf), so no previous-boot kernel log that way.

Open next steps: let a guest boot run longer before force-restarting (the early-adb script should be up within ~1–2 min of post-fs-data); check whether stock pstore is enabled at all; consider whether the guest even reaches post-fs-data on attempts 2–5 (only attempt 1 is proven to).
