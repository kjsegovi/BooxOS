$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch.mk)

PRODUCT_NO_CAMERA := true
$(call inherit-product, vendor/lineage/config/common_full_tablet_wifionly.mk)

PRODUCT_NAME := lineage_GoColor7_2
PRODUCT_DEVICE := GoColor7_2
PRODUCT_BRAND := Onyx
PRODUCT_MODEL := GoColor7_2
PRODUCT_MANUFACTURER := ONYX
PRODUCT_CHARACTERISTICS := tablet
PRODUCT_SHIPPING_API_LEVEL := 30
PRODUCT_EXTRA_VNDK_VERSIONS += 30

PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_USE_DYNAMIC_PARTITION_SIZE := true

# The existing physical recovery and original boot are retained for this first
# experiment. Do not generate userdata, recovery or full-super erase images.
PRODUCT_BUILD_BOOT_IMAGE := false
PRODUCT_BUILD_RECOVERY_IMAGE := false
PRODUCT_BUILD_VENDOR_BOOT_IMAGE := false
PRODUCT_BUILD_INIT_BOOT_IMAGE := false
PRODUCT_BUILD_VENDOR_IMAGE := false
PRODUCT_BUILD_ODM_IMAGE := false
PRODUCT_BUILD_USERDATA_IMAGE := false
PRODUCT_BUILD_SUPER_PARTITION := false
PRODUCT_BUILD_SUPER_EMPTY_IMAGE := false
PRODUCT_VIRTUAL_AB_COMPRESSION := false
PRODUCT_VIRTUAL_AB_USERSPACE_SNAPSHOTS := false

TARGET_SCREEN_WIDTH := 1264
TARGET_SCREEN_HEIGHT := 1680
PRODUCT_SYSTEM_PROPERTIES += \
    ro.sf.lcd_density=300 \
    persist.sys.sf.color_mode=7

# E-ink: the kernel's SDE EPDC hook only accepts one full-screen plane, so
# SurfaceFlinger must GPU-compose everything (stock: "h/w composer disabled").
# Read by the BOOXOS patch in SurfaceFlinger.cpp (tools/build-host/kpc_build.sh).
PRODUCT_SYSTEM_PROPERTIES += \
    ro.surface_flinger.booxos_force_client_composition=true

# E-ink panel updates (frameworks_native-0001-epdc-update-list.patch): one
# full-screen EPDC item per present. Mode word low nibble = waveform selector
# in the Onyx vendor composer (5 -> 0xff auto), bit 5 = full update.
# Ghost cleanup: after epdc_idle_ms of no screen changes, if partial updates
# since the last full refresh changed epdc_clean_pct % of the screen, redraw
# once with epdc_full_mode (34 = GC16-style full, one flash).
# Live override of any of these: setprop debug.booxos.<name> <n>.
PRODUCT_SYSTEM_PROPERTIES += \
    ro.surface_flinger.booxos_epdc_mode=5 \
    ro.surface_flinger.booxos_epdc_full_mode=34 \
    ro.surface_flinger.booxos_epdc_clean_pct=500 \
    ro.surface_flinger.booxos_epdc_idle_ms=1000

# Device init (touch controller fix): init/init.booxos.rc.
PRODUCT_COPY_FILES += \
    device/onyx/GoColor7_2/init/init.booxos.rc:$(TARGET_COPY_OUT_PRODUCT)/etc/init/init.booxos.rc

# No swipe lock screen by default: on e-ink the screen looks the same asleep or
# awake, and the swipe keyguard puts it back to sleep after 10 s.
PRODUCT_SYSTEM_PROPERTIES += \
    ro.lockscreen.disable.default=true

# Debug-only bring-up helpers (early USB adb + log snapshots). Never ship.
ifeq ($(BOOXOS_BRINGUP),1)
$(call inherit-product, device/onyx/GoColor7_2/bringup/bringup.mk)
endif

# Keep dexpreopt on (the default). With it off, first boot runs odrefresh for
# the whole boot classpath while init blocks at zygote-start, so USB/adb never
# come up (DSU tests 2026-11-17).
