#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              DeepStream配置验证"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

cd /home/liubo/Download/deepstream-vehicle-detection

# 检查文件
echo "【1. 文件检查】"
echo ""

if [ -f "models/yolov11.engine" ]; then
    SIZE=$(ls -lh models/yolov11.engine | awk '{print $5}')
    echo "  ✓ TensorRT引擎: models/yolov11.engine ($SIZE)"
else
    echo "  ✗ TensorRT引擎不存在"
    exit 1
fi

if [ -f "config/config_infer_yolov11.txt" ]; then
    echo "  ✓ 推理配置文件: config/config_infer_yolov11.txt"
else
    echo "  ✗ 推理配置文件不存在"
    exit 1
fi

if [ -f "config/config_tracker_NvDCF_accuracy.yml" ]; then
    echo "  ✓ 跟踪配置文件: config/config_tracker_NvDCF_accuracy.yml"
else
    echo "  ✗ 跟踪配置文件不存在"
    exit 1
fi

if [ -f "config/labels.txt" ]; then
    CLASSES=$(wc -l < config/labels.txt)
    echo "  ✓ 类别标签: config/labels.txt ($CLASSES 类)"
else
    echo "  ✗ 类别标签不存在"
    exit 1
fi

if [ -f "python_apps/deepstream_vehicle_detection.py" ]; then
    LINES=$(wc -l < python_apps/deepstream_vehicle_detection.py)
    echo "  ✓ Python应用: python_apps/deepstream_vehicle_detection.py ($LINES 行)"
else
    echo "  ✗ Python应用不存在"
    exit 1
fi

echo ""
echo "【2. 配置内容检查】"
echo ""

# 检查引擎路径
ENGINE_PATH=$(grep "model-engine-file" config/config_infer_yolov11.txt | cut -d= -f2 | tr -d ' ')
echo "  配置中的引擎路径: $ENGINE_PATH"

if [ "$ENGINE_PATH" = "../models/yolov11.engine" ]; then
    echo "  ✓ 引擎路径正确"
else
    echo "  ⚠ 引擎路径可能需要调整"
fi

# 检查类别数
NUM_CLASSES=$(grep "num-detected-classes" config/config_infer_yolov11.txt | cut -d= -f2 | tr -d ' ')
echo "  配置的类别数: $NUM_CLASSES"

if [ "$NUM_CLASSES" = "10" ]; then
    echo "  ✓ 类别数正确"
else
    echo "  ⚠ 类别数可能有误"
fi

# 检查网络模式
NETWORK_MODE=$(grep "network-mode" config/config_infer_yolov11.txt | cut -d= -f2 | tr -d ' ')
if [ "$NETWORK_MODE" = "2" ]; then
    echo "  ✓ 网络模式: FP16"
elif [ "$NETWORK_MODE" = "1" ]; then
    echo "  ✓ 网络模式: INT8"
else
    echo "  ✓ 网络模式: FP32"
fi

echo ""
echo "【3. Docker镜像检查】"
echo ""

if sudo docker images | grep -q "deepstream.*7.0-triton-multiarch"; then
    IMAGE_ID=$(sudo docker images | grep "deepstream.*7.0-triton-multiarch" | awk '{print $3}' | head -1)
    IMAGE_SIZE=$(sudo docker images | grep "$IMAGE_ID" | awk '{print $7}')
    echo "  ✓ DeepStream镜像已拉取"
    echo "    镜像ID: $IMAGE_ID"
    echo "    大小: $IMAGE_SIZE"
else
    echo "  ✗ DeepStream镜像未找到"
    echo "    请运行: sudo docker pull nvcr.io/nvidia/deepstream:7.0-triton-multiarch"
    exit 1
fi

echo ""
echo "【4. 测试视频检查】"
echo ""

TEST_VIDEO="/home/liubo/Download/20211216-101333.mp4"
if [ -f "$TEST_VIDEO" ]; then
    SIZE=$(ls -lh "$TEST_VIDEO" | awk '{print $5}')
    echo "  ✓ 测试视频: $TEST_VIDEO ($SIZE)"
else
    echo "  ⚠ 测试视频不存在: $TEST_VIDEO"
    echo "    可以使用其他视频进行测试"
fi

echo ""
echo "【5. GPU检查】"
echo ""

if command -v nvidia-smi &> /dev/null; then
    echo "  ✓ NVIDIA驱动已安装"
    echo ""
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | \
        awk -F', ' '{printf "    GPU: %s\n    总内存: %s\n    空闲: %s\n", $1, $2, $3}'
else
    echo "  ✗ nvidia-smi不可用"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "              配置验证完成"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "下一步："
echo "  1. 进入容器测试: bash 测试DeepStream应用.sh"
echo "  2. 或查看开发指南: cat 开发指南.md"
echo ""

