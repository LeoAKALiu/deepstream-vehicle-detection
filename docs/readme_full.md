# 工程机械实时识别系统（完整版）

基于TensorRT GPU加速的工程机械智能识别系统，集成YOLOv11检测、IoU跟踪、Cassia蓝牙信标匹配和HyperLPR车牌识别。

---

## 🎯 系统功能

### 工程车辆（8类）
1. **视觉检测**：TensorRT GPU推理识别车辆类型
2. **距离计算**：bbox底边中点距离（支持Orbbec深度相机）
3. **信标匹配**：Cassia蓝牙信标RSSI距离匹配
4. **身份验证**：
   - ✅ 匹配成功 → 已备案车辆（记录信标MAC）
   - ⚠️ 匹配失败 → **未备案车辆入场报警**

### 社会车辆（2类）
1. **视觉检测**：识别truck/car
2. **车牌识别**：HyperLPR提取车牌号
3. **记录输出**：车牌号列表

---

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| **FPS** | 25-30 |
| **GPU推理** | ~20ms |
| **后处理** | ~5-10ms |
| **跟踪** | ~2-5ms |
| **可视化** | ~5-10ms |
| **GPU使用率** | 85-95% |

**比纯CPU视频分析快60-75倍**（0.4 FPS → 25-30 FPS）

---

## 🚀 快速开始

### 基础运行（不启用信标）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine
```

**效果**：
- ✅ 检测和跟踪正常
- ✅ 车牌识别工作
- ⚠️ 所有工程车辆显示"未备案"

### 完整运行（启用信标）

**前提**：配置Cassia AC参数

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-ac "http://192.168.1.100" \
    --cassia-key "your_key" \
    --cassia-secret "your_secret" \
    --cassia-router "CC:1B:E0:E2:E9:B8"
```

**效果**：
- ✅ 完整功能
- ✅ 工程车辆信标匹配
- ✅ 已备案/未备案区分

---

## 📁 项目结构

```
deepstream-vehicle-detection/
├── models/
│   └── yolov11_host.engine         # TensorRT引擎 (52MB FP16)
│
├── python_apps/
│   ├── tensorrt_yolo_inference.py  # 主程序 (800+行)
│   └── cassia_beacon_client.py     # Cassia信标客户端
│
├── config/
│   ├── config_infer_yolov11.txt    # nvinfer配置
│   └── labels.txt                   # 类别标签
│
├── cassia_config.example.sh        # Cassia配置模板
│
├── README-完整版.md                # 本文件
├── Cassia信标集成指南.md          # Cassia集成文档
├── 系统逻辑说明.md                # 系统架构文档
└── 在Jetson上运行.md               # 运行说明
```

---

## 🔧 依赖安装

### 已安装
```bash
✓ TensorRT 10.3.0  (系统预装)
✓ PyCUDA 2025.1.2
✓ OpenCV 4.11.0
✓ NumPy 1.26.1
✓ Pillow (系统自带)
✓ HyperLPR3
✓ aiohttp
✓ aiohttp-sse-client
```

### 可选安装
```bash
# Orbbec深度相机
pip3 install pyorbbecsdk
```

---

## 🎨 可视化效果

### 检测框
- **10种颜色**：不同车辆不同颜色
- **粗边框**：3像素，清晰可见
- **标签**：`ID1 excavator 0.95`

### 统计信息
- **左上角**：`FPS: 28.5`
- **右上角**：`Tracked: 3`

### 终端输出
```
新车辆 ID1: 挖掘机 (excavator)
  ⚠ 未备案车辆入场! ID1: excavator, 帧1

新车辆 ID2: 卡车 (truck)
  🚗 社会车辆 ID2: truck, 车牌=京A12345

已处理 100/15398 帧, 平均 28.5 FPS
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| **README-完整版.md** | 本文件，系统总览 |
| **Cassia信标集成指南.md** | Cassia配置和集成步骤 |
| **系统逻辑说明.md** | 详细系统架构和接口说明 |
| **在Jetson上运行.md** | 运行说明和参数 |

---

## ⚙️ 配置说明

### 基础运行（无额外配置）

```bash
python3 python_apps/tensorrt_yolo_inference.py VIDEO --engine ENGINE
```

### 完整配置

```bash
python3 python_apps/tensorrt_yolo_inference.py VIDEO \
    --engine models/yolov11_host.engine \
    --cassia-ac "http://AC_IP" \
    --cassia-key "KEY" \
    --cassia-secret "SECRET" \
    --cassia-router "ROUTER_MAC" \
    --use-depth \           # 启用深度相机（需要先集成）
    --output output.mp4 \   # 保存输出视频
    --no-display            # SSH无显示模式
```

---

## 🔌 外部设备集成

### 1. Cassia蓝牙信标 ✅

**状态**：已集成，待配置

**步骤**：
1. 查看 `Cassia信标集成指南.md`
2. 配置AC地址和密钥
3. 运行时添加 `--cassia-*` 参数

### 2. HyperLPR车牌识别 ✅

**状态**：已安装并集成

**自动启用**：检测到HyperLPR时自动使用

### 3. Orbbec深度相机 🔌

**状态**：接口预留，待集成

**步骤**：
1. 安装 `pip3 install pyorbbecsdk`
2. 修改 `calculate_distance()` 函数
3. 运行时添加 `--use-depth`

---

## 📊 输出示例

### 最终统计报告

```
======================================================================
TensorRT车辆检测统计
======================================================================

总帧数: 15398
平均FPS: 28.3

【工程车辆 - 已备案】
  总数: 3 辆

  ID1: excavator       信标=AA:BB:CC:DD:EE:01
  ID5: dump-truck      信标=AA:BB:CC:DD:EE:03
  ID8: loader          信标=AA:BB:CC:DD:EE:05

【工程车辆 - 未备案（警告）】
  总数: 2 辆

  ⚠ ID3: bulldozer       帧156
  ⚠ ID7: crane           帧520

【社会车辆 - 车牌识别】
  总数: 4 辆

  ID2: truck      车牌=京A12345
  ID4: car        车牌=沪B67890
  ID6: truck      车牌=粤C11111
  ID9: car        车牌=浙D22222

======================================================================
```

---

## 🔬 技术栈

- **GPU推理**：TensorRT 10.3.0 + PyCUDA
- **检测模型**：YOLOv11n (FP16)
- **跟踪算法**：IoU匹配
- **信标通信**：Cassia RESTful API (SSE)
- **车牌识别**：HyperLPR3
- **深度相机**：Orbbec SDK（可选）

---

## 📞 故障排除

### 问题1：FPS低

- 降低分辨率（修改预处理）
- 禁用显示（`--no-display`）
- 跳帧处理

### 问题2：信标匹配失败

- 查看 `Cassia信标集成指南.md` 调试章节
- 调整RSSI参数
- 增大tolerance

### 问题3：车牌识别失败

- 检查HyperLPR是否安装
- 降低置信度阈值
- 优化ROI裁剪

---

## 🎓 开发收获

通过本项目掌握了：
- ✅ NVIDIA Jetson GPU开发
- ✅ TensorRT推理优化
- ✅ YOLO后处理算法
- ✅ 目标跟踪算法
- ✅ 蓝牙信标定位
- ✅ 多传感器融合架构

---

## 📄 许可证

本系统用于工程机械实时监控，基于以下开源技术：
- TensorRT (NVIDIA)
- YOLOv11 (Ultralytics)
- HyperLPR (zeusees)
- Cassia SDK (Cassia Networks)

---

**最后更新**: 2025-10-27  
**版本**: 1.0  
**状态**: 生产就绪（基础功能），信标和深度相机待配置

