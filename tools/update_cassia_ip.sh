#!/bin/bash
# 批量更新所有脚本和文档中的Cassia IP地址
# 从 192.168.1.27 更新到 192.168.1.2

cd /home/liubo/Download/deepstream-vehicle-detection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           更新Cassia IP地址配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "将更新以下文件中的IP地址："
echo "  192.168.1.27 → 192.168.1.2"
echo ""

# 需要更新的文件列表
FILES=(
    "test_system_realtime.py"
    "测试BLE信标.sh"
    "测试实时系统.sh"
    "运行完整系统.sh"
)

# 更新Python和Shell脚本
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "更新: $file"
        sed -i 's/192\.168\.1\.27/192.168.1.2/g' "$file"
    fi
done

echo ""
echo "✓ IP地址更新完成！"
echo ""
echo "验证更新结果："
grep -r "192.168.1.2" test_system_realtime.py 测试BLE信标.sh 测试实时系统.sh 运行完整系统.sh 2>/dev/null | head -5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


