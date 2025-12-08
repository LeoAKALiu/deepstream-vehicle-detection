# vehicle_type 字段修正说明

**修正时间**: 2025-12-05 23:30  
**版本**: v2.0  
**状态**: ⚠️ 需要重启系统

---

## 🔍 问题描述

之前对 `vehicle_type` 字段的理解有误，现已修正。

### ❌ 错误理解（v1.0）

```json
{
  "vehicle_type": "construction",    // ❌ 错误
  "detected_class": "excavator"
}
```

```json
{
  "vehicle_type": "civilian",        // ❌ 错误
  "detected_class": "car"
}
```

### ✅ 正确理解（v2.0）

```json
{
  "vehicle_type": "construction_vehicle",  // ✅ 正确
  "detected_class": "excavator"
}
```

```json
{
  "vehicle_type": "social_vehicle",        // ✅ 正确
  "detected_class": "car"
}
```

---

## 📊 数据结构说明

### 车辆类型 (vehicle_type)

系统将车辆分为 **两大类**：

1. **`construction_vehicle`** - 工程车辆
2. **`social_vehicle`** - 社会车辆

### 检测类别 (detected_class)

每个车辆类型下包含具体的检测类别：

#### 工程车辆 - 9 种类别

| detected_class | 中文名称 |
|----------------|---------|
| `excavator` | 挖掘机 |
| `bulldozer` | 推土机 |
| `roller` | 压路机 |
| `loader` | 装载机 |
| `dump-truck` | 自卸车 |
| `concrete-mixer` | 混凝土搅拌车 |
| `pump-truck` | 泵车 |
| `truck` | 卡车 |
| `crane` | 起重机 |

#### 社会车辆 - 1 种类别

| detected_class | 中文名称 |
|----------------|---------|
| `car` | 小汽车 |

---

## ✅ 修正内容

### 修改的文件

1. **`test_system_realtime.py`**
   - 所有 `'type': 'construction'` → `'type': 'construction_vehicle'`
   - 所有 `'type': 'civilian'` → `'type': 'social_vehicle'`

2. **`jetson-client/detection_result.py`**
   - 注释更新：`"construction" | "civilian"` → `"construction_vehicle" | "social_vehicle"`

3. **`docs/API_DOCUMENTATION.md`**
   - 完整重写，明确两大类车辆和对应的检测类别
   - 添加详细的数据示例和字段说明

### 修改行数统计

```bash
test_system_realtime.py:
  - 第 1359 行: 'construction' → 'construction_vehicle'
  - 第 1384 行: 'construction' → 'construction_vehicle'
  - 第 1401 行: 'construction' → 'construction_vehicle'
  - 第 1509 行: 'construction' → 'construction_vehicle'
  - 第 1529 行: 'construction' → 'construction_vehicle'
  - 第 1542 行: 'construction' → 'construction_vehicle'
  - 第 1702 行: 'civilian' → 'social_vehicle'
  - 第 1953 行: 'civilian' → 'social_vehicle'
```

---

## 🔄 部署步骤

### 1. 停止当前进程

```bash
pkill -f test_system_realtime
sleep 2
```

### 2. 启动新进程

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
nohup python test_system_realtime.py --no-display > /tmp/vehicle_detection_startup.log 2>&1 &
```

### 3. 验证进程

```bash
ps aux | grep test_system_realtime | grep -v grep
```

---

## 📋 数据示例对比

### 修正前（v1.0）

```json
{
  "timestamp": "2025-12-05T23:15:30.000",
  "track_id": 101,
  "vehicle_type": "construction",           // ❌ 错误格式
  "detected_class": "excavator",
  "status": "registered",
  "confidence": 0.95,
  "distance": 6.5,
  "bbox": {"x1": 100, "y1": 200, "x2": 500, "y2": 600}
}
```

### 修正后（v2.0）

```json
{
  "timestamp": "2025-12-05T23:35:00.000",
  "track_id": 105,
  "vehicle_type": "construction_vehicle",   // ✅ 正确格式
  "detected_class": "excavator",
  "status": "registered",
  "confidence": 0.95,
  "distance": 6.5,
  "bbox": {"x1": 100, "y1": 200, "x2": 500, "y2": 600},
  "beacon_mac": "AA:BB:CC:DD:EE:01",
  "company": "北京建工集团",
  "metadata": {"rssi": -55, "match_cost": 0.15}
}
```

---

## 🎯 云端验证

### 数据库查询

修正后，云端应该收到以下格式的数据：

```sql
SELECT 
  timestamp,
  vehicle_type,
  detected_class,
  status
