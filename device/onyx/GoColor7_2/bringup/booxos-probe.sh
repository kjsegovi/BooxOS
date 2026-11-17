#!/system/bin/sh
# BOOXOS_BRINGUP only (debug DSU builds). Never ship.
#
# Diagnostic probe for the DSU guest. Started `on init` as a root su service,
# so nothing init blocks on can stop it. It:
#   - works out how far boot got from properties/mounts (not init actions)
#   - rewrites /metadata/bootstat/persist.sys.boot.reason with a short state
#     string (stock copies it into sys.boot.reason.last on its next boot, even
#     after a forced power-off; /metadata is shared with stock)
#   - blinks the front light N times for stage N; toggles the warm light as a
#     heartbeat
#   - tries USB adb once APEXes are active
#   - reboots back to stock if boot stalls, so no Power-hold is needed
#
# Stages (blink count):
#   1 probe running        5 BPF loader finished (init.svc.bpfloader stopped)
#   2 /data mounted        6 odsign.verification.done=1
#   3 apexd activated      7 zygote running
#   4 odsign.key.done=1    8 sys.boot_completed=1

REASON_FILE=/metadata/bootstat/persist.sys.boot.reason
BR=/sys/class/backlight/onyx_bl_br/brightness
CT=/sys/class/backlight/onyx_bl_ct/brightness
STALL_SECS=90      # reboot if the state string stops changing this long
DEADLINE_SECS=200  # reboot if not fully booted by then
LOGDIR=/data/local/tmp/booxos

klog() { ( echo "booxos-probe: $*" > /dev/kmsg ) 2>/dev/null; }
uptime_s() { cut -d. -f1 /proc/uptime; }
p() { getprop "$1"; }

# --- exec_start services init may be blocked on (first one running wins) ---
WAIT_SVCS="apexd-snapshotde derive_sdk derive_classpath art_boot bpfloader \
update_verifier odsign wait_for_keymaster boringssl_self_test64_vendor \
boringssl_self_test32_vendor vold_prepare_subdirs"

waiting_on() {
  for s in $WAIT_SVCS; do
    [ "$(p init.svc.$s)" = running ] && { echo "$s"; return; }
  done
  for n in odrefresh dex2oat64 dex2oat32 dex2oat secilc fsck.f2fs e2fsck make_f2fs; do
    ps -A -o NAME 2>/dev/null | grep -qx "$n" && { echo "$n"; return; }
  done
  echo none
}

short() { echo "$1" | cut -c1-$2; }

