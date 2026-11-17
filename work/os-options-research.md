# BOOX replacement OS options

Verified **2026-11-11**. The user confirmed the model as **BOOX Go Color 7 (Gen II)** and supplied the installed version string **`2026_04_21_13_54_4.2rel_0421_19324b3ea`**. A subsequent read-only USB/ADB inventory confirmed device identifier **GoColor7_2** and display build **`2026-04-21_13-54_4.2-rel_0421_19324b3ea`**. The string identifies the BOOX **4.2** firmware family and appears to encode a build timestamp of **2026-04-21 13:54**; no timezone is established. This is a comparison of public evidence and local observations, not an installation guide. The user enabled USB debugging and authorized the Mac; no firmware, bootloader, boot-slot or partition changes were made.

## Finding

**This research did not establish a public, ready-to-install replacement OS for the exact Go Color 7 Gen II.** The strongest leads are a public Android port for the different, monochrome Go 7; an exact-model PaperOS announcement; and an exact-model Linux kernel source repository. None of the inspected sources supplied a verified color-model release image plus matching installation and restoration instructions. This is a bounded search result, not proof that no private or unindexed project exists. [Go 7 device source](https://github.com/go7-lineage/android_device_onyx_Go7), [Go 7 releases](https://github.com/go7-lineage/android_device_onyx_Go7/releases), [PaperOS author announcement](https://www.reddit.com/r/Onyx_Boox/comments/1vcdkmh/paperos_a_native_linux_e_ink_os_now_running_on/), [Go Color 7 Gen II kernel source](https://github.com/cloudrumbles/boox-gocolor7-linux).

## Comparison

| Candidate | Public evidence checked | Exact-model installation status |
| --- | --- | --- |
| **LineageOS / go7-lineage** | Real device source targeting **Go 7**, with a Carta 1300 monochrome display; repository describes LineageOS 24.0. Its Releases page explicitly contains no releases. | **Not established for GoColor7_2.** Treat it as porting reference code until its maintainers provide color-model evidence. [Device README](https://raw.githubusercontent.com/go7-lineage/android_device_onyx_Go7/lineage-24.0/README.md), [repository](https://github.com/go7-lineage/android_device_onyx_Go7), [releases](https://github.com/go7-lineage/android_device_onyx_Go7/releases). |
| **Generic Android GSI** | Android provides generic system images for compliant devices, with prerequisites including an unlocked bootloader, full Treble compliance and suitable Android launch version. A GSI excludes manufacturer customizations. | **An engineering experiment, not a verified BOOX replacement.** No inspected primary source demonstrated a GoColor7_2 image, working color refresh and restoration procedure. Generic availability does not establish these outcomes. [Android GSI documentation](https://developer.android.com/topic/generic-system-image). |
| **PaperOS** | Its author names **Go Color 7 Gen II** as the first hardware target and reports native Linux userspace booting with the stock kernel, display/input/Wi-Fi/frontlight/suspend support. Publication of source, configurations and tools is still described as planned in the inspected announcement. | **Announced prototype; no installable public release verified.** The author's hardware reports are not independent validation. [Author announcement and comments](https://www.reddit.com/r/Onyx_Boox/comments/1vcdkmh/paperos_a_native_linux_e_ink_os_now_running_on/). |
| **Mainline-style Linux kernel** | `cloudrumbles/boox-gocolor7-linux` explicitly describes itself as a Linux 6.18 downstream for **Go Color 7 Gen II** and exposes kernel source. | **Source lead, not a complete OS.** The inspected repository did not establish a downloadable distribution, model-specific installation guide or verified working hardware matrix. [Repository](https://github.com/cloudrumbles/boox-gocolor7-linux). |
| **postmarketOS / other native Linux distributions** | Exact-model searches did not produce a verified port or release. The official postmarketOS device directory returned an access-denied page during this check. | **Unresolved; no exact-model image verified.** The blocked directory prevents a categorical claim that postmarketOS has no such port. [Official device-directory URL checked](https://wiki.postmarketos.org/wiki/Devices). |

## First hardware inventory — 2026-11-11

Primary local evidence: [targeted device inventory](device-inventory-2026-11-11.json). The user reports **no previous rooting, bootloader unlocking or custom firmware installation**. The observations below describe the device's existing state; no unlock was performed.

| Item | Device observation |
| --- | --- |
| Model/device | `GoColor7_2`, ONYX |
| Platform | Qualcomm `SM6350`, `lito`, ARM64 |
| Android system | Android **13**, SDK **33** |
| Vendor software | Android **11**, SDK/VNDK **30**; distinct from the Android 13 system |
| Kernel | `4.19.157-perf-g3d47a6619220-dirty` |
| Screen | `1264x1680`, density 300; device-tree model says `Go7 V20 for Color` |
| Treble / slots | Treble enabled; A/B and dynamic partitions enabled; current slot `_a`; Virtual A/B enabled |
| Bootloader report | `ro.boot.vbmeta.device_state=unlocked`, `ro.boot.flash.locked=0`, `ro.boot.verifiedbootstate=orange`; verity reports `enforcing` |
| Shell access | Ordinary ADB shell (`uid=2000`); root access was not requested or tested |
| Display interfaces | `/dev/ebc`, DRM card0/connectors, `onyx_bl_br` and `onyx_bl_ct` frontlight channels present |
| Partition sizes | Boot 96 MiB; recovery 96 MiB; DTBO 24 MiB; super 6 GiB. Calculated from kernel-exported sector counts using 512-byte sectors. |
| Battery at inspection | 84%, charging, from `dumpsys battery` |
| Required app packages | Kindle detected. Expected Libby, Audible and KOReader packages not detected; other profiles and alternative builds were not inspected. No accounts or content were inspected. |

The processor/platform, kernel baseline and these partition sizes align with the monochrome Go 7 project's [README](https://github.com/go7-lineage/android_device_onyx_Go7/blob/lineage-24.0/README.md) and [BoardConfig](https://github.com/go7-lineage/android_device_onyx_Go7/blob/lineage-24.0/BoardConfig.mk). This makes that code a relevant **porting reference**, not a compatible image. Its build explicitly retains stock kernel, DTB/DTBO and vendor modules; a color-model adaptation would need matched GoColor7_2 assets and display validation.

### Remaining readiness gaps

**Later progress on 2026-11-11:** the user selected **LineageOS-based Android** as the starting direction, with color-model adaptation still required. The matching stock OTA is now downloaded and validated: exact system/vendor identity, all 13 extracted image hashes, archive checks and ZIP/payload signatures passed. See [validation evidence](stock-firmware-validation-2026-11-11.json) and [the current backup/recovery plan](stock-recovery-research.md). These results supersede the earlier missing-download/image statements below. No own-device raw backup or restoration test has occurred. The user prefers the MacBook as the main workstation and has a Windows computer available for a later Linux build host if needed; no host setup was performed.

- The unlock report comes from the running Android system. Actual bootloader command support and recovery/restore behavior have not been tested. An unlocked report does not establish root access or prove that flashing commands work.
- Protected boot/super block devices are root-only, so ordinary ADB cannot make the required raw firmware backup. No firmware partition backup or matching stock image has been obtained. The two checked shared-storage `update.upx` paths were absent; the protected OTA directory was inaccessible.
- The mapped device list includes snapshot/COW devices. This alone does not prove that an OTA is pending. Snapshot merge state still needs to be established before a partition-writing plan. `bootctl` and `snapshotctl` were unavailable, this device's updater does not support `--status`, and a brief read-only `--follow` observer failed to bind to the updater daemon. None of these failures establishes the OTA state; no update action was requested.
- Color refresh, ghosting, input, audio, sleep/wake and the required apps have not been tested under a replacement system.
- Full current AOSP builds use a supported x86-64 Linux environment; Google lists 400 GB free space and 64 GB RAM. The connected Mac is useful for USB diagnostics and transfers, but native macOS is not a supported current AOSP build environment. A build host has not been selected. [Official build requirements](https://source.android.com/docs/setup/start/requirements).

Google's Platform-Tools **37.0.1-15733141** were downloaded from the official Mac download and unpacked under ignored `.local/`. Archive SHA-256: `ee39ad5967e95c2a07f04dbcbde96b1a0c916ba376096db5d2f498b7727a5d1d`. A separate local ADB server uses port **5041**. Device serials and account data are excluded from the saved inventory. [Official Platform-Tools download](https://developer.android.com/tools/releases/platform-tools).

## Evidence that is easy to misread

### Downloadable Android candidates versus an exact-model port

Existing generic Android builds can be evaluated as **porting candidates** without calling them compatible. For example, TrebleDroid publishes Android 15 releases with attached assets. **/e/OS needs a qualification:** its dedicated GSI documentation currently says the project does not compile GSI images and points technically skilled users toward building or community builds, even though its FAQ still suggests trying a GSI. The public `spavikevik/palma2pro-eos` work is explicitly for **Palma 2 Pro**, so it is useful E Ink integration research rather than GoColor7_2 installation evidence. No exact-model /e/OS image was verified. [TrebleDroid release](https://github.com/TrebleDroid/treble_experimentations/releases/tag/ci-20250415), [/e/OS GSI documentation](https://doc.e.foundation/os/learn/understand-gsi/), [/e/OS FAQ](https://doc.e.foundation/os/faq/), [Palma 2 Pro project](https://github.com/spavikevik/palma2pro-eos).

### Monochrome Android demonstration and exact-model Linux announcement

The separate **“Android 16 on the Go7”** demonstration is first-party evidence about a monochrome device. Its author explicitly says color requires testing and changes to the E Ink work, explaining that the demonstrated setup converts output to grayscale. A later reply still describes it as configured for monochrome and proposes color testing after publication. The inspected post continues to describe release as forthcoming. Do not merge this announcement with the `go7-lineage` repository or assume the two have the same author; no such relationship was established. [Author's post and replies](https://www.reddit.com/r/Onyx_Boox/comments/1wb6v6b/oops_android_16_on_the_go7/).

**PaperOS** is the closest exact-model *announcement*, but its publication plan is not a download. Its main post describes Buildroot, while author comments describe Debian/apt; another comment promises future APK support. Those statements do not establish a reproducible architecture or working Kindle, Libby or Audible apps. No public source/release link was verified from the inspected announcement or exact-name searches. [PaperOS author announcement and comments](https://www.reddit.com/r/Onyx_Boox/comments/1vcdkmh/paperos_a_native_linux_e_ink_os_now_running_on/).

## Implications for the required apps

For a custom project whose acceptance criteria include **Kindle, Libby, Audible and KOReader**, Android remains the more direct starting direction: Android GSIs retain the Android system framework, whereas Waydroid is a separate Android-container project for GNU/Linux. Neither fact proves these apps, their account/content flows, color output or audio work on a modified BOOX. Those remain exact-build acceptance tests. [Android GSI documentation](https://developer.android.com/topic/generic-system-image), [Waydroid project documentation](https://docs.waydro.id/).

The current BOOX Go Color 7 Gen II is officially described as Android 13 with third-party app support. Keeping stock firmware while adjusting the home screen is therefore a useful comparison baseline before deciding that an OS port is needed; it does not answer whether a replacement image is compatible. [Official BOOX product specifications](https://shop.boox.com/products/gocolor7-gen2).

## What would change the conclusion

Before calling any candidate installable, obtain all of the following for the **confirmed model and firmware**:

1. A maintainer-published image or reproducible build target explicitly naming that model.
2. Working physical-panel evidence for color/full/partial refresh, plus input, frontlight, Wi-Fi, audio and sleep/wake.
3. Exact-model installation prerequisites and a demonstrated route back to matching stock firmware.
4. Successful sign-in, entitled downloads and offline reading/playback in the four required apps.

These are proposed review criteria, not claims that a candidate currently meets them. Chipset similarity, a generic ARM64 download, a source repository name and a screenshot do not independently establish exact-model compatibility.

## Verification limits

- Sources were checked through web retrieval on 2026-11-11; several GitHub pages report cached crawls from the preceding week.
- The `go7-lineage` Releases page was readable and explicitly empty. GitHub API requests and the Linux repository's Releases page could not be retrieved, so this note does not present the previous check's empty API result as fresh evidence.
- The official LineageOS device directory returned HTTP 403; postmarketOS's directory returned access denied. No blanket claim of official-project absence relies on these inaccessible directories.
- A matching stock OTA was subsequently downloaded, decrypted and validated entirely on the Mac; see the later progress note and linked evidence. No OS image was flashed. Targeted read-only ADB inventory inspected device properties, public update-verification certificates, reported boot state and partition metadata. Actual bootloader operations, raw partition contents, accounts and content were not inspected. Exact-build replacement compatibility and restoration feasibility remain unverified.

## Backup test checkpoint — 2026-11-11

The approved first service-mode test reached USB 9008 and queried the expected chipset family. A programmer-identity guard stopped it before upload or storage reads. A manual power-button restart returned the device to its verified original Android build and slot `_a`. Stock firmware is validated locally, but programmer acceptance, storage backup and restoration remain unverified. See [test outcome](backup-access-test-2026-11-11.json) and [recovery notes](stock-recovery-research.md).

The offline follow-up confirmed that the selected programmer's embedded root-certificate digest differs from the service-mode key report; this was not a hash-algorithm/padding mix-up. Programmer acceptance is unverified, so the guard remains in place and no further live attempt occurred. LineageOS remains the selected project direction, pending a viable backup/recovery path.

## Backup-route research correction — 2026-11-11

The first controller's digest-equality gate did not establish programmer incompatibility: exact-model reports show the same device-reported key and successful use of the original candidate. That candidate remains the strongest lead, with a corrected full-device-identity/pinned-binary check prepared for a bounded retry. Its acceptance and storage reads are still untested locally. Production recovery, temporary fastboot boot and BOOX Library exports have not supplied a verified replacement for a raw device backup. [Current evidence and recommendation](stock-recovery-research.md), [alternative routes](alternative-backup-routes.md). No additional mode entry or firmware write occurred.

## Backup access qualified — 2026-11-11

The revised read-only test passed after correcting the programmer's NULL-disk simulation setting. The original pinned programmer was accepted; primary/backup GPT metadata validated across 80 partitions; two 128 KiB `xbl_config_a` reads matched; and the reader automatically returned to the same stock build and slot `_a`. The Mac can perform these small reads successfully. [Verified test](backup-access-test-2026-11-11-03.json). A full 62.54 GB main-area backup and restoration remain outstanding; no LineageOS image or firmware write has been attempted.