FROM detections 
WHERE timestamp > '2025-12-05 23:35:00'
ORDER BY timestamp DESC 
LIMIT 10;
```

### 期望结果

| timestamp | vehicle_type | detected_class | status |
|-----------|--------------|----------------|--------|
| 2025-12-05 23:36:00 | construction_vehicle | excavator | registered |
| 2025-12-05 23:36:15 | social_vehicle | car | identified |
| 2025-12-05 23:36:30 | construction_vehicle | bulldozer | unregistered |

### ❌ 错误格式（如果出现，说明未重启）

| timestamp | vehicle_type | detected_class | status |
|-----------|--------------|----------------|--------|
| 2025-12-05 23:15:00 | construction | excavator | registered |
| 2025-12-05 23:15:15 | civilian | car | identified |

---

## 📞 云端对接说明

### 翻译函数（前端）

```javascript
// 车辆类型翻译
function translateVehicleType(vehicleType) {
  const translations = {
    'construction_vehicle': '工程车辆',
    'social_vehicle': '社会车辆'
  };
  return translations[vehicleType] || vehicleType;
}

// 检测类别翻译
function translateDetectedClass(detectedClass) {
  const translations = {
    // 工程车辆 (9 种)
    'excavator': '挖掘机',
    'bulldozer': '推土机',
    'roller': '压路机',
    'loader': '装载机',
    'dump-truck': '自卸车',
    'concrete-mixer': '混凝土搅拌车',
    'pump-truck': '泵车',
    'truck': '卡车',
    'crane': '起重机',
    // 社会车辆 (1 种)
    'car': '小汽车'
  };
  return translations[detectedClass] || detectedClass;
}
```

### 数据验证（后端）

```python
from enum import Enum

class VehicleType(str, Enum):
    CONSTRUCTION = "construction_vehicle"
    SOCIAL = "social_vehicle"

class ConstructionClass(str, Enum):
    EXCAVATOR = "excavator"
    BULLDOZER = "bulldozer"
    ROLLER = "roller"
    LOADER = "loader"
    DUMP_TRUCK = "dump-truck"
    CONCRETE_MIXER = "concrete-mixer"
    PUMP_TRUCK = "pump-truck"
    TRUCK = "truck"
    CRANE = "crane"

class SocialClass(str, Enum):
    CAR = "car"

def validate_detection(data):
    """验证检测数据的一致性"""
    vehicle_type = data.get('vehicle_type')
    detected_class = data.get('detected_class')
    
    if vehicle_type == VehicleType.CONSTRUCTION:
        assert detected_class in [e.value for e in ConstructionClass]
    elif vehicle_type == VehicleType.SOCIAL:
        assert detected_class == SocialClass.CAR
    else:
        raise ValueError(f"Invalid vehicle_type: {vehicle_type}")
```

---

## 📝 总结

- ✅ 代码已修正
- ⚠️ 需要重启系统
- ✅ API 文档已更新（v2.0）
- ⏳ 等待云端验证

### 关键变更

| 项目 | 旧值 | 新值 |
|------|------|------|
| 工程车辆类型 | `"construction"` | `"construction_vehicle"` |
| 社会车辆类型 | `"civilian"` | `"social_vehicle"` |
| 工程车辆类别 | 9 种 | 9 种（不变） |
| 社会车辆类别 | 1 种 (car) | 1 种 (car)（不变） |

---

**修正完成时间**: 2025-12-05 23:30  
**下一步**: 重启系统并等待云端验证