# --- adb: mirrors stock vendor init.qcom.usb.rc (adb-only config) ---
ADB=0   # 0 not tried, 1 configfs, 2 functionfs, 3 adbd started, 4 ep1, 5 UDC bound
adb_try() {
  G=/config/usb_gadget/g1
  grep -q " /config configfs " /proc/mounts || mount -t configfs none /config || return
  mkdir -p $G/strings/0x409 $G/functions/ffs.adb $G/configs/b.1/strings/0x409 || return
  echo 0x0200 > $G/bcdUSB
  echo 0x18d1 > $G/idVendor
  echo 0x4ee7 > $G/idProduct
  getprop ro.serialno > $G/strings/0x409/serialnumber
  echo BooxOS > $G/strings/0x409/manufacturer
  echo "BooxOS bring-up" > $G/strings/0x409/product
  echo adb > $G/configs/b.1/strings/0x409/configuration
  ADB=1
  mkdir -p /dev/usb-ffs/adb
  chown shell:system /dev/usb-ffs /dev/usb-ffs/adb
  grep -q " /dev/usb-ffs/adb functionfs " /proc/mounts || \
    mount -t functionfs -o uid=2000,gid=1000,rmode=0770,fmode=0660 adb /dev/usb-ffs/adb || return
  ADB=2
  setprop ctl.start adbd
  i=0; while [ "$(p init.svc.adbd)" != running ] && [ $i -lt 20 ]; do sleep 0.5; i=$((i+1)); done
  [ "$(p init.svc.adbd)" = running ] || return
  ADB=3
  i=0; while [ ! -e /dev/usb-ffs/adb/ep1 ] && [ $i -lt 40 ]; do sleep 0.5; i=$((i+1)); done
  [ -e /dev/usb-ffs/adb/ep1 ] || return
  ADB=4
  [ -L $G/configs/b.1/f1 ] || ln -s $G/functions/ffs.adb $G/configs/b.1/f1
  UDC=$(p ro.boot.usbcontroller); [ -n "$UDC" ] || UDC=a600000.dwc3
  grep -q . $G/UDC 2>/dev/null || echo "$UDC" > $G/UDC
  grep -q . $G/UDC 2>/dev/null && ADB=5
}
udc_state() {
  s=$(cat /sys/class/udc/*/state 2>/dev/null | head -1 | tr -c 'a-z0-9\n' '_')
  short "${s:-x}" 4
}

# --- light ---
light() { echo "$1" > $BR 2>/dev/null; }
warm() { echo "$1" > $CT 2>/dev/null; }
blink() {
  n=$1; i=0
  while [ $i -lt $n ]; do light 32; sleep 0.3; light 0; sleep 0.3; i=$((i+1)); done
}

write_crumb() {
  # stock bootstat lowercases; keep it short (<= 91 bytes) and free of
  # reserved words (recovery, bootloader, fastboot, userspace, edl, oem)
  echo -n "$1" > $REASON_FILE 2>/dev/null && chmod 0644 $REASON_FILE 2>/dev/null
  sync
}

do_reboot() {
  crumb="$1"
  klog "rebooting: $crumb"
  write_crumb "$crumb"
  setprop sys.powerctl "$crumb"
  sleep 15
  # still here: init didn't act on powerctl; force a warm reset
  write_crumb "$crumb,f"
  echo b > /proc/sysrq-trigger
}

# --- main loop ---
klog "start uptime=$(uptime_s)"
START=$(uptime_s)
LAST_STATE=""
LAST_CHANGE=$START
HB=0

while true; do
  NOW=$(uptime_s)
  D=0; grep -q " /data " /proc/mounts && D=1
  APX=$(p apexd.status)
  K=$(p odsign.key.done)
  BPF=$(p init.svc.bpfloader)
  V=$(p odsign.verification.done)
  Z=$(p init.svc.zygote)
  BC=$(p sys.boot_completed)

  S=1
  [ $D = 1 ] && S=2
  [ $S = 2 ] && [ "$APX" = activated -o "$APX" = ready ] && S=3
  [ $S = 3 ] && [ "$K" = 1 ] && S=4
  [ $S = 4 ] && [ "$BPF" = stopped ] && S=5
  [ $S = 5 ] && [ "$V" = 1 ] && S=6
  [ $S = 6 ] && [ "$Z" = running ] && S=7
  [ "$BC" = 1 ] && S=8

  if [ -n "$BOOXOS_PROBE_ONCE" ]; then
    # test mode: print the state string once, no side effects
    W=$(waiting_on)
    echo "reboot,bx,s$S,d$D,a$(short "${APX:-x}" 3),k${K:-x},b$(short "${BPF:-x}" 3),v${V:-x},z$(short "${Z:-x}" 3),u$ADB$(udc_state),w$(short "$W" 14),t$((NOW-START))"
    exit 0
  fi

  if [ $ADB = 0 ] && [ "$APX" = activated -o "$APX" = ready ]; then
    adb_try
    klog "adb step=$ADB udc=$(udc_state)"
  fi

  W=$(waiting_on)
  STATE="reboot,bx,s$S,d$D,a$(short "${APX:-x}" 3),k${K:-x},b$(short "${BPF:-x}" 3),v${V:-x},z$(short "${Z:-x}" 3),u$ADB$(udc_state),w$(short "$W" 14)"
  CRUMB="$STATE,t$((NOW-START))"

  if [ "$STATE" != "$LAST_STATE" ]; then
    klog "$CRUMB"
    LAST_STATE="$STATE"
    LAST_CHANGE=$NOW
  fi
  write_crumb "$CRUMB"

  # snapshots for adb pull, once /data is up
  if [ $D = 1 ]; then
    mkdir -p $LOGDIR 2>/dev/null && chmod 0777 $LOGDIR
    dmesg > $LOGDIR/dmesg.txt 2>&1
    logcat -b all -d -t 4000 > $LOGDIR/logcat.txt 2>&1
    getprop > $LOGDIR/getprop.txt 2>&1
    echo "$CRUMB" >> $LOGDIR/crumbs.txt
    chmod 0666 $LOGDIR/*.txt 2>/dev/null
  fi

  if [ $S = 8 ]; then
    klog "boot completed; probe exiting"
    write_crumb "$CRUMB"
    warm 0; light 16
    exit 0
  fi

  if [ "$(udc_state)" = conf ]; then
    : # a host has enumerated us: stay up so the stuck guest can be inspected over adb
  elif [ $((NOW-LAST_CHANGE)) -ge $STALL_SECS ]; then
    do_reboot "$STATE,stall"
  elif [ $((NOW-START)) -ge $DEADLINE_SECS ]; then
    do_reboot "$STATE,late"
  fi

  HB=$((1-HB)); warm $((HB*32))
  blink $S
  sleep 2
done
