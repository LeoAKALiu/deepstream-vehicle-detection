# 置信度问题修复说明

## 问题描述

云端收到的检测数据中，2885/2889 条记录的置信度为 0.0，仅 4 条为 0.95。经检查发现，Jetson 端发送的置信度大多为 0.0，这是数据源问题，非后端处理问题。

## 根本原因

1. **跟踪器未保存置信度**：`VehicleTracker.update()` 方法只保存了 `bbox`、`class`、`last_seen`、`processed` 等信息，但没有保存检测置信度。

2. **置信度传递链断裂**：
   - 检测阶段：`inference.postprocess()` 返回了 `confidences`
   - 跟踪阶段：`tracker.update()` 接收了 `confidences`，但没有保存到 track 中
   - Alert 创建阶段：从 track 中获取置信度时，因为 track 中没有置信度字段，所以使用了默认值 0.0

3. **错误使用信标置信度**：工程车辆的 alert 中使用了信标匹配的置信度（`beacon_info['confidence']`），而不是检测置信度。

## 修复内容

### 1. 修复跟踪器：保存检测置信度

**文件**：`test_system_realtime.py`

**修改**：
- `VehicleTracker.update()` 方法添加 `confidences` 参数
- 在 track 中保存 `confidence` 字段和 `confidence_history`（最近10帧的置信度历史）
- 使用最高置信度（最近10帧中的最大值）作为稳定置信度

```python
def update(self, boxes, class_ids, frame_id, confidences=None):
    # 保存置信度到 track
    current_tracks[best_track_id] = {
        'bbox': box,
        'class': stable_class,
        'confidence': stable_confidence,  # 使用最高置信度
        'last_seen': frame_id,
        'processed': track['processed'],
        'class_history': track['class_history'],
        'confidence_history': track['confidence_history']  # 置信度历史
    }
```

### 2. 修复 Simple IoU 跟踪器调用

**修改**：在调用 Simple IoU 跟踪器时传递置信度参数

```python
tracks = self.tracker.update(
    vehicle_boxes, 
    vehicle_class_ids, 
    self.frame_count, 
    confidences=vehicle_confidences  # 传递检测置信度
)
```

### 3. 修复工程车辆 Alert 创建

**修改**：
- `_create_construction_alert()` 添加 `detection_confidence` 参数
- 所有 alert 使用检测置信度，而不是信标置信度
- 所有调用 `_create_construction_alert()` 的地方传递检测置信度

```python
def _create_construction_alert(
    self, track_id, bbox, image, detected_class, beacon_info, 
    match_cost=None, detection_confidence=0.0  # 新增参数
):
    alert = {
        'confidence': detection_confidence,  # 使用检测置信度
        # ... 其他字段
    }
```

### 4. 修复社会车辆 Alert 创建

**修改**：
- 在创建社会车辆 alert 时，从 track 中获取检测置信度
- 数据库保存时使用 alert 中的置信度

```python
detection_confidence = track.get('confidence', 0.0)
alert = {
    'confidence': detection_confidence,  # 添加检测置信度
    # ... 其他字段
}
```

### 5. 修复所有调用链

**修改**：
- `check_construction_vehicle()` 添加 `detection_confidence` 参数
- `process_new_vehicle()` 添加 `detection_confidence` 参数
- 所有调用这些函数的地方传递检测置信度

## 修复后的数据流

```
检测阶段
  ↓
inference.postprocess() → confidences (检测置信度)
  ↓
跟踪阶段
  ↓
tracker.update(boxes, class_ids, confidences) → tracks[track_id]['confidence']
  ↓
Alert 创建阶段
  ↓
track.get('confidence', 0.0) → alert['confidence']
  ↓
数据库/云端
  ↓
DetectionResult.confidence → 云端数据库
```

## 验证方法

修复后，云端应该能够收到正确的检测置信度。可以通过以下方式验证：

1. **检查云端数据库**：
```sql
SELECT 
  id, 
  timestamp, 
  confidence,
  detected_class
FROM detections
WHERE timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC
LIMIT 20;
```

2. **预期结果**：
   - 置信度应该在 0.5-1.0 之间（根据检测阈值）
   - 不应该再有大量 0.0 的置信度
   - 置信度应该与检测质量相关

3. **检查日志**：
   - 查看 Jetson 端日志，确认置信度被正确传递
   - 检查 `_save_snapshot_and_upload` 中的 `DetectionResult` 对象

## 注意事项

1. **置信度来源**：
   - 工程车辆：使用检测置信度（YOLO 模型输出的置信度）
   - 社会车辆：使用检测置信度（YOLO 模型输出的置信度）
   - 信标匹配置信度：仅用于信标匹配质量评估，不用于检测置信度

2. **置信度稳定性**：
   - 跟踪器使用最近10帧的置信度历史
   - 使用最高置信度作为稳定值，避免单帧波动

3. **向后兼容**：
   - 所有新增参数都有默认值（0.0），确保向后兼容
   - 如果 track 中没有置信度，会使用默认值 0.0

## 修复日期

2024年（根据实际日期填写）

## 相关文件

- `test_system_realtime.py`：主检测程序
- `jetson-client/detection_result.py`：检测结果数据模型
- `jetson-client/cloud_client.py`：云端客户端

