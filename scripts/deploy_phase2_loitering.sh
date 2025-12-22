#!/bin/bash
#
# Phase 2 徘徊检测模块部署脚本
# 安全部署：备份、验证、测试
#

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Phase 2 徘徊检测模块部署"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "test_system_realtime.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 创建备份目录
BACKUP_DIR="backups/phase2_loitering_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "📦 备份目录: $BACKUP_DIR"

# 备份文件
echo ""
echo "📦 备份文件..."
files_to_backup=(
    "config.yaml"
    "test_system_realtime.py"
    "python_apps/loitering_detector.py"
)

for file in "${files_to_backup[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "  ✓ $file"
    else
        echo "  ⚠️  $file 不存在，跳过备份"
    fi
done

# 验证文件存在
echo ""
echo "🔍 验证文件..."
required_files=(
    "python_apps/loitering_detector.py"
    "tests/test_phase2_loitering.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ❌ $file 不存在"
        exit 1
    fi
done

# 运行测试
echo ""
echo "🧪 运行测试..."
if python3 tests/test_phase2_loitering.py; then
    echo "  ✅ 测试通过"
else
    echo "  ❌ 测试失败，部署中止"
    exit 1
fi

# 验证配置文件语法
echo ""
echo "🔍 验证配置文件..."
if python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo "  ✅ config.yaml 语法正确"
else
    echo "  ❌ config.yaml 语法错误"
    exit 1
fi

# 验证Python模块导入
echo ""
echo "🔍 验证Python模块..."
if python3 -c "
import sys
sys.path.insert(0, 'python_apps')
from loitering_detector import LoiteringDetector
from config_loader import get_config
config = get_config()
alert_cfg = config.get('alert', {}).get('loitering', {})
print('  ✅ 模块导入成功')
print(f'    启用: {alert_cfg.get(\"enabled\", True)}')
print(f'    最少停留时间: {alert_cfg.get(\"min_duration\", 10.0)}s')
" 2>&1; then
    echo "  ✅ Python模块验证通过"
else
    echo "  ❌ Python模块验证失败"
    exit 1
fi

# 验证语法
echo ""
echo "🔍 验证Python语法..."
if python3 -m py_compile test_system_realtime.py python_apps/loitering_detector.py 2>&1; then
    echo "  ✅ Python语法正确"
else
    echo "  ❌ Python语法错误"
    exit 1
fi

# 生成部署摘要
echo ""
echo "=========================================="
echo "部署摘要"
echo "=========================================="
echo ""
echo "✅ 备份完成: $BACKUP_DIR"
echo "✅ 测试通过"
echo "✅ 配置文件验证通过"
echo "✅ Python模块验证通过"
echo "✅ 语法检查通过"
echo ""
echo "📝 部署的文件:"
for file in "${files_to_backup[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done
echo ""
echo "🎯 功能:"
echo "  - 徘徊检测器 (LoiteringDetector)"
echo "  - 只对未备案车辆应用徘徊判定"
echo "  - 已备案车辆立即报警"
echo "  - 检测停留时间、画面占比、移动距离"
echo ""
echo "📋 配置参数 (config.yaml):"
python3 -c "
import sys
sys.path.insert(0, 'python_apps')
from config_loader import get_config
config = get_config()
alert_cfg = config.get('alert', {}).get('loitering', {})
print(f\"  - 启用: {alert_cfg.get('enabled', True)}\")
print(f\"  - 最少停留时间: {alert_cfg.get('min_duration', 10.0)}s\")
print(f\"  - 最小画面占比: {alert_cfg.get('min_area_ratio', 0.05)}\")
print(f\"  - 最小移动比例: {alert_cfg.get('min_movement_ratio', 0.1)}\")
print(f\"  - 只对未备案车辆应用: {alert_cfg.get('apply_to_unregistered_only', True)}\")
" 2>&1
echo ""
echo "✅ 部署准备完成！"
echo ""
echo "下一步:"
echo "  1. 停止当前运行的系统"
echo "  2. 重启系统以应用新功能"
echo "  3. 观察日志确认徘徊检测器初始化成功"
echo ""








