#!/bin/bash
# P0 功能测试脚本
# 测试所有已创建的脚本和功能

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

# 测试结果
PASSED=0
FAILED=0
WARNINGS=0

# 测试函数
test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASSED=$((PASSED + 1))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED=$((FAILED + 1))
}

test_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    WARNINGS=$((WARNINGS + 1))
}

test_info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

echo "=========================================="
echo "P0 功能测试"
echo "=========================================="
echo "项目目录: $PROJECT_ROOT"
echo ""

# 1. 测试脚本文件存在性
echo "1. 检查脚本文件..."
SCRIPTS=(
    "check_hardware.sh"
    "check_network.sh"
    "start_vehicle_detection.sh"
    "stop_vehicle_detection.sh"
    "setup_auto_start.sh"
    "fix_system_time.sh"
    "watchdog.sh"
    "monitor_resources.sh"
    "system_status.sh"
    "setup_logrotate.sh"
    "logrotate_vehicle_detection"
    "vehicle-detection.service"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        test_pass "脚本文件存在: $script"
        if [ -x "$SCRIPT_DIR/$script" ] || [[ "$script" == *.service ]] || [[ "$script" == logrotate_* ]]; then
            test_pass "脚本可执行或为配置文件: $script"
        else
            test_warn "脚本不可执行: $script"
        fi
    else
        test_fail "脚本文件不存在: $script"
    fi
done

echo ""

# 2. 测试硬件检查脚本
echo "2. 测试硬件检查脚本..."
if "$SCRIPT_DIR/check_hardware.sh" > /tmp/hardware_check.log 2>&1; then
    test_pass "硬件检查脚本执行成功"
    if grep -q "硬件检查全部通过" /tmp/hardware_check.log; then
        test_pass "硬件检查全部通过"
    elif grep -q "硬件检查通过，但有警告" /tmp/hardware_check.log; then
        test_warn "硬件检查有警告（这是正常的）"
    else
        test_fail "硬件检查失败"
        echo "  详细日志:"
        tail -n 10 /tmp/hardware_check.log | sed 's/^/    /'
    fi
else
    EXIT_CODE=$?
    test_fail "硬件检查脚本执行失败 (退出码: $EXIT_CODE)"
    echo "  详细日志:"
    tail -n 10 /tmp/hardware_check.log | sed 's/^/    /'
fi

echo ""

# 3. 测试网络检查脚本
echo "3. 测试网络检查脚本..."
if "$SCRIPT_DIR/check_network.sh" > /tmp/network_check.log 2>&1; then
    test_pass "网络检查脚本执行成功"
    if grep -q "网络检查全部通过" /tmp/network_check.log; then
        test_pass "网络检查全部通过"
    elif grep -q "网络检查通过，但有警告" /tmp/network_check.log; then
        test_warn "网络检查有警告（这是正常的，如果设备未联网）"
    else
        test_fail "网络检查失败"
        echo "  详细日志:"
        tail -n 10 /tmp/network_check.log | sed 's/^/    /'
    fi
else
    EXIT_CODE=$?
    test_warn "网络检查脚本执行失败 (退出码: $EXIT_CODE) - 可能是网络问题"
    echo "  详细日志:"
    tail -n 10 /tmp/network_check.log | sed 's/^/    /'
fi

echo ""

# 4. 测试系统状态脚本
echo "4. 测试系统状态脚本..."
if "$SCRIPT_DIR/system_status.sh" > /tmp/system_status.log 2>&1; then
    test_pass "系统状态脚本执行成功"
    if [ -s /tmp/system_status.log ]; then
        test_pass "系统状态输出正常"
        echo "  输出预览:"
        head -n 10 /tmp/system_status.log | sed 's/^/    /'
    else
        test_fail "系统状态输出为空"
    fi
else
    test_fail "系统状态脚本执行失败"
fi

# 测试 JSON 格式
if "$SCRIPT_DIR/system_status.sh" json > /tmp/system_status.json 2>&1; then
    if python3 -m json.tool /tmp/system_status.json > /dev/null 2>&1; then
        test_pass "系统状态 JSON 格式有效"
    else
        test_warn "系统状态 JSON 格式可能无效"
    fi
fi

echo ""

# 5. 测试资源监控脚本
echo "5. 测试资源监控脚本..."
if "$SCRIPT_DIR/monitor_resources.sh" > /tmp/resource_monitor.log 2>&1; then
    EXIT_CODE=$?
    test_pass "资源监控脚本执行成功"
    if [ $EXIT_CODE -eq 0 ]; then
        test_pass "资源监控检查全部通过"
    elif [ $EXIT_CODE -eq 1 ]; then
        test_warn "资源监控有警告（这是正常的）"
    else
        test_fail "资源监控检查失败"
    fi
    echo "  输出预览:"
    tail -n 15 /tmp/resource_monitor.log | sed 's/^/    /'
else
    test_fail "资源监控脚本执行失败"
fi

echo ""

# 6. 测试看门狗脚本
echo "6. 测试看门狗脚本..."
# 测试 status 命令
if "$SCRIPT_DIR/watchdog.sh" status > /tmp/watchdog_status.log 2>&1; then
    test_pass "看门狗 status 命令执行成功"
    cat /tmp/watchdog_status.log | sed 's/^/    /'
else
    test_warn "看门狗未运行（这是正常的，如果未启动）"
fi

# 测试 stop 命令（如果正在运行）
if [ -f "$PROJECT_ROOT/logs/watchdog.pid" ]; then
    OLD_PID=$(cat "$PROJECT_ROOT/logs/watchdog.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        test_info "看门狗正在运行 (PID: $OLD_PID)，测试停止..."
        if "$SCRIPT_DIR/watchdog.sh" stop > /tmp/watchdog_stop.log 2>&1; then
            test_pass "看门狗停止成功"
        else
            test_fail "看门狗停止失败"
        fi
    fi
fi

echo ""

# 7. 测试 systemd 服务
echo "7. 测试 systemd 服务..."
if systemctl list-unit-files | grep -q "vehicle-detection.service"; then
    test_pass "systemd 服务文件已安装"
    
    # 检查服务状态
    if systemctl is-active --quiet vehicle-detection.service 2>/dev/null; then
        test_pass "systemd 服务正在运行"
    elif systemctl is-enabled --quiet vehicle-detection.service 2>/dev/null; then
        test_pass "systemd 服务已启用（开机自启动）"
        test_info "服务当前未运行（这是正常的）"
    else
        test_warn "systemd 服务未启用"
    fi
    
    # 检查服务配置
    if systemctl cat vehicle-detection.service > /dev/null 2>&1; then
        test_pass "systemd 服务配置可读取"
    else
        test_fail "systemd 服务配置无法读取"
    fi
else
    test_warn "systemd 服务文件未安装（需要运行 setup_auto_start.sh）"
fi

echo ""

# 8. 测试日志轮转配置
echo "8. 测试日志轮转配置..."
if [ -f "/etc/logrotate.d/vehicle-detection" ]; then
    test_pass "日志轮转配置已安装"
    if logrotate -d /etc/logrotate.d/vehicle-detection > /tmp/logrotate_test.log 2>&1; then
        test_pass "日志轮转配置有效"
    else
        test_warn "日志轮转配置测试失败"
        tail -n 5 /tmp/logrotate_test.log | sed 's/^/    /'
    fi
else
    test_warn "日志轮转配置未安装（需要运行 setup_logrotate.sh）"
fi

echo ""

# 9. 测试日志目录
echo "9. 测试日志目录..."
LOG_DIRS=(
    "$PROJECT_ROOT/logs"
    "$(dirname "$(grep 'log_file:' "$PROJECT_ROOT/config.yaml" | awk '{print $2}' | tr -d '"')")"
)

for log_dir in "${LOG_DIRS[@]}"; do
    if [ -d "$log_dir" ]; then
        test_pass "日志目录存在: $log_dir"
        if [ -w "$log_dir" ]; then
            test_pass "日志目录可写: $log_dir"
        else
            test_warn "日志目录不可写: $log_dir"
        fi
    else
        test_warn "日志目录不存在: $log_dir（将在运行时创建）"
    fi
done

echo ""

# 10. 测试配置文件
echo "10. 测试配置文件..."
if [ -f "$PROJECT_ROOT/config.yaml" ]; then
    test_pass "配置文件存在"
    if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/config.yaml'))" 2>/dev/null; then
        test_pass "配置文件格式有效"
    else
        test_fail "配置文件格式无效"
    fi
else
    test_fail "配置文件不存在"
fi

echo ""

# 总结
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${YELLOW}警告: $WARNINGS${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}所有测试通过！${NC}"
        exit 0
    else
        echo -e "${YELLOW}测试通过，但有警告（请检查）${NC}"
        exit 0
    fi
else
    echo -e "${RED}部分测试失败，请检查上述错误${NC}"
    exit 1
fi

