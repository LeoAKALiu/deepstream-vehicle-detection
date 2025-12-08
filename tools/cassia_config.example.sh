#!/bin/bash
# Cassia蓝牙信标配置示例

# Cassia AC控制器地址
CASSIA_AC="http://192.168.1.100"

# 开发者密钥（在AC Web界面 -> Settings -> Developer account中设置）
CASSIA_KEY="your_developer_key"
CASSIA_SECRET="your_developer_secret"

# 路由器MAC地址（需要先在AC中添加路由器）
CASSIA_ROUTER="CC:1B:E0:E2:E9:B8"

# 运行命令
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-ac "$CASSIA_AC" \
    --cassia-key "$CASSIA_KEY" \
    --cassia-secret "$CASSIA_SECRET" \
    --cassia-router "$CASSIA_ROUTER"

