#!/bin/bash
# 实时车辆检测系统测试脚本

cd /home/liubo/Download/deepstream-vehicle-detection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           实时车辆检测系统 - 实验室模拟测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "测试场景："
echo "  1. 展示工程机械图 + 贴BLE标签 → 无报警（正常）"
echo "  2. 展示工程机械图 + 无BLE标签 → 报警（未备案工程车辆）"
echo "  3. 展示社会车辆图 + 无BLE标签 → 识别车牌"
echo ""
echo "硬件准备："
echo "  ✓ Orbbec Gemini 335L 相机"
echo "  ✓ Cassia蓝牙路由器 (192.168.1.2)"
echo "  ✓ iPad展示车辆图片"
echo "  ✓ BLE信标标签"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "启动系统..."
echo ""

python3 test_system_realtime.py \
    --engine models/custom_yolo.engine \
    --cassia-ip 192.168.1.2 \
    --camera-id camera_01 \
    --no-display

echo ""
echo "测试结束！"





