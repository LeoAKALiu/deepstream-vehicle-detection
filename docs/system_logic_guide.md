# 工程机械实时识别系统 - 逻辑说明

## 🎯 系统目标

### 工程车辆
**检测 → 距离计算 → 信标匹配 → 身份验证**

1. 检测到工程车辆
2. 通过Orbbec深度相机计算距离（bbox底边中点）
3. 请求蓝牙信标路由器数据
4. 根据信号强度计算信标距离
5. 匹配视觉距离和信标距离
6. 读取信标MAC地址确认车辆身份
7. **如果匹配失败** → 通知"未备案车辆入场"

### 社会车辆  
**检测 → 车牌识别**

1. 检测到社会车辆（truck/car）
2. 使用HyperLPR识别车牌
3. 记录车牌号

---

## 📋 当前实现状态

### ✅ 已实现

1. **TensorRT GPU推理**
   - YOLOv11检测（10类车辆）
   - FP16精度，~48 FPS
   - 输出：检测框 + 类别 + 置信度

2. **IoU跟踪算法**
   - 基于交并比的目标跟踪
   - 唯一ID分配
   - 避免重复处理同一车辆

3. **车牌识别接口**
   - HyperLPR集成（需安装）
   - ROI裁剪
   - 置信度阈值0.7

4. **可视化**
   - 10种车辆不同颜色
   - ID + 类型 + 置信度显示
   - FPS和跟踪数量实时显示

### 🔧 待接入

1. **Orbbec深度相机** → `calculate_distance()` 函数
2. **蓝牙信标路由器** → `match_beacon()` 函数

---

## 🔌 接口说明

### 1. 距离计算接口

**函数**：`calculate_distance(bbox, frame_shape)`

**当前实现**：
```python
# 简单估计：基于bbox高度
bbox_height = y2 - y1
estimated_distance = 1000 / max(bbox_height, 1)
```

**TODO - 接入Orbbec深度相机**：
```python
def calculate_distance(self, bbox, frame_shape, depth_frame=None):
    """
    计算车辆到相机的距离
    Args:
        bbox: [x1, y1, x2, y2]
        frame_shape: RGB帧shape
        depth_frame: Orbbec深度帧（可选）
    Returns:
        distance: 实际距离（米）
        bottom_center: bbox底边中点坐标 (x, y)
    """
    x1, y1, x2, y2 = bbox
    bottom_center_x = int((x1 + x2) / 2)
    bottom_center_y = int(y2)
    
    if depth_frame is not None:
        # 从深度帧读取距离
        # 注意：RGB和深度帧可能需要对齐
        depth_value = depth_frame[bottom_center_y, bottom_center_x]
        distance = depth_value / 1000.0  # 毫米转米
    else:
        # 备用：基于bbox高度估计
        bbox_height = y2 - y1
        distance = 1000 / max(bbox_height, 1)
    
    return distance, (bottom_center_x, bottom_center_y)
```

**Orbbec相机集成步骤**：
1. 安装Orbbec SDK（pyorbbecsdk）
2. 同步RGB和Depth流
3. 对齐RGB和Depth帧
4. 传入depth_frame参数

---

### 2. 信标匹配接口

**函数**：`match_beacon(distance, class_id)`

**当前实现**：
```python
# 暂时返回None（所有车辆都会报"未备案"）
return None
```

**TODO - 接入蓝牙信标路由器**：
```python
def match_beacon(self, distance, class_id):
    """
    匹配蓝牙信标
    Args:
        distance: 视觉估计距离（米）
        class_id: 车辆类别
    Returns:
        beacon_id: 信标MAC地址，否则None
    """
    # 1. 请求路由器API
    beacons = self.get_beacon_data()  # 返回 [{mac, rssi}, ...]
    
    # 2. 根据RSSI计算距离
    candidates = []
    for beacon in beacons:
        beacon_distance = self.rssi_to_distance(beacon['rssi'])
        distance_diff = abs(beacon_distance - distance)
        
        if distance_diff < 2.0:  # 距离差小于2米
            candidates.append({
                'mac': beacon['mac'],
                'distance_diff': distance_diff
            })
    
    # 3. 返回最接近的信标
    if candidates:
        best = min(candidates, key=lambda x: x['distance_diff'])
        return best['mac']
    
    return None

def get_beacon_data(self):
    """从蓝牙路由器获取数据"""
    # TODO: HTTP/MQTT请求路由器API
    # 示例: requests.get('http://router-ip/api/beacons')
    return []

def rssi_to_distance(self, rssi):
    """RSSI转距离（自由空间传播模型）"""
    # d = 10^((TxPower - RSSI) / (10 * n))
    # n = 路径衰减指数（室外约2-3）
    tx_power = -59  # 信标发射功率（需实测）
    n = 2.5
    distance = 10 ** ((tx_power - rssi) / (10 * n))
    return distance
```

