# Go Color 7 Gen II — backup and stock recovery research

Checked **2026-11-11** for **GoColor7_2**, installed display build **`2026-04-21_13-54_4.2-rel_0421_19324b3ea`**, Android 13 system / Android 11 vendor, Qualcomm SM6350 (`lito`). This note records source research, a proposed backup standard, and unresolved checks. **It is not a flashing procedure.** No device reboot, EDL/recovery entry, root, unlocking, boot-slot change, or firmware write was performed for this research.

**Later offline update:** the coordinating investigation has now completed matching OTA/image/signature checks and pinned the programmer. See the final appendix and [validation record](stock-firmware-validation-2026-11-11.json); those results supersede the earlier pending offline-validation statements below. Device backup and restoration remain untested.

## Finding

**A plausible exact-model backup route exists through Qualcomm EDL and a publicly catalogued Firehose programmer. A complete, demonstrated stock restoration route for this particular device and installed build is still unverified.** Matching stock OTA images are valuable, but they do not replace a backup of this unit. An October exact-model account using the same Android system build reports that the OTA omits boot-chain configuration needed after destructive mistakes. [Exact-model owner account](https://www.mobileread.com/forums/showthread.php?p=4617000), [programmer maintainer's model table](https://www.temblast.com/ref/onyxldr.htm).

The practical prerequisite for a LineageOS experiment is therefore **validated own-device backup plus verified access and exit routes**, alongside matching stock software. An Android boot property reporting “unlocked” is insufficient evidence that BOOX's fastboot can boot or flash an image. The older exact-model rooting guide now explicitly warns against following its instructions after reports of devices becoming unbootable. [Guide author's warning, updated May 7, 2026](https://buduroiu.com/blog/taming-boox-gocolor7/).

## What is already known locally

The saved [device inventory](device-inventory-2026-11-11.json) reports slot `_a`, Virtual A/B, dynamic partitions, root-only boot/super block devices, and an ordinary ADB shell (`uid=2000`). It also records COW mappings; merge state was not established. The boot properties report `orange` / `unlocked` / `flash.locked=0`. The user reports no previous modifications. These observations do not establish actual fastboot behavior, working recovery, or EDL access. No raw partition backup exists yet.

The main eMMC has many partitions outside `boot` and `super`, including both `xbl_config` slots, `persist`, `onyxconfig`, `devinfo`, `frp`, `metadata`, `keystore`, `modemst1/2`, `fsg` and `fsc`. Their names and existence are recorded locally; their exact contents and which contain unique calibration, identity or security state have **not** been inspected. Treat them as own-device preservation material until classified, and keep any future dumps private.

## Stock package evidence and limits

A primary community post from August 18, 2026 lists the exact vendor/boot build ending **`19324b3ea/8525`**, with a **1,948,279,067-byte** BOOX OTA and published MD5 **`2ec25cae46406260b5537683031e24db`**. This corroborates the candidate found by the coordinating investigation; download, digest validation, decryption, package metadata and extracted partition manifest must be recorded separately before treating it as a validated local restore asset. [Exact-build firmware listing and ensuing recovery report](https://www.mobileread.com/forums/showthread.php?nojs=1&t=374907).

The same thread contains an important limitation: a user reports recovery rejecting a decrypted package because its timestamp is older by about eleven minutes. The discussion does not conclusively identify the cause. **Even the same BOOX “4.2” label does not establish that stock recovery will accept a particular package.** Do not assume a downgrade, equal-version reinstall, or sideload succeeds solely because the filename/model looks correct. [Reported timestamp rejection](https://www.mobileread.com/forums/showthread.php?nojs=1&t=374907).

Android distinguishes **full** OTAs from **incremental** OTAs: incremental packages require their expected source build; full packages carry the update's final images but still require a device capable of applying them. This says nothing about the inclusion of every factory or per-device partition. The actual BOOX payload manifest is the controlling evidence for what this package can reconstruct. [AOSP OTA package documentation](https://source.android.com/docs/core/ota/tools).

### Exact-model evidence for the missing pieces

An October 2026 owner reports working EDL reads/writes with the candidate programmer on **Go Color 7 Gen II**, system build **`GV2.027.SQ83A`**, incremental **546**, patch **2026-04-01**—matching the local system properties. Their payload list contains `abl`, `boot`, `dtbo`, `modem`, `odm`, `product`, `recovery`, `system`, `system_ext`, `vbmeta`, `vbmeta_system`, `vendor` and `xbl`, but **no `xbl_config`**. They had also damaged `super` and erased other state; restoring OTA images did not produce a working device. A donor `xbl_config` improved signs of life but did not complete recovery. This is a first-person failure report, not a controlled experiment or proof of irrecoverability. [Owner's account and follow-up](https://www.mobileread.com/forums/showthread.php?p=4617000).

**Inference:** raw `super` with its logical-partition metadata, the complete boot chain, both physical slots, GPTs and own-device state matter more than a `boot_a` backup alone. `system.img` is a logical filesystem image; it cannot be substituted for the physical `super` container. AOSP documents that `super` includes the metadata assigning logical names and block ranges. [AOSP dynamic partition implementation](https://source.android.com/docs/core/ota/dynamic_partitions/implement).

## Access routes: evidence versus what remains untested

| Route | Source evidence | Status for this unit |
| --- | --- | --- |
| Authorized Android ADB | The standard client provides bootloader/recovery/sideload reboot targets and file transfer. Those are interface definitions, not promises that every vendor mode works. [ADB reference](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md) | Working for the saved read-only inventory. Root-only raw partitions remain inaccessible to the current shell. |
| Stock recovery | Exact-model owners report reaching recovery, including after slot-related complications in a modified bootloader setup. [April account, posts 54–60](https://www.mobileread.com/forums/showthread.php?page=4&t=372058) | Entry, usable screen/buttons, available menu options and safe return to Android are untested. |
| Bootloader fastboot | Older exact-model guide reports flash commands rejected as unknown; its author later withdrew the procedure. [Author's account and warning](https://buduroiu.com/blog/taming-boox-gocolor7/) | Android properties suggest unlocked state, but command implementation/support has not been verified. |
| Userspace fastboot (`fastbootd`) | It is a distinct Android mode, normally reached through recovery; it supports logical partitions. [AOSP fastbootd documentation](https://source.android.com/docs/core/architecture/bootloader/fastbootd) | Presence and capabilities untested. Do not confuse bootloader fastboot with fastbootd. |
| Qualcomm EDL | Programmer maintainer explicitly lists **Go Color 7 (Gen2)** in its SM_BITRA row; an exact-system-build owner reports it working. [Model table](https://www.temblast.com/ref/onyxldr.htm), [owner report](https://www.mobileread.com/forums/showthread.php?p=4617000) | Strongest candidate for obtaining a backup without first rooting Android. Entry, USB connection, successful storage reads and exit are untested here. |

### Recovery buttons: no verified exact-build recipe yet

The public evidence does **not** establish an official, model-specific physical recovery sequence for GoColor7_2 on this build. An independent demonstration's description explicitly names Gen II and describes holding power for about eight seconds then five rapid presses; the full footage and exact hardware identity were not verified in this research. It is a lead, not a proven procedure for this unit. [Demonstrator's video description](https://www.youtube.com/watch?v=lNa1r_zI0oE).

An older first-person report describes repeated power presses around the logo, but dates to January 2025 and names Go Color 7 without Gen II. It must not be promoted to exact-model evidence. [Older owner report](https://www.reddit.com/r/Onyx_Boox/comments/1hrgsmp). A model-specific BOOX support response or a later bounded, observed recovery-entry test would close this gap. Entering a menu would not itself authorize selecting reset, update, wipe or any other modifying option.

### Recovery ADB is not the current Android ADB session

AOSP explains that recovery does not normally inherit Android's host authorizations from `/data`. A production recovery can expose only restricted interfaces; a sideload connection does not establish an unrestricted root shell, raw partition backup, or decryptable user files. This is a general implementation explanation, not inspection of BOOX's recovery image. [AOSP recovery README, ADB and authorization sections](https://android.googlesource.com/platform/bootable/recovery/+/refs/heads/main/README.md).

### Community bootloader recovery recipes are not a stock return plan

The April exact-model report succeeds after using GoColor7_2 stock assets with a **Fairphone ABL**, changing active slot and resetting data. The surrounding monochrome Go 7 recipe reports that putting stock ABL back caused another failure. Those are materially modified states, not evidence of a complete return to original stock. [April reports](https://www.mobileread.com/forums/showthread.php?page=4&t=372058).

A later exact-model owner reached recovery and performed reset but still could not boot. The earlier successful participant explicitly acknowledges that they did not record the full sequence and cannot give an exact prescription. Another participant objects to flashing foreign-device bootloader code. [May follow-up, posts 76–87](https://www.mobileread.com/forums/showthread.php?page=6&t=372058). June 4.2 success reports in the thread explicitly describe **monochrome Go 7**, not this color model. [June reports](https://www.mobileread.com/forums/showthread.php?page=7&t=372058).

**Conclusion:** do not use foreign ABL, altered FRP, `devinfo` erasure, slot switching, or a reset as speculative backup-enabling steps. These reports help explain failure modes; they do not justify changing a functioning device before preserving its original state.

## EDL programmer and backup requirements

The maintainer's table, updated **October 21, 2026**, maps **HWID `0013f0e1` / SM_BITRA / Go Color 7 (Gen2)** to the public programmer **`0000000000000000_bdaf51b59ba21d8a_fhprg.bin`**, hosted under `bkerler/Loaders/lenovo_motorola`. This is exact-model maintainer evidence, despite the repository folder's vendor name. It does not authenticate any arbitrarily renamed copy or prove compatibility with every firmware/security configuration. [Maintainer table](https://www.temblast.com/ref/onyxldr.htm), [linked binary repository](https://github.com/bkerler/Loaders/blob/main/lenovo_motorola/0000000000000000_bdaf51b59ba21d8a_fhprg.bin).

The EDL tool documents macOS support, requires the device in USB **9008** mode, and supports reading eMMC GPTs, individual partitions and the whole main flash. Its read capabilities are useful for backup; its write/erase capabilities are outside this stage. [EDL tool's own documentation](https://github.com/bkerler/edl).

Before any future device session, preserve the programmer's source revision, exact byte size and SHA-256, pin the EDL tool revision, and inspect the selected read path. A programmer is code loaded onto the device; selecting a nominally read-only operation is not passive USB observation. The current research has not loaded this programmer or established its storage initialization behavior on this unit.

### Proposed acceptance standard for an own-device backup

These are engineering requirements proposed for this project, not a claim that a dump has been produced:

1. **Preserve ordinary files first.** Export required documents, annotations and app-supported backups while stock Android works. Validate sample files on the Mac. Do not equate shared-storage copying with all private app data or DRM entitlements.
2. **Establish update state.** Resolve snapshot/merge status before defining the storage checkpoint. Do not trigger, cancel or reset an update merely to make the state look simpler.
3. **Qualify EDL access without persistent writes.** Verify hardware/storage identification, programmer acceptance, GPT reading and a small partition read before a long dump. Record the expected exit path and its observed return to the same Android build/slot. This requires a separately authorized mode transition; it has not occurred.
4. **Capture an offline main-flash image and partition inventory.** Preserve GPT data, both physical boot-chain slots, complete `super`, all manufacturer/configuration partitions and—if consented and feasible—`userdata` and `metadata` from one coherent checkpoint. A second read or selected independent rereads must establish byte consistency, not merely a successful exit code.
5. **Validate locally.** Record byte counts and SHA-256 for the raw image and extracted partition files; validate both GPTs and logical-partition metadata, and ensure partition extents fit the device. Keep two protected copies, with a manifest containing no serials, credentials or account contents.
6. **Prepare a reviewed restoration map.** Map every intended future change to its exact own-device restore asset and access method. Missing partition assets, inconsistent snapshots, an unverified exit route or dependence on a foreign bootloader keep the experiment unready.

EDL's documented whole-flash operation supports the preservation goal, but “whole flash” should not be read as “every hardware security state.” Hardware-backed key state and rollback protection can make a byte-perfect storage dump insufficient to reverse all later security transitions. This is an inference from Android's key architecture, not a BOOX-specific recovery test. [EDL documentation](https://github.com/bkerler/edl), [AOSP file-based encryption and KeyMint integration](https://source.android.com/docs/security/features/encryption/file-based).

## User data, calibration and encryption limitations

Restoring operating-system images and restoring the user's previous working environment are different outcomes. Metadata encryption stores protected key blobs in the `metadata` partition; userdata alone is insufficient where that scheme applies. FBE keys also depend on hardware-backed key services and the trusted boot state. The local inventory did not establish the exact active encryption configuration, so this note does not claim that any proposed dump is already decryptable or guaranteed to survive a reset. [AOSP metadata encryption](https://source.android.com/docs/security/features/encryption/metadata), [AOSP FBE](https://source.android.com/docs/security/features/encryption/file-based).

Do not overwrite own `persist`, configuration, FRP, security or identity data with donor partitions. No BOOX factory source was found documenting the full calibration/unique-state partition map for GoColor7_2. Preserving every original partition avoids guessing which small areas can be reconstructed. It does not make publishing those dumps appropriate.

Virtual A/B adds a further consistency issue: current logical partition contents can depend on COW snapshots that later merge into the base. Therefore a raw `super` copy taken while snapshot dependencies remain unresolved may not describe the currently booted operating system by itself. COW mappings alone do not tell us whether a merge is pending, complete or in progress. [AOSP Virtual A/B overview](https://source.android.com/docs/core/ota/virtual_ab).

## Safe next milestone

**Complete offline stock-asset validation first:** finish the matching OTA download, verify its published digest and local SHA-256, decrypt it without changing its contents, confirm `pre-device=GoColor7_2` and matching build metadata, and enumerate the payload images. Compare that manifest with the saved partition inventory and explicitly list all uncovered partitions.

After that, prepare a bounded **backup-only EDL qualification** for review: entry and exit, programmer identity, host requirements, storage read operations, required free space, consistency checks and stop conditions. Its authorization must explicitly cover the mode transition and programmer execution. Do not include root, bootloader changes, unlock/relock, slot changes, flash, erase, update, or factory reset. A later restore plan must be reviewed against the actual validated backup rather than copied from a rooting tutorial.

Until those checks pass, **stock restoration remains a candidate route, not a demonstrated safety net**, and a LineageOS flash is premature.

## Verification boundaries

- Web sources were retrieved on 2026-11-11; some forum responses are cached. Community reports are primary accounts of their authors' devices and limitations, not manufacturer guarantees or independently reproduced results.
- No exact-model BOOX service/QFIL factory bundle or complete official restoration manual was verified.
- A public programmer was identified and linked; it was not downloaded, hashed, executed or independently reverse engineered in this subtask.
- The matching OTA candidate was independently corroborated in a public exact-build listing. Actual download/decryption/manifest evidence is owned by the coordinating investigation and must be recorded before upgrading its status.
- No live device action occurred. No recovery button sequence, fastboot support, sideload acceptance, EDL entry/exit, backup integrity, or restoration was tested here.

## Appendix — pinned EDL read-path review and proposed session

**Still pending user approval; no hardware execution.** Reviewed `bkerler/edl` master at **`1cda1a616748d608667b2d13b73a28d3197ceb45`**, package **3.62**. Public source files and their SHA-256 manifest are preserved under `.local/edl-source-review/1cda1a616748d608667b2d13b73a28d3197ceb45/`. This is a bounded review of normal Firehose connection/read/exit paths, not an audit of the programmer binary or every tool feature. [Pinned package metadata](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/pyproject.toml#L5).

The [offline validation record](stock-firmware-validation-2026-11-11.json) now records the exact system/vendor build match, full payload with no old-partition dependency, 13 verified extracted image hashes, and ZIP/payload signatures verified under a copied device update certificate. It also records programmer revision **`afb01ac1de3a2c2dbb7a622a04706c4899ff9a08`**, **759,504 bytes**, SHA-256 **`1eadbcd4c5e64d7f7ae6b13f51f548148d53c7163fe960e50840e03daa742e73`**. Its acceptance on this unit is untested. The 683-second difference between Android-system timestamp `1776750860` and vendor/boot timestamp `1776751543` is now observed locally; it does not establish what recovery would accept.

### What the selected code actually does

| Path | Reviewed behavior and consequence |
| --- | --- |
| Connection | Uploads the selected programmer through Sahara, then enters Firehose, negotiates `configure`, probes storage sector 1 and obtains storage information. This executes device-side code and initializes storage; it is not passive observation. Sahara handshake failure can automatically issue reset. [Entry/handshake](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/edl.py#L293), [configuration](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L890) |
| Memory and LUN | Supply **eMMC, LUN 0, 512-byte sectors** explicitly for reads. Otherwise chipset/capability guesses can choose UFS. Some configuration-error branches can change memory type even after an explicit selection; other branches adapt sector size. Stop on unexpected negotiation rather than accepting fallback as qualification. [Client defaults/LUNs](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose_client.py#L52), [fallbacks](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L917) |
| Configure side effects | Default XML carries **`SkipStorageInit=0`** and **`SkipWrite=0`**. The read-command grammar does not accept the advertised `--skipwrite` switch, so it cannot be casually added as a read safeguard. Automatic Xiaomi/Nothing authentication paths can run when corresponding responses/functions appear. Stop on such an unexpected path. [CLI grammar](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/edl.py#L17), [configure](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L897) |
| `printgpt` | Reads GPT sectors through `get_gpt` / `cmd_read_buffer`, parses and prints them. No program, patch, erase or GPT-repair call was found in this normal path. [Dispatch](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose_client.py#L224), [GPT reads](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L781) |
| Partition `r` | Finds a partition in GPT, then sends Firehose `<read>` for its extent and writes the returned bytes to a host file. It does not call flash-writing helpers. Its outer handler can report success despite a failed inner read, so verify ACK, expected byte count and hashes. [Partition dispatch](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose_client.py#L235), [transfer](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L659) |
| Full `rf` | For eMMC, derives length from parsed GPT and calls the same read transfer from sector 0. The GPT parser computes total sectors as `first_usable_lba + last_usable_lba`; independently compare that with reported physical capacity and backup-header location before trusting coverage. `rf` also returns true after some failure paths. [Full-read dispatch](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose_client.py#L333), [size calculation](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/gpt.py#L406) |
| GPT export/cache | The separate `gpt` command prints dump-success messages while its actual binary-file writes are commented out in this revision. Do not use those messages as backup evidence. Connection also writes/reads a local `edl_config.json` cache that can contain a serial and remembered capabilities: use a fresh private session directory and retain raw logs privately. [Export handler](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose_client.py#L191), [cache](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L1207) |
| Exit | Firehose reset sends a power/reset request; it does not itself restore firmware. A fresh CLI `reset` invocation still performs connection/configuration, but its grammar does not accept explicit memory selection. Resolve the controlled exit implementation before entry—for example, a reviewed same-client reset after the final read—rather than assuming a generic reset invocation shares the read session's settings. [Reset primitive](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/firehose.py#L331), [reset grammar](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/edl.py#L53) |

GPT repair and slot changes exist in other methods but were not called by the three normal read paths reviewed. This conclusion concerns host command selection; it does **not** prove that the opaque programmer performs no internal persistent actions. Reads also lack a robust hard deadline for stalled/empty transfers. Bound the session externally, treat incomplete files as failures, and do not automatically retry or escalate to repair commands.

### Mac preparation

Normal Firehose reads do not require Keystone or Capstone. Their imports in `utils.py` are explicitly optional, and the traced read methods do not call the assembler/disassembler helpers. An installed incompatible native package can still raise an error outside the caught `ImportError`; omitting an unusable package is preferable to forcing it into the environment. [Optional imports and helpers](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Library/utils.py#L24).

Use an isolated Mac environment, pinned source and the supplied ARM64 libusb. Validate imports and CLI help without entering the tool's connection loop. Python's declared minimum is 3.10, which alone does not establish compatibility with the host's 3.15 interpreter or every dependency. The Mac remains the proposed backup host; no Windows or Linux move is required by these reviewed read paths.

### Proposed bounded qualification and full-backup sequence

The following is a reviewable scope, **not authorization or a runnable script**:

1. **Before entry:** complete ordinary-file exports; record the unresolved snapshot/merge state, build, slot and battery; confirm private storage and the explicit exit/failure handling. Qualification reads of GPT and boot configuration do not establish logical-partition consistency. Resolve the checkpoint/consistency design before treating a later full dump as a validated rollback asset.
2. **Approve entry and exit together:** one deliberate transition from functioning Android to EDL, execution of the pinned programmer, storage configuration/read operations, and reset back to Android. Include the tool's possible handshake-failure reset in the reviewed scope. Hardware EDL-cable entry remains a fallback requiring its own concrete method, not an assumed automatic recovery.
3. **Qualify once:** confirm USB 9008, expected chipset, eMMC/512/LUN 0 and plausible capacity; read/parse GPT; read `xbl_config_a` twice and compare exact expected length and SHA-256. Stop on unexplained negotiation, auth, GPT, transfer or size errors. No write, erase, provisioning, repair or slot command is part of this session.
4. **If qualification and snapshot consistency pass:** make a whole-main-eMMC read, verify its exact capacity and both GPTs offline, then make an independent second read or a defined integrity sample plus repeat critical partition reads. Preserve all original partitions, including userdata/metadata, in the private raw image. The default proposal includes these sensitive contents; user approval must cover that scope.
5. **Exit and validate:** use the reviewed reset path; observe return to the same Android build and active slot; retain all originals plus a second protected copy. Extract partition files and logical-partition metadata locally from the validated image; do not depend on the broken GPT export messages. No restore, root, unlock/relock, update or flashing is included.

**Hardware acceptance still missing:** EDL entry, correct-programmer execution, `configure` acceptance without unexpected fallbacks, read ACK/data integrity, whole-main-area coverage, stable Mac USB transport and successful exit to Android. A good offline source review does not close these gaps or prove restoration works.

## Coordinating verification and proposed first device session

The user selected a **LineageOS-based Android port** as the project direction. The MacBook remains the preferred main workstation; a Windows computer is available, but no build host has been configured. This choice does not establish a compatible color-model LineageOS image.

The complete manufacturer-hosted `update.upx` is saved under `.local/firmware/GoColor7_2/2026-04-21_13-54_4.2-rel_0421_19324b3ea/`. Its size is **1,948,279,067 bytes**, published MD5 matches, and locally calculated SHA-256 is **`35f7fbeb00296bd2acb7628463148f08ae49977f06f681203d8627c2f3415648`**. Its decrypted ZIP passes CRC checks. `pre-device`, Android system fingerprint, SDK, incremental build and the exact vendor fingerprint match the connected reader. All **13 full-payload images** have been reconstructed and checked against their payload SHA-256 values. The whole-ZIP, payload-metadata and payload-file signatures verify using the public update certificate copied read-only from this reader. That certificate is named `testkey.x509.pem`; signature validation under it is an integrity check, not proof of an exclusive manufacturer signing identity. [Local validation evidence](stock-firmware-validation-2026-11-11.json).

The update supplies `abl`, `boot`, `dtbo`, `modem`, `odm`, `product`, `recovery`, `system`, `system_ext`, `vbmeta`, `vbmeta_system`, `vendor` and `xbl` (13 total). It does **not** supply the complete physical `super` container/GPT, `xbl_config_a/b`, manufacturer state, `metadata` or `userdata`. The machine-readable evidence includes the full uncovered partition list. It is a matched stock update asset, not an own-device disk backup or a demonstrated restore.

Host preparation is complete for the initial qualification: the pinned Python 3.62 tool's offline `--help` exits successfully under this Mac's project-local Python environment, its imports succeed, and the installed ARM64 libusb loads. Dependencies are recorded privately under `.local/firmware-tools/edl/dependency-versions.txt`. No EDL connection or programmer execution was performed. The current main eMMC exports **122,142,720 sectors of 512 bytes = 62,537,072,640 bytes**; normal Android still reports the original build and slot `_a`. A future main-area image must cover that size after independent comparison with EDL storage information and both GPTs.

**Proposed first device session, awaiting approval:**

1. Recheck the model, build, current slot, battery and ordinary Android ADB connection. Use a fresh ignored `.private/` session folder for raw device logs, GPT and unique boot-configuration reads.
2. Deliberately restart from Android into Qualcomm EDL and confirm the expected USB mode/hardware identity. Load only the pinned, hashed candidate programmer into RAM. No root, unlock, flash, erase, update, boot-slot change or factory reset is included.
3. Explicitly select eMMC/LUN 0/512-byte sectors, read and validate the GPT and capacity, then read the small `xbl_config_a` partition twice. Check exact lengths and SHA-256 agreement. Stop on unexpected identity, negotiation, authentication, incomplete transfer or inconsistent data. This first session does not include a whole userdata/main-flash backup.
4. Keep the configured client connection available for exit. The selected source exposes an imported `main(args)` session that can return with `cdc_close=False`; after reads, its existing `session.fh.firehose.cmd_reset("reset")` sends the reviewed power/reset XML without a new memory-selection/configuration pass. This same-client exit design is source-reviewed but not yet hardware-tested; any live implementation needs a bounded supervisor because the library's disconnect/read loop can stall.
5. Observe the return to Android and recheck the same build and slot `_a`. A successful qualification permits planning the full private 62.54 GB main-area backup; it does not establish a tested restoration path. If access or exit does not work as expected, stop this experiment and diagnose the actual state rather than trying a different bootloader or writing a partition.

This session requires explicit approval because it restarts a working reader and executes opaque service code in its RAM. Research/read-only Android inspection has not silently authorized that transition. No approval has been supplied yet.

BOOX documents holding the power button for **20 seconds** as its general forced-reboot method. This is a manufacturer-documented fallback to have ready with the user physically present, not evidence that exit from this unit's EDL session has already been tested. If the controlled reset does not return to Android, stop and assess USB/power state before any further action. [BOOX frozen-device guidance](https://booxsupport.zendesk.com/hc/en-us/articles/7900405304340-What-to-Do-If-My-Boox-Device-Is-Frozen-Unresponsive-Stuck).

## Approved backup-access test — 2026-11-11

The user explicitly approved the proposed read-only backup-access test. Final checks confirmed the same GoColor7_2 build and slot `_a`, completed Android startup, 99% battery, and unchanged pinned source/programmer files. A bounded controller restricted Firehose XML to configure/read/query/reset, required eMMC/LUN 0/512-byte sectors and `SkipWrite=1`, blocked storage-writing/erase/patch commands, limited reads to GPT and the selected small configuration partition, and enforced a time/read budget. Its host-only negative tests checked write-command rejection, read bounds and corrupted GPT rejection before any mode transition.

Android successfully entered Qualcomm USB **9008** mode. The Sahara identity query reported the catalogued chipset family, but the reported public-key hash did not match the programmer filename's expected prefix. The controller stopped **before** uploading the RAM programmer and before any GPT or storage read. The copied programmer's acceptance/execution remains untested. The current tool categorizes the reported root as `secboot_sha2_pss_subca2`; whether that means the filename comparison was overly strict still requires offline source/certificate analysis, and no alternate programmer was tried.

The Sahara restart request did not return the reader to Android. At the assistant's direction, the user held the power button for 20 seconds, after which Android booted. A fresh ADB check verified **GoColor7_2**, original build **`2026-04-21_13-54_4.2-rel_0421_19324b3ea`**, and slot **`_a`**. No programmer upload, storage read/write, root, unlock, slot change, wipe or firmware installation occurred. The outcome is **stopped before upload, Android restored**, not a passed backup qualification. [Test evidence](backup-access-test-2026-11-11.json).

Raw identity logs are retained in an ignored private session directory. The public test record excludes device serials and the actual public-key hash. No full backup or demonstrated restore exists; further operational entry requires resolving the programmer-identity assumptions first.

### Offline follow-up to the stopped test

The pinned programmer parser reproduces the catalogue filename using **SHA-384** of the first ELF's third certificate. That span is exactly the certificate DER bytes, so this mismatch is **not** explained by comparing SHA-256 with SHA-384 or by certificate padding. Neither that root nor the second ELF's root matches the device-reported SHA-384 value. The tool's recognized root-category label alone is insufficient to demonstrate this programmer's acceptance. This establishes an unresolved compatibility gap; it does not prove that the device would reject every programmer or that EDL backup is impossible. No guard was bypassed and no second service-mode entry was made. [Pinned parser](https://github.com/bkerler/edl/blob/1cda1a616748d608667b2d13b73a28d3197ceb45/edlclient/Tools/fhloaderparse.py#L116).

The next prerequisite is independent evidence for a programmer appropriate to the signing identity actually reported by this unit, or a different model-specific backup route. Current readiness remains **no firmware installation**: matched stock OTA assets exist, but an own-device backup, programmer acceptance and a demonstrated restore path do not.

## Compatibility interpretation correction — 2026-11-11

The certificate-digest mismatch in the first test is real, but **it did not establish that the programmer is incompatible**. The test stopped in our host-side gate before uploading it, so the BOOX never accepted or rejected it. That gate assumed that the ROM-reported digest must match the loader filename/embedded root; that requirement had not been established for this BOOX.

A direct comparison now confirms that a same-model first-person report has the same complete hardware identity, reported key and eMMC capacity as this unit and reports using the original pinned programmer for GPT/partition reads. The report names the same Gen-II OTA/system assets, but its author explicitly did not know the original installed firmware before damage; do not present it as a controlled qualification on our current stock build. A separate 2025 exact-model report also shows the same reported identity and successful upload of that programmer. These reports support a bounded retry, not a guarantee of programmer safety, local storage access or restoration. [October report](https://www.mobileread.com/forums/showthread.php?p=4617000), [earlier upload report](https://www.mobileread.com/forums/showpost.php?p=4517275&postcount=6), [redacted comparison evidence](programmer-compatibility-followup-2026-11-11.json).

The complete public loader catalogue was checked: files whose names match the reported key target other processors, and the two other explicit SM_BITRA entries target other OEM/model identities. Matching a filename digest alone is therefore not a sound replacement-selection rule. No alternate loader was executed or uploaded.

The revised host controller is prepared and its negative tests pass. It pins the **full observed hardware identity and reported key** to the corroborated same-model reference, and independently pins the **unchanged original programmer's exact SHA-256**. It retains Sahara version checking, eMMC/LUN 0/512-byte limits, `SkipWrite=1`, the XML command allowlist, bounds/read budget, blocked authentication paths and the same two small configuration reads. The original first-test controller was preserved byte-for-byte in its private session folder and its saved digest still matches. No new service-mode entry has occurred during this investigation.

**Recommendation:** the original programmer is still the strongest candidate for another bounded read-only qualification. It is not yet a locally verified programmer. Stock recovery and temporary boot have not supplied a better demonstrated whole-storage backup route; see the [alternative-route inspection](alternative-backup-routes.md). A repeated qualification would require a new service-mode restart under the revised comparison, with the user nearby for the now-observed manual restart fallback. The prior single-entry test is complete; this research has not performed that repeated session.

## Revised read-only qualification passed — 2026-11-11

The user explicitly approved the revised small-read test. The original pinned programmer was accepted and responded to Firehose commands on this unit. An initial configuration attempt stopped before storage reads because `SkipWrite=1` selected a NULL/simulated device; the programmer itself contains the message explaining that behavior. The reader reset automatically and returned to the original build and slot. That was a test-controller configuration error, not a finding that real storage was incompatible. [Configuration-attempt record](backup-access-test-2026-11-11-02.json).

The ongoing approved test continued after correcting that setting to the programmer's normal `SkipWrite=0` initialization. The explicit XML allowlist still blocked `program`, `patch`, `erase`, provisioning, repair and slot changes; memory remained eMMC, LUN 0, 512-byte sectors, with the same small-read bounds, pinned identities/binary and time/read budgets. The original controller for each attempt was retained in its private session directory. No firmware-writing command was sent.

**Verified outcome:**

- The device accepted the pinned RAM programmer and normal eMMC storage configuration. Its storage report agrees with the prior Android inventory: **122,142,720 sectors**, **512 bytes/sector**, product **C21E00**.
- Both GPT header CRCs and both partition-entry-array CRCs validate, and the two GPTs agree. The parsed table contains **80 partitions**.
- Two independent reads of **`xbl_config_a`**, **131,072 bytes each**, are byte-identical. The saved file starts with an ELF header. Hashes and original files remain in the ignored private session folder, alongside the original GPT metadata.
- The recorded host commands were one configure, one storage query, eight bounded reads and one power/reset request. No storage-writing/erase/patch command was observed; the total requested read size was **284,672 bytes**, including the initial probe.
- The programmer's reset was acknowledged, Android restarted **automatically**, and fresh ADB checks confirmed **GoColor7_2**, original build **`2026-04-21_13-54_4.2-rel_0421_19324b3ea`**, and slot **`_a`**. No manual restart was required.
- Android reports file-based encryption and metadata encryption enabled; Virtual A/B remains enabled.

The [successful test record](backup-access-test-2026-11-11-03.json) includes an independent host-side verification of the saved files. The first guard-stopped attempt and the later NULL-disk configuration attempt remain separately recorded. This qualifies the programmer and Mac transport for these **small reads and return to Android**, not yet a long whole-main-area transfer or a restoration.

### Next backup milestone

The next step is a separately scoped **62,537,072,640-byte (62.54 GB / 58.24 GiB) main-eMMC backup** to private storage on the Mac, including GPT, both slot sets, complete physical `super`, the snapshot backing data, `metadata` and encrypted `userdata`. It was explicitly excluded from the small-read test and has **not** been taken. Storage reports four physical areas; only LUN 0 was qualified. Any ancillary boot/RPMB-area inventory needs explicit scope and supported non-writing read semantics; do not claim a main-area image captures all hardware-backed state.

A full-backup plan should keep one offline checkpoint, preserve every COW/snapshot dependency, validate the exact file length and both GPTs, hash the complete image, reread critical partition extents, and preserve a second protected copy. Do not change update/merge state or flash anything merely to simplify the backup. Restore acceptance, hardware-backed encryption/rollback effects and actual write recovery remain untested; matching stock OTA files alone remain insufficient.


## Smaller recovery backup requested — incomplete first capture

The user replaced the full-userdata preservation goal with a smaller firmware recovery backup. A 76-partition 8.056 GB LUN0 scope was prepared, excluding userdata and apparent diagnostic logs. The first capture stopped after 31 verified partitions on a read failure; original Android return is awaiting physical restart verification. No storage-writing commands or userdata reads were observed. [Current backup status](recovery-backup-status.md), [attempt record](recovery-backup-attempt-2026-11-11-01.json). The old full-main-image proposal is superseded by this user choice; no complete recovery backup or tested restore exists yet.


## Original Android recovered; EDL procedure held

The user reached older slot-B stock recovery, entered fastbootd, and queries showed B current while A was unbootable. Saved pre-failure GPT showed A bootable. With explicit approval, one `set_active a` and normal restart restored original April 2026 Android; user confirmed home screen and increasing-uptime checks passed. No firmware image was flashed or data erased. Root cause remains unknown. The smaller backup is incomplete; protected offline recovery assets are assembled and both EDL controllers are gated against another entry. [Current status](recovery-backup-status.md), [recovery result](boot-loop-recovery-2026-11-11.json), [kit gap review](recovery-kit-gap-review.md). Earlier proposals to continue the service-mode capture are superseded.
