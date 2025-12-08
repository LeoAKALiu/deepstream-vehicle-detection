#!/bin/bash
# 启动现场测试系统（带显示，不带录制）
# 适用于Jetson连接屏幕的现场测试

cd /home/liubo/Download/deepstream-vehicle-detection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           现场测试系统 - 带显示模式"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "功能："
echo "  ✓ 实时车辆检测与识别（带视频显示）"
echo "  ✓ 工程车辆信标匹配"
echo "  ✓ 社会车辆车牌识别"
echo ""
echo "硬件准备："
echo "  ✓ Orbbec Gemini 335L 相机"
echo "  ✓ Cassia蓝牙路由器 (192.168.1.2)"
echo "  ✓ BLE信标标签"
echo "  ✓ Jetson已连接屏幕"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "启动系统..."
echo ""

# 检查相机是否可用
if [ ! -e /dev/video* ]; then
    echo "⚠ 警告: 未检测到相机设备"
    echo "   请检查相机连接和权限"
    echo ""
fi

# 启动主检测程序（带显示）
# 注意：如果不指定参数，会自动从 config.yaml 读取配置
python3 test_system_realtime.py \
    --config config.yaml \
    --engine models/custom_yolo.engine \
    --cassia-ip 192.168.1.2 \
    --camera-id camera_01

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""


