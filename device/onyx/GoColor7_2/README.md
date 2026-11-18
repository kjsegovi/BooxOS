# Go Color 7 Gen II bring-up target

Experimental LineageOS 21 / Android 14 target for the exact `GoColor7_2`. As
of 2026-11-18 it boots on hardware as a DSU guest (system, system_ext and product
images over the stock vendor/odm/boot), with working e-ink updates, touch, front
light and Wi-Fi. See the top-level README.md. It is not an installable release;
bring-up builds are debug builds.

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
