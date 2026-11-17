# Proposed stock debug-boot qualification

**Prepared locally; not approved or run on the BOOX. This does not install LineageOS.**

The native bootloader accepts a RAM download but rejects the command that starts it. Therefore a stock-based privileged backup session would require writing a boot partition. This proposal qualifies that route with a small read before attempting another long backup.

The proposed change replaces **boot_a only**, starts the original BOOX Android system with authenticated USB debugging, tests the privileged read path, and restores the exact original boot_a. It preserves the stock kernel, device tree, external color overlay, system, vendor, recovery and user storage. Startup behavior and acceptance of the modified image remain untested.

## Prepared images

| Role | Size | SHA-256 |
| --- | --- | --- |
| Local debug candidate in `.private/stock-debug-boot-development-20261111/boot.img` | 100,663,296 bytes | `92a3c30d80dccb91bc00eec0b54e261649a6e240272cad509f1d169237704d31` |
| Matching original stock `boot.img` in the downloaded April 2026 firmware | 100,663,296 bytes | `ede53420966b3af1a3a7b02cae3fef8583a0e01d19271006287dc14b4457ba63` |

An unchanged control repack reproduces the original boot payload byte-for-byte. The candidate preserves every original ramdisk entry and adds three files: the debug marker, debug properties and stock platform policy with three debug rules. Its internal AVB footer/hash verifies. Its changed boot content **does not match the manufacturer's parent VBMeta boot hash**; acceptance by this unlocked OEM bootloader is untested. Changing VBMeta or disabling verification is outside this proposal.

## Security change

USB authentication stays required. Normal ADB starts with privileges dropped, and root requires a separate request from the authenticated Mac. The added policy permits the ADB daemon to enter the existing `su` domain and makes **that domain permissive**; the global enforcement setting and other domains are unchanged. A root session can write storage as well as read it. This candidate is an engineering tool, not a read-only operating system or a daily-use release. No host private key is embedded.

The combined policy compiles with the flags used by stock init, and inspection finds exactly one permissive domain, `su`. Strict neverallow checking already fails on unmodified OEM policy; the compilation is not a clean release-policy qualification.

## Bounded proposed session

1. With the owner present, recheck the exact original Android build, slot A, unlocked state, sufficient charge, normal native USB connection and both local image hashes. Recheck that no update/snapshot is active. If a prerequisite differs, stop before writing.
2. Write only the reviewed candidate to boot_a and request one normal boot. No slot B, recovery, system, vendor, modem, bootloader firmware or VBMeta write is included. Do not erase, format or unlock anything.
3. Require the original Android system to finish startup, USB authentication to remain enabled, global SELinux to remain enforcing, and an explicitly requested ADB-root session to report UID 0 in `su`. If these checks fail, proceed to original-boot restoration rather than adding policy or verification bypasses.
4. Read two small samples from the hardware-configuration partition into private Mac files, repeat them and compare hashes. This qualification does not read userdata or perform a long partition backup.
5. Restore the exact original boot_a and restart. If the boot flag needs repair, selecting A is a separate explicitly included recovery action only after the original image is restored. Verify the original build, slot A, completed startup, normal non-root ADB and original debug-property values.

If the modified image fails to start, the owner may need to enter the already verified native bootloader physically so the original boot image can be restored. Stop if that interface is unavailable. Do not retry EDL, flash a different partition or disable verification as a fallback. Recovery from a failed persistent write is not guaranteed.

A successful qualification would establish the privileged read route and original-boot return for this candidate. A later coherent firmware backup and actual stock restoration still need their own scope and validation. It would not qualify the color LineageOS port, which has no complete product/image yet.
