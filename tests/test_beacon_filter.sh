#!/bin/bash

# ============================================
# 信标过滤器测试脚本
# 测试多级过滤功能
# ============================================

echo "========================================"
echo "   信标智能过滤器测试"
echo "========================================"
echo ""

# 进入工作目录
cd "$(dirname "$0")"

echo "【步骤1】检查依赖"
echo "--------------------"

# 检查YAML配置文件
if [ ! -f "beacon_whitelist.yaml" ]; then
    echo "❌ 找不到 beacon_whitelist.yaml"
    exit 1
fi
echo "✓ 配置文件存在"

# 检查过滤器模块
if [ ! -f "python_apps/beacon_filter.py" ]; then
    echo "❌ 找不到 python_apps/beacon_filter.py"
    exit 1
fi
echo "✓ 过滤器模块存在"

# 检查PyYAML
python3 -c "import yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  PyYAML未安装，正在安装..."
    pip3 install pyyaml
fi
echo "✓ PyYAML已安装"

echo ""
echo "【步骤2】运行过滤器测试"
echo "--------------------"

# 运行内置测试
cd python_apps
python3 beacon_filter.py

echo ""
echo "========================================"
echo "   测试完成！"
echo "========================================"
echo ""
echo "📖 查看配置文档:"
echo "   cat ../信标白名单配置指南.md"
echo ""
echo "🔧 编辑配置文件:"
echo "   nano ../beacon_whitelist.yaml"
echo ""
echo "🚀 启动完整系统:"
echo "   cd .."
echo "   bash 测试自定义模型.sh"
echo ""


