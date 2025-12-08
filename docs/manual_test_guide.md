# 手动测试指南（推荐）

## 🚀 快速开始（3步）

### 步骤1：进入DeepStream容器

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash
```

---

### 步骤2：安装依赖（在容器内）

使用清华源安装（快速）：

```bash
# 配置清华源
pip3 config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 安装依赖
pip3 install pycuda opencv-python --no-cache-dir
```

**预计时间**：1-2分钟

---

### 步骤3：运行测试（在容器内）

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    /workspace/20211216-101333.mp4 \
    --engine models/yolov11.engine
```

---

## 📋 完整命令（复制粘贴）

### 宿主机执行：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash
```

### 容器内执行：

```bash
# 配置清华源（一次性）
pip3 config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 安装依赖
pip3 install pycuda opencv-python --no-cache-dir

# 测试TensorRT是否可用
python3 << 'EOF'
try:
    import tensorrt as trt
    print(f"✓ TensorRT: {trt.__version__}")
except:
    print("✗ TensorRT不可用")

try:
    import pycuda
    print("✓ PyCUDA可用")
except:
    print("✗ PyCUDA不可用")

try:
    import cv2
    print(f"✓ OpenCV: {cv2.__version__}")
except:
    print("✗ OpenCV不可用")

import numpy as np
print(f"✓ NumPy: {np.__version__}")
EOF

# 运行推理
python3 python_apps/tensorrt_yolo_inference.py \
    /workspace/20211216-101333.mp4 \
    --engine models/yolov11.engine
```

---

## ⚠️ 可能的问题

### 问题1：TensorRT模块不存在

**错误**：`ModuleNotFoundError: No module named 'tensorrt'`

**原因**：DeepStream容器可能没有Python的TensorRT绑定

**解决方案A**：安装TensorRT Python包
```bash
pip3 install tensorrt --no-cache-dir
```

**解决方案B**：使用宿主机的TensorRT（如果宿主机有）
```bash
# 退出容器，在宿主机上运行
cd /home/liubo/Download/deepstream-vehicle-detection
python3 python_apps/tensorrt_yolo_inference.py \
    20211216-101333.mp4 \
    --engine deepstream-vehicle-detection/models/yolov11.engine
```

### 问题2：PyCUDA编译失败

**错误**：编译时间过长或失败

**解决方案**：使用预编译的wheel
```bash
pip3 install --pre pycuda --no-cache-dir
```

或者跳过PyCUDA，使用替代方案（见下文）

---

## 🔄 替代方案（如果TensorRT Python不可用）

### 方案：回退到CPU方案

如果容器内TensorRT Python绑定不可用，直接使用已经稳定运行的CPU方案：

**在宿主机上**：
```bash
cd /home/liubo/Download/vehicle-detection-system

# 使用现有的CPU方案
python3 src/video_analysis_tracking.py
```

**优势**：
- ✅ 已验证稳定
- ✅ 25-35 FPS实时检测
- ✅ 立即可用

---

## 💡 快速决策树

```
是否有TensorRT Python绑定？
  │
  ├─ 是 → 安装PyCUDA和OpenCV → 运行混合方案
  │
  └─ 否 → 两个选择：
         ├─ 尝试安装tensorrt包 (pip3 install tensorrt)
         └─ 或直接使用CPU方案（已满足需求）
```

---

## 📊 性能对比

| 方案 | FPS | 开发时间 | 当前状态 |
|------|-----|---------|---------|
| CPU | 25-35 | 0天 | ✅ 稳定运行 |
| 混合 | 50-100 | 已完成 | 🧪 测试中 |

如果混合方案遇到太多问题，**建议直接使用CPU方案**，因为：
- 25-35 FPS已满足实时需求
- 稳定可靠
- 无需额外调试

---

## 🎯 推荐流程

1. **先尝试混合方案**（15分钟）
   - 进入容器
   - 安装依赖
   - 测试运行

2. **如果顺利** → 使用混合方案

3. **如果有问题** → 直接用CPU方案
   - 已稳定
   - 性能已满足
   - 省时省力

---

**让我们开始吧！复制上面的命令进入容器。** 🚀

