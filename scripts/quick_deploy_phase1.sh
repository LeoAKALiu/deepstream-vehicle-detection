#!/bin/bash
# Phase 1 快速部署脚本（适用于已验证环境）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Phase 1 快速部署"
echo "=========================================="
echo ""

# 检查系统是否在运行
if pgrep -f "test_system_realtime" > /dev/null; then
    echo "⚠️  系统正在运行中..."
    echo ""
    echo "当前运行的进程:"
    ps aux | grep test_system_realtime | grep -v grep
    echo ""
    echo "请先停止系统，然后重新运行此脚本。"
    echo "停止命令: pkill -f test_system_realtime"
    exit 1
fi

# 快速验证
echo "【验证】检查文件..."
if [ ! -f "$PROJECT_ROOT/python_apps/beacon_match_tracker.py" ]; then
    echo "❌ 缺少必要文件: beacon_match_tracker.py"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/config.yaml" ]; then
    echo "❌ 缺少配置文件: config.yaml"
    exit 1
fi

echo "✅ 所有文件存在"
echo ""

# 运行测试
echo "【验证】运行测试..."
cd "$PROJECT_ROOT"
if python3 tests/test_phase1_optimizations.py > /tmp/phase1_test.log 2>&1; then
    echo "✅ 所有测试通过"
else
    echo "❌ 测试失败，查看日志: /tmp/phase1_test.log"
    cat /tmp/phase1_test.log | tail -30
    exit 1
fi
echo ""

# 创建备份（快速模式）
BACKUP_DIR="$PROJECT_ROOT/backups/phase1_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp "$PROJECT_ROOT/config.yaml" "$BACKUP_DIR/config.yaml.backup" 2>/dev/null || true
cp "$PROJECT_ROOT/test_system_realtime.py" "$BACKUP_DIR/test_system_realtime.py.backup" 2>/dev/null || true
echo "✅ 备份已创建: $BACKUP_DIR"
echo ""

echo "=========================================="
echo "✅ Phase 1 验证完成！"
echo "=========================================="
echo ""
echo "系统已准备好部署Phase 1。"
echo ""
echo "下一步："
echo "1. 检查系统状态（当前未运行）"
echo "2. 启动系统进行测试："
echo "   python3 test_system_realtime.py --no-display"
echo ""
echo "如需回滚，使用: ./scripts/rollback_phase1.sh"
echo ""

