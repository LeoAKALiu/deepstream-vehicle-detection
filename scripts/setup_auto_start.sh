#!/bin/bash
# -*- coding: utf-8 -*-
"""
自动启动安装脚本
安装 systemd 服务并配置开机自启动
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 获取脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 服务名称
SERVICE_NAME="vehicle-detection"
SERVICE_FILE="$SCRIPT_DIR/$SERVICE_NAME.service"
SYSTEMD_DIR="/etc/systemd/system"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

echo "=========================================="
echo "车辆检测系统 - 自动启动安装"
echo "=========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 检查服务文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    log_error "服务文件不存在: $SERVICE_FILE"
    exit 1
fi
log_success "服务文件存在"

# 2. 检查脚本文件权限
log "检查脚本文件权限..."
chmod +x "$SCRIPT_DIR/check_hardware.sh"
chmod +x "$SCRIPT_DIR/check_network.sh"
chmod +x "$SCRIPT_DIR/start_vehicle_detection.sh"
chmod +x "$SCRIPT_DIR/stop_vehicle_detection.sh"
log_success "脚本文件权限已设置"

# 3. 更新服务文件中的路径（如果需要）
log "更新服务文件路径..."
# 服务文件中的路径应该已经是正确的，这里只是验证
if grep -q "$PROJECT_ROOT" "$SERVICE_FILE"; then
    log_success "服务文件路径正确"
else
    log_warning "请检查服务文件中的路径是否正确"
fi

# 4. 复制服务文件到 systemd 目录
log "安装服务文件..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"
log_success "服务文件已安装到 $SYSTEMD_DIR"

# 5. 重新加载 systemd
log "重新加载 systemd..."
systemctl daemon-reload
log_success "systemd 已重新加载"

# 6. 启用服务（开机自启动）
log "启用服务（开机自启动）..."
systemctl enable "$SERVICE_NAME.service"
log_success "服务已启用（开机自启动）"

# 7. 显示服务状态
log "当前服务状态:"
systemctl status "$SERVICE_NAME.service" --no-pager || true

echo ""
echo "=========================================="
echo "安装完成"
echo "=========================================="
echo ""
echo "服务管理命令:"
echo "  启动服务:   sudo systemctl start $SERVICE_NAME"
echo "  停止服务:   sudo systemctl stop $SERVICE_NAME"
echo "  重启服务:   sudo systemctl restart $SERVICE_NAME"
echo "  查看状态:   sudo systemctl status $SERVICE_NAME"
echo "  查看日志:   sudo journalctl -u $SERVICE_NAME -f"
echo "  禁用自启:   sudo systemctl disable $SERVICE_NAME"
echo ""
echo "注意: 服务将在下次系统启动时自动运行"
echo ""

# 询问是否立即启动服务
read -p "是否立即启动服务? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "启动服务..."
    systemctl start "$SERVICE_NAME.service"
    sleep 2
    systemctl status "$SERVICE_NAME.service" --no-pager || true
    log_success "服务已启动"
fi

