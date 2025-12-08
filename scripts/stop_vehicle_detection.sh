#!/bin/bash
# -*- coding: utf-8 -*-
"""
车辆检测系统停止脚本
优雅关闭主程序，清理临时文件
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

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log "=========================================="
log "车辆检测系统停止"
log "=========================================="
log ""

# 1. 查找主程序进程
log_info "查找主程序进程..."
MAIN_PID=$(pgrep -f "test_system_realtime.py" || true)

if [ -z "$MAIN_PID" ]; then
    log_warning "主程序未运行"
    exit 0
fi

log_info "找到主程序进程: PID=$MAIN_PID"

# 2. 发送 SIGTERM 信号（优雅关闭）
log_info "发送停止信号..."
kill -TERM "$MAIN_PID" 2>/dev/null || true

# 等待进程退出（最多等待30秒）
TIMEOUT=30
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if ! kill -0 "$MAIN_PID" 2>/dev/null; then
        log_success "主程序已停止"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# 3. 如果进程仍在运行，强制终止
if kill -0 "$MAIN_PID" 2>/dev/null; then
    log_warning "主程序未响应，强制终止..."
    kill -KILL "$MAIN_PID" 2>/dev/null || true
    sleep 2
    log_success "主程序已强制终止"
fi

# 4. 清理临时文件
log_info "清理临时文件..."
rm -f /tmp/orbbec_shared_frame.npy
rm -f /tmp/orbbec_shared_depth.npy
log_success "临时文件清理完成"

# 5. 保存状态信息（可选）
log_info "保存状态信息..."
STATE_FILE="$PROJECT_ROOT/logs/last_stop_time.txt"
echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$STATE_FILE"
log_success "状态信息已保存"

log ""
log "=========================================="
log "系统已停止"
log "=========================================="

