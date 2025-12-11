# DeepStream开发 - 今日成果与明日计划

## ✅ 今日成果（10月27日）

### 环境准备完成

1. ✅ **系统全面诊断**
   - 发现DNS解析不稳定问题
   - 修复DNS配置
   - 确认网络可直接访问NVIDIA服务器

2. ✅ **DeepStream容器成功拉取**
   - `nvcr.io/nvidia/deepstream:7.0-triton-multiarch`
   - 大小：~7GB
   - 包含完整DeepStream SDK

3. ✅ **TensorRT引擎准备完成**
   - 文件：`models/yolov11.engine`
   - 大小：54MB (FP16)
   - 构建时间：15分钟
   - 基于：`best.onnx` (97MB)

4. ✅ **项目结构清理**
   - 归档33个失败/诊断脚本
   - deepstream-vehicle-detection/目录就绪
   - 配置文件已准备

### 耗时统计

| 任务 | 耗时 |
|------|------|
| GPU方案尝试（PyTorch、容器） | ~5小时 |
| 系统诊断和DNS修复 | ~1小时 |
| DeepStream容器拉取 | ~30分钟 |
| TensorRT引擎准备 | ~30分钟 |
| **总计** | **~7小时** |

---

## 📋 明日开发计划（Day 2）

### 阶段2：开发DeepStream Python应用（6-8小时）

#### 任务2.1：配置YOLOv11推理插件（2小时）

**文件**：`config/config_infer_yolov11.txt`

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

# YOLO特定配置
parse-bbox-func-name=NvDsInferParseYolo
# 或需要自定义解析器
```

**需要研究**：
- YOLOv11输出格式（1x14x8400）
- DeepStream如何解析YOLO输出
- 可能需要自定义C++解析器

---

#### 任务2.2：完善Python应用框架（4-6小时）

**文件**：`python_apps/deepstream_vehicle_detection.py`

**核心功能**：

1. **GStreamer Pipeline构建**
   ```python
   # 视频源 -> 解码器 -> Streammux -> nvinfer -> nvtracker -> OSD -> Sink
   ```

2. **Probe函数实现**
   - 访问检测结果（bbox, class_id, confidence）
   - 访问跟踪ID（object_id）
   - 车辆分类和计数
   - 统计数据更新

3. **HyperLPR集成**（可选，Day 3）
   - ROI提取
   - 车牌识别
   - 结果关联

---

### 阶段3：测试和调试（2-3小时）

#### 测试项目

1. **基础pipeline测试**
   ```bash
   python3 python_apps/deepstream_vehicle_detection.py /workspace/20211216-101333.mp4
   ```

2. **性能测试**
   - 目标：50-100 FPS
   - GPU使用率
   - 内存占用

3. **准确度验证**
   - 检测率
   - 跟踪稳定性
   - 计数准确性

---

## 🎯 关键挑战

### 挑战1：YOLO输出解析

**YOLOv11输出**：`[1, 14, 8400]`
- 14个通道：可能是 [x, y, w, h, conf, class0...class9]
- 8400个候选框：3个尺度 (80x80 + 40x40 + 20x20) × 3 anchors

**DeepStream需要**：
- 自定义解析器（C++或Python）
- 转换为DeepStream bbox格式

### 挑战2：NvDCF跟踪器配置

**需要调整**：
- 跟踪参数（匹配阈值、最大跟踪时间）
- 适配车辆场景
- 处理遮挡和离开/进入

### 挑战3：pyds Python绑定

**可能需要**：
- 在容器中安装pyds
- 或使用DeepStream Python示例作为参考

---

## 💡 明日开发建议

### 方案A：在DeepStream容器中开发（推荐）

**优势**：
- 完整的DeepStream环境
- 所有依赖都已配置
- pyds Python绑定可用

**启动方式**：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash 启动DeepStream容器.sh
# 选择1：交互式Shell
```

**在容器内**：
```bash
cd /workspace/deepstream-vehicle-detection

# 安装HyperLPR（从清华源）
pip3 install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple hyperlpr3

# 开发和测试
python3 python_apps/deepstream_vehicle_detection.py /workspace/20211216-101333.mp4
```

---

### 方案B：参考DeepStream Python示例

**容器中的示例路径**：
```
/opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/
```

**关键示例**：
- `deepstream-test1/` - 基础检测
- `deepstream-test2/` - 多流检测
- `deepstream-test3/` - 多模型推理
- `deepstream-imagedata-multistream/` - 图像访问

**学习重点**：
- Pipeline构建模式
- Probe函数实现
- Metadata访问方式

---

## 📊 时间评估

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| **Day 2** | 配置推理插件 | 2小时 |
| | Python应用开发 | 4-6小时 |
| | 基础测试 | 1-2小时 |
| **Day 3** | HyperLPR集成 | 4小时 |
| | 完整测试 | 2小时 |
| | 性能优化 | 2小时 |
| **总计** | | **15-18小时** |

---

## 🔄 与CPU方案对比

### 当前CPU方案（已稳定运行）

| 功能 | 性能 | 状态 |
|------|------|------|
| 实时检测 | 25-35 FPS | ✅ 满足需求 |
| 视频分析 | 0.4 FPS | ⚠️ 慢，可夜间批处理 |
| 跟踪计数 | ByteTrack | ✅ 唯一ID |
| 车牌识别 | HyperLPR | ✅ 可用 |

### DeepStream方案（开发中）

| 功能 | 预期性能 | 状态 |
|------|---------|------|
| 实时检测 | 50-100 FPS | 🔧 开发中 |
| 视频分析 | 50-100 FPS | 🔧 开发中 |
| 跟踪计数 | NvDCF | 🔧 开发中 |
| 车牌识别 | HyperLPR | 🔧 待集成 |

**投入**：
- 已用：7小时
- 还需：15-18小时
- 总计：22-25小时（3天）

---

## 💭 决策建议

### 如果追求快速上线

→ **使用CPU方案**
- 实时检测已满足需求（25-35 FPS）
- 立即可用
- 节省3天开发时间

### 如果追求极致性能

→ **继续DeepStream开发**
- 最终50-100 FPS
- 需要1-2天
- 学习曲线陡峭

---

## ⏭️ 明日第一步

### 进入DeepStream容器

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch
```

### 在容器内

```bash
# 1. 查看DeepStream示例
ls /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/

# 2. 安装HyperLPR
pip3 install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple hyperlpr3

# 3. 开始开发
python3 python_apps/deepstream_vehicle_detection.py
```

---

**今日工作已完成！** 明天可以继续DeepStream应用开发。


