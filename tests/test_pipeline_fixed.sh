#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              测试DeepStream Pipeline（修复版）"
echo "═══════════════════════════════════════════════════════════════════"
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
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c "
        echo '════════════════════════════════════════════'
        echo '  测试1: MP4解封装 + H264解码'
        echo '════════════════════════════════════════════'
        echo ''
        echo '使用qtdemux解封装MP4容器...'
        echo ''
        
        timeout 5 gst-launch-1.0 -e \
            filesrc location=/workspace/20211216-101333.mp4 ! \
            qtdemux ! \
            h264parse ! \
            nvv4l2decoder ! \
            fakesink 2>&1 | grep -E 'Setting|Execution|ended' | head -5
        
        echo ''
        echo '✓ 解封装和解码测试完成'
        echo ''
        
        echo '════════════════════════════════════════════'
        echo '  测试2: 完整Pipeline（不带推理）'
        echo '════════════════════════════════════════════'
        echo ''
        echo '测试nvstreammux...'
        echo ''
        
        timeout 5 gst-launch-1.0 -e \
            filesrc location=/workspace/20211216-101333.mp4 ! \
            qtdemux ! \
            h264parse ! \
            nvv4l2decoder ! \
            m.sink_0 nvstreammux name=m width=1920 height=1080 batch-size=1 ! \
            nvvideoconvert ! \
            nvdsosd ! \
            fakesink 2>&1 | grep -E 'Setting|Execution|ended' | head -5
        
        echo ''
        echo '✓ Streammux测试完成'
        echo ''
        
        echo '════════════════════════════════════════════'
        echo '  测试3: 添加TensorRT推理'
        echo '════════════════════════════════════════════'
        echo ''
        
        if [ ! -f 'models/yolov11.engine' ]; then
            echo '✗ TensorRT引擎不存在'
            exit 1
        fi
        
        echo '✓ TensorRT引擎: models/yolov11.engine'
        echo '✓ 推理配置: config/config_infer_yolov11.txt'
        echo ''
        echo '运行15秒测试...'
        echo ''
        
        timeout 15 gst-launch-1.0 -v -e \
            filesrc location=/workspace/20211216-101333.mp4 ! \
            qtdemux ! \
            h264parse ! \
            nvv4l2decoder ! \
            m.sink_0 nvstreammux name=m width=1920 height=1080 batch-size=1 batched-push-timeout=4000000 ! \
            nvinfer config-file-path=config/config_infer_yolov11.txt ! \
            nvvideoconvert ! \
            nvdsosd ! \
            fakesink 2>&1 | tail -100
        
        echo ''
        echo '════════════════════════════════════════════'
        echo '  测试完成'
        echo '════════════════════════════════════════════'
    "

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  容器已退出"
echo "═══════════════════════════════════════════════════════════════════"

