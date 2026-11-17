#!/system/bin/sh
# BOOXOS_BRINGUP only. Mirrors stock vendor init.qcom.usb.rc's adb gadget setup.
log() { echo "booxos-earlyadb: $*" > /dev/kmsg; }
log start
G=/config/usb_gadget/g1
mountpoint -q /config || mount -t configfs none /config
mkdir -p $G/strings/0x409 $G/functions/ffs.adb $G/configs/b.1/strings/0x409
echo 0x0200 > $G/bcdUSB
echo 0x18d1 > $G/idVendor
echo 0x4ee7 > $G/idProduct
getprop ro.serialno > $G/strings/0x409/serialnumber
echo BooxOS > $G/strings/0x409/manufacturer
echo "BooxOS bring-up" > $G/strings/0x409/product
echo adb > $G/configs/b.1/strings/0x409/configuration
mkdir -p /dev/usb-ffs/adb
chown shell:system /dev/usb-ffs /dev/usb-ffs/adb
mountpoint -q /dev/usb-ffs/adb || mount -t functionfs -o uid=2000,gid=1000,rmode=0770,fmode=0660 adb /dev/usb-ffs/adb
setprop ctl.start adbd
i=0; while [ ! -e /dev/usb-ffs/adb/ep1 ] && [ $i -lt 60 ]; do sleep 0.5; i=$((i+1)); done
log "ffs ep1 after $i polls"
[ -L $G/configs/b.1/f1 ] || ln -s $G/functions/ffs.adb $G/configs/b.1/f1
UDC=$(getprop ro.boot.usbcontroller); [ -n "$UDC" ] || UDC=a600000.dwc3
cat $G/UDC 2>/dev/null | grep -q . || echo $UDC > $G/UDC
log "udc=$(cat $G/UDC) adbd=$(getprop init.svc.adbd)"
D=/data/local/tmp/booxos; mkdir -p $D; chmod 0777 $D
n=0
while [ $n -lt 400 ]; do
  dmesg > $D/dmesg.txt 2>&1
  logcat -b all -d > $D/logcat.txt 2>&1
  getprop > $D/getprop.txt 2>&1
  ps -A -o PID,USER,S,WCHAN,NAME > $D/ps.txt 2>&1
  chmod 0666 $D/*.txt
  n=$((n+1)); sleep 3
done
