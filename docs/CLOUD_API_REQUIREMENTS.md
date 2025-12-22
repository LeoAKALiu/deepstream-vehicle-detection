# 云端服务器 API 需求文档

**版本**: v1.0  
**更新时间**: 2025-12-22  
**目标**: 说明前端页面"查看统计日期"功能所需的云端API端点

---

## 问题描述

前端页面左侧有"查看统计日期"功能，用户选择日期后无法看到历史检测数据。这是因为云端服务器缺少查询历史数据的API端点。

---

## 需要的API端点

### 1. 查询历史警报（按日期）

**端点**: `GET /api/alerts`

**说明**: 查询指定日期范围内的历史警报数据

**请求参数** (Query Parameters):

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `date` | string | 否 | 日期（YYYY-MM-DD格式），如果提供则查询该日期的数据 | `2025-12-21` |
| `start_date` | string | 否 | 开始日期（YYYY-MM-DD格式） | `2025-12-20` |
| `end_date` | string | 否 | 结束日期（YYYY-MM-DD格式） | `2025-12-22` |
| `vehicle_type` | string | 否 | 车辆类型过滤（`construction_vehicle` 或 `social_vehicle`） | `construction_vehicle` |
| `status` | string | 否 | 状态过滤（`registered`, `unregistered`, `identified`, `identifying`, `failed`） | `unregistered` |
| `limit` | integer | 否 | 返回记录数限制（默认100，最大1000） | `50` |
| `offset` | integer | 否 | 分页偏移量（默认0） | `0` |

**请求示例**:
```
GET /api/alerts?date=2025-12-21&vehicle_type=construction_vehicle&status=unregistered&limit=50
```

**响应格式**:
```json
{
  "status": "success",
  "total": 156,
  "count": 50,
  "offset": 0,
  "data": [
    {
      "id": 12345,
      "timestamp": "2025-12-21T09:15:30.123456",
      "track_id": 101,
      "vehicle_type": "construction_vehicle",
      "detected_class": "excavator",
      "status": "unregistered",
      "confidence": 0.95,
      "distance": 6.5,
      "bbox": {
        "x1": 100,
        "y1": 200,
        "x2": 500,
        "y2": 600
      },
      "beacon_mac": null,
      "company": null,
      "plate_number": null,
      "snapshot_url": "https://cdn.example.com/snapshots/101.jpg",
      "metadata": null
    },
    {
      "id": 12346,
      "timestamp": "2025-12-21T09:20:15.234567",
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
      "snapshot_url": "https://cdn.example.com/snapshots/102.jpg",
      "metadata": null
    }
  ]
}
```

**错误响应**:
```json
{
  "status": "error",
  "message": "Invalid date format. Expected YYYY-MM-DD"
}
```

---

### 2. 查询统计信息（按日期）

**端点**: `GET /api/stats`

**说明**: 查询指定日期范围内的统计信息

**请求参数** (Query Parameters):

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `date` | string | 否 | 日期（YYYY-MM-DD格式），如果提供则查询该日期的统计 | `2025-12-21` |
| `start_date` | string | 否 | 开始日期（YYYY-MM-DD格式） | `2025-12-20` |
| `end_date` | string | 否 | 结束日期（YYYY-MM-DD格式） | `2025-12-22` |

**请求示例**:
```
GET /api/stats?date=2025-12-21
```

**响应格式**:
```json
{
  "status": "success",
  "date": "2025-12-21",
  "total_count": 156,
  "by_type": {
    "construction_vehicle": 89,
    "social_vehicle": 67
  },
  "by_status": {
    "registered": 45,
    "unregistered": 44,
    "identified": 52,
    "identifying": 10,
    "failed": 5
  },
  "by_detected_class": {
    "excavator": 25,
    "bulldozer": 18,
    "roller": 12,
    "loader": 15,
    "dump-truck": 8,
    "concrete-mixer": 5,
    "pump-truck": 3,
    "truck": 2,
    "crane": 1,
    "car": 67
  },
  "time_range": {
    "start": "2025-12-21T00:00:00",
    "end": "2025-12-21T23:59:59"
  }
}
```

---

### 3. 查询监控截图（按日期）

**端点**: `GET /api/monitoring-snapshots`

**说明**: 查询指定日期范围内的监控截图

**请求参数** (Query Parameters):

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `date` | string | 否 | 日期（YYYY-MM-DD格式） | `2025-12-21` |
| `start_date` | string | 否 | 开始日期（YYYY-MM-DD格式） | `2025-12-20` |
| `end_date` | string | 否 | 结束日期（YYYY-MM-DD格式） | `2025-12-22` |
| `limit` | integer | 否 | 返回记录数限制（默认50，最大200） | `50` |
| `offset` | integer | 否 | 分页偏移量（默认0） | `0` |

