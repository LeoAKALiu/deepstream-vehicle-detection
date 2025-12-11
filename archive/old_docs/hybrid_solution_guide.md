# 混合方案说明

## 🎯 方案C：TensorRT GPU推理 + Python CPU后处理

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    输入视频流                            │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  视频解码 (CPU)     │
         │  OpenCV            │
         └────────┬───────────┘
                  │ BGR图像
                  ▼
         ┌────────────────────┐
         │  预处理 (CPU)       │
         │  - Resize          │
         │  - Padding         │
         │  - Normalize       │
         └────────┬───────────┘
                  │
                  ▼
    ╔═══════════════════════════╗
    ║  TensorRT推理 (GPU) ⚡     ║
    ║  - YOLOv11引擎            ║
    ║  - FP16精度               ║
    ║  - 输出: [1,14,8400]      ║
    ╚═══════════╦═══════════════╝
                ║
                ▼
         ┌────────────────────┐
         │  后处理 (CPU)       │
         │  - YOLO输出解析    │
         │  - NMS             │
         │  - 坐标还原        │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  跟踪 (CPU)         │
         │  ByteTrack/简单IoU │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  车牌识别 (CPU)     │
         │  HyperLPR (可选)   │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  结果绘制和显示     │
         └────────────────────┘
```

---

## ✅ 优势

### 1. 性能优势
- **GPU推理**：TensorRT FP16加速
- **预期FPS**：50-100 FPS（取决于硬件）
- **比纯CPU快**：5-10倍

### 2. 开发优势
- **纯Python**：易于开发和维护
- **无需pyds**：避开DeepStream Python绑定问题
- **无需C++**：不需要编写自定义解析器

### 3. 灵活性优势
- **易于调试**：Python代码易读
- **易于扩展**：添加新功能简单
- **易于集成**：可以集成任何Python库

---

## 📦 依赖

### 必需
- `tensorrt` ✓ (容器已包含)
- `pycuda` (需要安装)
- `opencv-python`
- `numpy`

### 可选
- `byte_tracker` (更好的跟踪)
- `hyperlpr3` (车牌识别)

---

## 🚀 使用方法

### 1. 快速测试

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
chmod +x 测试混合方案.sh
bash 测试混合方案.sh
```

脚本会自动：
- 启动DeepStream容器
- 安装缺失的依赖
- 运行推理程序

### 2. 手动运行

```bash
# 进入容器
sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash

# 在容器内
pip3 install pycuda opencv-python

# 运行
python3 python_apps/tensorrt_yolo_inference.py \
    /workspace/20211216-101333.mp4 \
    --engine models/yolov11.engine \
    --output output.mp4  # 可选
```

### 3. 参数说明

```bash
python3 python_apps/tensorrt_yolo_inference.py <video> [options]

参数:
  video              输入视频文件路径或'camera'
  --engine PATH      TensorRT引擎路径 (默认: models/yolov11.engine)
  --output PATH      输出视频路径 (可选)
```

---

## 📊 性能预期

### Jetson Orin

| 分辨率 | 预期FPS | GPU使用 | 备注 |
|--------|---------|---------|------|
| 1920x1080 | 50-80 | 85-95% | 推荐 |
| 1280x720 | 80-120 | 80-90% | 更快 |
| 640x480 | 100-150 | 70-80% | 最快 |

### 性能瓶颈

1. **GPU推理**：最快（TensorRT优化）
2. **CPU后处理**：较快（NumPy优化）
3. **视频I/O**：可能成为瓶颈

### 优化建议

1. **降低分辨率**
   ```python
   # 在 TensorRTInference.__init__() 中
   input_shape=(416, 416)  # 从640x640降低
   ```

2. **跳帧处理**
   ```python
   # 每N帧处理一次
   if frame_count % 2 == 0:
       continue
   ```

3. **禁用显示**
   ```python
   # 注释掉 cv2.imshow()
   # 只保存到文件
   ```

---

## 🔧 技术细节

### 1. YOLOv11输出格式

```
输出: [1, 14, 8400]
  - 1: batch size
  - 14: [x, y, w, h, objectness, class0, ..., class9]
  - 8400: 候选框数量 (80²/4 + 40²/4 + 20²/4)
```

### 2. 后处理流程

```python
1. 转置: [14, 8400] -> [8400, 14]
2. 提取: boxes[8400,4], objectness[8400,1], probs[8400,10]
3. 计算: scores = objectness * probs
4. 过滤: confidence > threshold
5. NMS: 去除重叠框
6. 还原: 坐标映射回原图
```

### 3. 内存管理

- **GPU内存**：~2GB (引擎 + 输入/输出缓冲)
- **CPU内存**：~500MB (视频缓冲 + NumPy数组)
- **总计**：~2.5GB

---

## 🐛 故障排除

### 问题1：PyCUDA导入失败

```bash
# 错误
ImportError: No module named 'pycuda'

# 解决
pip3 install pycuda
```

### 问题2：CUDA OOM

```
RuntimeError: out of memory

解决方案:
1. 降低分辨率 (640->416)
2. 减小batch size (已经是1)
3. 重启容器释放GPU内存
```

### 问题3：FPS很低

```
可能原因:
1. 显示窗口拖慢速度 → 禁用cv2.imshow()
2. 视频I/O瓶颈 → 使用SSD存储
3. CPU后处理慢 → 优化NumPy代码或降低分辨率
```

### 问题4：TensorRT引擎加载失败

```bash
# 错误
Failed to deserialize engine

# 原因
引擎是在x86平台生成的，不能在ARM平台使用

# 解决
在Jetson上重新生成引擎（已完成）
```

---

## 🔄 与其他方案对比

### 纯CPU方案（当前使用）

| 指标 | 性能 | 开发 |
|------|------|------|
| 实时检测 | 25-35 FPS | ✅ 完成 |
| 视频分析 | 0.4 FPS | ✅ 完成 |
| 开发难度 | 简单 | - |
| 维护成本 | 低 | - |

### 混合方案（方案C）

| 指标 | 性能 | 开发 |
|------|------|------|
| 实时检测 | 50-100 FPS | 🔧 进行中 |
| 视频分析 | 50-100 FPS | 🔧 进行中 |
| 开发难度 | 中等 | - |
| 维护成本 | 中等 | - |

### 纯DeepStream方案（方案A）

| 指标 | 性能 | 开发 |
|------|------|------|
| 实时检测 | 100-150 FPS | ❌ 需要C++ |
| 视频分析 | 100-150 FPS | ❌ 需要C++ |
| 开发难度 | 困难 | - |
| 维护成本 | 高 | - |

---

## 💡 下一步

### 立即测试

```bash
bash 测试混合方案.sh
```

### 如果成功

1. 集成ByteTrack提升跟踪效果
2. 添加HyperLPR车牌识别
3. 优化性能（跳帧、降分辨率）
4. 部署到生产环境

### 如果失败

1. 查看错误信息
2. 检查依赖是否安装
3. 验证TensorRT引擎是否正常
4. 回退到CPU方案

---

## 📚 参考资料

- **TensorRT Python API**: https://docs.nvidia.com/deeplearning/tensorrt/api/python_api/
- **PyCUDA文档**: https://documen.tician.de/pycuda/
- **YOLOv11**: https://docs.ultralytics.com/models/yolov11/

---

**混合方案：平衡性能、开发效率和维护成本的最佳选择！** 🚀

