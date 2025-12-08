# Jetson端数据问题修复方案

**创建时间**: 2025-12-05  
**状态**: 待修复  
**优先级**: 🔴 高优先级

---

## 📋 问题确认

根据云端开发团队反馈（`JETSON_DATA_ISSUES.md`），当前Jetson端发送的数据存在以下问题：

### 🔴 关键问题（必须修复）

| 问题 | 当前状态 | 期望状态 | 影响 |
|------|---------|---------|------|
| `detected_class` 缺失 | 100% null | 应为 "excavator", "bulldozer" 等 | 无法区分具体车辆类型 |
| `status` 缺失 | 100% null | 应为 "registered", "unregistered" 等 | 无法判断备案状态 |
| `bbox` 缺失 | 100% null | 应包含 x1, y1, x2, y2 坐标 | 无法定位车辆位置 |
| 图片字段缺失 | 100% null | 应包含 snapshot_path 或 snapshot_url | 无法查看检测快照 |
| `vehicle_type` 格式错误 | "construction vehicle" | 应为 "construction" | 格式不一致 |

### ⚠️ 次要问题（建议修复）

| 问题 | 当前状态 | 期望状态 |
|------|---------|---------|
| `metadata` 缺失 | 100% null | 应包含 rssi, match_cost 等 |
| 工程车辆信息缺失 | beacon_mac, company 均为 null | 应包含信标匹配信息 |

---

## 🔍 根本原因分析

### 问题 1: `DetectionResult` 类字段不完整

**文件**: `jetson-client/detection_result.py`

**当前定义**:
```python
@dataclass
class DetectionResult:
    vehicle_type: str
    confidence: float
    plate_number: Optional[str] = None
    timestamp: Optional[datetime] = None
    image_path: Optional[str] = None
    bbox: Optional[tuple] = None
    track_id: Optional[int] = None
    distance: Optional[float] = None
    is_registered: Optional[bool] = None
```

**缺失字段**:
- ❌ `detected_class` (检测类别，如 "excavator")
- ❌ `status` (状态，如 "registered")
- ❌ `metadata` (元数据，如 rssi, match_cost)
- ❌ `beacon_mac` (信标MAC地址)
- ❌ `company` (所属公司)

### 问题 2: `vehicle_type` 格式错误

**文件**: `jetson-client/detection_result.py:22-41`

**当前映射**:
```python
vehicle_type_map = {
    "construction": "Construction Vehicle",  # ❌ 错误：添加了空格和大写
    "civilian": "Civilian",                  # ❌ 错误：大写首字母
}
```

**应该是**:
```python
# 不应该修改 vehicle_type，保持原值
# "construction" -> "construction"
# "civilian" -> "civilian"
```

### 问题 3: `CloudClient.send_alert` 只发送部分字段

**文件**: `jetson-client/cloud_client.py:65-73`

**当前发送**:
```python
alert_data = {
    "timestamp": timestamp.isoformat(),
    "vehicle_type": vehicle_type,
    "plate_number": plate_number,
    "confidence": confidence,
    "distance": distance,
    "is_registered": is_registered,
    "track_id": track_id
}
```

**缺失字段**:
- ❌ `detected_class`
- ❌ `status`
- ❌ `bbox`
- ❌ `metadata`
- ❌ `beacon_mac`
- ❌ `company`
- ❌ `snapshot_path` / `snapshot_url`

### 问题 4: 创建 `DetectionResult` 时未传递完整数据

**文件**: `test_system_realtime.py:1290-1300`

**当前代码**:
```python
detection_result = DetectionResult(
    vehicle_type=alert.get('vehicle_type', alert.get('type', 'Unknown')),
    confidence=alert.get('confidence', 0.0),
    plate_number=alert.get('plate_number'),
    timestamp=datetime.now(),
    image_path=snapshot_path,
    bbox=bbox,
    track_id=alert.get('track_id'),
    distance=alert.get('distance'),
    is_registered=(alert.get('status') == 'registered')
)
```

**问题**:
- 获取 `vehicle_type` 的逻辑有问题：`alert.get('vehicle_type')` 优先于 `alert.get('type')`
- 实际 alert 中的字段是 `'type'`（值为 "construction" 或 "civilian"）
- 缺少 `detected_class`, `status`, `metadata` 等字段

---

## 🔧 修复方案

### 修复 1: 更新 `DetectionResult` 类

**文件**: `jetson-client/detection_result.py`

