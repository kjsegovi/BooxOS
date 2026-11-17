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
MAXLEN=91          # property / reason file limit
# The probe starts before APEX activation, so it stays in init's bootstrap
# mount namespace and can't see /data directly. Go through init's view.
INITROOT=/proc/1/root
LOGDIR=$INITROOT/data/local/tmp/booxos

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

# How init last saw a service die, from its kernel-log line
# "Service 'NAME' (pid N) exited with status X" / "... received signal X".
# Prints e<status> / s<signal> plus the death count, or x.
svc_exit() {
  l=$(dmesg 2>/dev/null | grep -E "Service '$1' \(pid [0-9]+\) (exited with status|received signal)")
  [ -n "$l" ] || { echo x; return; }
  n=$(echo "$l" | grep -c .)
  last=$(echo "$l" | tail -1)
  case "$last" in
    *"exited with status "*) c=e$(echo "$last" | sed 's/.*exited with status \([0-9-]*\).*/\1/') ;;
    *) c=s$(echo "$last" | sed 's/.*received signal \([0-9-]*\).*/\1/') ;;
  esac
  echo "${c}n$n"
}

# First useful error text for a crash: native abort message, else the first
# exception/error line in the crash buffer, else zygote/AndroidRuntime errors.
crash_msg() {
  c=$(logcat -b crash -d 2>/dev/null)
  m=$(echo "$c" | grep -m1 "Abort message:" | sed 's/.*Abort message: *//')
  if [ -z "$m" ]; then
    m=$(echo "$c" | grep -v "FATAL EXCEPTION" | grep -m1 -E "Exception|Error|failed|cannot|not found" \
        | sed 's/^.* [VDIWEF] [^:]*: //')
  fi
  if [ -z "$m" ]; then
    m=$(logcat -d -b main,system 2>/dev/null | grep -E " [EF] (Zygote|AndroidRuntime|zygote|zygote64|app_process|linker)" \
        | grep -m1 -E "Exception|Error|failed|cannot|not found|died" | sed 's/^.* [VDIWEF] [^:]*: //')
  fi
  [ -n "$m" ] || m=none
  # stock lowercases the reason; keep it compact and comma/space free
  echo "$m" | tr -d "'\"" \
    | sed 's/java\.lang\.//g; s/dalvik\.system\.//g; s/dlopen failed: /dlopen:/g; s/android\.//g; s/: */:/g' \
    | tr 'A-Z' 'a-z' | tr -c 'a-z0-9._:/=\n-' '_' | tr -s '_' | sed 's/^_//' | head -1
}

# --- /data failure details (probe v3) ---
# Keymaster HAL: stock libqtikeymaster4 waits forever for version properties,
# then aborts with "Configure failed" / "get_date_support failed" /
# "Android property not present" (see work/keymaster-hal-re-2026-11-17.md).
KM_SVC=vendor.keymaster-4-1
km_flag() {
  l=$(logcat -d -b all 2>/dev/null | grep -E "Configure failed|get_date_support failed|Android property not present" | head -1)
  case "$l" in
    *"Configure failed"*) echo C ;;
    *"get_date_support failed"*) echo G ;;
    *"Android property not present"*) echo P ;;
    *) echo - ;;
  esac
}
km_registered() {
  lshal list -i 2>/dev/null | grep -q "android.hardware.keymaster@4.1::IKeymasterDevice/default" && echo 1 || echo 0
}
vold_msg() {
  # Last meaningful vold error, prefixed with the count of such errors.
  # Benign lines skipped: vold's deliberate rollback-resistant generateKey
  # attempt (KeyStorage.cpp:129, retried without), earlyBootEnded and
  # StrongBox KeyMint lookups (seen on healthy stock too).
  L=$(logcat -d -b main,system 2>/dev/null | grep -E " [EF] (vold|Vold|fscrypt|MetadataCrypt|KeyStorage) *:" \
      | grep -v -i -E "earlybootended|strongbox|getting keymint device")
  if logcat -d -b main,system 2>/dev/null | grep -q "Failed to generate rollback-resistant key"; then
    L=$(echo "$L" | sed '1{/generateKey returned/d;}')
  fi
  n=$(echo "$L" | grep -c .)
  # error code of the last failing keystore2 call (identifies what KM rejected)
  g=$(echo "$L" | grep -o -E "(generateKey|exportKey|importKey|begin|update|finish|deleteKey) returned service specific error: *-?[0-9]+" \
      | tail -1 | sed -E 's/ returned service specific error: */=/')
  m=$(echo "$L" | tail -1 | sed 's/^.* [VDIWEF] [^:]*: //')
  [ -n "$m" ] && m="$n:${g:+$g:}$m"
  [ -n "$m" ] || m=$(dmesg 2>/dev/null | grep -i -E "fs_mgr|userdata|metadata_encryption|default-key|f2fs" \
      | grep -i -E "fail|error|invalid|unable|cannot" | head -1 | sed 's/^\[[^]]*\] *//')
  [ -n "$m" ] || m=$(logcat -d -b main,system 2>/dev/null | grep -E " [EF] (keystore2|Keystore) *:" \
      | grep -v -i -E "earlybootended|strongbox|getting keymint devic" | tail -1 | sed 's/^.* [VDIWEF] [^:]*: //')
  [ -n "$m" ] || m=none
  echo "$m" | tr -d "'\"" \
    | sed 's/keystore2 Keystore //; s/ returned service specific error: */=sse/; s/ returned status: */=st/; s/Failed to /f:/g; s/: */:/g' \
    | tr 'A-Z' 'a-z' | tr -c 'a-z0-9._:/=\n-' '_' | tr -s '_' | sed 's/^_//' | head -1
}

