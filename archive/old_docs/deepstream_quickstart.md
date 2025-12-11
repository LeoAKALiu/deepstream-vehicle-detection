# DeepStream车辆检测 - 快速入门

## 🎯 DeepStream方案优势

与之前方案对比：

| 方案 | GPU | FPS | 准确度 | 开发难度 |
|------|-----|-----|--------|----------|
| 实时检测（当前） | ❌ CPU | 25-35 | 高 | 低 ✓ |
| CPU跟踪版 | ❌ | 0.4 | 高 | 低 ✓ |
| **DeepStream** | **✅** | **50-100** | **高** | **中** |

**DeepStream是唯一能在Jetson上实现真GPU视频处理的方案！**

---

## 📋 开发步骤

### 第1步：安装DeepStream

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 自动安装
sudo bash scripts/install_deepstream.sh
```

预计时间：30-60分钟

### 第2步：准备TensorRT引擎

```bash
bash scripts/prepare_tensorrt.sh
```

预计时间：10-20分钟

### 第3步：测试DeepStream

```bash
# 测试官方示例
bash scripts/test_deepstream.sh

# 测试YOLOv11推理
bash scripts/test_yolo_deepstream.sh
```

### 第4步：集成HyperLPR

编辑Python probe函数，添加车牌识别逻辑

### 第5步：完整测试

```bash
# 测试视频文件
bash run_deepstream.sh test_video.mp4

# 测试实时相机
bash run_deepstream.sh camera
```

---

## 🏗️ DeepStream架构说明

### GStreamer Pipeline

```
视频文件/相机
    ↓
nvv4l2decoder (硬件解码，GPU)
    ↓
nvstreammux (批处理，GPU)
    ↓
nvinfer (TensorRT推理，GPU)
    ↓
nvtracker (NvDCF跟踪，GPU)
    ↓
nvvideoconvert (格式转换，GPU)
    ↓
nvdsosd (OSD叠加，GPU)
    ↓
nveglglessink (显示) / filesink (录制)
```

**全程GPU加速！**

### Python Probe函数

在pipeline中插入Python回调：
- 访问检测结果
- 访问跟踪ID
- 裁剪ROI进行车牌识别
- 统计车辆数据

---

## 💡 关键技术点

### 1. YOLOv11自定义解析器

DeepStream需要理解YOLO输出格式：
- 编写NvDsInferParseYolo函数（C++）
- 或使用Python解析

### 2. 跟踪ID管理

NvDCF跟踪器自动分配ID：
- 唯一车辆计数
- 假阴性处理（容忍帧数可配置）
- 卡尔曼滤波

### 3. HyperLPR集成

在Python probe中：
```python
def probe_function(pad, info):
    # 获取帧数据
    frame_data = get_numpy_from_nvbuf(...)
    
    # 遍历检测对象
    for obj in objects:
        if obj.class_id in [8, 9]:  # 社会车辆
            # 裁剪ROI
            roi = frame_data[y1:y2, x1:x2]
            
            # HyperLPR识别
            plates = lpr.detect(roi)
```

### 4. 性能优化

- 批处理大小：根据视频数量调整
- 跟踪器参数：平衡准确度和速度
- TensorRT精度：FP16推荐

---

## 📊 预期性能

### Jetson Orin

| 任务 | FPS | GPU占用 | 说明 |
|------|-----|---------|------|
| 单路1080p视频 | 50-80 | 60% | TensorRT FP16 |
| 单路720p视频 | 80-100 | 50% | TensorRT FP16 |
| 多路720p视频 | 120+ | 90% | 批处理 |

### 资源占用

```
DeepStream pipeline:
  GPU: 1.5GB
  RAM: 1.0GB
  CPU: 20-30%
```

可以与其他算法共存！

---

## 🐛 常见问题

### Q1: 安装DeepStream失败

**检查JetPack版本**:
```bash
dpkg -l | grep nvidia-jetpack
```

**匹配DeepStream版本**:
- JetPack 6.x → DeepStream 7.x
- JetPack 5.x → DeepStream 6.x

### Q2: Python绑定编译失败

**确保依赖完整**:
```bash
sudo apt install python3-gi python3-dev cmake g++
```

### Q3: Pipeline报错

**检查配置文件路径**:
- TensorRT引擎路径
- labels.txt路径
- 跟踪器配置路径

---

## 📚 学习资源

### 官方文档

- [DeepStream SDK文档](https://docs.nvidia.com/metropolis/deepstream/)
- [DeepStream Python参考](https://docs.nvidia.com/metropolis/deepstream/python-api/)
- [GStreamer教程](https://gstreamer.freedesktop.org/documentation/tutorials/)

### 示例代码

```bash
# DeepStream官方示例
cd /opt/nvidia/deepstream/deepstream/sources/apps/sample_apps

# Python示例
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps
```

###社区

- [NVIDIA DeepStream论坛](https://forums.developer.nvidia.com/c/accelerated-computing/intelligent-video-analytics/deepstream-sdk/)

---

## 🎯 开发时间线

### Day 1: 环境搭建
- ✓ DeepStream安装
- ✓ Python绑定配置
- ✓ TensorRT引擎准备

### Day 2: 基础功能
- Pipeline构建
- YOLOv11推理
- 基本显示

### Day 3: 高级功能
- NvDCF跟踪集成
- HyperLPR集成
- 统计功能

### Day 4: 测试优化
- 性能测试
- 参数调优
- 文档完善

---

## 🚀 立即开始

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 1. 环境检查
bash scripts/check_deepstream.sh

# 2. 如果未安装，运行安装
sudo bash scripts/install_deepstream.sh

# 3. 准备TensorRT
bash scripts/prepare_tensorrt.sh

# 4. 开始开发！
```

---

**版本**: 1.0  
**预计完成**: 2-3天  
**最终性能**: 50-100 FPS (GPU)


