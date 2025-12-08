#!/bin/bash
# 安装日志轮转配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

echo "=========================================="
echo "安装日志轮转配置"
echo "=========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 检查 logrotate 是否安装
if ! command -v logrotate &> /dev/null; then
    log_error "logrotate 未安装，正在安装..."
    apt-get update && apt-get install -y logrotate
fi

# 复制配置文件
LOGROTATE_CONFIG="$SCRIPT_DIR/logrotate_vehicle_detection"
TARGET_CONFIG="/etc/logrotate.d/vehicle-detection"

log "复制日志轮转配置..."
cp "$LOGROTATE_CONFIG" "$TARGET_CONFIG"
log_success "配置文件已安装到 $TARGET_CONFIG"

# 测试配置
log "测试日志轮转配置..."
logrotate -d "$TARGET_CONFIG" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_success "配置测试通过"
else
    log_error "配置测试失败，请检查配置文件"
    exit 1
fi

# 创建日志目录（如果不存在）
mkdir -p "$PROJECT_ROOT/logs"
chown liubo:liubo "$PROJECT_ROOT/logs" 2>/dev/null || true

log_success "日志轮转配置安装完成"
echo ""
echo "日志轮转配置："
echo "  - 日志文件: $PROJECT_ROOT/logs/*.log"
echo "  - 轮转周期: 每天"
echo "  - 保留天数: 30天"
echo "  - 自动压缩: 是"
echo ""
echo "测试日志轮转："
echo "  sudo logrotate -d /etc/logrotate.d/vehicle-detection"
echo ""
echo "手动执行日志轮转："
echo "  sudo logrotate -f /etc/logrotate.d/vehicle-detection"

