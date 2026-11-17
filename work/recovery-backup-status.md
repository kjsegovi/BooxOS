# BOOX recovered; smaller backup incomplete

**Current state:** the BOOX is running its original April 2026 firmware on slot A. The user confirms the home screen. Mac checks confirm model `GoColor7_2`, build `2026-04-21_13-54_4.2-rel_0421_19324b3ea`, slot `_a`, completed startup, and increasing uptime through a 30-second observation. No further restart was observed during that initial stability check. A subsequent approved boot-status check found slot A marked successful and bootable, with no pending snapshot update. One normal restart then returned to the original build on A with startup complete. That check issued no slot/flag changes, firmware writes, erase, or EDL operation. [Boot-status result](boot-status-check-2026-11-11.json).

## What happened and what fixed it

The user approved a smaller recovery backup excluding personal storage. The selected scope was 76 LUN0 partitions, excluding `userdata`, `rawdump`, `logdump`, and `logfs`. The read stopped at `core_nhlos_b` after 31 complete partition files had been independently reread with matching hashes. The partial remaining file is not a restore asset.

The backup host command audit found configure ×1, storage query ×1, read ×187 and reset ×1: no host flash, program, erase, patch or slot-change command, and no userdata read. This audit does not establish the closed programmer's internal effects. The reader subsequently looped at the first logo approximately every 15 seconds.

The reader later reached stock recovery from the older November 2025 B build. Entering **fastboot** from that menu exposed a working Mac connection. Queries confirmed **B selected, A marked unbootable, no pending snapshot update**. The saved pre-failure GPT had A active, successful and bootable. With explicit user approval, `fastboot set_active a` made A bootable again, followed by one normal reboot. Original Android started successfully. **No firmware image was flashed and no data was erased.**

This resolves the observed boot loop. The underlying reason for the failed read and changed A bootability is still unknown. A full firmware restore was not performed or tested; the successful operation was boot-selection recovery. [Recovery evidence](boot-loop-recovery-2026-11-11.json).

## Protected recovery kit

A separate private file copy on this Mac contains **31 own-device partition images, GPT metadata, the matched manufacturer full OTA ZIP, its 13 extracted images, and verification/recovery records**. All copied asset sizes and SHA-256 values were verified. The initial assembly was 58 assets, 8,226,837,641 bytes; final evidence additions are recorded in the [inventory](recovery-kit-inventory-2026-11-11.json). Files are read-only, and directories are private. This protects against accidental editing, not loss of the Mac.

The stock OTA contains all five complete logical OS images (`odm`, `product`, `system`, `system_ext`, `vendor`). Exact original `super` metadata/extents, 45 selected raw partitions, auxiliary eMMC areas and RPMB remain uncaptured. Userdata and incomplete files are excluded. **This is verified stock firmware and partial own-device recovery material, not a complete device backup or a tested restore kit.** [Coverage review](recovery-kit-gap-review.md).

The kit is at `/Users/kjsegovi/Projects/BooxOS/.private/recovery-kit-GoColor7_2-20261111`. Its README and manifest describe coverage and limits. Configuration images remain private even though personal userdata was omitted.

## Current boundary

Leave the reader in normal Android. Both EDL controllers now stop before device access while the incident hold exists. Do not repeat the extended EDL read, blindly restore GPT/misc/metadata, or start LineageOS from this kit. A supported capture/restoration method, exact layout/AVB/reset/slot plan and review of the incident remain necessary. No documented compatible raw backup path through this stock Android 11 fastbootd or the ordinary unrooted Android shell was established. [Source review](recovery-kit-gap-review.md).

## Downloads copy

At the user’s request, a separate local copy was placed in `/Users/kjsegovi/Downloads/BOOX-Recovery-GoColor7-GenII-2026-11-11`. All 64 files, totaling 8,226,869,408 bytes including README and manifest, passed exact size and SHA-256 checks. Existing files were not overwritten. The folder is private and its files are read-only. This remains on the Mac; no external-drive copy was made. [Copy verification](recovery-kit-downloads-copy-2026-11-11.json).
