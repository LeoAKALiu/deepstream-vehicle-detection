# 在Jetson上直接运行混合方案

## ✅ 环境已就绪

### 宿主机环境
```
✓ TensorRT: 10.3.0
✓ PyCUDA: 已安装
✓ OpenCV: 4.11.0
✓ NumPy: 1.26.1
✓ GPU: Orin (8.7计算能力, 7.4GB内存)
```

### TensorRT引擎
```
✓ 文件: models/yolov11_host.engine
✓ 大小: 52MB
✓ 精度: FP16
✓ 性能: 48 FPS (单推理)
✓ 延迟: ~21ms
```

---

## 🚀 运行命令

### 基础运行

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine
```

### 保存输出视频

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --output output.mp4
```

### 使用摄像头

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    camera \
    --engine models/yolov11_host.engine
```

---

## 📊 预期输出

### 终端输出

```
======================================================================
TensorRT车辆检测系统（混合方案）
======================================================================
GPU: TensorRT推理
CPU: YOLO后处理、跟踪、车牌识别
======================================================================

加载TensorRT引擎: models/yolov11_host.engine
  输入: images [1, 3, 640, 640]
  输出: output0 [1, 14, 8400]
✓ TensorRT引擎初始化完成

视频信息:
  分辨率: 1920x1080
  帧率: 30.00 FPS
  总帧数: 3000

开始处理...
  已处理 100/3000 帧, 平均 65.3 FPS, 用时 1.5s
  已处理 200/3000 帧, 平均 68.1 FPS, 用时 2.9s
  ...
```

### 窗口显示

- 实时视频画面
- 检测框（绿色=工程车辆，蓝色=社会车辆）
- 车辆类型标签和置信度
- 左上角实时FPS显示

### 操作

- 按 `q` 键退出
- Ctrl+C 强制停止

---

## 📊 性能预期

| 指标 | 值 |
|------|-----|
| **FPS** | 50-80 (含后处理) |
| **GPU使用率** | 85-95% |
| **GPU延迟** | ~20ms |
| **总延迟** | ~30-40ms (含视频I/O和后处理) |
| **内存占用** | ~2GB GPU, ~500MB CPU |

---

## 🎯 测试检查清单

运行后检查：

- [ ] 程序正常启动
- [ ] TensorRT引擎成功加载
- [ ] 视频窗口显示
- [ ] 能看到检测框
- [ ] 检测类别正确
- [ ] FPS达到50+
- [ ] 没有崩溃或错误
- [ ] 统计信息正确输出

---

## 🐛 可能的问题

### 问题1：初始化失败

检查TensorRT引擎是否正确：
```bash
ls -lh models/yolov11_host.engine
```

### 问题2：FPS很低

可能原因和解决：
- 显示窗口拖慢 → 使用--output保存到文件
- 视频I/O慢 → 使用SSD存储
- 后处理慢 → 降低conf_threshold

### 问题3：内存不足

减小分辨率或关闭其他GPU程序

---

## 🔧 性能优化

### 优化1：降低置信度阈值

编辑代码第188行附近：
```python
def postprocess(self, output, ratio, pad, conf_threshold=0.3, ...  # 从0.5降到0.3
```

### 优化2：跳帧处理

在process_video函数中添加：
```python
if frame_count % 2 == 0:  # 每2帧处理1次
    continue
```

### 优化3：禁用绘制加速

```python
# 注释掉draw_results调用
# self.draw_results(frame, detections)
```

---

## 📈 预期结果

如果一切正常，你应该看到：

**终端**：
```
✓ TensorRT引擎初始化完成
已处理 100/3000 帧, 平均 65.3 FPS
已处理 200/3000 帧, 平均 68.1 FPS
...

TensorRT检测统计
【工程车辆】
  总数: 15 辆
  挖掘机: 5 辆 (33.3%)
  装载机: 3 辆 (20.0%)
  自卸车: 7 辆 (46.7%)
```

**窗口**：
- 实时视频
- 绿色框标注工程车辆
- 蓝色框标注社会车辆
- FPS: 60-80

---

## 🎉 成功标志

- ✅ FPS > 50
- ✅ GPU使用率 > 80%
- ✅ 检测准确
- ✅ 无崩溃

---

**准备好了！直接在Jetson上运行上面的命令！** 🚀

