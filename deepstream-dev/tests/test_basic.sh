#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              测试DeepStream车辆检测应用（开发版本）"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# 检查视频文件
VIDEO_FILE="/home/liubo/Download/20211216-101333.mp4"
if [ ! -f "$VIDEO_FILE" ]; then
    echo "⚠️  视频文件不存在: $VIDEO_FILE"
    echo ""
    echo "请使用自己的视频文件："
    echo "  python3 python_apps/deepstream_vehicle_detection.py /path/to/your/video.mp4"
    exit 1
fi

echo "✓ 视频文件: $VIDEO_FILE"
echo "✓ TensorRT引擎: models/yolov11.engine"
echo ""

# 检查DeepStream容器
if ! sudo docker images | grep -q deepstream; then
    echo "⚠️  DeepStream容器未找到"
    echo "请先拉取容器："
    echo "  sudo docker pull nvcr.io/nvidia/deepstream:7.0-triton-multiarch"
    exit 1
fi

echo "✓ DeepStream容器已找到"
echo ""

# 启动DeepStream容器并运行应用
echo "启动DeepStream容器..."
echo ""

cd /home/liubo/Download/deepstream-vehicle-detection/deepstream-dev

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    -w /workspace/deepstream-vehicle-detection/deepstream-dev \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c "
        echo '════════════════════════════════════════════'
        echo '  DeepStream容器已启动'
        echo '════════════════════════════════════════════'
        echo ''
        echo '检查环境...'
        echo ''
        
        # 检查文件
        echo '✓ 工作目录:' \$(pwd)
        echo '✓ TensorRT引擎:' \$(ls -lh ../models/yolov11.engine 2>/dev/null | awk '{print \$9, \$5}' || echo '未找到')
        echo '✓ 配置文件:' \$(ls config/config_infer_yolov11.txt 2>/dev/null && echo 'OK' || echo '未找到')
        echo '✓ Python应用:' \$(ls python_apps/deepstream_vehicle_detection.py 2>/dev/null && echo 'OK' || echo '未找到')
        echo ''
        
        # 设置Python路径
        export PYTHONPATH=/opt/nvidia/deepstream/deepstream/lib:\$PYTHONPATH
        
        # 检查pyds
        if python3 -c 'import pyds' 2>/dev/null; then
            echo '✓ pyds已安装'
        else
            echo '⚠ pyds未安装，尝试安装...'
            cd /opt/nvidia/deepstream/deepstream/lib
            python3 -c 'import pyds' 2>/dev/null || echo '需要手动安装pyds'
            cd /workspace/deepstream-vehicle-detection/deepstream-dev
        fi
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  启动DeepStream应用'
        echo '════════════════════════════════════════════'
        echo ''
        
        # 运行应用
        python3 python_apps/deepstream_vehicle_detection.py $VIDEO_FILE
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  测试完成'
        echo '════════════════════════════════════════════'
    "

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  容器已退出"
echo "═══════════════════════════════════════════════════════════════════"



