# Included only when BOOXOS_BRINGUP=1 (see lineage_GoColor7_2.mk). Never ship.
PRODUCT_COPY_FILES += \
    device/onyx/GoColor7_2/bringup/init.booxos.bringup.rc:$(TARGET_COPY_OUT_PRODUCT)/etc/init/init.booxos.bringup.rc \
    device/onyx/GoColor7_2/bringup/booxos-probe.sh:$(TARGET_COPY_OUT_PRODUCT)/etc/booxos-probe.sh
