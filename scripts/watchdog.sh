#!/bin/bash
# 看门狗脚本
# 监控主程序进程，检测崩溃或卡死，自动重启

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

# 配置
CHECK_INTERVAL=30          # 检查间隔（秒）
MAX_RESTART_COUNT=5        # 最大重启次数（0表示无限）
RESTART_WINDOW=300         # 重启窗口（秒）
LOG_FILE="${PROJECT_ROOT}/logs/watchdog.log"
PID_FILE="${PROJECT_ROOT}/logs/watchdog.pid"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# 检查主程序是否运行
check_main_process() {
    MAIN_PID=$(pgrep -f "test_system_realtime.py" || echo "")
    
    if [ -z "$MAIN_PID" ]; then
        return 1  # 进程不存在
    fi
    
    # 检查进程是否响应
    if ! kill -0 "$MAIN_PID" 2>/dev/null; then
        return 1  # 进程无响应
    fi
    
    return 0  # 进程正常
}

# 检查主程序是否卡死（通过检查日志文件更新时间）
check_process_hung() {
    MAIN_PID=$(pgrep -f "test_system_realtime.py" || echo "")
    if [ -z "$MAIN_PID" ]; then
        return 1
    fi
    
    # 检查日志文件最后更新时间
    LOG_FILE_MAIN="${PROJECT_ROOT}/logs/startup.log"
    if [ -f "$LOG_FILE_MAIN" ]; then
        LAST_MODIFIED=$(stat -c %Y "$LOG_FILE_MAIN" 2>/dev/null || echo "0")
        CURRENT_TIME=$(date +%s)
        TIME_DIFF=$((CURRENT_TIME - LAST_MODIFIED))
        
        # 如果日志超过5分钟未更新，认为程序可能卡死
        if [ $TIME_DIFF -gt 300 ]; then
            log_warning "主程序可能卡死（日志超过5分钟未更新）"
            return 1
        fi
    fi
    
    return 0
}

# 重启主程序
restart_main_process() {
    log_info "尝试重启主程序..."
    
    # 停止现有进程
    if [ -n "$MAIN_PID" ]; then
        log_info "停止现有进程 (PID: $MAIN_PID)..."
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        sleep 5
        
        # 如果还在运行，强制终止
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            log_warning "进程未响应，强制终止..."
            kill -KILL "$MAIN_PID" 2>/dev/null || true
            sleep 2
        fi
    fi
    
    # 启动新进程（通过systemd服务）
    if systemctl is-active --quiet vehicle-detection.service; then
        log_info "通过 systemd 重启服务..."
        systemctl restart vehicle-detection.service
    else
        log_info "直接启动主程序..."
        "$SCRIPT_DIR/start_vehicle_detection.sh" > /dev/null 2>&1 &
    fi
    
    sleep 5
    
    # 检查是否启动成功
    if check_main_process; then
        log_info "主程序重启成功"
        return 0
    else
        log_error "主程序重启失败"
        return 1
    fi
}

# 主循环
main_loop() {
    RESTART_COUNT=0
    LAST_RESTART_TIME=0
    
    log_info "看门狗启动，检查间隔: ${CHECK_INTERVAL}秒"
    
    while true; do
        sleep "$CHECK_INTERVAL"
        
        # 检查主程序进程
        if ! check_main_process; then
            log_error "主程序进程不存在或无响应"
            
            # 检查重启限制
            CURRENT_TIME=$(date +%s)
            if [ $RESTART_COUNT -ge $MAX_RESTART_COUNT ] && [ $MAX_RESTART_COUNT -gt 0 ]; then
                TIME_SINCE_LAST_RESTART=$((CURRENT_TIME - LAST_RESTART_TIME))
                if [ $TIME_SINCE_LAST_RESTART -lt $RESTART_WINDOW ]; then
                    log_error "达到最大重启次数限制，停止重启"
                    log_error "请检查系统日志并手动修复问题"
                    exit 1
                else
                    # 重置计数（超过重启窗口）
                    RESTART_COUNT=0
                fi
            fi
            
            # 尝试重启
            if restart_main_process; then
                RESTART_COUNT=$((RESTART_COUNT + 1))
                LAST_RESTART_TIME=$(date +%s)
                log_info "重启计数: $RESTART_COUNT"
            else
                log_error "重启失败，将在下次检查时重试"
            fi
        elif ! check_process_hung; then
            log_warning "主程序可能卡死，尝试重启..."
            restart_main_process
        else
            # 进程正常，重置重启计数
            if [ $RESTART_COUNT -gt 0 ]; then
                TIME_SINCE_LAST_RESTART=$(($(date +%s) - LAST_RESTART_TIME))
                if [ $TIME_SINCE_LAST_RESTART -gt $RESTART_WINDOW ]; then
                    log_info "主程序已稳定运行，重置重启计数"
                    RESTART_COUNT=0
                fi
            fi
        fi
    done
}

# 启动看门狗
start() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log_warning "看门狗已在运行 (PID: $OLD_PID)"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    log_info "启动看门狗..."
    main_loop &
    WATCHDOG_PID=$!
    echo $WATCHDOG_PID > "$PID_FILE"
    log_info "看门狗已启动 (PID: $WATCHDOG_PID)"
}

# 停止看门狗
stop() {
    if [ -f "$PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$PID_FILE")
        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            log_info "停止看门狗 (PID: $WATCHDOG_PID)..."
            kill "$WATCHDOG_PID" 2>/dev/null || true
            rm -f "$PID_FILE"
            log_info "看门狗已停止"
        else
            log_warning "看门狗进程不存在"
            rm -f "$PID_FILE"
        fi
    else
        log_warning "看门狗未运行"
    fi
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            sleep 2
            start
            ;;
        status)
            if [ -f "$PID_FILE" ]; then
                WATCHDOG_PID=$(cat "$PID_FILE")
                if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
                    echo "看门狗正在运行 (PID: $WATCHDOG_PID)"
                    if check_main_process; then
                        echo "主程序状态: 运行中"
                    else
                        echo "主程序状态: 未运行"
                    fi
                else
                    echo "看门狗未运行"
                fi
            else
                echo "看门狗未运行"
            fi
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# 如果直接运行脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

