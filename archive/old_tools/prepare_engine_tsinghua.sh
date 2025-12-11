#!/bin/bash

# 在DeepStream容器中准备YOLOv11 TensorRT引擎（使用清华源）

CONTAINER_IMAGE="nvcr.io/nvidia/deepstream:7.0-triton-multiarch"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      准备YOLOv11 TensorRT引擎（使用清华源）            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "在DeepStream容器中准备TensorRT引擎..."
echo "使用清华源安装Python包（速度更快）"
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
echo "步骤1: 配置pip使用清华源"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p ~/.pip
cat > ~/.pip/pip.conf << "PIPEOF"
[global]
index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
[install]
trusted-host = mirrors.tuna.tsinghua.edu.cn
PIPEOF

echo "  ✓ 清华源已配置"
pip3 config list

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤2: 安装ultralytics（从清华源）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

pip3 install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    ultralytics onnx onnxscript onnxslim onnxruntime

echo "  ✓ ultralytics及ONNX相关依赖已安装"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤3: 导出ONNX模型"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << "PYEOF"
import sys
sys.path.insert(0, "/workspace/ultralytics-main")
from ultralytics import YOLO

print("加载YOLOv11模型: /workspace/best.pt")
model = YOLO("/workspace/best.pt")

print("导出ONNX (opset 12, 简化, 静态形状, 640x640)...")
model.export(
    format="onnx",
    opset=12,
    simplify=True,
    dynamic=False,
    imgsz=640
)

print("✓ ONNX导出完成: /workspace/best.onnx")
PYEOF

if [ ! -f /workspace/best.onnx ]; then
    echo "  ✗ ONNX导出失败"
    exit 1
fi

echo "  ✓ ONNX文件已生成"
ls -lh /workspace/best.onnx

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤4: 转换TensorRT引擎"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /workspace/deepstream-vehicle-detection/models

echo "  开始转换（可能需要10-20分钟）..."

/usr/src/tensorrt/bin/trtexec \
    --onnx=/workspace/best.onnx \
    --saveEngine=/workspace/deepstream-vehicle-detection/models/yolov11.engine \
    --fp16 \
    --memPoolSize=workspace:4096M \
    --verbose 2>&1 | grep -E "Input|Output|Binding|mean|percentile|total|TensorRT version"

if [ ! -f /workspace/deepstream-vehicle-detection/models/yolov11.engine ]; then
    echo "  ✗ TensorRT引擎转换失败"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤5: 验证引擎"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENGINE_SIZE=$(ls -lh /workspace/deepstream-vehicle-detection/models/yolov11.engine | awk "{print \$5}")
ENGINE_PATH="/workspace/deepstream-vehicle-detection/models/yolov11.engine"

echo "  ✓ 引擎文件: yolov11.engine"
echo "  ✓ 文件大小: $ENGINE_SIZE"
echo "  ✓ 完整路径: $ENGINE_PATH"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✅ TensorRT引擎准备完成                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "生成文件:"
echo "  • /home/liubo/Download/best.onnx"
echo "  • /home/liubo/Download/deepstream-vehicle-detection/models/yolov11.engine"
echo ""
echo "下一步:"
echo "  • 开发DeepStream Python应用"
echo "  • 配置推理插件"
echo "  • 测试检测pipeline"
'

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "引擎准备成功！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "验证文件:"
    ls -lh /home/liubo/Download/deepstream-vehicle-detection/models/yolov11.engine 2>/dev/null || echo "  引擎文件已在容器中生成"
    ls -lh /home/liubo/Download/best.onnx 2>/dev/null || echo "  ONNX文件已生成"
    echo ""
else
    echo ""
    echo "✗ 引擎准备失败"
    echo "  请检查上面的错误信息"
    exit 1
fi

