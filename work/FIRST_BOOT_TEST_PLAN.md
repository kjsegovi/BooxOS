# First-boot test plan — LineageOS 21 on GoColor7_2

Drafted **2026-11-16**. Planning only: no USB/device access was used to write this. Every device step below needs the owner's explicit go-ahead at the time it runs.

## Recommendation

**Do the first boot as a Dynamic System Update (DSU) guest, not a flash.** DSU boots the new `system`, `system_ext` and `product` images from files in `userdata`, on top of the device's own stock `boot`, `dtbo`, `vendor` and `odm`. That is exactly the split this port is built around (`device/onyx/GoColor7_2`). It writes **no firmware partition**, needs **no root and no EDL**, keeps the stock data untouched (the guest gets its own data image), and a normal reboot returns to stock.

A real install comes later, after DSU shows the system actually runs, and needs separate decisions (see "After DSU").

## Why the other routes are out

| Route | Evidence | Status |
| --- | --- | --- |
| Bootloader `fastboot flash` | `Writing 'boot_a' FAILED (remote: 'unknown command')` — [magisk-root-install](magisk-root-install-2026-11-11.json) | Disabled by Onyx |
| Bootloader `fastboot boot` (RAM boot) | Unchanged stock boot: `Booting FAILED (remote: 'unknown command')` — [RAM boot test](stock-ram-boot-test-result-2026-11-11.json) | Disabled |
| fastbootd `flash` | `Unrecognized command flash` — [fastbootd test](fastbootd-magisk-write-rejected-stock-return-2026-11-11.json) | Disabled |
| Signed OTA (recovery / update_engine) | Stock trusts a cert named `testkey.x509.pem`, but DER SHA-256 `d15235d2…` ≠ AOSP testkey `a40da80a…` (checked 2026-11-16). It's Onyx's private key under the testkey filename. | Can't sign |
| Side-by-side slot B install | Stock slot A logical images = 4.84 GB; Lineage set (incl. vendor/odm) = 2.32 GB; `super` group = 6.44 GB → ~0.7 GB short | Doesn't fit |
| EDL firehose write | Programmer accepted on this unit, but the Nov 11 bootloop followed an EDL session with cause unknown; [hold in place](recovery-backup-status.md) | Kept for later / last resort |

## DSU evidence from the stock firmware (offline)

- Stock `system.img` contains `DynamicSystemInstallationService`, `gsid.rc` and `gsi_tool`.
- Stock boot ramdisk first-stage `init` (extracted 2026-11-16) contains the DSU paths `/metadata/gsi/dsu/one_shot_boot`, `lp_names` (multi-partition guests), `avb_enforce`, plus `avb/{q,r,s}-gsi.avbpubkey`.
- Bootloader reports unlocked/orange, so the guest isn't held to Google's GSI keys.
- **Not yet shown:** that Onyx left DSU *working* (the service could be disabled by policy or overlay), that the stock Android 13 installer accepts a multi-image zip, and that there's enough free space in internal storage (~6 GB needed).

## Phase 0 — offline prep (no device)

1. **Bring-up build changes**, on a separate debug-only config so they never reach a daily build:
   - ADB on at boot and usable without the screen: `ro.adb.secure=0` (simplest), or the Mac's public key via `PRODUCT_ADB_KEYS`. Without this, a blank e-ink screen leaves us blind.
   - Keep `userdebug` so `adb root`, `logcat` and `dmesg` work.
2. **Rebuild on KPC** (incremental, should be well under the first 2h10m), then package `system.img`, `system_ext.img`, `product.img` as a DSU zip. Record hashes.
3. **Expectation check:** the DSU guest runs on the *stock* vendor, not our derivative vendor, so `eink-shim` is **not** in play. The screen may refresh badly or not at all. This test is "does LineageOS boot on this hardware," not "is the display good."
4. **Write the abort/rollback card** (below) and a capture script that pulls `logcat -b all`, `dmesg`, `getprop`, `dumpsys SurfaceFlinger`, SELinux denials and VINTF errors.

## Phase 1 — read-only device checks (owner present)

1. Stock Android, slot A, battery ≥ 80%, USB to the Mac.
2. Read: free internal storage; whether `com.android.dynsystem` is installed and enabled (`pm list packages`, `dumpsys package`); `gsid` service present; no DSU already installed (`gsi_tool status`).
3. Back up anything on-device you care about (books not in the cloud, notes, Readest/KOReader settings). DSU shouldn't touch them, but this is the first time new code runs on the reader.

## Phase 2 — DSU install and first boot (owner present)

1. Copy the DSU zip to the device (`/sdcard/Download/`).
2. Start the install from the Mac with the stock installer activity (`com.android.dynsystem`, `START_INSTALL`, guest userdata ~4 GB). Watch the notification; it writes only under `/data/gsi` and `/metadata/gsi`.
3. Reboot into the guest from the notification.
4. **Time-boxed observation (10 min):**
   - Does USB enumerate, and does `adb devices` show it?
   - If yes, run the capture script. Then check boot progress (`sys.boot_completed`), SELinux mode, crashing services, display stack (`/dev/ebc`, composer, SurfaceFlinger), touch, buttons, Wi-Fi, frontlight, battery reading.
   - Note what the screen physically shows (photo is fine).
5. Reboot. The device should return to stock Android on slot A.

## Abort / rollback card

| Situation | Action |
| --- | --- |
| Guest hangs or loops | Hold Power ~10 s to force restart. DSU is one-shot, so the next boot is stock. |
| Back in stock but guest still installed | `gsi_tool disable` or remove it from the DSU notification/Settings; `gsi_tool wipe` frees the space. |
| Stock won't start | Stock recovery → fastboot → `fastboot getvar current-slot` / `slot-unbootable:a`, then `set_active a` if needed (proven Nov 11). Recovery entry lead: Power 8 s, release, Power ×5, **stop pressing once the menu shows**. |
| Nothing responds | Stop. EDL is last resort and needs a fresh decision. |

## Success criteria

- **Pass:** guest reaches ADB and we capture logs, even with a bad screen.
- **Strong pass:** `sys.boot_completed=1` and some visible screen update.
- **Fail but useful:** no ADB, but stock returns cleanly. Next step is making failures visible (e.g. earlier ADB start, or pstore/`last_kmsg` from stock after the attempt).

## After DSU (decisions for later, not now)

1. **Write path for a real install.** Options: (a) a small EDL write of a Magisk-patched `boot_a` (known restore image in the recovery kit), then do everything else from a rooted shell, including the full backup the kit is missing (`super`, the 45 uncaptured partitions); (b) reverse engineer the Onyx `abl` bootloader for hidden/OEM flash commands. This is a good job for REA (`abl.img` is in the stock OTA); (c) direct EDL writes. All depend on first understanding the Nov 11 incident.
2. **Where it lives.** It can't sit beside stock in `super`. Either Lineage replaces stock on slot A after a full backup, or stock's logical partitions get shrunk.
3. **Display.** The real `eink-shim` needs our derivative vendor, which DSU can't provide. The color refresh work is where REA comes back in, reverse engineering Onyx's composer/`/dev/ebc` path.
4. **Data.** Moving from stock Android 13 to Lineage 14 on real partitions will almost certainly need a data wipe, and going back to stock would need another.
