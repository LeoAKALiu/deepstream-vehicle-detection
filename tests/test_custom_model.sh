#!/bin/bash

cd /home/liubo/Download/deepstream-vehicle-detection

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          自定义工程车辆检测模型测试                              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "模型信息:"
echo "  • 引擎: models/custom_yolo.engine"
echo "  • 类别数: 10"
echo "  • 工程车辆: excavator, bulldozer, roller, loader, dump-truck,"
echo "             concrete-mixer, pump-truck, truck, crane"
echo "  • 社会车辆: car"
echo ""
echo "测试场景:"
echo "  1. iPad显示挖掘机 + 贴BLE标签 → 应检测并显示【工程车辆-已备案】"
echo "  2. iPad显示挖掘机 + 无标签   → 应检测并报警【未备案工程车辆】"
echo "  3. iPad显示小汽车 + 无标签   → 应检测并识别车牌"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 test_system_realtime.py

echo ""
echo "测试结束"

