# 图像字段修复说明

## 问题描述

云端无法看到图像，因为传输的 alert 数据中缺少图像相关字段。

## 修复内容

### 1. 修改 `cloud_client.py`

在 `send_alert` 方法中添加了 3 个图像字段参数：

- `snapshot_path`: 本地快照路径
- `snapshot_url`: 云端图片 URL（**推荐使用此字段显示图片**）
- `image_path`: 图片路径（备用字段）

### 2. 修改 `main_integration.py`

调整了上传流程：

1. **先上传图片**：如果检测结果包含图片路径，先调用 `upload_image` 上传图片，获取云端 URL
2. **发送 alert**：将图片 URL 包含在 alert 数据中一起发送
3. **关联图片**：如果图片上传成功且 alert_id 已返回，再次上传图片以关联 alert_id（如果云端需要）

### 3. 更新 API 文档

在 `docs/API_DOCUMENTATION.md` 中更新了图像字段说明，明确：
- `snapshot_url` 是推荐使用的字段，包含云端可访问的图片 URL
- 如果 `snapshot_url` 为 `null`，说明图片上传失败或未启用图片上传功能

## 数据字段说明

### Alert 数据中的图像字段

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `snapshot_path` | string | 本地快照路径 | `"/tmp/vehicle_snapshots/snapshot_101.jpg"` |
| `snapshot_url` | string | **云端图片 URL（推荐使用）** | `"https://cdn.example.com/snapshots/101.jpg"` |
| `image_path` | string | 图片路径（备用） | `"/tmp/vehicle_snapshots/snapshot_101.jpg"` |

### 工作流程

```
检测到车辆
    ↓
保存快照到本地
    ↓
上传图片到云端 → 获取 snapshot_url
    ↓
发送 alert（包含 snapshot_url）
    ↓
（可选）再次上传图片以关联 alert_id
```

## 验证方法

### 1. 检查代码修改

```bash
# 检查 cloud_client.py
grep -A 5 "snapshot_path\|snapshot_url\|image_path" jetson-client/cloud_client.py

# 检查 main_integration.py
grep -A 10 "先上传图片" jetson-client/main_integration.py
```

### 2. 查看云端接收的数据

云端团队可以查询数据库，检查新接收的数据是否包含图像字段：

```sql
SELECT
  id,
  timestamp,
  vehicle_type,
  detected_class,
  snapshot_path,
  snapshot_url,
  image_path
FROM detections
WHERE timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC
LIMIT 10;
```

### 3. 检查日志

```bash
# 查看图像上传日志
tail -f /tmp/vehicle_detection.log | grep -i "image\|snapshot"
```

## 注意事项

1. **图片上传失败处理**：如果图片上传失败，`snapshot_url` 将为 `null`，但 alert 仍会正常发送
2. **配置检查**：确保 `config.yaml` 中 `cloud.enable_image_upload` 为 `true`
3. **网络状况**：图片上传需要网络连接，如果网络不稳定可能导致上传失败
4. **文件大小限制**：图片会自动压缩，确保不超过 `cloud.max_image_size_mb` 限制

## 部署步骤

1. **重启系统以应用修复**：

```bash
# 停止当前进程
pkill -f test_system_realtime

# 等待进程完全停止
sleep 2

# 重新启动
cd /home/liubo/Download/deepstream-vehicle-detection
nohup python test_system_realtime.py --no-display > /tmp/vehicle_detection_startup.log 2>&1 &

# 检查进程
ps aux | grep "test_system_realtime.py --no-display" | grep -v grep
```

2. **验证修复**：

等待 10-15 分钟后，云端团队可以查询数据库验证图像字段是否已包含在数据中。

## 相关文件

- `jetson-client/cloud_client.py` - 云端客户端，包含 `send_alert` 和 `upload_image` 方法
- `jetson-client/main_integration.py` - 集成模块，处理检测结果上传
- `docs/API_DOCUMENTATION.md` - API 文档，包含完整的数据字段说明

## 修复时间

2025-12-05



