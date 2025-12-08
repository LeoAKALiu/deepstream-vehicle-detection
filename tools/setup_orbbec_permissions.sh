#!/bin/bash

cat << 'EOF' > /tmp/99-obsensor-libusb.rules
# Orbbec USB devices udev rules

# Gemini 335L and other Orbbec devices
SUBSYSTEM=="usb", ATTRS{idVendor}=="2bc5", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666", GROUP="plugdev"

EOF

sudo cp /tmp/99-obsensor-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger

echo "✓ Orbbec udev规则已安装"
echo ""
echo "请重新插拔相机或重启系统以使规则生效"






