#!/bin/bash
# 检查Cassia路由器连接和扫描功能

cd /home/liubo/Download/deepstream-vehicle-detection

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          🔍 Cassia路由器连接和扫描检查                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 从配置文件读取IP
CASSIA_IP=$(grep -A 1 "^network:" config.yaml | grep "cassia_ip" | awk '{print $2}' | tr -d '"')
if [ -z "$CASSIA_IP" ]; then
    CASSIA_IP="192.168.1.2"  # 默认值
fi

echo "配置的Cassia IP: $CASSIA_IP"
echo ""

# ============================================
# 1. 检查网络连接
# ============================================
echo "【1. 检查网络连接】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ping -c 3 -W 2 $CASSIA_IP > /dev/null 2>&1; then
    echo "✓ Cassia路由器可达 ($CASSIA_IP)"
    ping_time=$(ping -c 1 -W 2 $CASSIA_IP 2>&1 | grep "time=" | awk -F'time=' '{print $2}' | awk '{print $1}')
    echo "  延迟: $ping_time"
else
    echo "✗ Cassia路由器不可达 ($CASSIA_IP)"
    echo ""
    echo "可能的原因："
    echo "  1. Cassia路由器未开机"
    echo "  2. 网线未连接或松动"
    echo "  3. IP地址配置错误"
    echo "  4. 网络接口未启用"
    echo ""
    echo "请检查："
    echo "  - 网线连接状态"
    echo "  - 路由器电源指示灯"
    echo "  - Jetson网卡状态: ip addr show"
    exit 1
fi
echo ""

# ============================================
# 2. 检查HTTP API
# ============================================
echo "【2. 检查HTTP API】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 测试管理API
echo "测试管理API: http://$CASSIA_IP/management/nodes"
api_response=$(curl -s --connect-timeout 5 -w "\n%{http_code}" http://$CASSIA_IP/management/nodes 2>&1)
http_code=$(echo "$api_response" | tail -1)
api_body=$(echo "$api_response" | head -n -1)

if [ "$http_code" = "200" ] || [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
    echo "✓ HTTP API响应正常 (状态码: $http_code)"
    if [ -n "$api_body" ] && [ "$api_body" != "null" ]; then
        echo "  响应内容: $(echo "$api_body" | head -c 100)..."
    fi
else
    echo "✗ HTTP API无响应或错误 (状态码: $http_code)"
    if [ -n "$api_body" ]; then
        echo "  错误信息: $(echo "$api_body" | head -c 200)"
    fi
    echo ""
    echo "可能的原因："
    echo "  1. Cassia路由器未完全启动"
    echo "  2. 需要认证（用户名/密码）"
    echo "  3. API路径不正确"
fi
echo ""

# ============================================
# 3. 测试SSE扫描（快速测试）
# ============================================
echo "【3. 测试BLE扫描功能（10秒）】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "请确保BLE标签已开启并在10米范围内..."
echo ""

scan_url="http://$CASSIA_IP/gap/nodes?event=1&filter_rssi=-90&active=1"
beacon_count=0
beacons_found=()

echo "开始扫描..."
timeout 10 curl -N -s "$scan_url" 2>&1 | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
        json_data="${line#data:}"
        if echo "$json_data" | grep -q "bdaddr"; then
            mac=$(echo "$json_data" | grep -o '"bdaddr":"[^"]*"' | head -1 | cut -d'"' -f4)
            rssi=$(echo "$json_data" | grep -o '"rssi":[0-9-]*' | head -1 | cut -d':' -f2)
            name=$(echo "$json_data" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
            
            if [ -n "$mac" ] && [ -n "$rssi" ]; then
                beacon_count=$((beacon_count + 1))
                beacons_found+=("$mac")
                echo "  ✓ 发现信标 #$beacon_count: MAC=$mac, RSSI=$rssi dBm${name:+", 名称=$name"}"
            fi
        fi
    fi
done

echo ""
if [ ${#beacons_found[@]} -eq 0 ]; then
    echo "⚠ 10秒内未扫描到任何信标"
    echo ""
    echo "可能的原因："
    echo "  1. BLE标签未开启（检查LED指示灯）"
    echo "  2. BLE标签电量不足"
    echo "  3. BLE标签距离过远（>10米）"
    echo "  4. Cassia路由器扫描功能异常"
    echo ""
    echo "建议："
    echo "  - 将BLE标签靠近路由器（<5米）"
    echo "  - 检查标签是否正常工作"
    echo "  - 尝试延长扫描时间"
else
    echo "✓ 扫描功能正常，发现 ${#beacons_found[@]} 个信标"
fi
echo ""

# ============================================
# 4. 使用Python客户端测试（更详细）
# ============================================
echo "【4. 使用Python客户端测试（可选）】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "运行以下命令进行更详细的测试："
echo ""
echo "  cd python_apps"
echo "  python3 cassia_local_client.py $CASSIA_IP"
echo ""
echo "这将启动实时扫描，显示所有发现的信标及其详细信息"
echo ""

# ============================================
# 5. 检查配置
# ============================================
echo "【5. 检查配置文件】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "config.yaml" ]; then
    echo "✓ config.yaml 存在"
    config_ip=$(grep -A 1 "^network:" config.yaml | grep "cassia_ip" | awk '{print $2}' | tr -d '"')
    echo "  配置的IP: $config_ip"
else
    echo "✗ config.yaml 不存在"
fi

if [ -f "beacon_whitelist.yaml" ]; then
    echo "✓ beacon_whitelist.yaml 存在"
    whitelist_count=$(grep -c "mac:" beacon_whitelist.yaml 2>/dev/null || echo "0")
    echo "  白名单信标数量: $whitelist_count"
else
    echo "✗ beacon_whitelist.yaml 不存在"
fi
echo ""

# ============================================
# 总结
# ============================================
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    检查完成                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "如果扫描不到信标，请："
echo "  1. 确认BLE标签已开启并靠近路由器（<5米）"
echo "  2. 检查标签电量"
echo "  3. 运行Python客户端进行详细测试："
echo "     cd python_apps && python3 cassia_local_client.py $CASSIA_IP"
echo ""