**请求示例**:
```
GET /api/monitoring-snapshots?date=2025-12-21&limit=50
```

**响应格式**:
```json
{
  "status": "success",
  "total": 120,
  "count": 50,
  "offset": 0,
  "data": [
    {
      "id": 1001,
      "timestamp": "2025-12-21T09:53:20.123456",
      "image_url": "https://cdn.example.com/monitoring/2025-12-21/09-53-20.jpg",
      "file_size": 283456,
      "device_id": "jetson-001"
    },
    {
      "id": 1002,
      "timestamp": "2025-12-21T09:43:17.234567",
      "image_url": "https://cdn.example.com/monitoring/2025-12-21/09-43-17.jpg",
      "file_size": 294567,
      "device_id": "jetson-001"
    }
  ]
}
```

---

## 日期处理说明

### 日期格式
- 所有日期参数使用 `YYYY-MM-DD` 格式（例如：`2025-12-21`）
- 如果只提供 `date` 参数，查询该日期的全天数据（00:00:00 到 23:59:59）
- 如果提供 `start_date` 和 `end_date`，查询该日期范围内的数据

### 时区处理
- 建议使用UTC时区存储和查询
- 前端可以根据用户时区进行转换显示

### 示例

**查询单日数据**:
```
GET /api/alerts?date=2025-12-21
```
等价于：
```
GET /api/alerts?start_date=2025-12-21&end_date=2025-12-21
```

**查询日期范围**:
```
GET /api/alerts?start_date=2025-12-20&end_date=2025-12-22
```

---

## 数据库查询建议

### SQL查询示例

**查询指定日期的警报**:
```sql
SELECT * FROM alerts 
WHERE DATE(timestamp) = '2025-12-21'
ORDER BY timestamp DESC
LIMIT 50;
```

**查询日期范围的警报**:
```sql
SELECT * FROM alerts 
WHERE DATE(timestamp) >= '2025-12-20' 
  AND DATE(timestamp) <= '2025-12-22'
ORDER BY timestamp DESC
LIMIT 50;
```

**统计指定日期的数据**:
```sql
SELECT 
  COUNT(*) as total_count,
  vehicle_type,
  status,
  detected_class,
  COUNT(*) as count
FROM alerts
WHERE DATE(timestamp) = '2025-12-21'
GROUP BY vehicle_type, status, detected_class;
```

---

## 前端集成建议

### 日期选择器处理

前端应该：
1. 用户选择日期后，调用 `GET /api/alerts?date=YYYY-MM-DD`
2. 同时调用 `GET /api/stats?date=YYYY-MM-DD` 获取统计信息
3. 如果查看监控截图页面，调用 `GET /api/monitoring-snapshots?date=YYYY-MM-DD`

### 错误处理

- 如果API返回错误，显示友好的错误消息
- 如果查询结果为空，显示"该日期暂无数据"
- 如果日期格式无效，提示用户选择正确的日期格式

---

## 测试建议

### 测试用例

1. **正常查询**:
   ```
   GET /api/alerts?date=2025-12-21
   ```
   预期：返回该日期的所有警报数据

2. **日期范围查询**:
   ```
   GET /api/alerts?start_date=2025-12-20&end_date=2025-12-22
   ```
   预期：返回该日期范围内的所有警报数据

3. **过滤查询**:
   ```
   GET /api/alerts?date=2025-12-21&vehicle_type=construction_vehicle&status=unregistered
   ```
   预期：返回该日期、车辆类型和状态的警报数据

4. **无效日期格式**:
   ```
   GET /api/alerts?date=2025/12/21
   ```
   预期：返回400错误，提示日期格式错误

5. **无数据日期**:
   ```
   GET /api/alerts?date=2025-01-01
   ```
   预期：返回空数组（`{"status": "success", "total": 0, "count": 0, "data": []}`）

---

## 优先级

**高优先级**（必须实现）:
- ✅ `GET /api/alerts` - 查询历史警报（按日期）
- ✅ `GET /api/stats` - 查询统计信息（按日期）

**中优先级**（建议实现）:
- ⚠️ `GET /api/monitoring-snapshots` - 查询监控截图（按日期）

---

## 联系信息

**Jetson端负责人**: liubo  
**云端平台负责人**: [待填写]  
**技术支持**: [待填写]

---

**最后更新**: 2025-12-22  
**文档版本**: v1.0


