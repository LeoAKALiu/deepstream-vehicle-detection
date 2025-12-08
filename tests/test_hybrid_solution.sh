#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              测试混合方案（TensorRT GPU + Python CPU）"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

VIDEO_FILE="/home/liubo/Download/20211216-101333.mp4"

if [ ! -f "$VIDEO_FILE" ]; then
    echo "✗ 视频文件不存在: $VIDEO_FILE"
    exit 1
fi

echo "✓ 视频文件: $VIDEO_FILE"
echo "✓ TensorRT引擎: models/yolov11.engine"
echo ""
echo "启动DeepStream容器..."
echo ""

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c "
        echo '════════════════════════════════════════════'
        echo '  检查环境'
        echo '════════════════════════════════════════════'
        echo ''
        
        # 检查Python包
        echo '检查依赖...'
        python3 -c 'import tensorrt; print(\"✓ TensorRT:\", tensorrt.__version__)' || echo '✗ TensorRT不可用'
        python3 -c 'import pycuda; print(\"✓ PyCUDA可用\")' || echo '⚠ PyCUDA需要安装'
        python3 -c 'import cv2; print(\"✓ OpenCV:\", cv2.__version__)' || echo '⚠ OpenCV需要安装'
        python3 -c 'import numpy; print(\"✓ NumPy:\", numpy.__version__)' || echo '⚠ NumPy需要安装'
        echo ''
        
        echo '════════════════════════════════════════════'
        echo '  安装缺失的依赖'
        echo '════════════════════════════════════════════'
        echo ''
        
        # 安装PyCUDA（如果需要）
        if ! python3 -c 'import pycuda' 2>/dev/null; then
            echo '安装PyCUDA...'
            pip3 install pycuda --no-cache-dir
        fi
        
        # 安装OpenCV（如果需要）
        if ! python3 -c 'import cv2' 2>/dev/null; then
            echo '安装OpenCV...'
            pip3 install opencv-python --no-cache-dir
        fi
        
        # 安装NumPy（如果需要）
        if ! python3 -c 'import numpy' 2>/dev/null; then
            echo '安装NumPy...'
            pip3 install numpy --no-cache-dir
        fi
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  运行混合方案'
        echo '════════════════════════════════════════════'
        echo ''
        
        # 运行应用（限制处理100帧进行测试）
        python3 python_apps/tensorrt_yolo_inference.py \
            /workspace/20211216-101333.mp4 \
            --engine models/yolov11.engine
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  测试完成'
        echo '════════════════════════════════════════════'
    "

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  容器已退出"
echo "═══════════════════════════════════════════════════════════════════"

