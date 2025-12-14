#!/bin/bash
# Phase 1 回滚脚本
# 用于回滚Phase 1的修改

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Phase 1 回滚脚本"
echo "=========================================="
echo ""

# 查找最新的备份
BACKUP_BASE="$PROJECT_ROOT/backups"
if [ ! -d "$BACKUP_BASE" ]; then
    echo "❌ 备份目录不存在: $BACKUP_BASE"
    exit 1
fi

LATEST_BACKUP=$(ls -td "$BACKUP_BASE"/phase1_* 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 未找到Phase 1备份"
    exit 1
fi

echo "找到最新备份: $LATEST_BACKUP"
echo ""

# 检查系统是否在运行
if pgrep -f "test_system_realtime" > /dev/null; then
    echo "⚠️  检测到系统正在运行！"
    read -p "   是否现在停止系统以进行回滚? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   正在停止系统..."
        pkill -f "test_system_realtime" || true
        sleep 2
        echo "   ✅ 系统已停止"
    else
        echo "   ❌ 回滚已取消"
        exit 1
    fi
fi
echo ""

# 确认回滚
echo "⚠️  警告：这将恢复以下文件："
echo "   - config.yaml"
echo "   - test_system_realtime.py"
echo ""
read -p "确认回滚? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "回滚已取消"
    exit 0
fi
echo ""

# 恢复文件
echo "【步骤1】恢复配置文件..."
if [ -f "$LATEST_BACKUP/config.yaml.backup" ]; then
    cp "$LATEST_BACKUP/config.yaml.backup" "$PROJECT_ROOT/config.yaml"
    echo "   ✅ 已恢复: config.yaml"
else
    echo "   ⚠️  备份文件不存在: config.yaml.backup"
fi

echo "【步骤2】恢复主程序文件..."
if [ -f "$LATEST_BACKUP/test_system_realtime.py.backup" ]; then
    cp "$LATEST_BACKUP/test_system_realtime.py.backup" "$PROJECT_ROOT/test_system_realtime.py"
    echo "   ✅ 已恢复: test_system_realtime.py"
else
    echo "   ⚠️  备份文件不存在: test_system_realtime.py.backup"
fi

echo ""
echo "=========================================="
echo "✅ 回滚完成！"
echo "=========================================="
echo ""
echo "注意: beacon_match_tracker.py 仍保留在原位置"
echo "如果不再需要，可以手动删除:"
echo "  rm $PROJECT_ROOT/python_apps/beacon_match_tracker.py"
echo ""
echo "现在可以重启系统。"
echo ""

