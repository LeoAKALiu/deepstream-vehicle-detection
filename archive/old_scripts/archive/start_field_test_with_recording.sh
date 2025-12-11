#!/bin/bash
# 启动现场测试系统（主程序 + 视频录制）
# 主程序独占相机，录制脚本从共享缓冲区读取帧

cd /home/liubo/Download/deepstream-vehicle-detection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           现场测试系统 - 主程序 + 视频录制"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "功能："
echo "  ✓ 实时车辆检测与识别（主程序独占相机）"
echo "  ✓ 同步录制原始测试视频（录制脚本从共享缓冲区读取）"
echo ""
echo "硬件准备："
echo "  ✓ Orbbec Gemini 335L 相机"
echo "  ✓ Cassia蓝牙路由器 (192.168.1.2)"
echo "  ✓ BLE信标标签"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 创建录制输出目录
RECORDING_DIR="recordings"
mkdir -p "$RECORDING_DIR"

# 检查相机是否可用
if [ ! -e /dev/video* ]; then
    echo "⚠ 警告: 未检测到相机设备"
    echo "   请检查相机连接和权限"
    echo ""
fi

# 清理旧的共享缓冲区文件
rm -f /tmp/orbbec_shared_frame.npy /tmp/orbbec_shared_depth.npy

# 启动视频录制（后台运行，从共享缓冲区读取）
echo "【1. 启动视频录制】"
python3 python_apps/record_field_test.py \
    --output-dir "$RECORDING_DIR" \
    > "$RECORDING_DIR/recording_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
RECORDING_PID=$!

echo "✓ 录制进程已启动 (PID: $RECORDING_PID)"
echo "  输出目录: $RECORDING_DIR"
echo "  模式: 从共享缓冲区读取（主程序独占相机）"
echo ""

# 等待录制器初始化（等待主程序创建共享缓冲区）
echo "等待主程序启动并创建共享缓冲区..."
sleep 2

# 启动主检测程序（前台运行，独占相机）
echo "【2. 启动主检测程序】"
echo ""
echo "✓ 主程序将独占相机并创建共享缓冲区"
echo "  录制脚本将从共享缓冲区读取帧"
echo ""

python3 test_system_realtime.py \
    --engine models/custom_yolo.engine \
    --cassia-ip 192.168.1.2 \
    --camera-id camera_01 \
    --no-display

# 主程序退出后，停止录制
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "主程序已停止，正在停止录制..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 发送停止信号给录制进程
if kill -0 $RECORDING_PID 2>/dev/null; then
    kill -INT $RECORDING_PID
    echo "✓ 已发送停止信号给录制进程"
    
    # 等待录制进程结束
    wait $RECORDING_PID 2>/dev/null
    echo "✓ 录制进程已停止"
else
    echo "⚠ 录制进程已不存在"
fi

# 清理共享缓冲区文件
rm -f /tmp/orbbec_shared_frame.npy /tmp/orbbec_shared_depth.npy

echo ""
echo "测试完成！"
echo "录制文件保存在: $RECORDING_DIR"
echo ""
