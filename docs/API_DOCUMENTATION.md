# Jetson 车辆检测系统 API 文档

**版本**: v2.0  
**更新时间**: 2025-12-05  
**目标用户**: 远程管理平台开发人员

---

## 📋 目录

1. [概述](#概述)
2. [数据字段说明](#数据字段说明)
3. [车辆类型与检测类别对照](#车辆类型与检测类别对照)
4. [API 端点](#api-端点)
5. [数据示例](#数据示例)
6. [错误处理](#错误处理)

---

## 概述

本文档描述了 Jetson 车辆检测系统向云端平台发送的数据格式和字段说明。

### 核心概念

- **车辆类型 (vehicle_type)**: 两大类
  - `construction_vehicle`: 工程车辆（包含 9 种工程机械）
  - `social_vehicle`: 社会车辆（只有小汽车 car）

- **检测类别 (detected_class)**: 具体的车辆型号
  - 工程车辆: 9 种类别
  - 社会车辆: 1 种类别 (car)

---

## 数据字段说明

### 核心字段

| 字段名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `timestamp` | string | ✅ | ISO 8601 格式时间戳 | `"2025-12-05T23:15:30.123456"` |
| `track_id` | integer | ✅ | 追踪 ID，同一车辆保持不变 | `101` |
| `vehicle_type` | string | ✅ | 车辆类型（两大类） | `"construction_vehicle"` 或 `"social_vehicle"` |
| `detected_class` | string | ✅ | 检测到的具体类别 | `"excavator"`, `"car"` 等 |
| `status` | string | ✅ | 车辆状态 | 见下文状态说明 |
| `confidence` | float | ✅ | 检测置信度 (0.0-1.0) | `0.95` |
| `distance` | float | ✅ | 距离（米） | `6.5` |
| `bbox` | object | ✅ | 边界框坐标 | `{"x1": 100, "y1": 200, "x2": 500, "y2": 600}` |

### 工程车辆特有字段

| 字段名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `beacon_mac` | string | ⚠️ | 蓝牙信标 MAC 地址 | `"AA:BB:CC:DD:EE:01"` |
| `company` | string | ⚠️ | 所属公司（仅备案车辆） | `"北京建工集团"` |
| `metadata` | object | ⚠️ | 额外元数据 | `{"rssi": -55, "match_cost": 0.15}` |

> ⚠️ 这些字段仅在工程车辆**匹配到信标**时存在

### 社会车辆特有字段

| 字段名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `plate_number` | string | ⚠️ | 车牌号 | `"京B67890"` |

> ⚠️ 车牌号仅在识别成功时存在

### 图片字段

| 字段名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `snapshot_path` | string | ⚠️ | 本地快照路径 | `"/tmp/vehicle_snapshots/snapshot_101.jpg"` |
| `snapshot_url` | string | ⚠️ | 云端图片 URL（**推荐使用此字段显示图片**） | `"https://cdn.example.com/snapshots/101.jpg"` |
| `image_path` | string | ⚠️ | 图片路径（备用，通常与 snapshot_path 相同） | `"/tmp/snapshots/101.jpg"` |

> ⚠️ **重要**: 图片字段会在检测到车辆时自动上传，`snapshot_url` 字段包含云端可访问的图片 URL。如果 `snapshot_url` 为 `null`，说明图片上传失败或未启用图片上传功能。

---

## 车辆类型与检测类别对照

### ✅ 正确的数据结构

#### 工程车辆 (construction_vehicle)

工程车辆包含 **9 种**工程机械类别：

| detected_class | 中文名称 | 说明 |
|----------------|---------|------|
| `excavator` | 挖掘机 | 履带式或轮式挖掘机 |
| `bulldozer` | 推土机 | 履带式推土机 |
| `roller` | 压路机 | 单钢轮或双钢轮压路机 |
| `loader` | 装载机 | 轮式装载机 |
| `dump-truck` | 自卸车 | 工程自卸车 |
| `concrete-mixer` | 混凝土搅拌车 | 罐车 |
| `pump-truck` | 泵车 | 混凝土泵车 |
| `truck` | 卡车 | 工程卡车 |
| `crane` | 起重机 | 塔吊、汽车吊等 |

**数据示例**:
```json
{
  "vehicle_type": "construction_vehicle",
  "detected_class": "excavator"
}
```

#### 社会车辆 (social_vehicle)

社会车辆只有 **1 种**类别：

| detected_class | 中文名称 | 说明 |
|----------------|---------|------|
| `car` | 小汽车 | 社会车辆 |

**数据示例**:
```json
{
  "vehicle_type": "social_vehicle",
  "detected_class": "car"
}
```

---

## 车辆状态 (status) 说明

### 工程车辆状态

| status | 说明 | 触发条件 |
|--------|------|---------|
| `registered` | 已备案 | 检测到信标且信标在备案列表中 |
| `unregistered` | 未备案 | 检测到车辆但未匹配到信标，或信标不在备案列表 |

### 社会车辆状态

| status | 说明 | 触发条件 |
|--------|------|---------|
| `identified` | 识别成功 | 车牌识别成功 |
| `identifying` | 识别中 | 正在进行车牌识别 |
| `failed` | 识别失败 | 车牌识别失败 |

---

## API 端点

### 1. 告警推送

**端点**: `POST /api/alerts/`

**说明**: Jetson 设备检测到车辆时推送告警数据

**请求格式**:
```json
{
  "timestamp": "2025-12-05T23:15:30.123456",
  "track_id": 101,
  "vehicle_type": "construction_vehicle",
  "detected_class": "excavator",
  "status": "registered",
  "confidence": 0.95,
  "distance": 6.5,
  "bbox": {
    "x1": 100,
    "y1": 200,
    "x2": 500,
    "y2": 600
  },
  "beacon_mac": "AA:BB:CC:DD:EE:01",
  "company": "北京建工集团",
  "plate_number": null,
  "metadata": {
    "rssi": -55,
    "match_cost": 0.15
  },
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_101.jpg"
}
```

**响应格式**:
```json
{
  "status": "success",
  "alert_id": 12345
}
```

### 2. 心跳上报

**端点**: `POST /api/heartbeat/`

**说明**: Jetson 设备定期（60秒）上报设备状态和统计信息

**请求格式**:
```json
{
  "device_id": "jetson-001",
  "timestamp": "2025-12-05T23:16:00.000000",
  "status": "running",
  "stats": {
    "fps": 28.5,
    "total_detections": 156,
    "construction_vehicles": 89,
    "social_vehicles": 67,
    "active_tracks": 3,
    "uptime_seconds": 25200
  },
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 38.5,
    "gpu_usage": 78.3
  }
}
```

**响应格式**:
```json
{
  "status": "ok"
}
```

### 3. 图片上传

**端点**: `POST /api/upload/image/`

**说明**: 上传检测快照图片

**请求格式**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | file | 图片文件 (JPEG) |
| `track_id` | integer | 关联的追踪 ID |
| `timestamp` | string | 时间戳 |

**响应格式**:
```json
{
  "status": "success",
  "url": "https://cdn.example.com/snapshots/101.jpg"
}
```

---

## 数据示例

### 示例 1: 工程车辆 - 已备案挖掘机

```json
{
  "timestamp": "2025-12-05T23:15:30.123456",
  "track_id": 101,
  "vehicle_type": "construction_vehicle",
  "detected_class": "excavator",
  "status": "registered",
  "confidence": 0.95,
  "distance": 6.5,
  "bbox": {
    "x1": 100,
    "y1": 200,
    "x2": 500,
    "y2": 600
  },
  "beacon_mac": "AA:BB:CC:DD:EE:01",
  "company": "北京建工集团",
  "plate_number": null,
  "metadata": {
    "rssi": -55,
    "match_cost": 0.15,
    "detection_time": "2025-12-05T23:15:30"
  },
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_101.jpg",
  "snapshot_url": "https://cdn.example.com/snapshots/101.jpg",
  "image_path": "/tmp/vehicle_snapshots/snapshot_101.jpg"
}
```

### 示例 2: 工程车辆 - 未备案推土机

```json
{
  "timestamp": "2025-12-05T23:16:45.678901",
  "track_id": 102,
  "vehicle_type": "construction_vehicle",
  "detected_class": "bulldozer",
  "status": "unregistered",
  "confidence": 0.92,
  "distance": 8.2,
  "bbox": {
    "x1": 150,
    "y1": 250,
    "x2": 550,
    "y2": 650
  },
  "beacon_mac": null,
  "company": null,
  "plate_number": null,
  "metadata": null,
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_102.jpg",
  "snapshot_url": "https://cdn.example.com/snapshots/102.jpg",
  "image_path": "/tmp/vehicle_snapshots/snapshot_102.jpg"
}
```

### 示例 3: 社会车辆 - 识别成功

```json
{
  "timestamp": "2025-12-05T23:17:20.234567",
  "track_id": 103,
  "vehicle_type": "social_vehicle",
  "detected_class": "car",
  "status": "identified",
  "confidence": 0.89,
  "distance": 5.8,
  "bbox": {
    "x1": 200,
    "y1": 300,
    "x2": 600,
    "y2": 700
  },
  "beacon_mac": null,
  "company": null,
  "plate_number": "京B67890",
  "metadata": null,
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_103.jpg"
}
```

### 示例 4: 社会车辆 - 识别失败

```json
{
  "timestamp": "2025-12-05T23:18:05.345678",
  "track_id": 104,
  "vehicle_type": "social_vehicle",
  "detected_class": "car",
  "status": "failed",
  "confidence": 0.87,
  "distance": 7.1,
  "bbox": {
    "x1": 180,
    "y1": 280,
    "x2": 580,
    "y2": 680
  },
  "beacon_mac": null,
  "company": null,
  "plate_number": null,
  "metadata": null,
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_104.jpg"
}
```

---

## 字段完整性检查

### 必须存在的字段 (100%)

以下字段在**所有**告警中都必须存在：

- ✅ `timestamp`
- ✅ `track_id`
- ✅ `vehicle_type`
- ✅ `detected_class`
- ✅ `status`
- ✅ `confidence`
- ✅ `distance`
- ✅ `bbox`

### 条件存在的字段

| 字段 | 存在条件 | 期望比例 |
|------|---------|---------|
| `beacon_mac` | 工程车辆 + 匹配到信标 | 视现场情况 |
| `company` | 工程车辆 + 匹配到信标 + 已备案 | 视现场情况 |
| `metadata` | 工程车辆 + 匹配到信标 | 视现场情况 |
| `plate_number` | 社会车辆 + 识别成功 | 60-90% |
| `snapshot_path` | 触发快照保存 | 视配置 |

---

## 错误处理

### 数据验证规则

1. **vehicle_type 枚举值检查**
   ```python
   assert vehicle_type in ["construction_vehicle", "social_vehicle"]
   ```

2. **detected_class 与 vehicle_type 一致性检查**
   ```python
   if vehicle_type == "construction_vehicle":
       assert detected_class in [
           "excavator", "bulldozer", "roller", "loader", 
           "dump-truck", "concrete-mixer", "pump-truck", "truck", "crane"
       ]
   elif vehicle_type == "social_vehicle":
       assert detected_class == "car"
   ```

3. **status 与 vehicle_type 一致性检查**
   ```python
   if vehicle_type == "construction_vehicle":
       assert status in ["registered", "unregistered"]
   elif vehicle_type == "social_vehicle":
       assert status in ["identified", "identifying", "failed"]
   ```

4. **bbox 格式检查**
   ```python
   assert isinstance(bbox, dict)
   assert all(key in bbox for key in ["x1", "y1", "x2", "y2"])
   assert bbox["x2"] > bbox["x1"]
   assert bbox["y2"] > bbox["y1"]
   ```

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| `vehicle_type` 为 `"construction vehicle"` | 旧版本代码 | 应为 `"construction_vehicle"` |
| `vehicle_type` 为 `"civilian"` | 旧版本代码 | 应为 `"social_vehicle"` |
| `detected_class` 为 `null` | 数据未传递 | 检查 Jetson 端代码 |
| `status` 为 `null` | 数据未传递 | 检查 Jetson 端代码 |
| `bbox` 为 `null` | 数据未传递 | 检查 Jetson 端代码 |

---

## 版本历史

### v2.0 (2025-12-05)
- ✅ 修正 `vehicle_type` 为 `construction_vehicle` 和 `social_vehicle`
- ✅ 明确 9 种工程机械类别和 1 种社会车辆类别
- ✅ 添加 `detected_class` 字段
- ✅ 添加 `status` 字段
- ✅ 添加 `bbox` 字段
- ✅ 添加工程车辆特有字段 (`beacon_mac`, `company`, `metadata`)

### v1.0 (2025-12-04)
- 初始版本

---

## 联系方式

**Jetson 端负责人**: liubo  
**云端平台负责人**: [待填写]  
**技术支持**: [待填写]

---

**最后更新**: 2025-12-05 23:30  
**文档版本**: v2.0