**蓝牙信标集成步骤**：
1. 确定路由器API地址
2. 实现HTTP/MQTT客户端
3. 解析信标数据
4. 实现RSSI转距离公式
5. 调整距离匹配阈值

---

### 3. 车牌识别接口

**函数**：`recognize_plate(frame, bbox)`

**当前实现**：
```python
# 使用HyperLPR识别ROI中的车牌
roi = frame[y1:y2, x1:x2]
results = self.lpr.simple_recognize(roi)
```

**已集成**，需要安装HyperLPR：
```bash
pip3 install hyperlpr3 -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

---

## 🔄 系统流程

```
视频帧输入
    ↓
TensorRT检测（GPU）
    ↓
YOLO后处理（NMS）
    ↓
IoU跟踪
    ↓
    ├─ 新工程车辆
    │   ├─ 计算距离（Orbbec）
    │   ├─ 匹配信标
    │   ├─ 成功 → 已备案
    │   └─ 失败 → ⚠️ 未备案车辆入场
    │
    └─ 新社会车辆
        ├─ 车牌识别（HyperLPR）
        ├─ 成功 → 记录车牌
        └─ 失败 → 车牌识别失败
```

---

## 📊 输出示例

### 实时终端输出

```
帧1: 3 个检测
  ⚠ 未备案车辆入场! ID1: excavator, 帧1
  🚗 社会车辆 ID2: truck, 车牌识别失败

帧50: 2 个检测
  ⚠ 未备案车辆入场! ID3: dump-truck, 帧50

已处理 100/15398 帧, 平均 28.5 FPS
```

### 最终统计输出

```
======================================================================
TensorRT车辆检测统计
======================================================================

总帧数: 15398
平均FPS: 28.3

【工程车辆 - 已备案】
  总数: 0 辆
  无

【工程车辆 - 未备案（警告）】
  总数: 5 辆

  ⚠ ID1: excavator       帧1
  ⚠ ID3: dump-truck      帧50
  ⚠ ID5: loader          帧120
  ⚠ ID7: excavator       帧200
  ⚠ ID9: dump-truck      帧350

【社会车辆 - 车牌识别】
  总数: 0 辆
  无

======================================================================
```

**注意**：当前所有工程车辆都显示"未备案"，因为信标匹配接口未实现。

---

## 🚀 测试当前版本

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine
```

---

## 🔧 后续集成

### 集成Orbbec深度相机

1. 安装SDK
   ```bash
   pip3 install pyorbbecsdk
   ```

2. 修改代码读取RGB+Depth
   ```python
   from pyorbbecsdk import Pipeline, Config
   
   # 创建pipeline
   pipeline = Pipeline()
   config = Config()
   config.enable_color_stream()
   config.enable_depth_stream()
   pipeline.start(config)
   
   # 读取帧
   frames = pipeline.wait_for_frames()
   color_frame = frames.get_color_frame()
   depth_frame = frames.get_depth_frame()
   ```

3. 传入depth_frame到calculate_distance

### 集成蓝牙信标

1. 确定路由器API格式
2. 实现HTTP/MQTT客户端
3. 填充`get_beacon_data()`函数
4. 调整RSSI转距离参数

### 集成HyperLPR

```bash
pip3 install hyperlpr3 -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

重新运行即可自动使用。

---

## 💡 重要说明

**当前版本**：
- ✅ 基础功能完整（检测、跟踪、可视化）
- ⚠️ 信标匹配未实现（所有工程车辆显示"未备案"）
- ⚠️ HyperLPR未安装（车牌识别失败）
- ⚠️ 深度相机未接入（距离估计不准确）

**下一步**：
1. 测试当前版本的检测和跟踪效果
2. 安装HyperLPR测试车牌识别
3. 接入Orbbec深度相机
4. 接入蓝牙信标路由器

---

**系统逻辑已按需求重新设计！** 🚀

