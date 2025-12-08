#!/bin/bash
# -*- coding: utf-8 -*-
"""
车辆检测系统启动脚本
包含硬件检查、网络检查、环境配置等
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

# 日志文件
LOG_FILE="${PROJECT_ROOT}/logs/startup.log"
mkdir -p "$(dirname "$LOG_FILE")"

# 检查系统时间（如果时间明显错误，给出警告）
check_system_time() {
    CURRENT_YEAR=$(date +%Y 2>/dev/null || echo "0")
    if [ "$CURRENT_YEAR" -lt 2020 ]; then
        echo -e "${YELLOW}警告: 系统时间可能不正确 (当前年份: $CURRENT_YEAR)${NC}" >&2
        echo -e "${YELLOW}建议运行: sudo ./scripts/fix_system_time.sh${NC}" >&2
    fi
}

# 获取时间戳（带错误处理）
get_timestamp() {
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
    if [ -z "$TIMESTAMP" ] || [ "$(date +%Y 2>/dev/null)" -lt 2020 ]; then
        # 如果时间获取失败或明显错误，使用相对时间
        TIMESTAMP="$(date +%s 2>/dev/null || echo "0")"
        TIMESTAMP="[时间错误: $TIMESTAMP]"
    fi
    echo "$TIMESTAMP"
}

# 日志函数
log() {
    TIMESTAMP=$(get_timestamp)
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log_error() {
    TIMESTAMP=$(get_timestamp)
    echo -e "${RED}[$TIMESTAMP] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    TIMESTAMP=$(get_timestamp)
    echo -e "${BLUE}[$TIMESTAMP] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    TIMESTAMP=$(get_timestamp)
    echo -e "${GREEN}[$TIMESTAMP] SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    TIMESTAMP=$(get_timestamp)
    echo -e "${YELLOW}[$TIMESTAMP] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# 检查系统时间
check_system_time

# 进入项目目录
cd "$PROJECT_ROOT"

log "=========================================="
log "车辆检测系统启动"
log "=========================================="
log "项目目录: $PROJECT_ROOT"
log ""

# 1. 硬件检查
log_info "执行硬件检查..."
if "$SCRIPT_DIR/check_hardware.sh" >> "$LOG_FILE" 2>&1; then
    log_success "硬件检查通过"
else
    HARDWARE_EXIT_CODE=$?
    if [ $HARDWARE_EXIT_CODE -eq 1 ]; then
        log_error "硬件检查失败，无法启动系统"
        exit 1
    else
        log_warning "硬件检查有警告，但可以继续启动"
    fi
fi

# 2. 网络检查（非阻塞）
log_info "执行网络检查..."
if "$SCRIPT_DIR/check_network.sh" >> "$LOG_FILE" 2>&1; then
    log_success "网络检查通过"
else
    NETWORK_EXIT_CODE=$?
    if [ $NETWORK_EXIT_CODE -eq 1 ]; then
        log_error "网络检查失败，但系统可以继续运行（本地模式）"
    else
        log_warning "网络检查有警告，但可以继续运行"
    fi
fi

# 3. 检查配置文件
log_info "检查配置文件..."
if [ ! -f "$PROJECT_ROOT/config.yaml" ]; then
    log_error "配置文件不存在: $PROJECT_ROOT/config.yaml"
    exit 1
fi
log_success "配置文件存在"

# 4. 检查模型文件
log_info "检查模型文件..."
MODEL_PATH=$(grep -A 1 "detection:" "$PROJECT_ROOT/config.yaml" | grep "model_path:" | awk '{print $2}' | tr -d '"')
if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH="$PROJECT_ROOT/models/custom_yolo.engine"
fi

if [ ! -f "$MODEL_PATH" ]; then
    # 尝试相对路径
    MODEL_PATH="$PROJECT_ROOT/$(grep -A 1 "detection:" "$PROJECT_ROOT/config.yaml" | grep "model_path:" | awk '{print $2}' | tr -d '"')"
fi

if [ ! -f "$MODEL_PATH" ]; then
    log_error "模型文件不存在: $MODEL_PATH"
    exit 1
fi
log_success "模型文件存在: $MODEL_PATH"

# 5. 设置环境变量
log_info "设置环境变量..."
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export CUDA_VISIBLE_DEVICES=0

# 设置 Python 路径
if [ -d "$PROJECT_ROOT/python_apps" ]; then
    export PYTHONPATH="$PROJECT_ROOT/python_apps:$PYTHONPATH"
fi

log_success "环境变量已设置"

# 6. 创建必要的目录
log_info "创建必要的目录..."
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/recordings"
mkdir -p "$(dirname "$(grep "snapshot_dir:" "$PROJECT_ROOT/config.yaml" | awk '{print $2}' | tr -d '"')")"
mkdir -p "$(dirname "$(grep "log_file:" "$PROJECT_ROOT/config.yaml" | awk '{print $2}' | tr -d '"')")"
log_success "目录创建完成"

# 7. 清理临时文件（可选）
log_info "清理临时文件..."
rm -f /tmp/orbbec_shared_frame.npy
rm -f /tmp/orbbec_shared_depth.npy
log_success "临时文件清理完成"

# 8. 启动主程序
log_info "启动主程序..."
log "命令: python3 $PROJECT_ROOT/test_system_realtime.py --no-display"
log ""

# 切换到项目目录
cd "$PROJECT_ROOT"

# 启动主程序（无头模式，适合长期运行）
exec python3 "$PROJECT_ROOT/test_system_realtime.py" --no-display >> "$LOG_FILE" 2>&1

