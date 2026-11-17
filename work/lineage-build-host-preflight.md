# BOOX LineageOS build-host preflight

Checked 2026-11-11. Scope: read-only Mac inventory, current primary-source requirements, and preparation of an offline Linux host screen. No system packages, VM, daemon, Docker setting, SSH connection, Android source checkout, paid service, or device action was started.

## Decision: honor the Mac-first attempt

The user explicitly wants to **try the Mac first and switch to the PC only after a concrete hiccup**. Proceed with bounded toolchain probes in the existing Docker Desktop Linux environment before any full Android checkout. The upstream reference baseline is **x86_64 Linux with glibc 2.17+, 64 GB RAM, and at least 400 GB free**, using case-sensitive source storage. This Mac does not meet that reference; that is a disclosed experimental constraint, not a reason to skip the user's requested probe. [AOSP requirements](https://source.android.com/docs/setup/start/requirements), [LineageOS build prerequisites source](https://github.com/LineageOS/lineage_wiki/blob/main/_includes/templates/device_build_before_init.md)

The user freed storage and reports about 390 GB available. The latest direct filesystem reading here is **369.05 decimal GB / 343.70 GiB** (different free-space accounting and ongoing use can change this). The PC has **64 GB RAM but under 300 GB free**, per the user, so it is **not currently a storage-ready fallback**. Its CPU architecture, Linux environment, and access remain unverified.

## Actual Mac inventory

The companion [sanitized JSON inventory](build-host-inventory-2026-11-11.json) records the observations without serial numbers, hostnames, account identities, credentials, or remote endpoints.

| Item | Observed | Consequence |
| --- | --- | --- |
| Computer | MacBook Pro, Apple M3 Pro, 12-core CPU | Native host architecture is arm64, outside the documented x86_64 recipe. |
| Operating system | macOS 27.2, Darwin arm64 | Modern native macOS AOSP builds are unsupported. |
| Memory | 18 GB reported by System Information | Below the documented 64 GB baseline, before allocating anything to a VM. |
| Workspace free space | Initially 253.54 decimal GB; after cleanup, latest read 369.05 decimal GB / 343.70 GiB | Much improved; still below the upstream 400 GB reference by about 31 GB at measurement time. A bounded probe fits without a full checkout. |
| Workspace case sensitivity | Case-insensitive; existing `.gitignore` and `.GITIGNORE` resolve to the same file | Do not use a Mac bind-mounted source tree as the planned Linux build directory. |
| Existing useful tools | Git 2.56.1, Python 3.15.2, SSH client, Homebrew, Make; Java launcher exists but was not invoked | Enough for documentation, manifest preparation, source review, small checks, and transferring work once a host is identified. Presence does not certify build dependencies. |
| Docker | Client/server 29.9.3; running Linux `aarch64` daemon, 12 CPUs, 8,319,172,608 bytes guest RAM (7.75 GiB) | The read-only check outside the restricted execution context succeeded. An actual Linux environment exists; its configured memory is currently small. No setting was changed. |
| Other VM tools | No Lima/Colima/UTM/QEMU/Podman/Multipass/Parallels command found; Docker was the only matching installed application | No independent Linux VM was established. This inventory is an executable/application check, not a search of every disk image. |
| Repo / Ninja | Not found in PATH | No Android checkout was initialized or synchronized. |

System Information supplied CPU/memory data. Direct `sysctl` reads were denied and `diskutil info` could not use the DiskManagement framework in this execution environment. Free space came from `statvfs`; case sensitivity was established without creating a probe file. The initial Docker socket denial was an execution restriction: a subsequent authorized read-only check confirmed the daemon is running. No permissions were changed or daemon started.

## What the official documentation actually says

