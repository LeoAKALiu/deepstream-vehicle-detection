#!/bin/bash
# 系统状态监控脚本
# 提供系统运行状态、服务状态、硬件状态等信息

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

# 输出格式（json 或 text）
OUTPUT_FORMAT="${1:-text}"

print_status() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "$1"
    else
        echo -e "$1"
    fi
}

# JSON 输出函数
json_start() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "{"
    fi
}

json_end() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "}"
    fi
}

json_field() {
    local key="$1"
    local value="$2"
    local comma="$3"
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        if [ "$comma" = "true" ]; then
            echo "  \"$key\": \"$value\","
        else
            echo "  \"$key\": \"$value\""
        fi
    else
        print_status "${BLUE}$key:${NC} $value"
    fi
}

# 1. 系统信息
get_system_info() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "  \"system\": {"
        echo "    \"hostname\": \"$(hostname)\","
        echo "    \"uptime\": \"$(uptime -p | sed 's/up //')\","
        echo "    \"load_average\": \"$(uptime | awk -F'load average:' '{print $2}' | xargs)\","
        echo "    \"kernel\": \"$(uname -r)\","
        echo "    \"os\": \"$(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')\""
        echo "  },"
    else
        print_status "${GREEN}=== 系统信息 ===${NC}"
        print_status "主机名: $(hostname)"
        print_status "运行时间: $(uptime -p | sed 's/up //')"
        print_status "负载: $(uptime | awk -F'load average:' '{print $2}' | xargs)"
        print_status "内核: $(uname -r)"
        print_status "操作系统: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
        echo ""
    fi
}

# 2. 服务状态
get_service_status() {
    if systemctl is-active --quiet vehicle-detection.service; then
        SERVICE_STATUS="running"
        SERVICE_COLOR="${GREEN}"
    else
        SERVICE_STATUS="stopped"
        SERVICE_COLOR="${RED}"
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "  \"service\": {"
        echo "    \"status\": \"$SERVICE_STATUS\","
        echo "    \"enabled\": \"$(systemctl is-enabled vehicle-detection.service 2>/dev/null || echo 'unknown')\""
        echo "  },"
    else
        print_status "${GREEN}=== 服务状态 ===${NC}"
        print_status "${SERVICE_COLOR}车辆检测服务: $SERVICE_STATUS${NC}"
        print_status "开机自启: $(systemctl is-enabled vehicle-detection.service 2>/dev/null || echo 'unknown')"
        echo ""
    fi
}

# 3. 主程序进程状态
get_process_status() {
    MAIN_PID=$(pgrep -f "test_system_realtime.py" || echo "")
    
    if [ -n "$MAIN_PID" ]; then
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            PROCESS_STATUS="running"
            PROCESS_COLOR="${GREEN}"
            PROCESS_INFO=$(ps -p "$MAIN_PID" -o pid,user,%cpu,%mem,rss,etime,cmd --no-headers 2>/dev/null || echo "")
        else
            PROCESS_STATUS="zombie"
            PROCESS_COLOR="${RED}"
            PROCESS_INFO=""
        fi
    else
        PROCESS_STATUS="not_running"
        PROCESS_COLOR="${RED}"
        PROCESS_INFO=""
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "  \"process\": {"
        echo "    \"status\": \"$PROCESS_STATUS\","
        echo "    \"pid\": \"$MAIN_PID\""
        echo "  },"
    else
        print_status "${GREEN}=== 进程状态 ===${NC}"
        print_status "${PROCESS_COLOR}主程序: $PROCESS_STATUS${NC}"
        if [ -n "$MAIN_PID" ]; then
            print_status "PID: $MAIN_PID"
            if [ -n "$PROCESS_INFO" ]; then
                print_status "详情: $PROCESS_INFO"
            fi
        fi
        echo ""
    fi
}

