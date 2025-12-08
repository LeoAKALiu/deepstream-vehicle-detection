# DeepStream开发指南

## 🚀 快速开始

### 1. 进入DeepStream容器（交互模式）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash
```

### 2. 在容器内检查环境

```bash
# 检查文件
ls -lh models/yolov11.engine
ls config/config_infer_yolov11.txt
ls python_apps/deepstream_vehicle_detection.py

# 检查pyds
python3 -c "import pyds; print('pyds版本:', pyds.__version__)"

# 检查GStreamer插件
gst-inspect-1.0 nvstreammux
gst-inspect-1.0 nvinfer
gst-inspect-1.0 nvtracker
```

### 3. 测试最简pipeline（不运行Python）

```bash
# 测试基础推理
gst-launch-1.0 \
    filesrc location=/workspace/20211216-101333.mp4 ! \
    h264parse ! \
    nvv4l2decoder ! \
    nvstreammux width=1920 height=1080 batch-size=1 batched-push-timeout=4000000 ! \
    nvinfer config-file-path=config/config_infer_yolov11.txt ! \
    nvvideoconvert ! \
    nvdsosd ! \
    nvegltransform ! \
    nveglglessink
```

### 4. 运行Python应用

```bash
python3 python_apps/deepstream_vehicle_detection.py /workspace/20211216-101333.mp4
```

---

## 🔧 调试技巧

### 调试1：查看DeepStream日志

设置环境变量以启用详细日志：

```bash
export GST_DEBUG=3
export NVDS_LOG_LEVEL=5

python3 python_apps/deepstream_vehicle_detection.py /workspace/20211216-101333.mp4
```

### 调试2：测试TensorRT引擎

```bash
/usr/src/tensorrt/bin/trtexec \
    --loadEngine=models/yolov11.engine \
    --verbose
```

### 调试3：查看DeepStream示例

```bash
# 查看所有示例
ls /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/

# 运行test1示例（使用自己的模型）
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/deepstream-test1/
python3 deepstream_test_1.py /workspace/20211216-101333.mp4
```

### 调试4：检查配置文件语法

```bash
# nvinfer配置文件验证
cat config/config_infer_yolov11.txt

# 检查引擎文件路径
ls -la $(cat config/config_infer_yolov11.txt | grep model-engine-file | cut -d= -f2)
```

---

## 🎯 当前已知问题

### 问题1：YOLO输出解析

**现状**：
- YOLOv11输出：`[1, 14, 8400]`
- DeepStream期望：bbox坐标 + 类别概率

**解决方案（3选1）**：

#### 方案A：使用DeepStream内置解析器（最简单）

修改`config/config_infer_yolov11.txt`：
```ini
parse-bbox-func-name=NvDsInferParseYolo
```

可能有效，取决于YOLOv11格式是否兼容。

#### 方案B：自定义C++解析器

需要编写`nvdsinfer_custom_impl_yolo.cpp`：
```cpp
extern "C" bool NvDsInferParseYolo(
    std::vector<NvDsInferLayerInfo> const& outputLayersInfo,
    NvDsInferNetworkInfo const& networkInfo,
    NvDsInferParseDetectionParams const& detectionParams,
    std::vector<NvDsInferObjectDetectionInfo>& objectList)
{
    // 解析YOLOv11输出 [1, 14, 8400]
    // 转换为objectList
    return true;
}
```

编译：
```bash
g++ -shared -fPIC -o libnvdsinfer_custom_yolo.so \
    nvdsinfer_custom_impl_yolo.cpp \
    -I/opt/nvidia/deepstream/deepstream/sources/includes \
    -L/opt/nvidia/deepstream/deepstream/lib \
    -lnvdsinfer
