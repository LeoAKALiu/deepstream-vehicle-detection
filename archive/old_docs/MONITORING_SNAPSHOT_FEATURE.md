# 定时监控截图功能

## 功能说明

当系统没有检测到车辆（包括社会车辆和工程车辆）时，定时上传一张现场高清截图，证明系统正在正常监控。

---

## ✅ 功能特点

1. **定时上传**：在指定间隔（默认10分钟）上传现场截图
2. **高清质量**：使用JPEG质量95，保持高清画质
3. **自动管理**：临时文件自动清理（如果未启用本地保存）
4. **云端标识**：上传时标记为"monitoring_snapshot"类型，便于云端区分

---

## 📋 配置说明

### 配置文件：`config.yaml`

```yaml
cloud:
  enable_monitoring_snapshot: true            # 是否启用定时上传监控截图
  monitoring_snapshot_interval: 600           # 监控截图上传间隔（秒），默认10分钟
```

### 配置项说明

- **enable_monitoring_snapshot**：
  - 类型：`bool`
  - 默认值：`true`
  - 说明：是否启用定时上传监控截图功能

- **monitoring_snapshot_interval**：
  - 类型：`int`
  - 默认值：`600`（10分钟）
  - 说明：监控截图上传间隔（秒）
  - 建议值：
    - 600（10分钟）- 默认，平衡监控频率和服务器负载
    - 300（5分钟）- 更频繁的监控
    - 1800（30分钟）- 降低服务器负载

---

## 🔧 实现细节

### 1. 帧获取回调

在 `test_system_realtime.py` 中设置帧回调函数：

```python
def get_current_frame():
    """获取当前帧的回调函数"""
    try:
        frame = self.depth_camera.get_color_frame()
        return frame
    except Exception as e:
        return None

self.cloud_integration.set_frame_callback(get_current_frame)
```

### 2. 定时上传线程

在 `main_integration.py` 中实现 `_monitoring_snapshot_worker` 线程：

- 定时获取当前帧
- 保存为高质量JPEG（quality=95）
- 上传到云端
- 自动清理临时文件

### 3. 云端上传接口

在 `cloud_client.py` 中实现 `upload_monitoring_snapshot` 方法：

- 支持更大的文件（允许2倍于普通图片的大小）
- 标记为"monitoring_snapshot"类型
- 包含设备ID信息

---

## 📊 数据流

```
定时器触发（每10分钟）
    ↓
获取当前帧（通过回调函数）
    ↓
保存为临时文件（高质量JPEG）
    ↓
上传到云端（标记为monitoring_snapshot）
    ↓
清理临时文件（如果未启用本地保存）
```

---

## 🔍 日志输出

### 正常情况

```
Monitoring snapshot saved: /tmp/monitoring_snapshot_jetson-01_20251209_143022.jpg (2.45MB)
Monitoring snapshot uploaded successfully: 2025-12-09/143022_monitoring_snapshot_jetson-01_20251209_143022.jpg.jpg
```

### 错误情况

```
⚠ No frame available, skipping monitoring snapshot
⚠ Failed to upload monitoring snapshot
```

---

## 🚀 使用说明

### 启用功能

1. **配置文件**：确保 `config.yaml` 中已配置：
   ```yaml
   cloud:
     enable_monitoring_snapshot: true
     monitoring_snapshot_interval: 600
   ```

2. **重启服务**：
   ```bash
   sudo systemctl restart vehicle-detection
   ```

### 验证功能

1. **检查日志**：
   ```bash
   sudo journalctl -u vehicle-detection -f | grep "monitoring snapshot"
   ```

2. **等待上传**：等待10分钟（或配置的间隔时间）

3. **检查云端**：在云端查看是否有新的监控截图上传

---

## ⚙️ 调优建议

### 如果截图太大

1. **降低JPEG质量**（不推荐，影响画质）：
   - 修改 `main_integration.py` 中的 `cv2.IMWRITE_JPEG_QUALITY` 参数

2. **调整上传间隔**：
   - 增加 `monitoring_snapshot_interval` 值

3. **启用压缩**：
   - 系统会自动压缩超过限制的文件

### 如果上传失败

1. **检查网络连接**：
   ```bash
   curl -I http://123.249.9.250:8000/health
   ```

2. **检查API Key**：
   - 确认 `config.yaml` 中的 `api_key` 正确

3. **检查日志**：
   - 查看详细错误信息

---

## 📝 注意事项

1. **帧获取失败**：如果无法获取帧，会跳过本次上传，等待下次定时触发

2. **文件大小限制**：监控截图允许更大的文件（2倍于普通图片），但仍受 `max_image_size_mb` 限制

3. **临时文件清理**：如果 `save_snapshots: false`，临时文件会在上传后自动删除

4. **线程安全**：帧获取回调函数应该是线程安全的

---

## 🔗 相关文档

- `docs/JETSON_IMAGE_API_REQUIREMENTS.md` - 图像接口要求
- `jetson-client/main_integration.py` - 主集成模块
- `jetson-client/cloud_client.py` - 云端客户端

---

**功能状态**：✅ 已实现  
**测试状态**：⏳ 待验证  
**文档版本**：v1.0

