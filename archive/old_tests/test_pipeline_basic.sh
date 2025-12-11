#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              测试DeepStream基础Pipeline"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "这个测试不使用Python，直接用gst-launch-1.0测试pipeline"
echo ""

VIDEO_FILE="/home/liubo/Download/20211216-101333.mp4"

if [ ! -f "$VIDEO_FILE" ]; then
    echo "✗ 视频文件不存在: $VIDEO_FILE"
    exit 1
fi

echo "✓ 视频文件: $VIDEO_FILE"
echo ""
echo "启动DeepStream容器..."
echo ""

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -e DISPLAY=$DISPLAY \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c "
        echo '════════════════════════════════════════════'
        echo '  测试1: 验证视频文件'
        echo '════════════════════════════════════════════'
        echo ''
        
        ls -lh /workspace/20211216-101333.mp4
        echo ''
        
        echo '════════════════════════════════════════════'
        echo '  测试2: 基础解码pipeline（不使用推理）'
        echo '════════════════════════════════════════════'
        echo ''
        echo '运行5秒...'
        echo ''
        
        timeout 5 gst-launch-1.0 -e \
            filesrc location=/workspace/20211216-101333.mp4 ! \
            h264parse ! \
            nvv4l2decoder ! \
            nvvideoconvert ! \
            'video/x-raw(memory:NVMM), format=RGBA' ! \
            nvdsosd ! \
            fakesink 2>&1 | grep -E 'Setting|ERROR|WARNING' | head -20
        
        echo ''
        echo '✓ 基础解码pipeline测试完成'
        echo ''
        
        echo '════════════════════════════════════════════'
        echo '  测试3: 添加推理引擎'
        echo '════════════════════════════════════════════'
        echo ''
        echo '检查配置文件...'
        
        if [ ! -f 'config/config_infer_yolov11.txt' ]; then
            echo '✗ 配置文件不存在'
            exit 1
        fi
        
        if [ ! -f 'models/yolov11.engine' ]; then
            echo '✗ TensorRT引擎不存在'
            exit 1
        fi
        
        echo '✓ 配置文件: config/config_infer_yolov11.txt'
        echo '✓ TensorRT引擎: models/yolov11.engine'
        echo ''
        echo '运行10秒测试推理...'
        echo ''
        
        timeout 10 gst-launch-1.0 -e \
            filesrc location=/workspace/20211216-101333.mp4 ! \
            h264parse ! \
            nvv4l2decoder ! \
            nvstreammux name=mux width=1920 height=1080 batch-size=1 batched-push-timeout=4000000 ! \
            nvinfer config-file-path=config/config_infer_yolov11.txt ! \
            nvvideoconvert ! \
            nvdsosd ! \
            fakesink 2>&1 | tail -50
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  测试完成'
        echo '════════════════════════════════════════════'
        echo ''
        echo '如果看到错误，记录下来并查看 开发指南.md'
    "

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  容器已退出"
echo "═══════════════════════════════════════════════════════════════════"