```

#### 方案C：使用自定义模型后处理（Python）

在probe函数中直接访问TensorRT输出张量，Python后处理。

---

### 问题2：pyds可能不可用

**现象**：`ImportError: No module named 'pyds'`

**解决方案**：

在容器内安装：
```bash
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/bindings/
pip3 install ./
```

或使用系统路径：
```bash
export PYTHONPATH=/opt/nvidia/deepstream/deepstream/lib:$PYTHONPATH
```

---

### 问题3：配置文件路径

**现象**：找不到配置文件

**原因**：相对路径`../config/config_infer_yolov11.txt`

**解决方案**：

使用绝对路径：
```python
pgie.set_property('config-file-path', 
    '/workspace/deepstream-vehicle-detection/config/config_infer_yolov11.txt')
```

---

## 📝 开发检查清单

### 阶段1：基础pipeline运行 ✓

- [x] TensorRT引擎生成
- [x] 配置文件准备
- [ ] Pipeline能启动
- [ ] 能看到视频输出
- [ ] 没有GStreamer错误

### 阶段2：检测输出

- [ ] nvinfer能加载引擎
- [ ] 有检测框输出
- [ ] 类别正确
- [ ] 置信度合理

### 阶段3：跟踪功能

- [ ] nvtracker能运行
- [ ] 跟踪ID稳定
- [ ] 不会重复计数

### 阶段4：统计和输出

- [ ] probe函数能访问metadata
- [ ] 车辆计数正确
- [ ] 统计输出完整

---

## 🔬 实验性功能

### HyperLPR集成（未完成）

在容器内安装：
```bash
pip3 install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple hyperlpr3
```

需要：
1. 在probe函数中访问图像数据（`NvBufSurface`）
2. 裁剪车辆ROI
3. 调用HyperLPR识别
4. 关联结果到跟踪ID

这是DeepStream最复杂的部分，涉及：
- GPU-CPU内存拷贝
- 图像格式转换（NV12 → RGB）
- Python-C互操作

**建议**：先完成检测和跟踪，车牌识别可以后续添加或使用CPU方案。

---

## 📊 性能优化建议

### 优化1：调整batch-size

如果有多个视频流：
```ini
# config/config_infer_yolov11.txt
batch-size=4  # 同时处理4帧
```

### 优化2：降低分辨率

```python
streammux.set_property('width', 1280)   # 从1920降低
streammux.set_property('height', 720)   # 从1080降低
```

### 优化3：跳帧检测

```ini
# 每隔N帧检测一次
interval=2  # 每3帧检测1次
```

### 优化4：INT8量化

重新生成INT8引擎（需要校准数据集）：
```bash
/usr/src/tensorrt/bin/trtexec \
    --onnx=best.onnx \
    --saveEngine=yolov11_int8.engine \
    --int8 \
    --calib=/path/to/calibration/data
```

---

## 💡 快速故障排除

### 错误1：`Could not load library 'libnvinfer.so'`

→ 确保在DeepStream容器中运行

### 错误2：`No such element 'nvstreammux'`

→ 检查GStreamer插件：`gst-inspect-1.0 nvstreammux`

### 错误3：`Failed to create engine`

→ 检查引擎文件路径和权限

### 错误4：`Segmentation fault`

→ 通常是pyds版本不匹配或metadata访问错误

### 错误5：Pipeline卡住不动

→ 检查`batched-push-timeout`参数，增大超时时间

---

## 📚 参考资源

### 官方文档

- **DeepStream SDK**: https://docs.nvidia.com/metropolis/deepstream/dev-guide/
- **Python Bindings**: https://github.com/NVIDIA-AI-IOT/deepstream_python_apps
- **Plugin Manual**: https://docs.nvidia.com/metropolis/deepstream/plugin-manual/

### 示例代码

- **容器内路径**: `/opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/`
- **GitHub**: https://github.com/NVIDIA-AI-IOT/deepstream_python_apps

### 论坛

- **NVIDIA Developer Forum**: https://forums.developer.nvidia.com/c/accelerated-computing/intelligent-video-analytics/deepstream-sdk/

---

## ⏭️ 下一步

1. **立即测试**：运行`bash 测试DeepStream应用.sh`
2. **查看日志**：观察GStreamer和DeepStream输出
3. **逐步调试**：从基础pipeline开始
4. **参考示例**：对比官方示例代码

如果遇到问题，记录完整错误信息并参考故障排除部分。

祝开发顺利！🚀

