#!/bin/bash
# Experimental image build only. This script never accesses the BOOX device.
# BOOXOS_BRINGUP=1 makes a debug-only bring-up build: ADB on at boot without
# on-screen authorization (WITH_ADB_INSECURE), plus a DSU zip of the system
# images. Never use bring-up output as a daily build.
set -euo pipefail
cd /work
export TARGET_PRODUCT=lineage_GoColor7_2
export TARGET_RELEASE=ap2a
export TARGET_BUILD_VARIANT=userdebug
export TARGET_BUILD_TYPE=release
export LINEAGE_BUILD=GoColor7_2
# Dexpreopt must stay on: without it, first boot runs odrefresh for the whole
# boot classpath while init blocks at zygote-start (wait_for_prop
# odsign.verification.done), so USB/adb never come up (DSU test 2026-11-17).
export WITH_AVB=true
unset WITH_DEXPREOPT
export GOMAXPROCS=8 GOGC=50
export JAVA_TOOL_OPTIONS=-Xmx4g
export BUILD_DATETIME=$(date +%s)
# Bring-up only: keep the guest running when netbpfload fails so its logs can be
# read (upstream's documented debug step in netbpfload.rc). Standard builds
# always restore the upstream files from git first.
BPF_RC=(netbpfload/netbpfload.rc netbpfload/netbpfload.mainline.rc)
git -c safe.directory='*' -C packages/modules/Connectivity checkout -- "${BPF_RC[@]}"
if [ "${BOOXOS_BRINGUP:-0}" = 1 ]; then
  export WITH_ADB_INSECURE=true
  for f in "${BPF_RC[@]}"; do
    sed -i 's/^\(\s*\)reboot_on_failure reboot,bpfloader-failed/\1# BOOXOS_BRINGUP: reboot_on_failure reboot,bpfloader-failed/' packages/modules/Connectivity/$f
  done
  # Don't let a failing/hanging loader block init before USB/adbd start.
  sed -i 's/^\(\s*\)exec_start bpfloader$/\1start bpfloader  # BOOXOS_BRINGUP: was exec_start/' \
    packages/modules/Connectivity/netbpfload/netbpfload.rc
  grep -q 'start bpfloader  # BOOXOS_BRINGUP' packages/modules/Connectivity/netbpfload/netbpfload.rc
  echo bringup > /logs/build-flavor.txt
else
  unset WITH_ADB_INSECURE
  echo standard > /logs/build-flavor.txt
fi
git -c safe.directory='*' -C packages/modules/Connectivity diff --stat > /logs/connectivity-diff.txt

P=out/target/product/GoColor7_2
python3 .repo/repo/repo manifest -r -o /logs/resolved-manifest.xml
sha256sum device/onyx/GoColor7_2/prebuilts/*.img > /logs/prebuilt-images.sha256
date --iso-8601=seconds > /logs/started-at.txt
build/soong/soong_ui.bash --make-mode -j8 nothing 2>&1 | tee /logs/configure.log
touch /logs/configure-passed
build/soong/soong_ui.bash --make-mode -j8 systemimage productimage systemextimage vbmetaimage 2>&1 | tee /logs/images.log
sha256sum $P/{system,product,system_ext,vbmeta,vbmeta_system}.img > /logs/output-images.sha256
grep -h -E '^(ro\.adb\.secure|persist\.sys\.usb\.config|ro\.build\.version\.incremental)=' \
  $P/system/build.prop $P/system/etc/prop.default $P/product/etc/build.prop 2>/dev/null > /logs/adb-props.txt || true
if [ "${BOOXOS_BRINGUP:-0}" = 1 ]; then
  grep -qx 'ro.adb.secure=0' /logs/adb-props.txt
  python3 - "$P" <<'EOF'
import sys, zipfile
p = sys.argv[1]
with zipfile.ZipFile(p + '/booxos-dsu-bringup.zip', 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
    for name in ('system.img', 'system_ext.img', 'product.img'):
        z.write(p + '/' + name, name)
EOF
  sha256sum $P/booxos-dsu-bringup.zip > /logs/dsu-zip.sha256
fi
touch /logs/images-passed
date --iso-8601=seconds > /logs/finished-at.txt
