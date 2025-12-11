#!/bin/bash

# 在DeepStream容器中准备YOLOv11 TensorRT引擎

CONTAINER_IMAGE="nvcr.io/nvidia/deepstream:7.0-triton-multiarch"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      准备YOLOv11 TensorRT引擎                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "在DeepStream容器中准备TensorRT引擎..."
echo ""

sudo docker run --rm \
    --runtime nvidia \
    --network host \
    -v /home/liubo/Download:/workspace \
    -w /workspace \
    "$CONTAINER_IMAGE" \
    bash -c '
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤1: 安装ultralytics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

pip3 install ultralytics --quiet
echo "  ✓ ultralytics已安装"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤2: 导出ONNX模型"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << "PYEOF"
import sys
sys.path.insert(0, "/workspace/ultralytics-main")
from ultralytics import YOLO

print("加载YOLOv11模型...")
model = YOLO("/workspace/best.pt")

print("导出ONNX...")
model.export(
    format="onnx",
    opset=12,
    simplify=True,
    dynamic=False,
    imgsz=640
)

print("✓ ONNX导出成功: /workspace/best.onnx")
PYEOF

if [ ! -f /workspace/best.onnx ]; then
    echo "✗ ONNX导出失败"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤3: 转换TensorRT引擎"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

/usr/src/tensorrt/bin/trtexec \
    --onnx=/workspace/best.onnx \
    --saveEngine=/workspace/deepstream-vehicle-detection/models/yolov11.engine \
    --fp16 \
    --memPoolSize=workspace:4096M \
    --verbose \
    2>&1 | grep -E "Input|Output|Engine|mean|GPU"

if [ ! -f /workspace/deepstream-vehicle-detection/models/yolov11.engine ]; then
    echo "✗ TensorRT引擎转换失败"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤4: 验证引擎"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ENGINE_SIZE=$(ls -lh /workspace/deepstream-vehicle-detection/models/yolov11.engine | awk "{print \$5}")

echo "  ✓ 引擎文件大小: $ENGINE_SIZE"
echo "  ✓ 引擎路径: /workspace/deepstream-vehicle-detection/models/yolov11.engine"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✅ TensorRT引擎准备完成                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
'

if [ $? -eq 0 ]; then
    echo ""
    echo "下一步："
    echo "  更新config/config_infer_yolov11.txt中的引擎路径"
    echo "  然后运行DeepStream应用"
    echo ""
else
    echo ""
    echo "✗ 引擎准备失败，请检查错误信息"
    exit 1
fi


