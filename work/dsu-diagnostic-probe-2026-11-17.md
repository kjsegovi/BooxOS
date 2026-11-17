# DSU diagnostic probe — 2026-11-17

Why: attempts 2–5 hung with no USB and no logs, so each fix was a guess. This step adds a readout that works even when the guest hangs. Plan: `~/.claude/plans/we-need-to-plan-buzzing-pebble.md`.

## Observability findings

| Channel | Result |
|---|---|
| `/metadata/bootstat/persist.sys.boot.reason` → stock `sys.boot.reason.last` | **Main readout.** Shared /metadata; survives forced power-off (after power-holds stock showed the file's `reboot,shell`). ≤ 91 bytes; stock bootstat lowercases. |
| Guest self-reboot via `sys.powerctl` | Works even while init's action queue is stalled (init.cpp:364-373, 1116-1124). Kernel gets `bx,…` via RESTART2: no Qualcomm reboot-mode prefix match. |
| pstore / last kmsg on stock | **Not readable.** Pre-check (warm `adb reboot`): kernel registers ramoops (`console [pstore-1] enabled`), but DropBox has no `SYSTEM_LAST_KMSG`, bugreport `LAST LOGCAT` fails and `LAST KMSG` looks only at `/proc/last_kmsg` (absent). Stock is a user build, so pmsg isn't written either. Bugreport: `.local/captures/precheck-bugreport-20261117/`. |
| Front light | `onyx_bl_br` / `onyx_bl_ct` (0–32) writable by a root su service before vendor's `on boot` chmod. |
| UART | Not available (`SERIAL_MSM_GENI_CONSOLE` off). |
| `gsi_tool wipe` | Destroys the DSU metadata encryption key (gsi_service.cpp:996), so leftover keys don't explain attempts 2–5. |

Correction to an earlier inference: the leftover `reboot,shell` after attempts 2–5 doesn't prove they died before `/data`. The guest's bootstat runs from a property trigger queued behind `zygote-start`/`boot`.

## Probe (`device/onyx/GoColor7_2/bringup/`, `BOOXOS_BRINGUP=1` only)

`init.booxos.bringup.rc` starts `booxos-probe.sh` `on init` (root, `u:r:su:s0`, permissive on userdebug). Each ~7 s loop:

- Stage 1–8: 1 probe up · 2 `/data` mounted · 3 apexd activated · 4 `odsign.key.done` · 5 `init.svc.bpfloader=stopped` · 6 `odsign.verification.done` · 7 zygote running · 8 `sys.boot_completed`.
- Breadcrumb, e.g. `reboot,bx,s5,d1,aact,k1,bsto,v0,zx,u5not_,wodsign,t95`:
  `s` stage · `d` /data · `a` apexd.status · `k` odsign key · `b` bpfloader state · `v` odsign verification · `z` zygote state · `u` adb step (0 none, 1 configfs, 2 functionfs, 3 adbd running, 4 ep1, 5 UDC bound) + UDC state · `w` running exec_start service or odrefresh/dex2oat/secilc/fsck · `t` seconds since probe start · suffix `stall`/`late`, `f` = forced sysrq.
- Front light: N blinks = stage N; warm light toggles each loop (heartbeat). Blinking stops → kernel/userspace wedged.
- Reboots to stock after 90 s with no state change or 200 s total, unless the UDC is `configured` (then it stays up for live adb).
- Snapshots to `/data/local/tmp/booxos/` once /data is up; `booxos-probe:` lines to `/dev/kmsg`.
- Print-once test mode: `BOOXOS_PROBE_ONCE=1 sh booxos-probe.sh` (checked on stock: `reboot,bx,s8,d1,ax,k1,bsto,v1,zrun,u0conf,wnone,t0`, 50 bytes).

## Reading the result on stock

```
adb shell getprop sys.boot.reason.last
adb shell getprop persist.sys.boot.reason.history
```

## Result: bring-up 6 test boot (2026-11-17 13:49)

Zip `81870257…`. Guest rebooted itself back to stock after ~150 s (no Power-hold). Stock `sys.boot.reason.last`:

`reboot,bx,s1,d0,aact,k1,bsto,v1,zres,u2not_,wnone,stall`

- apexd activated, odsign key done, BPF loader stopped, odsign verification done → init got through post-fs-data and the zygote-start wait.
- **`zres`: zygote is restarting (crash loop).** This is the real blocker.
- **`u2`: functionfs mounted but adbd never reached `running`** (UDC not attached) → why USB never appeared.
- `wnone`: init isn't waiting on an exec service.
- Probe bug: `d0`/`s1` are artifacts. The probe starts before APEX activation, so it lives in init's bootstrap mount namespace and can't see `/data` (service.cpp:796). The stage chain depends on `d`, and snapshots only run when `d=1`, so none were taken. Raw fields are valid.

The readout channel is confirmed end-to-end.

## Result: bring-up 7 (probe v2) test boot (2026-11-17 14:13)

Zip `5c9abb17…`. Guest rebooted itself after ~150 s. Stock `sys.boot.reason.last`:

`reboot,bx,c,s1,zx,ax,u2,mfailed_to_open_database.:failed_to_attach_database_persisten,stall`

- Crash text is **keystore2**: `database.rs:1035` "Failed to attach database persistent" → `/data/misc/keystore/persistent.sqlite` unusable.
- `d0` again with the corrected check (`/proc/1/mounts`) → **guest `/data` is not mounted**.
- `ax`: `init.svc.adbd` empty, so init never registered adbd (APEX service definitions load during post-fs-data setup). That's why there's no USB.
- `zx`: no zygote death lines; zygote restarting is likely downstream of missing `/data`.

Stock `fstab.emmc` (`ro.boot.fstab_suffix=emmc`) `/data`: f2fs, `inlinecrypt`, `fileencryption=aes-256-xts:aes-256-cts:v2+emmc_optimized+wrappedkey_v0`, `metadata_encryption=aes-256-xts:wrappedkey_v0`, `keydirectory=/metadata/vold/metadata_encryption`, `formattable`, `checkpoint=fs`. **Hardware-wrapped keys.** keystore2 is `class early_hal` with db root `/data/misc/keystore`; vold's metadata path uses keystore2 + `exportWrappedStorageKey` (`MetadataCrypt.cpp:164`).

Working conclusion: guest `/data` (DSU userdata) fails to mount; keystore2's crash and missing adbd follow from that. Suspects: (1) wrapped-key metadata encryption through A14 vold/keystore2 → stock KM 4.0; (2) formatting the fresh DSU userdata (f2fs/inlinecrypt/emmc_optimized on 4.19); (3) DSU /data remapping. Next readout should capture the vold/fs_mgr error for `/data`.

## Result: bring-up 8 (probe v3) test boot (2026-11-17 14:45)

Zip `e0903d45…`. Stock `sys.boot.reason.last`:

`reboot,bx,d,s1,krunx,r1,f-,vkeystore2_keystore_generatekey_returned_service_specific_,stall`

- Keymaster HAL `vendor.keymaster-4-1` **running, no deaths (`krunx`), 4.1 registered (`r1`), no configure/date/property abort (`f-`)**. The configure-failure hypothesis from the RE work is **ruled out**.
- `/data` still not mounted. The vold error shown was the **first** one: probably vold's deliberate rollback-resistant `generateKey` attempt (`KeyStorage.cpp:129`), which is expected to fail and is retried without rollback resistance. The real failure is later; likely candidate `generateWrappedStorageKey` (`KeyStorage.cpp:138-154`: AES-256 + `TAG_STORAGE_KEY` + vendor `KM_TAG_FBE_ICE`).
- Probe fix: report the **last** vold error after skipping known benign lines, with the error count and the last keystore2 call's error code (`v<n>:generatekey=<code>:<msg>`).

## Result: bring-up 9 (probe v3.1) test boot (2026-11-17 15:02)

Zip `c063f8b3…`. Stock `sys.boot.reason.last`:

`reboot,bx,d,s1,krunx,r1,f-,v4:f:prepare_/data/misc/vold/user_keys:no_such_file_or_dir,stall`

- Keymaster again healthy. **No `generateKey` code**: apart from the expected rollback-resistance attempt, key generation didn't fail.
- 4 non-benign vold errors; last = `Failed to prepare /data/misc/vold/user_keys: No such file or directory` → FBE user-key setup in post-fs-data runs on an **unmounted `/data`**. The failure is earlier, in the userdata mount (`mount_all --late` → metadata-encryption mount), and its text is in the earlier vold errors / init `fs_mgr` kmsg.
- Next: probe v4 with paging (full report across boots via a page counter on /metadata).