- **AOSP:** x86 64-bit host, 64 GB RAM, 400 GB free (250 GB checkout + 150 GB build), Linux/glibc 2.17+. The requirements page explicitly ends native macOS support at Android 11 in June 2021. Its current latest-release text names Android 17; that does not determine the Android base of the separate BOOX fork. [AOSP requirements](https://source.android.com/docs/setup/start/requirements)
- **LineageOS:** its current shared build template specifies an x86_64 computer and lists 64 GB RAM / 400 GB storage for LineageOS 21 and later. The template still mentions Linux/macOS/Windows generically, while saying its instructions were tested with Ubuntu 20.04 LTS. This generic wording is not evidence that a modern Apple Silicon native build works. [LineageOS template](https://github.com/LineageOS/lineage_wiki/blob/main/_includes/templates/device_build_before_init.md)
- **ARM nuance:** current `lineage-24.0` Soong selects `linux-arm64` on an ARM Linux host, and its bootstrap script expects `prebuilts/go/linux-arm64`. However the upstream default manifest currently includes only `prebuilts/go/linux-x86`, plus optional Darwin Go; it does not supply that ARM Go directory. It also lists x86-host Clang. The BOOX fork must supply compatible ARM prebuilts/overrides, or native ARM bootstrap is concretely incomplete. Do not describe ARM Linux as inherently impossible or assume that one ARM selector makes the manifest ready. [Soong host selection](https://github.com/LineageOS/android_build_soong/blob/lineage-24.0/ui/build/config.go), [Go bootstrap script](https://github.com/LineageOS/android_build_soong/blob/lineage-24.0/scripts/microfactory.bash), [upstream manifest](https://github.com/LineageOS/android/blob/lineage-24.0/default.xml)
- **Case-sensitive storage:** Android's build documentation explicitly diagnoses case-insensitive source filesystems as a build error. The conservative plan is guest-native Linux storage, rather than sharing this case-insensitive Mac workspace as the source tree. [AOSP build error documentation source](https://android.googlesource.com/platform/docs/source.android.com/+/37c652c518349acbb900d0a222b85ac2315eb9c0/src/source/building.md)

The BOOX branch, Android version, device-tree completeness, exact manifest, proprietary blob source, and build target are separate source-audit findings; this report does not infer them from the branch name.

## Candidate build routes

| Route | Assessment |
| --- | --- |
| Native macOS build | Outside current AOSP support. Use the existing Linux Docker environment for the Mac-first attempt. |
| Native ARM Linux container on this Mac | First check the fork's host-prebuilt paths. The upstream ARM Go manifest gap above is a concrete bootstrap issue to confirm against the fork before downloading. Replacing the Android toolchain with an arbitrary distribution compiler is not equivalent. |
| Emulated amd64 Linux container on this Mac | Best next experimental candidate if the fork uses the upstream x86 prebuilts. Verify actual pinned binaries, a tiny compilation, and build bootstrap before a full source sync. Docker documents that emulated compilation can be much slower. [Docker emulation guidance](https://docs.docker.com/build/building/multi-platform/) |
| An existing x86_64 Linux computer | Best match for the documented recipe. Verify guest/host RAM, actual target-filesystem free space, filesystem behavior, distribution dependencies, and access before downloading Android sources. |
| The user's Windows computer | User reports 64 GB RAM but under 300 GB free. Storage is currently below the same source/build reference. CPU, availability, Linux installation, and access remain unverified; it is not a ready fallback. |
| WSL2 on an x86_64 Windows computer | Conditional alternative to evaluate after its hardware and installed environment are known; not certified by this preflight. Keep sources in WSL's Linux filesystem, not `/mnt/c`. Measure memory inside Linux: Microsoft's default WSL memory limit is 50% of Windows RAM. Also verify free physical Windows disk capacity; a guest virtual disk's reported capacity is insufficient. [Microsoft filesystem guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems), [WSL memory allocation](https://learn.microsoft.com/en-us/windows/wsl/wsl-config) |
| A new VM/tool installation, remote host, or cloud service | None was created, purchased, assumed available, or configured. |

## Concrete Mac-first probe plan

These are the next probe stages, **not commands already executed by this subtask**. The parent task owns container creation, small downloads, and any approved Docker resource adjustments. No complete source sync is needed for these stages.

1. Pin the BOOX manifest and enumerate its host-prebuilt projects at the audited revisions. Check its Go, Clang, Rust, JDK, build-tools/Ninja, and any kernel compiler binaries by host architecture; Android's target `arm64` is separate from the computer that runs the compiler. Compare the fork's ARM Go path against the upstream bootstrap requirement above.
2. Use a small disposable Linux container in the existing Docker daemon. First test the native ARM userspace and report `uname -m`, glibc version, effective memory, and filesystem free space. Then, if x86 host tools are required, run an explicit `linux/amd64` container and verify that an actual x86-64 executable runs successfully. `uname` alone is insufficient evidence of binary translation. Do not enable a new daemon or install a separate VM for this test.
3. Keep the scratch files in a Docker-managed Linux volume, not a bind mount of this case-insensitive Mac workspace. Test two distinct case-differing filenames in the scratch volume, then inspect guest free space. Inspect existing Docker disk capacity and physical host free space before increasing any virtual limit; changing a virtual ceiling does not create physical free space. [Docker resource settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/)
4. Download **only the exact required executables and their shared-library dependencies** from the manifest-pinned toolchain revision, with an explicit small transfer budget and recorded hashes. Start with Go and build-tools/Ninja; run their version commands and a tiny Go bootstrap program. A static distribution executable or a generic compiler alone does not prove the fork's toolchain works.
5. For the pinned Clang, JDK, and Rust tools, inspect directory/archive sizes first. Run their version commands only after the minimal dependency set is identified; compile and run one tiny host program and compile one tiny Android ARM64 object where the selected compiler supports it. Do not silently fetch multi-gigabyte prebuilt repositories to satisfy a supposedly small probe. Defer oversized bundles and record the limit clearly.
6. With only the build/Soong/Blueprint bootstrap pieces and required small host tools, attempt the earliest bootstrap/host-tool stage that does not demand a complete platform tree. Missing source because the tree is intentionally partial is an expected boundary; an illegal instruction, missing ELF loader, absent required ARM prebuilt, or tool-specific execution failure is a concrete architecture hiccup.
7. Advance to source download planning only if the selected architecture passes these probes. A full build remains experimental with 18 GB physical RAM and a currently ~7.75 GiB Docker guest. Measure memory/OOM behavior, elapsed time, disk growth, and preserve logs. Stop before physical storage exhaustion. If a concrete hiccup prevents progress, evaluate the PC only after resolving its own storage/environment gaps.

If native ARM fails because the audited manifest lacks host prebuilts but amd64 emulation passes, continue the Mac-first experiment with amd64 rather than declaring the Mac impossible. If both fail, report the exact failing binary and error. Official resource targets are useful context but are not an architecture probe result.

## Prepared now

The portable [Linux host screen](../tools/build-host/preflight.py) only reads local host information and existing files. On a candidate Linux machine, run it against an **existing** intended build directory:

```sh
python3 /path/to/BooxOS/tools/build-host/preflight.py /existing/build/directory --mode experimental
```

It prints JSON and exits `0` when the selected screen passes, or `2` otherwise. Default `--mode documented` checks the reference Linux/x86_64/glibc/RAM/storage baseline, existing-file case sensitivity, and selected commands. **`--mode experimental` permits a bounded toolchain probe on Linux ARM64 or x86_64 with compatible glibc; it preserves every full-build resource shortfall in the report and never claims official support or build success.** It performs no installations, network requests, credential inspection, builds, or device actions. An empty directory may leave case sensitivity unknown. It does not check every development package, all versions, nested cgroup-v1 limits, underlying WSL physical disk capacity, or device-port correctness. Passing must be followed by the actual pinned-toolchain probes above.

The Mac can already hold the small source audit, pinned manifests, preparation instructions, patches, checksums, and review artifacts. Docker provides the Linux test environment for the user's Mac-first request. Installing macOS Repo or Java alone would not validate the Linux host toolchain. No remote endpoint or credentials were assumed or inspected here.

## Remaining host information

No additional user answer is needed to run the authorized bounded Mac-first probes. If switching machines becomes necessary, ask once: **What CPU and Linux/WSL2 setup does the PC have, and can its available build storage be increased beyond its current under-300-GB level?** Do not treat its 64 GB RAM as evidence that its storage or access is ready.

## Actual Mac qualification update — 2026-11-11

The user chose Mac first after freeing storage; the 64 GB RAM Windows computer remains a fallback and has under 300 GB free. In the isolated Ubuntu 22 x86 Linux environment, the manifest-selected Lineage 21 Go 1.21.4, Clang 18, Rust 1.75 and JDK 17 all executed. C, Rust and Java compile/link/run probes passed; an ARM64 Android API 30 shared-library link and ELF inspection passed; Blueprint pathtools/parser/proptools tests passed. See `lineage21-actual-tool-probe-2026-11-11.json`. These results do not establish whole-platform build capacity or device compatibility.

Eight host/build source revisions are pinned in `lineage21-toolchain-subset-final-2026-11-11.json`. Only the selected Linux Rust 1.75 subtree is materialized. The first broad toolchain checkout was deliberately stopped because unused Darwin binaries were being fetched one at a time; it was completed by a batched sparse Linux checkout. Its exit 137 records that manual stop, not an observed memory exhaustion. No Docker resource settings were changed. The full platform has not been synchronized or built, and no GoColor7_2 image exists.
