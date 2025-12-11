# Jetson端数据修复说明 - 云端开发团队

## 文档版本
v1.0  
**更新日期**: 2024-12-08  
**适用系统**: Jetson端车辆检测系统

---

## 📋 修复概述

本次修复解决了两个关键数据质量问题：

1. **置信度问题**: 2885/2889 条记录的置信度为 0.0，仅 4 条为 0.95
2. **图像分辨率问题**: 前端接收到的图像分辨率过低（320×240）

所有修复已在 2024-12-08 完成并部署。

---

## 🔧 修复1: 置信度问题

### 问题描述

**现象**: 云端收到的检测数据中，2885/2889 条记录的置信度为 0.0，仅 4 条为 0.95。

**根本原因**: 
- 检测置信度在跟踪器中没有被保存
- Alert创建时使用了默认值 0.0 而不是实际的检测置信度
- 工程车辆错误使用了信标匹配置信度而不是检测置信度

### 修复内容

#### 1. 跟踪器保存置信度
- 修改 `VehicleTracker.update()` 方法，保存检测置信度到 track 中
- 维护最近10帧的置信度历史
- 使用最高置信度（最近10帧中的最大值）作为稳定值

#### 2. Alert使用检测置信度
- 所有 alert 现在使用 YOLO 模型输出的检测置信度
- 不再使用信标匹配置信度作为检测置信度
- 社会车辆和工程车辆都使用检测置信度

#### 3. 数据流修复
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

### 修复后的数据格式

**置信度字段 (`confidence`)**:
- **类型**: `float`
- **范围**: `0.0 - 1.0`
- **来源**: YOLO 模型输出的检测置信度
- **说明**: 
  - 工程车辆：使用检测置信度（不是信标匹配置信度）
  - 社会车辆：使用检测置信度
  - 值应该在 0.5-1.0 之间（根据检测阈值 0.5）

### 验证方法

修复后，云端应该能够收到正确的检测置信度。可以通过以下SQL查询验证：

```sql
SELECT 
  id, 
  timestamp, 
  confidence,
  detected_class,
  vehicle_type
FROM detections
WHERE timestamp > NOW() - INTERVAL '15 minutes'
ORDER BY timestamp DESC
LIMIT 20;
```

**预期结果**:
- ✅ 置信度应该在 0.5-1.0 之间（根据检测阈值 0.5）
- ✅ 不应该再有大量 0.0 的置信度
- ✅ 置信度应该与检测质量相关

---

## 🖼️ 修复2: 图像分辨率问题

### 问题描述

**现象**: 前端接收到的图像分辨率很低（320×240），影响显示质量。

**根本原因**:
- 最小分辨率设置过低（320×240）
- 最大分辨率限制过低（1920）
- 压缩质量过低（85-30）
- 文件大小限制过小（5MB），导致过度压缩

### 修复内容

#### 1. 提高最小分辨率
- **之前**: 320×240
- **之后**: **640×480**（提高前端显示质量）

#### 2. 提高最大分辨率限制
- **之前**: 1920（单边最大）
- **之后**: **2560**（支持更高分辨率）

#### 3. 提高压缩质量
- **之前**: 85-30（质量范围）
- **之后**: **95-70**（保持高质量，最低不低于70）

#### 4. 增加文件大小限制
- **之前**: 5MB
- **之后**: **10MB**（支持更高分辨率图像）

### 修复后的图像规格

#### 分辨率范围
- **最小分辨率**: 640×480 像素
- **最大分辨率**: 2560×2560 像素（保持宽高比）
- **推荐分辨率**: 根据原始图像和裁剪区域自动调整

#### 图像质量
- **JPEG质量**: 95-70（优先保持高质量）
- **压缩策略**: 优先保持分辨率，然后调整质量
- **文件大小**: 最大 10MB

#### 图像处理流程
1. **快照裁剪**: 从原始帧（1920×1080）裁剪车辆区域，扩展20%边界
2. **分辨率调整**: 确保最小640×480，最大2560（保持宽高比）
3. **图像压缩**: 
   - 优先保持分辨率
   - 从质量95开始压缩
   - 最低质量不低于70
   - 如果仍然太大，才缩小尺寸（但保持最小640×480）

### 图像字段说明

**相关字段**:
- `snapshot_path`: 本地快照路径
- `snapshot_url`: 云端快照URL（上传后）
- `image_path`: 图片路径（备用字段）

**图像格式**:
- **格式**: JPEG
- **质量**: 95-70
- **颜色空间**: RGB（上传前转换为BGR保存）

### 验证方法

#### 1. 检查图像尺寸
前端接收到的图像应该：
- 最小尺寸：640×480 像素
- 质量：JPEG质量 95-70
- 文件大小：通常 500KB - 2MB（取决于分辨率）

#### 2. 检查图像URL
```sql
SELECT 
  id, 
  timestamp, 
  snapshot_url,
  snapshot_path,
  image_path
FROM detections
WHERE timestamp > NOW() - INTERVAL '15 minutes'
  AND snapshot_url IS NOT NULL
ORDER BY timestamp DESC
LIMIT 10;
```

**预期结果**:
- ✅ `snapshot_url` 字段有值（云端可访问的图片 URL）
- ✅ `snapshot_path` 字段有值（本地路径）
- ✅ 图像分辨率至少 640×480
- ✅ 图像质量清晰，无明显压缩伪影

---

## 📊 数据格式变更总结

### 置信度字段 (`confidence`)

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| **值范围** | 大多为 0.0 | 0.5-1.0（正常范围） |
| **数据来源** | 默认值或信标置信度 | YOLO检测置信度 |
| **数据质量** | 2885/2889 为 0.0 | 正常分布 |

