#!/bin/bash

# 为DeepStream准备TensorRT引擎

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      DeepStream TensorRT引擎准备                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

ONNX_MODEL="/home/liubo/Download/best.onnx"
ENGINE_OUTPUT="../models/yolov11_deepstream.engine"

# 检查ONNX模型
if [ ! -f "$ONNX_MODEL" ]; then
    echo "⚠ ONNX模型不存在: $ONNX_MODEL"
    echo ""
    echo "步骤1: 导出ONNX"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/liubo/Download/ultralytics-main')
from ultralytics import YOLO

print("导出ONNX...")
model = YOLO('/home/liubo/Download/best.pt')
model.export(
    format='onnx',
    imgsz=640,
    simplify=True,
    opset=12  # DeepStream兼容
)
print("✓ ONNX导出成功")
PYEOF

    if [ $? -ne 0 ]; then
        echo "✗ ONNX导出失败"
        exit 1
    fi
    echo ""
fi

echo "步骤2: 转换为TensorRT引擎（DeepStream优化）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 查找trtexec
if command -v trtexec &> /dev/null; then
    TRTEXEC="trtexec"
elif [ -f /usr/src/tensorrt/bin/trtexec ]; then
    TRTEXEC="/usr/src/tensorrt/bin/trtexec"
else
    echo "✗ trtexec未找到"
    exit 1
fi

echo "使用: $TRTEXEC"
echo "输入: $ONNX_MODEL"
echo "输出: $ENGINE_OUTPUT"
echo ""

mkdir -p $(dirname "$ENGINE_OUTPUT")

# DeepStream优化参数
$TRTEXEC \
    --onnx="$ONNX_MODEL" \
    --saveEngine="$ENGINE_OUTPUT" \
    --fp16 \
    --memPoolSize=workspace:2048M \
    --minShapes=input:1x3x640x640 \
    --optShapes=input:1x3x640x640 \
    --maxShapes=input:1x3x640x640 \
    --verbose

if [ $? -eq 0 ] && [ -f "$ENGINE_OUTPUT" ]; then
    SIZE=$(du -h "$ENGINE_OUTPUT" | cut -f1)
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          ✅ TensorRT引擎创建成功                        ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "引擎文件: $ENGINE_OUTPUT ($SIZE)"
    echo ""
    echo "下一步:"
    echo "  1. 配置DeepStream配置文件"
    echo "  2. 编写YOLOv11解析器"
    echo "  3. 集成HyperLPR"
else
    echo ""
    echo "✗ 转换失败"
    exit 1
fi


