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

# Debug-only bring-up helpers (early USB adb + log snapshots). Never ship.
ifeq ($(BOOXOS_BRINGUP),1)
$(call inherit-product, device/onyx/GoColor7_2/bringup/bringup.mk)
endif

# Keep dexpreopt on (the default). With it off, first boot runs odrefresh for
# the whole boot classpath while init blocks at zygote-start, so USB/adb never
# come up (DSU tests 2026-11-17).
