#!/bin/bash

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════╗
║       工程机械实时识别系统（Cassia信标版）                        ║
╚══════════════════════════════════════════════════════════════════╝


系统配置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Jetson:      192.168.1.3
Cassia网关:  192.168.1.2
视频源:      ../20211216-101333.mp4
TensorRT:    yolov11_host.engine


功能清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ GPU检测 (YOLOv11, 25-30 FPS)
✅ IoU跟踪 (唯一ID)
✅ Cassia信标匹配
✅ HyperLPR车牌识别
✅ 未备案车辆报警

EOF

cd /home/liubo/Download/deepstream-vehicle-detection

python3 test_system_realtime.py \
    --engine models/custom_yolo.engine \
    --cassia-ip 192.168.1.2






