# DeepStream车辆检测开发指南

## ✅ 当前状态

### 环境准备完成
- ✅ DeepStream容器已拉取：`nvcr.io/nvidia/deepstream:7.0-triton-multiarch`
- ✅ Docker已安装并配置
- ✅ DNS问题已解决
- ✅ 项目结构已创建

### ⚠️ 需要注意
- 用户不在docker组中
- 所有docker命令需要sudo
- 或者注销重新登录让docker组生效

---

## 🚀 开发步骤

### 阶段1：准备TensorRT引擎（20-30分钟）

#### 方法A：使用sudo执行脚本

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
sudo bash 准备TensorRT引擎.sh
```

#### 方法B：直接执行命令（推荐）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

sudo docker run --rm \
    --runtime nvidia \
    --network host \
    -v /home/liubo/Download:/workspace \
    -w /workspace \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c '
set -e

echo "步骤1: 安装ultralytics"
pip3 install ultralytics

echo "步骤2: 导出ONNX"
python3 << "PYEOF"
import sys
sys.path.insert(0, "/workspace/ultralytics-main")
from ultralytics import YOLO

model = YOLO("/workspace/best.pt")
model.export(format="onnx", opset=12, simplify=True, dynamic=False, imgsz=640)
print("✓ ONNX导出完成")
PYEOF

echo "步骤3: 转换TensorRT引擎"
mkdir -p /workspace/deepstream-vehicle-detection/models

/usr/src/tensorrt/bin/trtexec \
    --onnx=/workspace/best.onnx \
    --saveEngine=/workspace/deepstream-vehicle-detection/models/yolov11.engine \
    --fp16 \
    --memPoolSize=workspace:4096M

ls -lh /workspace/deepstream-vehicle-detection/models/yolov11.engine
echo "✓ TensorRT引擎准备完成"
'
```

**预期输出**：
- ONNX导出：`/home/liubo/Download/best.onnx`
- TensorRT引擎：`/home/liubo/Download/deepstream-vehicle-detection/models/yolov11.engine`

---

### 阶段2：配置DeepStream推理插件（30分钟）

引擎准备完成后，需要配置`config/config_infer_yolov11.txt`

**关键配置**：
```ini
[property]
model-engine-file=../models/yolov11.engine
labelfile-path=../config/labels.txt
batch-size=1
network-mode=2  # FP16
num-detected-classes=10
interval=0
gie-unique-id=1
process-mode=1
network-type=0
cluster-mode=2
maintain-aspect-ratio=1
parse-bbox-func-name=NvDsInferParseCustomYoloV8
custom-lib-path=/opt/nvidia/deepstream/deepstream/lib/libnvds_infercustomparser.so

[class-attrs-all]
nms-iou-threshold=0.45
pre-cluster-threshold=0.25
```

---

### 阶段3：开发DeepStream Python应用（4-6小时）

**核心功能**：
1. 构建GStreamer pipeline
2. 配置nvinfer（YOLO）
3. 配置nvtracker（NvDCF）
4. 处理检测结果和跟踪数据
5. 车辆分类统计
6. HyperLPR车牌识别

**应用框架已创建**：
```
python_apps/deepstream_vehicle_detection.py
```

---

### 阶段4：测试和优化（2-3小时）

**测试**：
- 视频文件检测
- 实时相机流
- 性能benchmark

**预期性能**：
- 视频分析：50-100 FPS
- 实时流：50-100 FPS

---

## 💡 开发建议

### 分步测试策略

1. **先测试DeepStream示例**（验证容器）
   ```bash
   sudo docker run -it --rm --runtime nvidia \
       nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
       deepstream-app -c /opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/source1_usb_dec_infer_resnet_int8.txt
   ```

2. **准备TensorRT引擎**

3. **测试YOLOv11推理**（简单pipeline）

4. **逐步添加功能**（跟踪、分类、车牌识别）

---

## 📚 参考资源

### 项目文档
- **开发计划**：`/home/liubo/Download/DeepStream开发计划.md`
- **快速入门**：`docs/DeepStream快速入门.md`
- **安装指南**：`docs/DEEPSTREAM_INSTALL_GUIDE.md`

### NVIDIA官方文档
- DeepStream SDK：https://docs.nvidia.com/metropolis/deepstream/dev-guide/
- DeepStream Python：https://github.com/NVIDIA-AI-IOT/deepstream_python_apps
- TensorRT：https://docs.nvidia.com/deepstream/deepstream-sdk/text/DS_using_custom_model.html

---

## ⏭️ 立即行动

### 第一步：准备TensorRT引擎

**执行命令**（需要sudo）：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
sudo bash 准备TensorRT引擎.sh
```

**预计时间**：20-30分钟

**完成后**：
- ✅ `models/yolov11.engine` 文件生成
- ✅ 可以开始编写DeepStream应用

---

**现在可以开始第一步了！** 🚀


