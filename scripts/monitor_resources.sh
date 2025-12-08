#!/bin/bash
# 资源监控脚本
# 监控 CPU、内存、GPU、磁盘等系统资源

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

# 阈值配置
CPU_WARNING=80
CPU_CRITICAL=95
MEMORY_WARNING=80
MEMORY_CRITICAL=95
DISK_WARNING=80
DISK_CRITICAL=90
GPU_TEMP_WARNING=75
GPU_TEMP_CRITICAL=85

# 日志文件
LOG_FILE="${PROJECT_ROOT}/logs/resource_monitor.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# 1. CPU 使用率
check_cpu() {
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    CPU_USAGE=${CPU_USAGE%.*}
    
    if [ "$CPU_USAGE" -ge "$CPU_CRITICAL" ]; then
        log_error "CPU 使用率过高: ${CPU_USAGE}% (临界值: ${CPU_CRITICAL}%)"
        return 2
    elif [ "$CPU_USAGE" -ge "$CPU_WARNING" ]; then
        log_warning "CPU 使用率较高: ${CPU_USAGE}% (警告值: ${CPU_WARNING}%)"
        return 1
    else
        log "CPU 使用率: ${CPU_USAGE}% (正常)"
        return 0
    fi
}

# 2. 内存使用率
check_memory() {
    MEMORY_TOTAL=$(free -m | awk 'NR==2{print $2}')
    MEMORY_USED=$(free -m | awk 'NR==2{print $3}')
    MEMORY_PERCENT=$((MEMORY_USED * 100 / MEMORY_TOTAL))
    
    if [ "$MEMORY_PERCENT" -ge "$MEMORY_CRITICAL" ]; then
        log_error "内存使用率过高: ${MEMORY_PERCENT}% (${MEMORY_USED}MB/${MEMORY_TOTAL}MB) (临界值: ${MEMORY_CRITICAL}%)"
        return 2
    elif [ "$MEMORY_PERCENT" -ge "$MEMORY_WARNING" ]; then
        log_warning "内存使用率较高: ${MEMORY_PERCENT}% (${MEMORY_USED}MB/${MEMORY_TOTAL}MB) (警告值: ${MEMORY_WARNING}%)"
        return 1
    else
        log "内存使用率: ${MEMORY_PERCENT}% (${MEMORY_USED}MB/${MEMORY_TOTAL}MB) (正常)"
        return 0
    fi
}

# 3. 磁盘使用率
check_disk() {
    DISK_USAGE=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -ge "$DISK_CRITICAL" ]; then
        log_error "磁盘使用率过高: ${DISK_USAGE}% (临界值: ${DISK_CRITICAL}%)"
        return 2
    elif [ "$DISK_USAGE" -ge "$DISK_WARNING" ]; then
        log_warning "磁盘使用率较高: ${DISK_USAGE}% (警告值: ${DISK_WARNING}%)"
        return 1
    else
        log "磁盘使用率: ${DISK_USAGE}% (正常)"
        return 0
    fi
}

# 4. GPU 使用率和温度（Jetson设备）
check_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        # NVIDIA GPU
        GPU_USAGE=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d ' ' || echo "N/A")
        GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d ' ' || echo "N/A")
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d ' ' || echo "N/A")
        GPU_MEMORY_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d ' ' || echo "N/A")
        
        log "GPU 使用率: ${GPU_USAGE}%, 温度: ${GPU_TEMP}°C, 显存: ${GPU_MEMORY}MB/${GPU_MEMORY_TOTAL}MB"
        
        # 检查温度（只有当温度是数字时才检查）
        if [ "$GPU_TEMP" != "N/A" ] && [ -n "$GPU_TEMP" ] && [ "$GPU_TEMP" -eq "$GPU_TEMP" ] 2>/dev/null; then
            if [ "$GPU_TEMP" -ge "$GPU_TEMP_CRITICAL" ]; then
                log_error "GPU 温度过高: ${GPU_TEMP}°C (临界值: ${GPU_TEMP_CRITICAL}°C)"
                return 2
            elif [ "$GPU_TEMP" -ge "$GPU_TEMP_WARNING" ]; then
                log_warning "GPU 温度较高: ${GPU_TEMP}°C (警告值: ${GPU_TEMP_WARNING}°C)"
                return 1
            fi
        fi
    elif [ -f /sys/devices/soc0/family ]; then
        # Jetson设备 - 使用tegrastats
        if command -v tegrastats &> /dev/null; then
            TEGRA_STATS=$(timeout 1 tegrastats 2>/dev/null | tail -n 1)
            if [ -n "$TEGRA_STATS" ]; then
                log "Jetson 状态: $TEGRA_STATS"
            fi
        fi
    fi
    
    return 0
}

# 5. 主程序进程状态
check_main_process() {
    MAIN_PID=$(pgrep -f "test_system_realtime.py" || echo "")
    
    if [ -z "$MAIN_PID" ]; then
        log_error "主程序进程未运行"
        return 2
    else
        # 检查进程是否响应
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            # 获取进程资源使用
            PROCESS_STATS=$(ps -p "$MAIN_PID" -o %cpu,%mem,rss --no-headers 2>/dev/null || echo "0 0 0")
            CPU_PROC=$(echo "$PROCESS_STATS" | awk '{print $1}')
            MEM_PROC=$(echo "$PROCESS_STATS" | awk '{print $2}')
            RSS_PROC=$(echo "$PROCESS_STATS" | awk '{print $3}')
            
            log "主程序进程 (PID: $MAIN_PID) - CPU: ${CPU_PROC}%, 内存: ${MEM_PROC}% (${RSS_PROC}KB)"
            return 0
        else
            log_error "主程序进程 (PID: $MAIN_PID) 无响应"
            return 2
        fi
    fi
}

# 主函数
main() {
    log "=========================================="
    log "资源监控检查"
    log "=========================================="
    
    ERRORS=0
    WARNINGS=0
    
    # 执行各项检查
    check_cpu
    STATUS=$?
    [ $STATUS -eq 2 ] && ERRORS=$((ERRORS + 1))
    [ $STATUS -eq 1 ] && WARNINGS=$((WARNINGS + 1))
    
    check_memory
    STATUS=$?
    [ $STATUS -eq 2 ] && ERRORS=$((ERRORS + 1))
    [ $STATUS -eq 1 ] && WARNINGS=$((WARNINGS + 1))
    
    check_disk
    STATUS=$?
    [ $STATUS -eq 2 ] && ERRORS=$((ERRORS + 1))
    [ $STATUS -eq 1 ] && WARNINGS=$((WARNINGS + 1))
    
    check_gpu
    STATUS=$?
    [ $STATUS -eq 2 ] && ERRORS=$((ERRORS + 1))
    [ $STATUS -eq 1 ] && WARNINGS=$((WARNINGS + 1))
    
    check_main_process
    STATUS=$?
    [ $STATUS -eq 2 ] && ERRORS=$((ERRORS + 1))
    [ $STATUS -eq 1 ] && WARNINGS=$((WARNINGS + 1))
    
    log "=========================================="
    log "检查完成 - 错误: $ERRORS, 警告: $WARNINGS"
    log "=========================================="
    
    # 返回状态码
    if [ $ERRORS -gt 0 ]; then
        exit 2
    elif [ $WARNINGS -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# 如果直接运行脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