### 图像字段

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| **最小分辨率** | 320×240 | 640×480 |
| **最大分辨率** | 1920 | 2560 |
| **JPEG质量** | 85-30 | 95-70 |
| **文件大小限制** | 5MB | 10MB |
| **图像质量** | 较低 | 高质量 |

---

## 🔍 数据验证SQL查询

### 验证置信度修复

```sql
-- 检查置信度分布
SELECT 
  CASE 
    WHEN confidence = 0.0 THEN '0.0'
    WHEN confidence < 0.5 THEN '< 0.5'
    WHEN confidence < 0.7 THEN '0.5-0.7'
    WHEN confidence < 0.9 THEN '0.7-0.9'
    ELSE '>= 0.9'
  END AS confidence_range,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM detections
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY confidence_range
ORDER BY confidence_range;
```

**预期结果**: 不应该有大量 0.0 的置信度。

### 验证图像分辨率修复

```sql
-- 检查图像URL和路径
SELECT 
  id,
  timestamp,
  detected_class,
  snapshot_url,
  snapshot_path,
  image_path,
  CASE 
    WHEN snapshot_url IS NOT NULL THEN '有URL'
    WHEN snapshot_path IS NOT NULL THEN '仅本地路径'
    ELSE '无图像'
  END AS image_status
FROM detections
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 20;
```

**预期结果**: 
- ✅ 大部分记录应该有 `snapshot_url`
- ✅ 图像应该可以通过 URL 访问
- ✅ 图像分辨率至少 640×480

---

## 📝 API数据格式

### Alert数据格式（POST /api/alerts）

```json
{
  "timestamp": "2024-12-08T13:53:58.795000",
  "vehicle_type": "construction_vehicle",
  "detected_class": "excavator",
  "status": "registered",
  "plate_number": "京A12345",
  "confidence": 0.95,
  "distance": 4.23,
  "is_registered": true,
  "track_id": 1,
  "bbox": {
    "x1": 100,
    "y1": 200,
    "x2": 500,
    "y2": 600
  },
  "beacon_mac": "45:C6:6A:F2:46:13",
  "company": "XX建筑公司",
  "metadata": {
    "rssi": -65,
    "match_cost": 0.12
  },
  "snapshot_path": "/tmp/vehicle_snapshots/snapshot_1_20241208_135358_123.jpg",
  "snapshot_url": "http://123.249.9.250:8000/media/images/snapshot_1_20241208_135358_123.jpg",
  "image_path": "/tmp/vehicle_snapshots/snapshot_1_20241208_135358_123.jpg"
}
```

### 关键字段说明

| 字段 | 类型 | 说明 | 修复后变化 |
|------|------|------|-----------|
| `confidence` | float | 检测置信度 (0.0-1.0) | ✅ 现在使用检测置信度，不再是0.0 |
| `snapshot_url` | string | 云端图像URL | ✅ 图像分辨率至少640×480 |
| `snapshot_path` | string | 本地图像路径 | ✅ 图像分辨率至少640×480 |
| `image_path` | string | 备用图像路径 | ✅ 图像分辨率至少640×480 |

---

## ⚠️ 注意事项

### 置信度字段

1. **置信度来源**: 
   - 所有车辆（工程车辆和社会车辆）都使用 YOLO 模型输出的检测置信度
   - 信标匹配置信度仅用于信标匹配质量评估，不用于检测置信度

2. **置信度稳定性**: 
   - 跟踪器使用最近10帧的置信度历史
   - 使用最高置信度作为稳定值，避免单帧波动

3. **向后兼容**: 
   - 如果 track 中没有置信度（旧数据），会使用默认值 0.0
   - 新检测的车辆都会有正确的置信度

### 图像字段

1. **文件大小**: 
   - 10MB限制可能增加网络传输时间，但图像质量更好
   - 如果网络带宽有限，可以调整 `max_image_size_mb` 配置

2. **存储空间**: 
   - 更高分辨率图像占用更多存储空间
   - 建议定期清理旧图像

3. **网络带宽**: 
   - 如果网络带宽有限，可能需要调整 `max_image_size_mb` 配置
   - 建议监控网络使用情况

4. **性能影响**: 
   - 处理更高分辨率图像可能略微增加CPU占用
   - 但图像质量显著提升

---

## 🔄 数据迁移建议

### 对于已有数据

1. **置信度为0.0的历史数据**:
   - 这些数据无法修复（因为检测时没有保存置信度）
   - 建议在查询时过滤掉置信度为0.0的数据，或者标记为"历史数据"

2. **低分辨率图像**:
   - 历史图像无法自动升级
   - 新检测的图像将使用新的分辨率标准

### 数据清理建议

```sql
-- 标记置信度为0.0的历史数据
UPDATE detections
SET metadata = jsonb_set(
  COALESCE(metadata, '{}'::jsonb),
  '{data_quality}',
  '"legacy"'
)
WHERE confidence = 0.0
  AND timestamp < '2024-12-08 00:00:00';

-- 查询新数据（修复后）
SELECT *
FROM detections
WHERE timestamp >= '2024-12-08 00:00:00'
  AND confidence > 0.0
ORDER BY timestamp DESC;
```

---

## 📞 技术支持

如有问题，请联系：
- **Jetson端开发团队**: 负责数据生成和上传
- **云端开发团队**: 负责数据接收和存储

---

## 📚 相关文档

- `docs/API_DOCUMENTATION.md` - 完整API文档
- `docs/archive/CONFIDENCE_FIX.md` - 置信度修复详细说明
- `docs/archive/IMAGE_RESOLUTION_FIX.md` - 图像分辨率修复详细说明

---

**文档版本**: v1.0  
**最后更新**: 2024-12-08  
**状态**: 已部署并验证


