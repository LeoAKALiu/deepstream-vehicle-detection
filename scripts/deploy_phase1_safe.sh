#!/bin/bash
# Phase 1 安全部署脚本
# 用于在生产环境安全部署Phase 1优化

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups/phase1_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "Phase 1 安全部署脚本"
echo "=========================================="
echo ""

# 1. 检查系统是否正在运行
echo "【步骤1】检查系统状态..."
if pgrep -f "test_system_realtime" > /dev/null; then
    echo "⚠️  检测到系统正在运行！"
    echo "   为了安全部署，需要先停止系统。"
    read -p "   是否现在停止系统? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   正在停止系统..."
        pkill -f "test_system_realtime" || true
        sleep 2
        if pgrep -f "test_system_realtime" > /dev/null; then
            echo "   ❌ 系统仍在运行，请手动停止后重试"
            exit 1
        fi
        echo "   ✅ 系统已停止"
    else
        echo "   ❌ 部署已取消"
        exit 1
    fi
else
    echo "   ✅ 系统未运行"
fi
echo ""

# 2. 创建备份目录
echo "【步骤2】创建备份..."
mkdir -p "$BACKUP_DIR"
echo "   备份目录: $BACKUP_DIR"
echo ""

# 3. 备份关键文件
echo "【步骤3】备份关键文件..."
BACKUP_FILES=(
    "config.yaml"
    "test_system_realtime.py"
)

for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        cp "$PROJECT_ROOT/$file" "$BACKUP_DIR/$file.backup"
        echo "   ✅ 已备份: $file"
    else
        echo "   ⚠️  文件不存在: $file (跳过)"
    fi
done

# 备份新添加的文件（如果存在）
NEW_FILES=(
    "python_apps/beacon_match_tracker.py"
)

for file in "${NEW_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp "$PROJECT_ROOT/$file" "$BACKUP_DIR/$file.backup"
        echo "   ✅ 已备份新文件: $file"
    fi
done

echo ""

# 4. 验证Phase 1文件存在
echo "【步骤4】验证Phase 1文件..."
REQUIRED_FILES=(
    "python_apps/beacon_match_tracker.py"
    "config.yaml"
    "test_system_realtime.py"
)

ALL_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo "   ✅ $file 存在"
    else
        echo "   ❌ $file 不存在"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo "   ❌ 缺少必需文件，部署终止"
    exit 1
fi
echo ""

# 5. 运行测试验证
echo "【步骤5】运行测试验证..."
cd "$PROJECT_ROOT"
if python3 tests/test_phase1_optimizations.py > /tmp/phase1_test.log 2>&1; then
    echo "   ✅ 所有测试通过"
else
    echo "   ❌ 测试失败，查看日志: /tmp/phase1_test.log"
    echo "   部署终止（文件已备份）"
    exit 1
fi
echo ""

# 6. 验证配置文件语法
echo "【步骤6】验证配置文件语法..."
if python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo "   ✅ 配置文件语法正确"
else
    echo "   ❌ 配置文件语法错误"
    exit 1
fi
echo ""

# 7. 检查Python导入
echo "【步骤7】检查Python模块导入..."
if python3 -c "
import sys
sys.path.insert(0, 'python_apps')
from beacon_match_tracker import BeaconMatchTracker
from config_loader import get_config
print('✅ 模块导入成功')
" 2>/dev/null; then
    echo "   ✅ 所有模块可以正常导入"
else
    echo "   ❌ 模块导入失败"
    exit 1
fi
echo ""

# 8. 生成部署摘要
echo "【步骤8】生成部署摘要..."
cat > "$BACKUP_DIR/DEPLOYMENT_INFO.txt" << EOF
Phase 1 部署信息
================
部署时间: $(date)
备份目录: $BACKUP_DIR

部署内容:
1. 移除硬编码阈值（配置化）
2. 信标匹配时空一致性
3. 配置文件更新

修改的文件:
- config.yaml (新增配置项)
- test_system_realtime.py (集成新功能)
- python_apps/beacon_match_tracker.py (新文件)

回滚方法:
1. 恢复备份文件:
   cp $BACKUP_DIR/config.yaml.backup $PROJECT_ROOT/config.yaml
   cp $BACKUP_DIR/test_system_realtime.py.backup $PROJECT_ROOT/test_system_realtime.py

2. 如果不再需要，删除新文件:
   rm $PROJECT_ROOT/python_apps/beacon_match_tracker.py

3. 重启系统

测试日志: /tmp/phase1_test.log
EOF

echo "   ✅ 部署摘要已保存到: $BACKUP_DIR/DEPLOYMENT_INFO.txt"
echo ""

# 9. 部署完成
echo "=========================================="
echo "✅ Phase 1 部署准备完成！"
echo "=========================================="
echo ""
echo "备份位置: $BACKUP_DIR"
echo "测试日志: /tmp/phase1_test.log"
echo ""
echo "【重要提示】"
echo "1. 所有文件已备份到: $BACKUP_DIR"
echo "2. 如果出现问题，可以使用备份恢复"
echo "3. 查看 $BACKUP_DIR/DEPLOYMENT_INFO.txt 了解详情"
echo ""
echo "现在可以启动系统进行测试。"
echo "启动命令: python3 test_system_realtime.py"
echo ""

