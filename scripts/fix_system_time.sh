#!/bin/bash
# 修复系统时间脚本
# 同步系统时间（需要网络连接）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "修复系统时间"
echo "=========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 1. 检查当前时间
echo "当前系统时间:"
date
echo ""

# 2. 检查 NTP 服务状态
echo "检查 NTP 服务..."
if systemctl is-active --quiet systemd-timesyncd || systemctl is-active --quiet ntpd; then
    echo -e "${GREEN}✓ NTP 服务正在运行${NC}"
else
    echo -e "${YELLOW}⚠ NTP 服务未运行，尝试启动...${NC}"
    systemctl start systemd-timesyncd 2>/dev/null || systemctl start ntpd 2>/dev/null || true
fi

# 3. 尝试同步时间
echo ""
echo "尝试同步系统时间..."

# 方法1: 使用 systemd-timesyncd
if command -v timedatectl &> /dev/null; then
    echo "使用 timedatectl 同步时间..."
    timedatectl set-ntp true
    sleep 2
    timedatectl status
fi

# 方法2: 使用 ntpdate (如果可用)
if command -v ntpdate &> /dev/null; then
    echo ""
    echo "使用 ntpdate 同步时间..."
    ntpdate -s pool.ntp.org || ntpdate -s time.nist.gov || true
fi

# 方法3: 使用 rdate (如果可用)
if command -v rdate &> /dev/null; then
    echo ""
    echo "使用 rdate 同步时间..."
    rdate -s time.nist.gov || rdate -s pool.ntp.org || true
fi

# 4. 如果网络同步失败，提供手动设置选项
echo ""
CURRENT_YEAR=$(date +%Y)
if [ "$CURRENT_YEAR" -lt 2020 ]; then
    echo -e "${YELLOW}⚠ 系统时间仍然不正确 (当前年份: $CURRENT_YEAR)${NC}"
    echo ""
    echo "网络时间同步失败，尝试手动设置时间..."
    echo ""
    
    # 先禁用 NTP 自动同步
    echo "禁用 NTP 自动同步..."
    timedatectl set-ntp false
    sleep 1
    
    # 尝试从网络获取时间（如果可用）
    if ping -c 1 -W 2 pool.ntp.org > /dev/null 2>&1; then
        echo "尝试使用 ntpdate 同步..."
        if command -v ntpdate &> /dev/null; then
            ntpdate -s pool.ntp.org 2>/dev/null || ntpdate -s time.nist.gov 2>/dev/null || true
        fi
    fi
    
    # 如果还是失败，手动设置
    CURRENT_YEAR=$(date +%Y)
    if [ "$CURRENT_YEAR" -lt 2020 ]; then
        echo ""
        echo "需要手动设置时间。"
        read -p "是否手动设置时间? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # 获取当前实际时间（如果可能）
            SUGGESTED_TIME=$(date -d "now" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "2025-01-08 12:00:00")
            echo "建议时间: $SUGGESTED_TIME"
            read -p "请输入日期时间 (格式: YYYY-MM-DD HH:MM:SS，直接回车使用建议时间): " MANUAL_TIME
            if [ -z "$MANUAL_TIME" ]; then
                MANUAL_TIME="$SUGGESTED_TIME"
            fi
            if [ -n "$MANUAL_TIME" ]; then
                echo "设置时间为: $MANUAL_TIME"
                timedatectl set-time "$MANUAL_TIME"
                echo -e "${GREEN}✓ 时间已设置为: $MANUAL_TIME${NC}"
            fi
        fi
    else
        echo -e "${GREEN}✓ 时间已通过 ntpdate 同步${NC}"
    fi
    
    # 重新启用 NTP（可选）
    echo ""
    read -p "是否重新启用 NTP 自动同步? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        timedatectl set-ntp true
        echo -e "${GREEN}✓ NTP 自动同步已启用${NC}"
    fi
fi

# 5. 显示最终时间
echo ""
echo "=========================================="
echo "最终系统时间:"
date
timedatectl status
echo "=========================================="

