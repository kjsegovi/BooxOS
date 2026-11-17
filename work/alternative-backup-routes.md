# Go Color 7 Gen II — alternatives to EDL for an own-device backup

Checked **2026-11-11** for **GoColor7_2**, installed BOOX build **`2026-04-21_13-54_4.2-rel_0421_19324b3ea`**. This investigation used primary web sources and offline inspection of the already-validated stock OTA. **No live device command, mode entry, reboot, root operation or device write was performed.**

## Finding

**No better demonstrated whole-storage backup alternative was found.** Stock recovery is a production build with restricted ADB settings; BOOX's supported Library backup preserves books and reading data rather than firmware; temporary custom boot remains an unqualified possibility, with no verified exact-model image or command support here.

The coordinating investigation has independently matched an exact-model owner's reported hardware/signing identity and capacity to this unit; the reported Gen-II OTA/system assets also match. That owner reports successful GPT and partition reads using the original `0000000000000000_bdaf51b59ba21d8a_fhprg.bin` candidate. The owner did not know the original installed firmware before damage. This evidence is more relevant than the earlier assumption that the ROM-reported root hash must equal the programmer filename prefix. Our stopped session did **not** upload that programmer or test its acceptance. The sensible next whole-storage route remains a separately reviewed, bounded read-only qualification of that original candidate, with the corrected identity assumptions. Community success is evidence for qualification, not a local pass or a demonstrated restore. [Exact-model owner's report](https://www.mobileread.com/forums/showthread.php?p=4617000), [local stopped-test record](backup-access-test-2026-11-11.json).

## What the exact stock recovery contains

The inspected source is the **100,663,296-byte** OTA `recovery.img`, SHA-256 **`4f040455a462a516d1c8e2261d34c1e93e4d3a63564788899faa0359363d1ac7`**. It is Android boot image header v2, with a gzip ramdisk. These are direct offline observations, not conclusions drawn from a similar BOOX model. Source-image integrity is covered by the [firmware validation record](stock-firmware-validation-2026-11-11.json); extraction hashes and the ramdisk file index are preserved in [offline inspection evidence](../.local/alternative-backup-research/recovery-offline-inspection.json) and [CPIO index](../.local/alternative-backup-research/recovery-cpio-index.json).

| Item | Direct observation | Consequence / limit |
| --- | --- | --- |
| Kernel command line | `buildvariant=user` | This is not an engineering or userdebug recovery. |
| `prop.default` | `ro.secure=1`, `ro.adb.secure=1`, `ro.debuggable=0`, `persist.sys.usb.config=none` | The stock image does not advertise an unauthenticated root ADB configuration. |
| Build identity | `GoColor7_2-user`, release keys, matching vendor/boot build | These findings apply to the matched stock recovery asset, not a generic recovery. |
| ADB components | `system/bin/adbd`, `system/bin/minadbd`; normal adbd contains the production-root-refusal string | Presence of the programs does not establish that the user can get an authorized root shell. |
| Recovery services | Disabled `adbd` and `fastbootd` services; USB property triggers start each | Entering recovery and entering userspace fastboot are distinct runtime states. |
| Host keys | No `adb_keys` file in the 346-entry ramdisk | No built-in host authorization was found. |
| User interface strings | Reboot, sideload/update, wipe, mount system, logs, tests, fastboot/rescue | No full partition-backup menu or unrestricted ADB-enable menu was found by this static inspection. |

These settings matter because AOSP's Android 11 adbd drops to shell privileges when `ro.secure=1`; requesting root only overrides that in a debuggable build. An orange/unlocked state affects whether authentication *can* be disabled, but `ro.adb.secure=1` still requires it. This is source-backed interpretation of the stock settings, not proof that BOOX has no vendor-specific exception. [AOSP Android 11 adbd privilege/authentication logic](https://android.googlesource.com/platform/system/core/+/refs/heads/android11-platform-release/adb/daemon/main.cpp#69).

Recovery can start ADB on an unlocked device in current AOSP, so **`ro.debuggable=0` alone does not prove there will be no ADB USB connection**. However, a connection, a sideload endpoint, an authorized shell and a root shell are different capabilities. Recovery ordinarily cannot reuse normal Android's authorizations from `/data`; its production settings here give no established raw-read route. [AOSP recovery startup](https://android.googlesource.com/platform/bootable/recovery/+/refs/heads/main/recovery_main.cpp#477), [AOSP recovery ADB documentation](https://android.googlesource.com/platform/bootable/recovery/+/refs/heads/main/README.md).

**Assessment:** stock recovery is worth qualifying later as a recovery/exit capability, but current evidence does not justify using it as the preferred disk-backup route. This inspection did not decompile all BOOX binaries or prove the absence of every vendor-specific interface.

## Temporary boot and fastboot readback

`fastboot boot` has a different protocol meaning from `fastboot flash`: the host downloads an image into RAM and asks the bootloader to boot it. In principle, a compatible temporary recovery with a root shell and an audited read-only startup could read partitions without flashing itself. This still executes new code on the device, and its startup must be checked for mounts, snapshot activity and other writes; “RAM boot” does not itself guarantee unchanged storage. [AOSP fastboot protocol](https://android.googlesource.com/platform/system/core/+/refs/heads/main/fastboot/README.md#87).

**Missing here:** verified support for the boot command on this unit, acceptance of an unsigned/custom image, and an exact-model backup recovery that has been reviewed. An older first-generation Go Color 7 owner reports `fastboot boot` failing with unknown command; that is a warning against assuming support, not exact-Gen-II proof. The exact-Gen-II rooting author's withdrawn guide reports broken fastboot flashing and now warns against following the procedure. [First-generation owner's result](https://www.mobileread.com/forums/showthread.php?p=4432541), [exact-Gen-II author's updated account](https://buduroiu.com/blog/taming-boox-gocolor7/).

Modern `fastboot fetch` examples are also not a whole-flash-backup promise: AOSP makes fetch optional and restricts the illustrated implementation to `vendor_boot` and its slots. The local stock recovery `fastbootd` binary has no `fetch` or `max-fetch-size` strings. That negative string result is supporting evidence, not a complete binary audit. No unrestricted BOOX partition-read command was verified. [AOSP optional fetch implementation](https://android.googlesource.com/platform/system/core/+/25d759901/fastboot/device/commands.cpp).

**Assessment:** keep temporary boot as a fallback research project. Do not flash a custom recovery, patch boot, replace ABL or root the working reader merely to enable its first original-state backup.

## Supported personal-data preservation

BOOX documents **Library → Library Settings → Backup and Restore → Local Backup and Restore**. On firmware 4.1+, it creates a `.booxc` archive containing local books with their associated reading data, including annotations and themes. Copy that archive off the reader and check the copied file. This complements ordinary document copies and each third-party app's own export/sync features. The documented feature does not claim to capture GPT, bootloaders, calibration/configuration partitions, all private app data or a raw disk image. [BOOX's Library backup documentation](https://booxsupport.zendesk.com/hc/en-us/articles/25096430940436-Reading-Data-Syncing-and-Backup).

Android's older `adb backup` is not a full-device firmware backup. Android 12+ additionally excludes private data for non-debuggable apps targeting API 31+, so it cannot establish complete app-data preservation on this Android 13 system. [Android's ADB backup restriction](https://developer.android.com/about/versions/12/behavior-changes-12#adb-backup-restrictions).

## Concrete next path

1. Preserve personal documents and BOOX Library data while stock Android works; verify the copies on the Mac.
2. Finish the coordinating review of the original programmer evidence and the corrected pre-upload gate. Do not substitute a different loader merely because its filename appears closer to the reported root.
3. If the user authorizes another bounded session, qualify the original candidate: acceptance, expected eMMC capacity/GPT, two identical small partition reads, and return to the original Android build/slot. A failed acceptance or storage negotiation stops that session; it is not a reason to try bootloader writes.
4. Resolve Virtual A/B snapshot state and define a coherent full-main-area capture before the long backup. The matched OTA remains a stock software asset, and a successful read remains separate from a demonstrated restore.

Any optional future stock-recovery or bootloader-fastboot test should have its own concrete entry/exit plan and only named observation/read operations. This research authorizes none of those transitions. There is no verified alternative here that closes the current raw-backup gap without a new qualification.

## Subsequent local result

The coordinating revised EDL qualification has now **passed**: original programmer accepted, real eMMC/GPT reads validated, two 128 KiB boot-configuration reads identical, automatic return to the original Android build and slot. This supersedes the earlier pending-acceptance statements in this note. [Test evidence](backup-access-test-2026-11-11-03.json). A full backup and restore remain untested.
