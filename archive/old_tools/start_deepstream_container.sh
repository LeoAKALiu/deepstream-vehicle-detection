#!/bin/bash

# 启动DeepStream开发容器

CONTAINER_IMAGE="nvcr.io/nvidia/deepstream:7.0-triton-multiarch"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      启动DeepStream开发容器                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "容器: $CONTAINER_IMAGE"
echo "项目目录: /home/liubo/Download"
echo ""

echo "选择运行模式:"
echo ""
echo "  1. 交互式Shell（开发调试）"
echo "  2. 运行DeepStream示例应用"
echo "  3. 准备YOLOv11 TensorRT引擎"
echo "  4. 运行车辆检测应用"
echo ""

read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "启动交互式Shell..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "容器内路径:"
        echo "  项目: /workspace/deepstream-vehicle-detection"
        echo "  模型: /workspace/best.pt"
        echo "  视频: /workspace/*.mp4"
        echo ""
        
        sudo docker run -it --rm \
            --runtime nvidia \
            --network host \
            -v /home/liubo/Download:/workspace \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            -w /workspace/deepstream-vehicle-detection \
            "$CONTAINER_IMAGE"
        ;;
        
    2)
        echo ""
        echo "运行DeepStream示例应用..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        sudo docker run -it --rm \
            --runtime nvidia \
            --network host \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            "$CONTAINER_IMAGE" \
            deepstream-app -c /opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/source1_usb_dec_infer_resnet_int8.txt
        ;;
        
    3)
        echo ""
        echo "准备YOLOv11 TensorRT引擎..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        sudo docker run -it --rm \
            --runtime nvidia \
            --network host \
            -v /home/liubo/Download:/workspace \
            -w /workspace/deepstream-vehicle-detection \
            "$CONTAINER_IMAGE" \
            bash -c "
                cd /workspace
                
                echo '步骤1: 安装ultralytics'
                pip3 install ultralytics --quiet
                
                echo '步骤2: 导出ONNX'
                python3 << 'PYEOF'
import sys
sys.path.insert(0, '/workspace/ultralytics-main')
from ultralytics import YOLO

model = YOLO('/workspace/best.pt')
model.export(format='onnx', opset=12, simplify=True, dynamic=False, imgsz=640)
print('✓ ONNX导出成功')
PYEOF
                
                echo '步骤3: 转换TensorRT引擎'
                /usr/src/tensorrt/bin/trtexec \
                    --onnx=/workspace/best.onnx \
                    --saveEngine=/workspace/best.engine \
                    --fp16 \
                    --workspace=4096 \
                    --verbose
                
                echo '✓ TensorRT引擎准备完成'
                ls -lh /workspace/best.engine
            "
        ;;
        
    4)
        echo ""
        echo "运行车辆检测应用..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "⚠ 车辆检测应用正在开发中"
        echo ""
        echo "当前可以:"
        echo "  1. 进入交互式Shell（选项1）"
        echo "  2. 准备TensorRT引擎（选项3）"
        echo "  3. 然后开始编写DeepStream应用"
        ;;
        
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          完成                                            ║"
echo "╚══════════════════════════════════════════════════════════╝"