**操作**: 添加缺失字段，修复 `vehicle_type` 映射逻辑

```python
@dataclass
class DetectionResult:
    """车辆检测结果"""
    vehicle_type: str  # 车辆类型: "construction" | "civilian"
    confidence: float  # 置信度 (0.0-1.0)
    detected_class: Optional[str] = None  # 🆕 检测类别: "excavator", "bulldozer", "car" 等
    status: Optional[str] = None  # 🆕 状态: "registered", "unregistered", "identified" 等
    plate_number: Optional[str] = None  # 车牌号
    timestamp: Optional[datetime] = None  # 检测时间
    image_path: Optional[str] = None  # 快照路径
    bbox: Optional[tuple] = None  # 边界框 (x1, y1, x2, y2)
    track_id: Optional[int] = None  # 跟踪ID
    distance: Optional[float] = None  # 距离（米）
    is_registered: Optional[bool] = None  # 是否已备案
    beacon_mac: Optional[str] = None  # 🆕 信标MAC地址（工程车辆）
    company: Optional[str] = None  # 🆕 所属公司（工程车辆）
    metadata: Optional[dict] = None  # 🆕 元数据（rssi, match_cost等）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 🔧 移除 vehicle_type 映射逻辑，保持原值
        # vehicle_type 应该已经是 "construction" 或 "civilian"
        # 不需要再次转换
```

### 修复 2: 更新 `CloudClient.send_alert` 方法

**文件**: `jetson-client/cloud_client.py`

**操作**: 添加缺失字段参数和发送逻辑

```python
def send_alert(
    self,
    vehicle_type: str,
    timestamp: datetime,
    detected_class: Optional[str] = None,  # 🆕
    status: Optional[str] = None,  # 🆕
    plate_number: Optional[str] = None,
    confidence: Optional[float] = None,
    distance: Optional[float] = None,
    is_registered: Optional[bool] = None,
    track_id: Optional[int] = None,
    bbox: Optional[dict] = None,  # 🆕
    beacon_mac: Optional[str] = None,  # 🆕
    company: Optional[str] = None,  # 🆕
    metadata: Optional[dict] = None  # 🆕
) -> Optional[int]:
    """发送警报到云端"""
    if not self.config.enable_alert_upload:
        logger.debug("Alert upload is disabled")
        return None
    
    alert_data = {
        "timestamp": timestamp.isoformat(),
        "vehicle_type": vehicle_type,
        "detected_class": detected_class,  # 🆕
        "status": status,  # 🆕
        "plate_number": plate_number,
        "confidence": confidence,
        "distance": distance,
        "is_registered": is_registered,
        "track_id": track_id,
        "bbox": bbox,  # 🆕
        "beacon_mac": beacon_mac,  # 🆕
        "company": company,  # 🆕
        "metadata": metadata  # 🆕
    }
    
    # 移除None值
    alert_data = {k: v for k, v in alert_data.items() if v is not None}
    
    # ... 其余代码保持不变
```

### 修复 3: 更新 `main_integration.py` 调用代码

**文件**: `jetson-client/main_integration.py:94-102`

**操作**: 传递完整字段到 `send_alert`

```python
# 上传警报
alert_id = self.cloud_client.send_alert(
    vehicle_type=detection.vehicle_type,
    timestamp=detection.timestamp,
    detected_class=detection.detected_class,  # 🆕
    status=detection.status,  # 🆕
    plate_number=detection.plate_number,
    confidence=detection.confidence,
    distance=detection.distance,
    is_registered=detection.is_registered,
    track_id=detection.track_id,
    bbox={  # 🆕 格式化 bbox
        "x1": detection.bbox[0],
        "y1": detection.bbox[1],
        "x2": detection.bbox[2],
        "y2": detection.bbox[3]
    } if detection.bbox else None,
    beacon_mac=detection.beacon_mac,  # 🆕
    company=detection.company,  # 🆕
    metadata=detection.metadata  # 🆕
)
```

### 修复 4: 更新 `test_system_realtime.py` 创建 `DetectionResult` 的代码

**文件**: `test_system_realtime.py:1290-1300`

**操作**: 传递完整字段

