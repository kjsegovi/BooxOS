# Go Color 7 Gen II: non-destructive boot/recovery research

Checked 2026-11-11. Research only: no USB access, device commands, button actions, mode transitions, or device writes were performed for this note. Target: `GoColor7_2`, installed BOOX build `2026-04-21_13-54_4.2-rel_0421_19324b3ea`. Local incident observations and the command audit remain in [backup status](recovery-backup-status.md); they do not establish the cause of the loop.

## Immediate findings

**The only exact-model-labeled physical recovery lead located is: begin powered off, hold Power about eight seconds, release, then immediately press Power rapidly five times. Confidence is limited.** The live HardReset.Info video is titled *Boox Go Color 7 Gen 2 Boot Loop Fix and Recovery Mode*; its description identifies the recovery segment at **3:14** and gives that timing. However, the description also includes the first-generation Go Color 7, and this investigation could retrieve the public description but not usable captions/footage to independently identify the demonstrated hardware or build. Thus this is a demonstrator's claimed procedure, **not a verified BOOX manufacturer or exact-build instruction**. [Original demonstration, recovery segment](https://www.youtube.com/watch?v=lNa1r_zI0oE&t=194s).

If the coordinating investigation elects to try that lead, the narrowly bounded objective is **reach and photograph the menu, then stop pressing keys**. It is not a reset/update procedure. In particular, do not continue rapid Power presses after a screen/menu change: an exact-model owner reports that an extra Power press both revealed the recovery menu and immediately selected its default reboot entry. That report involved a modified bootloader and cannot verify stock entry timing, but it demonstrates why blindly continuing presses is unsuitable. [Exact-model owner's first-person account, post 58](https://www.mobileread.com/forums/showthread.php?t=372058&page=4).

## Manufacturer-confirmed power checks

BOOX's current official frozen/unresponsive-device article gives these general BOOX steps, without a model-specific exclusion:

1. Connect a USB-C power adapter or computer, charge for several hours, then hold Power **20 seconds** to force a reboot.
2. If the charging light is on, hold Power **10 seconds until the light goes off**, then press Power **two seconds** to check startup.
3. If the light is off, try a different USB-C cable. If the issue persists, contact BOOX support.

These are manufacturer instructions for power troubleshooting, **not a diagnosis of a fifteen-second first-logo loop**. The article does not supply a recovery-entry sequence, a blue/red/purple blink-code table, or a meaning for “logo without moving dots.” [BOOX official frozen-device guidance](https://booxsupport.zendesk.com/hc/en-us/articles/7900405304340-What-to-Do-If-My-Boox-Device-Is-Frozen-Unresponsive-Stuck).

BOOX's separate official troubleshooting page also suggests charging for an hour and holding Power about ten seconds while still connected when the device will not turn on. This is an alternative general support instruction, not evidence that further repetitions will resolve this incident. [BOOX official troubleshooting, Hardware](https://booxsupport.zendesk.com/hc/en-us/articles/8569506159124-Troubleshooting).

An e-paper image can remain visible without power; therefore the static BOOX logo alone does not prove that shutdown failed. Repeated fresh flashes/logos, light transitions, and observed USB enumeration are more useful observations. The image-retention property is manufacturer technology documentation; applying it to interpretation of this BOOX screen is an inference. [E Ink on bistability and image retention](https://esg.eink.com/en/report/0322082417c8192054/2017-ESG-Report).

## Menu/control evidence and limits

The already extracted stock recovery files contain the menu entry `Reboot system now`; `librecovery_ui.so` contains the help string `Use volume up/down and power.` This is **offline exact-package evidence of available text**, not a successful physical test or proof that all stored strings appear on this model. Source files: `.local/alternative-backup-research/recovery-extracted/system/bin/recovery` and `.local/alternative-backup-research/recovery-extracted/system/lib64/librecovery_ui.so`.

A Go Color 7 Gen 2 owner describes page-turn keys navigating and Power selecting, but their procedure had installed a Fairphone ABL. Do not treat the surrounding write/erase recipe as a stock recovery method. [Owner's first-person account, post 73](https://www.mobileread.com/forums/showthread.php?p=4581477).

No manufacturer or independently verified exact-stock-build source was found for:

- A distinct LED/screen sequence proving entry into stock recovery on this firmware.
- A safe blind key sequence to reveal a hidden recovery menu on this model.
- A different exact-model physical shortcut using the page-turn keys.

A BOOX-logo/blank loop does not itself distinguish boot-chain, kernel, storage, power, or peripheral causes. No identified source establishes which applies here.

## Programmer/read side effects: what can and cannot be concluded

The public loader maintainer lists Go Color 7 Gen 2 under `SM_BITRA` with the selected `0000000000000000_bdaf51b59ba21d8a_fhprg.bin`; that is compatibility evidence, not a promise that all sessions or exits succeed. No primary-source exact-model report was located establishing that this programmer's read command causes a persistent boot loop, or that a read-count/NAK failure diagnoses damaged storage. [Programmer maintainer's table](https://www.temblast.com/ref/onyxldr.htm), [original loader repository](https://github.com/bkerler/Loaders/blob/main/lenovo_motorola/0000000000000000_bdaf51b59ba21d8a_fhprg.bin).

The local host XML audit is evidence about commands the host sent; it cannot prove the closed programmer had no internal state effects. Conversely, the loop beginning after a read session does not prove that persistent firmware bytes changed. AOSP documents that an A/B bootloader can change retry/bootability state during failed boots **for a slot not already marked successful**. That is a general mechanism and reason not to equate repeated restarts with bitwise-unchanged state; it is **not evidence that this BOOX changed slots or that it caused this incident**. [AOSP bootloader slot handling](https://source.android.com/docs/core/architecture/bootloader/updating).

No wipe, update, sideload, flash, slot change, foreign bootloader, partition repair, or repeated EDL backup is proposed by this note. If bounded power/recovery-entry observation yields no usable menu, the source-backed next path is a BOOX support request with model, firmware, symptom video, and the read-only-session audit—not a speculative storage change. [BOOX customer-service routes](https://booxsupport.zendesk.com/hc/en-us/articles/8569505814420-Customer-Service).

## Subsequent local outcome

The reader eventually reached stock Android recovery with the exact saved slot-B November2025 build6191. The precise successful power-button timing was not isolated. The user selected Enter fastboot; Mac queries confirmed userspacefastboot and slotB, Aunbootable, no snapshot update. One explicitly approved A selection and normal reboot restored the original April2026 Android. This is local evidence for menu→fastbootd access and boot-selection recovery, not a successful firmware-image restore. [Final report](boot-loop-recovery-2026-11-11.json).
