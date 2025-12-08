#!/bin/bash

cd /home/liubo/Download/deepstream-vehicle-detection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           调试模式：显示所有检测到的物体"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "此模式会:"
echo "  • 显示所有检测到的COCO类别"
echo "  • 降低置信度阈值到0.3"
echo "  • 统计各类别检测次数"
echo "  • 显示FPS"
echo ""
echo "颜色说明:"
echo "  🟠 橙色: truck/bus (可作为工程车)"
echo "  🟢 绿色: car (社会车辆)"
echo "  🔵 蓝色: 其他类别"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 test_debug_detection.py

