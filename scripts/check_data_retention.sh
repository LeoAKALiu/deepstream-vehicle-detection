#!/bin/bash
# 检查数据留存状态脚本

cd "$(dirname "$0")/.." || exit 1

echo "=== 数据留存状态检查 ==="
echo ""

# 检查数据库
if [ -f "detection_results.db" ]; then
    echo "📊 检测结果数据库:"
    echo "  文件大小: $(ls -lh detection_results.db | awk '{print $5}')"
    echo "  记录数: $(sqlite3 detection_results.db "SELECT COUNT(*) FROM detections;" 2>/dev/null || echo "0")"
    echo "  最近记录: $(sqlite3 detection_results.db "SELECT COUNT(*) FROM detections WHERE timestamp > datetime('now', '-1 day');" 2>/dev/null || echo "0") 条（24小时内）"
else
    echo "📊 检测结果数据库: 不存在"
fi

echo ""

# 检查快照
if [ -d "/tmp/vehicle_snapshots" ]; then
    SNAPSHOT_COUNT=$(find /tmp/vehicle_snapshots -name "snapshot_*.jpg" ! -name "monitoring_snapshot_*" 2>/dev/null | wc -l)
    SNAPSHOT_SIZE=$(du -sh /tmp/vehicle_snapshots 2>/dev/null | awk '{print $1}')
    echo "📸 车辆快照:"
    echo "  数量: $SNAPSHOT_COUNT 张"
    echo "  总大小: $SNAPSHOT_SIZE"
    echo "  最近24小时: $(find /tmp/vehicle_snapshots -name "snapshot_*.jpg" ! -name "monitoring_snapshot_*" -mtime -1 2>/dev/null | wc -l) 张"
else
    echo "📸 车辆快照: 目录不存在"
fi

echo ""

# 检查监控截图
if [ -d "/tmp/vehicle_snapshots" ]; then
    MONITORING_COUNT=$(find /tmp/vehicle_snapshots -name "monitoring_snapshot_*.jpg" 2>/dev/null | wc -l)
    MONITORING_SIZE=$(find /tmp/vehicle_snapshots -name "monitoring_snapshot_*.jpg" -exec du -ch {} + 2>/dev/null | tail -1 | awk '{print $1}')
    echo "📷 监控截图:"
    echo "  数量: $MONITORING_COUNT 张"
    echo "  总大小: ${MONITORING_SIZE:-0}"
    echo "  最近24小时: $(find /tmp/vehicle_snapshots -name "monitoring_snapshot_*.jpg" -mtime -1 2>/dev/null | wc -l) 张"
else
    echo "📷 监控截图: 目录不存在"
fi

echo ""

# 检查配置
if [ -f "config.yaml" ]; then
    echo "⚙️ 数据留存配置:"
    if grep -q "data_retention:" config.yaml; then
        echo "  ✅ 已配置数据留存策略"
        echo "  数据库最大记录数: $(grep -A 2 "database:" config.yaml | grep "max_records" | awk '{print $2}' || echo "未设置")"
        echo "  快照最大数量: $(grep -A 2 "snapshots:" config.yaml | grep "max_count" | awk '{print $2}' || echo "未设置")"
        echo "  快照最大大小: $(grep -A 2 "snapshots:" config.yaml | grep "max_size_mb" | awk '{print $2}' || echo "未设置")MB"
    else
        echo "  ⚠️ 未配置数据留存策略（将使用默认值）"
    fi
else
    echo "⚙️ 配置文件: 不存在"
fi

echo ""
echo "=== 检查完成 ==="


