#!/bin/bash
# 长期测试启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="/home/liubo/Download/deepstream-vehicle-detection"
cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           长期测试启动检查                                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    return 1
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. 检查服务配置
echo "【1. 检查系统服务配置】"
if systemctl is-enabled vehicle-detection > /dev/null 2>&1; then
    check_pass "Systemd服务已启用"
else
    check_fail "Systemd服务未启用，请运行: sudo ./scripts/setup_auto_start.sh"
    exit 1
fi

# 2. 检查硬件
echo ""
echo "【2. 检查硬件连接】"
if bash scripts/check_hardware.sh > /dev/null 2>&1; then
    check_pass "硬件检查通过"
else
    check_warn "硬件检查有警告，请查看详细信息"
    bash scripts/check_hardware.sh
fi

# 3. 检查网络
echo ""
echo "【3. 检查网络连接】"
if bash scripts/check_network.sh > /dev/null 2>&1; then
    check_pass "网络检查通过"
else
    check_warn "网络检查有警告，请查看详细信息"
    bash scripts/check_network.sh
fi

# 4. 检查配置文件
echo ""
echo "【4. 检查配置文件】"
if [ -f "config.yaml" ]; then
    CASSIA_IP=$(grep -A 1 "network:" config.yaml | grep "cassia_ip:" | awk '{print $2}' | tr -d '"')
    if [ "$CASSIA_IP" = "192.168.3.26" ]; then
        check_pass "Cassia IP配置正确: $CASSIA_IP"
    else
        check_warn "Cassia IP配置: $CASSIA_IP (期望: 192.168.3.26)"
    fi
else
    check_fail "配置文件不存在"
    exit 1
fi

# 5. 检查磁盘空间
echo ""
echo "【5. 检查磁盘空间】"
DISK_USAGE=$(df -h /tmp | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "磁盘空间充足: ${DISK_USAGE}% 已使用"
else
    check_warn "磁盘空间不足: ${DISK_USAGE}% 已使用，建议清理"
fi

# 6. 检查数据库
echo ""
echo "【6. 检查数据存储】"
if [ -f "detection_results.db" ]; then
    DB_SIZE=$(du -h detection_results.db | awk '{print $1}')
    check_pass "数据库文件存在: $DB_SIZE"
else
    check_pass "数据库文件不存在（首次运行正常）"
fi

# 7. 显示系统状态
echo ""
echo "【7. 当前系统状态】"
bash scripts/system_status.sh --brief 2>/dev/null || true

# 8. 询问是否启动
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    准备启动                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

read -p "是否启动长期测试? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消启动"
    exit 0
fi

# 9. 启动服务
echo ""
echo "【8. 启动服务】"
if sudo systemctl start vehicle-detection; then
    sleep 3
    if systemctl is-active vehicle-detection > /dev/null 2>&1; then
        check_pass "服务启动成功"
    else
        check_fail "服务启动失败，请查看日志: sudo journalctl -u vehicle-detection -n 50"
        exit 1
    fi
else
    check_fail "无法启动服务"
    exit 1
fi

# 10. 显示启动信息
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    启动完成                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "服务状态:"
sudo systemctl status vehicle-detection --no-pager -l | head -15
echo ""
echo "监控命令:"
echo "  查看日志:   sudo journalctl -u vehicle-detection -f"
echo "  查看状态:   sudo systemctl status vehicle-detection"
echo "  系统状态:   bash scripts/system_status.sh"
echo "  资源监控:   bash scripts/monitor_resources.sh"
echo "  生成报告:   python3 scripts/generate_daily_report.py"
echo ""
echo "停止服务:"
echo "  sudo systemctl stop vehicle-detection"
echo ""

