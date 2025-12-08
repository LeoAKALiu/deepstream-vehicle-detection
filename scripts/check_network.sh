#!/bin/bash
# -*- coding: utf-8 -*-
"""
网络检查脚本
检查 Cassia 路由器、互联网连接、DNS 等
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ERRORS=0
WARNINGS=0

echo "=========================================="
echo "网络检查开始"
echo "=========================================="
echo ""

# 1. 检查 Cassia 路由器连接
echo -n "检查 Cassia 路由器... "
CASSIA_IP=$(grep -A 1 "network:" "$PROJECT_ROOT/config.yaml" | grep "cassia_ip:" | awk '{print $2}' | tr -d '"')
if [ -z "$CASSIA_IP" ]; then
    CASSIA_IP="192.168.1.2"  # 默认IP
fi

if ping -c 3 -W 2 "$CASSIA_IP" > /dev/null 2>&1; then
    LATENCY=$(ping -c 1 -W 2 "$CASSIA_IP" 2>/dev/null | grep "time=" | awk -F'time=' '{print $2}' | awk '{print $1}')
    echo -e "${GREEN}✓ 路由器可访问 ($CASSIA_IP, 延迟: ${LATENCY}ms)${NC}"
else
    echo -e "${YELLOW}⚠ 路由器不可访问 ($CASSIA_IP)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 2. 检查互联网连接
echo -n "检查互联网连接... "
if ping -c 2 -W 3 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 互联网连接正常${NC}"
    INTERNET_AVAILABLE=1
else
    echo -e "${YELLOW}⚠ 互联网连接不可用${NC}"
    WARNINGS=$((WARNINGS + 1))
    INTERNET_AVAILABLE=0
fi

# 3. 检查 DNS 解析
echo -n "检查 DNS 解析... "
if [ "$INTERNET_AVAILABLE" = "1" ]; then
    if nslookup google.com > /dev/null 2>&1; then
        echo -e "${GREEN}✓ DNS 解析正常${NC}"
    else
        echo -e "${YELLOW}⚠ DNS 解析失败${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠ 跳过 DNS 检查（无互联网连接）${NC}"
fi

# 4. 检查网络接口
echo -n "检查网络接口... "
ACTIVE_INTERFACES=$(ip -o link show | grep -c "state UP")
if [ "$ACTIVE_INTERFACES" -gt 0 ]; then
    echo -e "${GREEN}✓ 检测到 $ACTIVE_INTERFACES 个活动网络接口${NC}"
else
    echo -e "${RED}✗ 无活动网络接口${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 5. 检查默认网关
echo -n "检查默认网关... "
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -n 1)
if [ -n "$GATEWAY" ]; then
    if ping -c 1 -W 2 "$GATEWAY" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 默认网关可访问 ($GATEWAY)${NC}"
    else
        echo -e "${YELLOW}⚠ 默认网关不可访问 ($GATEWAY)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠ 未配置默认网关${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. 检查云端服务器连接（如果配置了）
echo -n "检查云端服务器... "
CLOUD_URL=$(grep -A 10 "cloud:" "$PROJECT_ROOT/config.yaml" | grep "api_base_url:" | awk '{print $2}' | tr -d '"')
if [ -n "$CLOUD_URL" ] && [ "$CLOUD_URL" != "http://your-server-ip:8000" ]; then
    # 提取主机名
    HOST=$(echo "$CLOUD_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f1)
    PORT=$(echo "$CLOUD_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f2)
    if [ -z "$PORT" ]; then
        PORT=80
    fi
    
    if timeout 3 bash -c "echo > /dev/tcp/$HOST/$PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ 云端服务器可访问 ($HOST:$PORT)${NC}"
    else
        echo -e "${YELLOW}⚠ 云端服务器不可访问 ($HOST:$PORT)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠ 云端服务器未配置${NC}"
fi

echo ""
echo "=========================================="
echo "网络检查完成"
echo "=========================================="
echo "错误: $ERRORS"
echo "警告: $WARNINGS"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}网络检查失败${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}网络检查通过，但有警告（系统可继续运行）${NC}"
    exit 0
else
    echo -e "${GREEN}网络检查全部通过${NC}"
    exit 0
fi

