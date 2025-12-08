#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          BLE信标扫描测试                                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Cassia路由器IP
CASSIA_IP="192.168.1.2"

# 检查网络
echo "【1. 检查网络连接】"
if ping -c 1 -W 2 $CASSIA_IP > /dev/null 2>&1; then
    echo "✓ Cassia路由器可达 ($CASSIA_IP)"
else
    echo "✗ Cassia路由器不可达 ($CASSIA_IP)"
    echo "请检查："
    echo "  1. Cassia路由器是否开机"
    echo "  2. 网线是否连接"
    echo "  3. IP地址是否正确"
    exit 1
fi
echo ""

# 测试HTTP API
echo "【2. 测试HTTP API】"
if curl -s --connect-timeout 3 http://$CASSIA_IP/management/nodes > /dev/null; then
    echo "✓ HTTP API响应正常"
else
    echo "✗ HTTP API无响应"
    exit 1
fi
echo ""

# 测试SSE扫描
echo "【3. 测试实时扫描（30秒）】"
echo "请确保BLE标签已开启并在10米范围内..."
echo ""

timeout 30 curl -N "http://$CASSIA_IP/gap/nodes?event=1&filter_rssi=-90&active=1" 2>&1 | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
        # 解析JSON
        json_data="${line#data:}"
        if echo "$json_data" | grep -q "bdaddr"; then
            mac=$(echo "$json_data" | grep -o '"bdaddr":"[^"]*"' | head -1 | cut -d'"' -f4)
            rssi=$(echo "$json_data" | grep -o '"rssi":[0-9-]*' | head -1 | cut -d':' -f2)
            if [ -n "$mac" ] && [ -n "$rssi" ]; then
                echo "  ✓ 发现信标: MAC=$mac, RSSI=$rssi dBm"
            fi
        fi
    fi
done

echo ""
echo "【4. 测试完成】"
echo ""
echo "如果上面没有显示任何信标，请检查："
echo "  1. BLE标签是否开启（LED是否闪烁）"
echo "  2. BLE标签电量是否充足"
echo "  3. BLE标签距离是否<10米"
echo "  4. Cassia路由器是否正常工作"
echo ""
echo "手动扫描测试："
echo "  curl -N 'http://$CASSIA_IP/gap/nodes?event=1&filter_rssi=-90&active=1'"
echo ""


