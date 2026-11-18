# Initial Go Color 7 Gen II / Android 14 bring-up. Not a qualified release.
DEVICE_PATH := device/onyx/GoColor7_2

TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a-dotprod
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := cortex-a76
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := cortex-a76

TARGET_BOOTLOADER_BOARD_NAME := lito
TARGET_BOARD_PLATFORM := lito
TARGET_NO_BOOTLOADER := true
TARGET_NO_KERNEL := true
TARGET_SCREEN_DENSITY := 300
TARGET_GRALLOC_HANDLE_HAS_RESERVED_SIZE := true

# Optional Qualcomm HAL declarations for the retained legacy vendor services.
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += \
    hardware/qcom-caf/common/vendor_framework_compatibility_matrix.xml

# The exact original boot image retains kernel, ramdisk and color DTB.
BOARD_PREBUILT_BOOTIMAGE := $(DEVICE_PATH)/prebuilts/boot.img
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilts/dtbo.img
BOARD_BOOT_HEADER_VERSION := 2
BOARD_KERNEL_PAGESIZE := 4096
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 100663296
BOARD_METADATAIMAGE_PARTITION_SIZE := 16777216
BOARD_USES_METADATA_PARTITION := true
BOARD_FLASH_BLOCK_SIZE := 262144

# Vendor is a narrowly recorded derivative of the matched stock filesystem.
# ODM and its VINTF level 5 / VNDK30 interface remain original.
BOARD_PREBUILT_VENDORIMAGE := $(DEVICE_PATH)/prebuilts/vendor.img
BOARD_PREBUILT_ODMIMAGE := $(DEVICE_PATH)/prebuilts/odm.img
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += boot dtbo odm product system system_ext vbmeta vbmeta_system vendor
BOARD_SUPER_PARTITION_SIZE := 6442450944
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 6438256640
BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := odm product system system_ext vendor

# No anti-rollback advance from the existing original framework chain.
BOARD_AVB_ENABLE := true
BOARD_AVB_ALGORITHM := SHA256_RSA2048
BOARD_AVB_KEY_PATH := $(DEVICE_PATH)/prebuilts/avb-development-key.pem
BOARD_AVB_ROLLBACK_INDEX := 0
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := $(BOARD_AVB_KEY_PATH)
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := 1775001600
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 2

# Truthful stock boot/vendor patch metadata. The framework has its own SPL.
BOOT_SECURITY_PATCH := 2025-10-01
VENDOR_SECURITY_PATCH := 2025-10-01

# BOOXOS: device sepolicy (sysfs labels, properties) on top of system_ext.
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += device/onyx/GoColor7_2/sepolicy/private