# --- paged report (probe v4) ---
# One breadcrumb holds ~68 chars, so data mode builds a full report and shows
# page N of it, where N advances by one on every guest boot (counter on
# /metadata, untouched by stock). Read further pages by re-enabling the DSU
# guest and rebooting; no rebuild needed.
PAGEFILE=/metadata/booxos-probe-page
clean() {
  tr -d "'\"" | sed 's/keystore2 Keystore //; s/ returned service specific error: */=sse/; s/Failed to /f:/g; s/failed to /f:/g; s/: */:/g' \
    | tr 'A-Z' 'a-z' | tr -c 'a-z0-9._:/=\n-' '_' | tr -s '_'
}
data_report() {
  printf 's%s,k%s%s,r%s,f%s' "$S" "$(short "$(p init.svc.$KM_SVC)" 3)" "$(svc_exit $KM_SVC)" "$(km_registered)" "$(km_flag)"
  VL=$(logcat -d -b main,system 2>/dev/null | grep -E " [EF] (vold|Vold|fscrypt|MetadataCrypt|KeyStorage|vdc) *:" \
    | grep -v -i -E "earlybootended|strongbox|getting keymint device")
  # drop vold's deliberate rollback-resistant attempt (KeyStorage.cpp:129)
  if logcat -d -b main,system 2>/dev/null | grep -q "Failed to generate rollback-resistant key"; then
    VL=$(echo "$VL" | sed '1{/generateKey returned/d;}')
  fi
  echo "$VL" | grep . | head -8 | sed 's/^.* [VDIWEF] [^:]*: //' | clean | sed 's/^/,/' | tr -d '\n'
  dmesg 2>/dev/null | grep -i -E "fs_mgr|mount_all|vdc|/data|userdata|metadata|fscrypt|default-key|f2fs" \
    | grep -i -E "fail|error|invalid|unable|cannot|not |denied|unsupported|unknown|bad |corrupt|wrong|mismatch" | head -6 \
    | sed 's/^\[[^]]*\] *//; s/^init: *//' | clean | sed 's/^/,dm:/' | tr -d '\n'
}

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
PAGEIDX=$(cat $PAGEFILE 2>/dev/null); case "$PAGEIDX" in ''|*[!0-9]*) PAGEIDX=0 ;; esac
[ -n "$BOOXOS_PROBE_PAGE" ] && PAGEIDX=$BOOXOS_PROBE_PAGE
if [ -z "$BOOXOS_PROBE_ONCE" ]; then
  echo $((PAGEIDX + 1)) > $PAGEFILE 2>/dev/null && sync
fi
klog "start uptime=$(uptime_s) page=$PAGEIDX"
START=$(uptime_s)
LAST_STATE=""
LAST_CHANGE=$START
HB=0

while true; do
  NOW=$(uptime_s)
  D=0; grep -q " /data " /proc/1/mounts && D=1
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

  if [ -z "$BOOXOS_PROBE_ONCE" ] && [ $ADB = 0 ] && [ "$APX" = activated -o "$APX" = ready ]; then
    adb_try
    klog "adb step=$ADB udc=$(udc_state)"
  fi

  W=$(waiting_on)
  STATE="reboot,bx,s$S,d$D,a$(short "${APX:-x}" 3),k${K:-x},b$(short "${BPF:-x}" 3),v${V:-x},z$(short "${Z:-x}" 3),u$ADB$(udc_state),w$(short "$W" 14)"
  CRUMB="$STATE,t$((NOW-START))"

  # Crash mode: once zygote has died at least once, report why instead.
  # reboot,bx,c,s<stage>,z<e|s><code>n<deaths>,a<adbd state><e|s><code>,m<message>
  ZX=$(svc_exit zygote)
  if [ "$ZX" != x ] || [ "$Z" = restarting ] || [ "$BOOXOS_PROBE_ONCE" = crash ]; then
    AX=$(svc_exit adbd)
    HEAD="reboot,bx,c,s$S,z$ZX,a$(short "$(p init.svc.adbd)" 3)$AX,u$ADB,m"
    ROOM=$((MAXLEN - ${#HEAD} - 6))   # keep room for ",stall"/",late"
    [ $ROOM -gt 8 ] || ROOM=8
    STATE="$HEAD$(crash_msg | cut -c1-$ROOM)"
    CRUMB="$STATE"
  fi

  # Data mode (probe v3): APEXes are up but /data isn't mounted after 20 s.
  # Report the Keymaster HAL and vold instead (takes priority over crash mode).
  # reboot,bx,d,s<stage>,k<km state><e|s><code>n<deaths>,r<km registered>,f<km log flag>,v<vold/fs_mgr msg>
  if { [ $D = 0 ] && [ "$APX" = activated -o "$APX" = ready ] && [ $((NOW-START)) -ge 20 ]; } \
     || [ "$BOOXOS_PROBE_ONCE" = data ]; then
    # reboot,bx,p<page>/<pages>,<slice of the report>
    REP=$(data_report)
    PG=60
    PAGES=$(( (${#REP} + PG - 1) / PG )); [ $PAGES -gt 0 ] || PAGES=1
    K=$((PAGEIDX % PAGES))
    STATE="reboot,bx,p$K/$PAGES,$(echo "$REP" | cut -c$((K*PG+1))-$(((K+1)*PG)))"
    CRUMB="$STATE"
    [ -n "$BOOXOS_PROBE_ONCE" ] && echo "full report (${#REP} chars): $REP" >&2
  fi

  if [ -n "$BOOXOS_PROBE_ONCE" ]; then
    # test mode: print the breadcrumb once, no side effects
    echo "$CRUMB"
    exit 0
  fi

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
    logcat -b crash -d > $LOGDIR/crash.txt 2>&1
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