```python
# 创建检测结果并上传
detection_result = DetectionResult(
    vehicle_type=alert.get('type', 'Unknown'),  # 🔧 修复：直接使用 'type'
    detected_class=alert.get('detected_type') or alert.get('detected_class'),  # 🆕
    status=alert.get('status'),  # 🆕
    confidence=alert.get('confidence', 0.0),
    plate_number=alert.get('plate_number') or alert.get('plate'),  # 支持两种字段名
    timestamp=datetime.now(),
    image_path=snapshot_path,
    bbox=bbox,
    track_id=alert.get('track_id'),
    distance=alert.get('distance'),
    is_registered=(alert.get('status') == 'registered'),
    beacon_mac=alert.get('beacon_mac'),  # 🆕
    company=alert.get('company'),  # 🆕
    metadata={  # 🆕
        'rssi': alert.get('rssi'),
        'match_cost': alert.get('match_cost'),
        'depth_confidence': 0.9  # 可以从其他地方获取
    } if alert.get('rssi') is not None else None
)
```

### 修复 5: 确保 `alert` 字典包含 `detected_type` 字段

**文件**: `test_system_realtime.py` 各处创建 alert 的代码

**检查点**:
1. `check_construction_vehicle` 方法中创建的 alert 应该包含 `detected_type` 或 `detected_class`
2. `check_civilian_vehicle` 方法中创建的 alert 应该包含 `detected_type` 或 `detected_class`
3. 批量处理工程车辆时的 alert 应该包含 `detected_class`

**示例修改** (在 `check_civilian_vehicle` 中):
```python
alert = {
    'track_id': track_id,
    'type': 'civilian',
    'status': 'identified' if plate_number else 'failed',  # 🔧 修复
    'message': f"社会车辆",
    'plate': plate_number,
    'detected_class': class_name,  # 🆕 添加
    'color': COLORS['civilian']
}
```

---

## ✅ 验证清单

修复完成后，需要验证：

- [ ] `DetectionResult` 类包含所有必需字段
- [ ] `vehicle_type` 保持原值（不转换为 "Construction Vehicle"）
- [ ] `CloudClient.send_alert` 发送所有必需字段
- [ ] `main_integration.py` 传递完整数据
- [ ] `test_system_realtime.py` 创建完整的 `DetectionResult` 对象
- [ ] 工程车辆的 alert 包含 `detected_class`, `beacon_mac`, `company`
- [ ] 社会车辆的 alert 包含 `detected_class`, `status`
- [ ] `metadata` 包含 `rssi`, `match_cost` 等信息
- [ ] `bbox` 以正确格式发送（字典，包含 x1, y1, x2, y2）
- [ ] 图片上传后，`snapshot_url` 或 `snapshot_path` 正确关联

---

## 🧪 测试步骤

1. **单元测试**: 测试 `DetectionResult` 类的创建和字段
2. **集成测试**: 运行系统，检测一辆工程车辆和一辆社会车辆
3. **云端验证**: 在云端数据库查询最新记录，确认所有字段都有值
4. **对比验证**: 对比云端期望的数据格式和实际发送的数据

**测试命令**:
```bash
# 1. 运行系统
cd /home/liubo/Download/deepstream-vehicle-detection
python test_system_realtime.py --no-display

# 2. 检查日志，确认发送的数据
tail -f /tmp/vehicle_detection.log | grep "Alert sent"

# 3. 在云端查询数据库
# (需要云端开发团队协助)
```

---

## 📊 预期结果

修复后，云端应该接收到类似以下格式的完整数据：

```json
{
  "id": 45,
  "timestamp": "2025-12-05T21:41:47.681213",
  "track_id": 39,
  "vehicle_type": "construction",
  "detected_class": "excavator",
  "status": "registered",
  "confidence": 0.95,
  "beacon_mac": "AA:BB:CC:DD:EE:01",
  "plate_number": "京A12345",
  "company": "北京建工集团",
  "distance": 6.9235,
  "bbox": {
    "x1": 100,
    "y1": 200,
    "x2": 500,
    "y2": 600
  },
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_39_20251205_214147.jpg",
  "snapshot_url": "http://123.249.9.250:8000/uploads/images/snapshot_39_20251205_214147.jpg",
  "metadata": {
    "rssi": -55,
    "match_cost": 0.15,
    "depth_confidence": 0.9
  }
}
```

---

## 📝 相关文档

- 云端问题反馈: `/home/liubo/Download/JETSON_DATA_ISSUES.md`
- API 文档: `docs/API_DOCUMENTATION.md`
- 数据模型: `jetson-client/detection_result.py`
- 云端客户端: `jetson-client/cloud_client.py`
- 主程序: `test_system_realtime.py`

---

**最后更新时间**: 2025-12-05  
**修复状态**: 📋 待执行



