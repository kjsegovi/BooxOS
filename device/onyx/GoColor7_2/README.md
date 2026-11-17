# Go Color 7 Gen II bring-up target

This is an incomplete, experimental LineageOS 21 / Android 14 target for the
exact `GoColor7_2`. It has not passed a complete build or booted on hardware.
It does not constitute an installable release.

The initial design reuses the matched original boot image, color DTB/DTBO and
ODM; provides the VNDK30 framework snapshot; retains dynamic/Virtual A/B layout;
and introduces a recorded derivative vendor filesystem for the color-profile
display shim. The original recovery and firmware bootloaders are preserved.
No BPF networking-enforcement bypass is included. The vendor derivative and
full platform/VINTF/policy/AVB outputs still need to be built and checked.

`prebuilts/` is private generated input, excluded from source control. Its
contents must be provisioned from the verified stock package and local build
artifacts, with hashes recorded. Do not substitute a monochrome DTBO or include
the reference raw-I2C frontlight daemon. Color display behavior, lighting,
charging, storage, inputs and applications remain untested on the new system.
