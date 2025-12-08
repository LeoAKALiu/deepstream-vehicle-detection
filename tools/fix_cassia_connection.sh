#!/bin/bash
# 修复Cassia连接问题

cd /home/liubo/Download/deepstream-vehicle-detection

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          🔧 修复Cassia路由器连接                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 检查网卡状态
echo "【1. 检查网卡状态】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ip link show enP8p1s0 | grep -E "state|NO-CARRIER"
echo ""

# 检查网线连接
echo "【2. 检查网线连接】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ip link show enP8p1s0 | grep -q "NO-CARRIER"; then
    echo "⚠ 检测到 NO-CARRIER（无载波信号）"
    echo ""
    echo "可能的原因："
    echo "  1. 网线未连接"
    echo "  2. 网线损坏"
    echo "  3. Cassia路由器未开机"
    echo "  4. 网口故障"
    echo ""
    echo "请检查："
    echo "  - 网线是否牢固插入Jetson的enP8p1s0网口"
    echo "  - 网线另一端是否连接到Cassia路由器"
    echo "  - Cassia路由器电源指示灯是否亮起"
    echo ""
    read -p "确认网线已连接且路由器已开机后，按Enter继续..."
else
    echo "✓ 网线连接正常"
fi
echo ""

# 尝试配置IP地址
echo "【3. 配置网络接口】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 从配置文件读取IP
CASSIA_IP=$(grep -A 1 "^network:" config.yaml | grep "cassia_ip" | awk '{print $2}' | tr -d '"')
if [ -z "$CASSIA_IP" ]; then
    CASSIA_IP="192.168.1.2"
fi

# 提取网段
NETWORK=$(echo $CASSIA_IP | cut -d'.' -f1-3)
JETSON_IP="${NETWORK}.3"

echo "Cassia IP: $CASSIA_IP"
echo "Jetson IP: $JETSON_IP"
echo ""

# 先尝试DHCP
echo "尝试通过DHCP获取IP..."
sudo dhclient -v enP8p1s0 2>&1 | head -5 &
DHCP_PID=$!
sleep 3
sudo kill $DHCP_PID 2>/dev/null

# 检查是否获取到IP
if ip addr show enP8p1s0 | grep -q "inet "; then
    CURRENT_IP=$(ip addr show enP8p1s0 | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
    echo "✓ 通过DHCP获取到IP: $CURRENT_IP"
    echo ""
    echo "尝试ping Cassia路由器..."
    if ping -c 2 -W 2 $CASSIA_IP > /dev/null 2>&1; then
        echo "✓ 成功连接到Cassia路由器 ($CASSIA_IP)"
    else
        echo "⚠ 无法ping通 $CASSIA_IP"
        echo "  可能Cassia的实际IP不是 $CASSIA_IP"
        echo "  请检查路由器标签或使用其他设备查看"
    fi
else
    echo "⚠ DHCP未获取到IP，尝试手动配置静态IP..."
    echo ""
    echo "配置静态IP: $JETSON_IP/24"
    sudo ip addr add $JETSON_IP/24 dev enP8p1s0 2>/dev/null
    sudo ip link set enP8p1s0 up
    
    sleep 1
    
    if ip addr show enP8p1s0 | grep -q "inet "; then
        echo "✓ 静态IP配置成功"
        echo ""
        echo "尝试ping Cassia路由器..."
        if ping -c 2 -W 2 $CASSIA_IP > /dev/null 2>&1; then
            echo "✓ 成功连接到Cassia路由器 ($CASSIA_IP)"
        else
            echo "⚠ 无法ping通 $CASSIA_IP"
            echo ""
            echo "可能的原因："
            echo "  1. Cassia的实际IP不是 $CASSIA_IP"
            echo "  2. Cassia路由器需要时间启动"
            echo "  3. 网线或路由器故障"
            echo ""
            echo "建议："
            echo "  - 查看Cassia路由器标签上的IP地址"
            echo "  - 使用其他设备（如笔记本）直连路由器查看IP"
            echo "  - 运行扫描脚本查找路由器: ./find_cassia_router.sh"
        fi
    else
        echo "✗ 静态IP配置失败"
    fi
fi
echo ""

# 显示当前网络状态
echo "【4. 当前网络状态】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ip addr show enP8p1s0 | grep -E "state|inet "
echo ""

# 如果连接成功，测试Cassia API
if ping -c 1 -W 1 $CASSIA_IP > /dev/null 2>&1; then
    echo "【5. 测试Cassia API】"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    api_response=$(curl -s --connect-timeout 3 -w "\n%{http_code}" http://$CASSIA_IP/management/nodes 2>&1)
    http_code=$(echo "$api_response" | tail -1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        echo "✓ Cassia API响应正常 (状态码: $http_code)"
        echo ""
        echo "现在可以运行扫描测试："
        echo "  ./check_cassia.sh"
    else
        echo "⚠ Cassia API无响应 (状态码: $http_code)"
        echo "  可能需要认证或路由器未完全启动"
    fi
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    修复完成                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""




