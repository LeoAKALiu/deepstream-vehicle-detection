#!/bin/bash
# 测试Cassia路由器连通性

CASSIA_IP="192.168.3.26"
PROJECT_ROOT="/home/liubo/Download/deepstream-vehicle-detection"

# 从配置文件读取IP（如果存在）
if [ -f "$PROJECT_ROOT/config.yaml" ]; then
    CONFIG_IP=$(grep -A 1 "network:" "$PROJECT_ROOT/config.yaml" | grep "cassia_ip:" | awk '{print $2}' | tr -d '"' || echo "")
    if [ -n "$CONFIG_IP" ]; then
        CASSIA_IP="$CONFIG_IP"
    fi
fi

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          测试Cassia路由器连通性                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Cassia IP: $CASSIA_IP"
echo ""

# 1. Ping测试
echo "【1. Ping测试】"
if ping -c 3 -W 2 "$CASSIA_IP" > /dev/null 2>&1; then
    LATENCY=$(ping -c 1 -W 2 "$CASSIA_IP" 2>/dev/null | grep "time=" | awk -F'time=' '{print $2}' | awk '{print $1}')
    echo "  ✓ Ping成功 (延迟: ${LATENCY})"
else
    echo "  ✗ Ping失败"
    exit 1
fi
echo ""

# 2. Web接口测试
echo "【2. Web接口测试（端口80）】"
HTTP_CODE=$(timeout 3 curl -s -o /dev/null -w "%{http_code}" "http://$CASSIA_IP" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Web接口可访问 (HTTP $HTTP_CODE)"
else
    echo "  ⚠ Web接口响应异常 (HTTP $HTTP_CODE)"
fi
echo ""

# 3. SSE扫描接口测试
echo "【3. SSE扫描接口测试】"
echo "  测试: http://$CASSIA_IP/gap/nodes?event=1&filter_rssi=-90&active=1"
SSE_OUTPUT=$(timeout 5 curl -N -s "http://$CASSIA_IP/gap/nodes?event=1&filter_rssi=-90&active=1" 2>&1 | head -5)
if [ -n "$SSE_OUTPUT" ]; then
    echo "  ✓ SSE接口响应正常"
    echo "  响应示例:"
    echo "$SSE_OUTPUT" | head -3 | sed 's/^/    /'
else
    echo "  ⚠ SSE接口无响应或超时"
fi
echo ""

# 4. 网络路由检查
echo "【4. 网络路由检查】"
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
JETSON_IP=$(ip addr show | grep -E "inet.*192.168.3" | awk '{print $2}' | cut -d'/' -f1 | head -1)
echo "  Jetson IP: ${JETSON_IP:-未找到}"
echo "  网关: ${GATEWAY:-未找到}"
if [ -n "$JETSON_IP" ] && [ -n "$GATEWAY" ]; then
    echo "  ✓ 网络配置正常"
else
    echo "  ⚠ 网络配置可能异常"
fi
echo ""

# 5. 总结
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    测试完成                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Cassia路由器状态:"
echo "  IP地址: $CASSIA_IP"
echo "  连通性: $(ping -c 1 -W 2 "$CASSIA_IP" > /dev/null 2>&1 && echo '✓ 正常' || echo '✗ 异常')"
echo ""
echo "配置文件: $PROJECT_ROOT/config.yaml"
echo "  当前配置: cassia_ip: $CASSIA_IP"
echo ""