# 4. 硬件状态
get_hardware_status() {
    # CPU
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    CPU_USAGE=${CPU_USAGE%.*}
    
    # 内存
    MEMORY_TOTAL=$(free -m | awk 'NR==2{print $2}')
    MEMORY_USED=$(free -m | awk 'NR==2{print $3}')
    MEMORY_PERCENT=$((MEMORY_USED * 100 / MEMORY_TOTAL))
    
    # 磁盘
    DISK_USAGE=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
    DISK_AVAILABLE=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    
    # GPU
    GPU_INFO=""
    if command -v nvidia-smi &> /dev/null; then
        GPU_USAGE=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -n 1)
        GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | head -n 1)
        GPU_INFO="GPU: ${GPU_USAGE}%, 温度: ${GPU_TEMP}°C"
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "  \"hardware\": {"
        echo "    \"cpu_usage\": \"$CPU_USAGE%\","
        echo "    \"memory_usage\": \"$MEMORY_PERCENT%\","
        echo "    \"memory_used_mb\": \"$MEMORY_USED\","
        echo "    \"memory_total_mb\": \"$MEMORY_TOTAL\","
        echo "    \"disk_usage\": \"$DISK_USAGE%\","
        echo "    \"disk_available\": \"$DISK_AVAILABLE\""
        if [ -n "$GPU_INFO" ]; then
            echo "    ,\"gpu_usage\": \"$GPU_USAGE%\","
            echo "    \"gpu_temp\": \"${GPU_TEMP}°C\""
        fi
        echo "  },"
    else
        print_status "${GREEN}=== 硬件状态 ===${NC}"
        print_status "CPU 使用率: ${CPU_USAGE}%"
        print_status "内存使用率: ${MEMORY_PERCENT}% (${MEMORY_USED}MB/${MEMORY_TOTAL}MB)"
        print_status "磁盘使用率: ${DISK_USAGE}% (可用: ${DISK_AVAILABLE})"
        if [ -n "$GPU_INFO" ]; then
            print_status "$GPU_INFO"
        fi
        echo ""
    fi
}

# 5. 网络状态
get_network_status() {
    CASSIA_IP=$(grep -A 1 "network:" "$PROJECT_ROOT/config.yaml" | grep "cassia_ip:" | awk '{print $2}' | tr -d '"' || echo "192.168.1.2")
    
    if ping -c 1 -W 2 "$CASSIA_IP" > /dev/null 2>&1; then
        CASSIA_STATUS="connected"
        CASSIA_COLOR="${GREEN}"
    else
        CASSIA_STATUS="disconnected"
        CASSIA_COLOR="${RED}"
    fi
    
    if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        INTERNET_STATUS="connected"
        INTERNET_COLOR="${GREEN}"
    else
        INTERNET_STATUS="disconnected"
        INTERNET_COLOR="${YELLOW}"
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "  \"network\": {"
        echo "    \"cassia_status\": \"$CASSIA_STATUS\","
        echo "    \"cassia_ip\": \"$CASSIA_IP\","
        echo "    \"internet_status\": \"$INTERNET_STATUS\""
        echo "  },"
    else
        print_status "${GREEN}=== 网络状态 ===${NC}"
        print_status "${CASSIA_COLOR}Cassia路由器: $CASSIA_STATUS ($CASSIA_IP)${NC}"
        print_status "${INTERNET_COLOR}互联网: $INTERNET_STATUS${NC}"
        echo ""
    fi
}

# 6. 最近日志
get_recent_logs() {
    LOG_FILE="${PROJECT_ROOT}/logs/startup.log"
    if [ -f "$LOG_FILE" ]; then
        LOG_LINES=$(tail -n 5 "$LOG_FILE" 2>/dev/null || echo "")
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo "  \"recent_logs\": ["
            echo "$LOG_LINES" | while IFS= read -r line; do
                echo "    \"$line\","
            done | sed '$ s/,$//'
            echo "  ]"
        else
            print_status "${GREEN}=== 最近日志 ===${NC}"
            echo "$LOG_LINES"
        fi
    fi
}

# 主函数
main() {
    json_start
    
    get_system_info
    get_service_status
    get_process_status
    get_hardware_status
    get_network_status
    get_recent_logs
    
    json_end
}

main

