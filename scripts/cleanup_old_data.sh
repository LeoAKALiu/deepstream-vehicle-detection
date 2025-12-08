#!/bin/bash
# 数据清理脚本
# 自动清理旧日志、视频、快照等数据

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 配置（从config.yaml读取，或使用默认值）
LOG_RETENTION_DAYS=30          # 日志保留天数
VIDEO_RETENTION_DAYS=7         # 视频保留天数
SNAPSHOT_RETENTION_DAYS=7      # 快照保留天数
DISK_CLEANUP_THRESHOLD=80      # 磁盘使用率阈值（超过此值开始清理）

# 日志文件
LOG_FILE="${PROJECT_ROOT}/logs/cleanup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# 检查磁盘使用率
check_disk_usage() {
    DISK_USAGE=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "$DISK_USAGE"
}

# 清理旧日志
cleanup_logs() {
    log_info "清理旧日志（保留 ${LOG_RETENTION_DAYS} 天）..."
    
    LOG_DIRS=(
        "$PROJECT_ROOT/logs"
        "/tmp"
    )
    
    TOTAL_DELETED=0
    TOTAL_SIZE=0
    
    for log_dir in "${LOG_DIRS[@]}"; do
        if [ -d "$log_dir" ]; then
            # 查找并删除旧日志文件
            while IFS= read -r file; do
                if [ -f "$file" ]; then
                    FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
                    rm -f "$file"
                    TOTAL_DELETED=$((TOTAL_DELETED + 1))
                    TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
                    log "删除日志: $file"
                fi
            done < <(find "$log_dir" -name "*.log" -type f -mtime +${LOG_RETENTION_DAYS} 2>/dev/null)
            
            # 删除压缩的日志文件
            while IFS= read -r file; do
                if [ -f "$file" ]; then
                    FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
                    rm -f "$file"
                    TOTAL_DELETED=$((TOTAL_DELETED + 1))
                    TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
                    log "删除压缩日志: $file"
                fi
            done < <(find "$log_dir" -name "*.log.*" -type f -mtime +${LOG_RETENTION_DAYS} 2>/dev/null)
        fi
    done
    
    if [ $TOTAL_DELETED -gt 0 ]; then
        SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))
        log_success "清理完成: 删除 $TOTAL_DELETED 个日志文件，释放 ${SIZE_MB}MB 空间"
    else
        log_info "没有需要清理的日志文件"
    fi
}

# 清理旧视频
cleanup_videos() {
    log_info "清理旧视频（保留 ${VIDEO_RETENTION_DAYS} 天）..."
    
    VIDEO_DIRS=(
        "$PROJECT_ROOT/recordings"
    )
    
    TOTAL_DELETED=0
    TOTAL_SIZE=0
    
    for video_dir in "${VIDEO_DIRS[@]}"; do
        if [ -d "$video_dir" ]; then
            # 查找并删除旧视频文件
            while IFS= read -r file; do
                if [ -f "$file" ]; then
                    FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
                    rm -f "$file"
                    TOTAL_DELETED=$((TOTAL_DELETED + 1))
                    TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
                    log "删除视频: $file"
                fi
            done < <(find "$video_dir" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mkv" \) -mtime +${VIDEO_RETENTION_DAYS} 2>/dev/null)
            
            # 删除空的录制目录
            find "$video_dir" -type d -empty -mtime +${VIDEO_RETENTION_DAYS} -delete 2>/dev/null || true
        fi
    done
    
    if [ $TOTAL_DELETED -gt 0 ]; then
        SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))
        log_success "清理完成: 删除 $TOTAL_DELETED 个视频文件，释放 ${SIZE_MB}MB 空间"
    else
        log_info "没有需要清理的视频文件"
    fi
}

# 清理旧快照
cleanup_snapshots() {
    log_info "清理旧快照（保留 ${SNAPSHOT_RETENTION_DAYS} 天）..."
    
    # 从config.yaml读取快照目录
    SNAPSHOT_DIR=$(grep "snapshot_dir:" "$PROJECT_ROOT/config.yaml" | awk '{print $2}' | tr -d '"' || echo "/tmp/vehicle_snapshots")
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        log_info "快照目录不存在: $SNAPSHOT_DIR"
        return
    fi
    
    TOTAL_DELETED=0
    TOTAL_SIZE=0
    
    # 查找并删除旧快照
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
            rm -f "$file"
            TOTAL_DELETED=$((TOTAL_DELETED + 1))
            TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
            log "删除快照: $file"
        fi
    done < <(find "$SNAPSHOT_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) -mtime +${SNAPSHOT_RETENTION_DAYS} 2>/dev/null)
    
    # 删除空的快照目录
    find "$SNAPSHOT_DIR" -type d -empty -delete 2>/dev/null || true
    
    if [ $TOTAL_DELETED -gt 0 ]; then
        SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))
        log_success "清理完成: 删除 $TOTAL_DELETED 个快照文件，释放 ${SIZE_MB}MB 空间"
    else
        log_info "没有需要清理的快照文件"
    fi
}

# 清理临时文件
cleanup_temp_files() {
    log_info "清理临时文件..."
    
    TEMP_FILES=(
        "/tmp/orbbec_shared_frame.npy"
        "/tmp/orbbec_shared_depth.npy"
        "/tmp/*.npy"
    )
    
    TOTAL_DELETED=0
    
    for pattern in "${TEMP_FILES[@]}"; do
        for file in $pattern; do
            if [ -f "$file" ]; then
                # 只删除超过1小时未使用的临时文件
                if [ $(find "$file" -mmin +60 2>/dev/null | wc -l) -gt 0 ]; then
                    rm -f "$file"
                    TOTAL_DELETED=$((TOTAL_DELETED + 1))
                    log "删除临时文件: $file"
                fi
            fi
        done
    done
    
    if [ $TOTAL_DELETED -gt 0 ]; then
        log_success "清理完成: 删除 $TOTAL_DELETED 个临时文件"
    else
        log_info "没有需要清理的临时文件"
    fi
}

# 主函数
main() {
    log "=========================================="
    log "数据清理开始"
    log "=========================================="
    
    # 检查磁盘使用率
    DISK_USAGE=$(check_disk_usage)
    log_info "当前磁盘使用率: ${DISK_USAGE}%"
    
    # 如果磁盘使用率超过阈值，执行清理
    if [ "$DISK_USAGE" -ge "$DISK_CLEANUP_THRESHOLD" ]; then
        log_warning "磁盘使用率超过阈值 (${DISK_CLEANUP_THRESHOLD}%)，开始清理..."
        cleanup_logs
        cleanup_videos
        cleanup_snapshots
        cleanup_temp_files
    else
        log_info "磁盘使用率正常，执行常规清理..."
        cleanup_logs
        cleanup_videos
        cleanup_snapshots
        cleanup_temp_files
    fi
    
    # 显示清理后的磁盘使用率
    DISK_USAGE_AFTER=$(check_disk_usage)
    log_info "清理后磁盘使用率: ${DISK_USAGE_AFTER}%"
    
    log "=========================================="
    log "数据清理完成"
    log "=========================================="
}

# 如果直接运行脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

