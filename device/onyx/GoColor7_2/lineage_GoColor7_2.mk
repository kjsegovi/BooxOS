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
    ro.sf.lcd_density=320 \
    persist.sys.sf.color_mode=7

# E-ink: the kernel's SDE EPDC hook only accepts one full-screen plane, so
# SurfaceFlinger must GPU-compose everything (stock: "h/w composer disabled").
# Read by the BOOXOS patch in SurfaceFlinger.cpp (tools/build-host/kpc_build.sh).
PRODUCT_SYSTEM_PROPERTIES += \
    ro.surface_flinger.booxos_force_client_composition=true

# E-ink refresh policy (frameworks_native-0001-epdc-update-list.patch; tuned
# live with the user 2026-11-18, see work/eink-live-experiments-2026-11-18.md).
# Mode word low nibble = Onyx composer waveform selector, bit 5 = full update,
# bit 8 = dither.
#   every update: 260 = A2 + dither (smooth scrolling and page turns)
#   clean after an app switch (or lots of change), 300 ms after the screen
#   goes quiet, covering only the area that changed since the last clean:
#   gentle 35 (wf3 full) normally, hard 34 (GC16 full) every 4th clean
# Live override of any of these: setprop debug.booxos.<name> <n>.
PRODUCT_SYSTEM_PROPERTIES += \
    ro.surface_flinger.booxos_epdc_mode=260 \
    ro.surface_flinger.booxos_epdc_settle_mode=35 \
    ro.surface_flinger.booxos_epdc_full_mode=34 \
    ro.surface_flinger.booxos_epdc_hard_every=4 \
    ro.surface_flinger.booxos_epdc_regional=1 \
    ro.surface_flinger.booxos_epdc_idle_ms=300 \
    ro.surface_flinger.booxos_epdc_clean_on_switch=1 \
    ro.surface_flinger.booxos_epdc_switch_pct=50 \
    ro.surface_flinger.booxos_epdc_clean_pct=0

# Resource overlays: home screen with only the app store, privacy and e-ink
# first-boot defaults (animations, sounds, location off), Lineage stats off.
PRODUCT_PACKAGE_OVERLAYS += device/onyx/GoColor7_2/overlay  # before Lineage's, so ours win

# App stores instead of Google Play: Aurora Store (Play apps, no Google account)
# and F-Droid (open-source apps); Readest (GitHub build) as the default reader.
# See prebuilt/apps/Android.bp.
PRODUCT_PACKAGES += \
    BooxosAuroraStore \
    BooxosFDroid \
    BooxosReadest

# Light (brightness + warmth) and B&W/Color Quick Settings tiles, first-boot text
# defaults (bold + high contrast). apps/BooxosDisplay.
PRODUCT_PACKAGES += \
    BooxosDisplay

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
