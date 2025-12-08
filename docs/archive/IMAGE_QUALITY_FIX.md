# 图像质量问题修复

## 问题描述

云端收到的图像存在以下问题：
1. **低分辨率**：图像分辨率过低
2. **识别类别错误**：同一张图像或同一辆车识别出多种类别
3. **色彩空间问题**：图像色彩异常

## 修复方案

### 1. 色彩空间修复 ✅

**问题**：
- `orbbec_depth.py` 的 `get_color_frame()` 返回 RGB 格式
- 但保存时色彩空间转换逻辑不够清晰

**修复**：
- 明确标注 frame 来自 Orbbec 相机，始终是 RGB 格式
- 保存时统一转换为 BGR（OpenCV `imwrite` 需要 BGR）
- 使用高质量 JPEG 保存（quality=95）

**修改文件**：`test_system_realtime.py` - `_save_snapshot_and_upload` 方法

```python
# frame来自Orbbec相机，始终是RGB格式，需要转换为BGR保存（OpenCV imwrite需要BGR）
if len(snapshot.shape) == 3 and snapshot.shape[2] == 3:
    # RGB -> BGR
    snapshot_bgr = cv2.cvtColor(snapshot, cv2.COLOR_RGB2BGR)
    # 使用高质量JPEG保存（quality=95）
    cv2.imwrite(snapshot_path, snapshot_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
```

### 2. 分辨率修复 ✅

**问题**：
- 裁剪区域可能很小，导致保存的图片分辨率过低
- 压缩函数没有最小分辨率限制

**修复**：
- 添加最小分辨率限制（320x240）
- 如果裁剪区域太小，按比例放大到最小尺寸
- 扩展边界从 10% 增加到 20%，增加更多上下文
- 压缩函数也添加最小分辨率保护

**修改文件**：
- `test_system_realtime.py` - `_save_snapshot_and_upload` 方法
- `jetson-client/cloud_client.py` - `_compress_image` 方法

```python
# 确保最小分辨率（至少320x240）
min_width, min_height = 320, 240
if snapshot.shape[0] < min_height or snapshot.shape[1] < min_width:
    # 如果裁剪区域太小，按比例放大到最小尺寸
    scale = max(min_width / snapshot.shape[1], min_height / snapshot.shape[0])
    new_width = int(snapshot.shape[1] * scale)
    new_height = int(snapshot.shape[0] * scale)
    snapshot = cv2.resize(snapshot, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
```

### 3. 检测类别一致性修复 ✅

**问题**：
- 同一辆车在不同帧中被识别为不同类别
- 跟踪器只匹配相同类别的检测，导致类别切换时创建新track

**修复**：
- 添加类别历史记录（保留最近10帧）
- 使用多数投票机制选择最稳定的类别
- 允许不同类别匹配（但需要更高的IoU阈值）
- 跟踪器使用稳定类别而不是单帧检测类别

**修改文件**：`test_system_realtime.py` - `VehicleTracker.update` 方法

```python
# 更新类别历史（保留最近10帧）
if 'class_history' not in track:
    track['class_history'] = []
track['class_history'].append(class_id)
if len(track['class_history']) > 10:
    track['class_history'].pop(0)

# 使用稳定的类别（多数投票）
stable_class = self._get_stable_class(track.get('class_history', [class_id]))
```

## 修复效果

### 色彩空间
- ✅ 确保 RGB -> BGR 转换正确
- ✅ 使用高质量 JPEG 保存（quality=95）

### 分辨率
- ✅ 最小分辨率：320x240
- ✅ 最大分辨率：1920（保持宽高比）
- ✅ 边界扩展：20%（增加上下文）

### 类别一致性
- ✅ 类别历史记录（最近10帧）
- ✅ 多数投票选择稳定类别
- ✅ 减少同一辆车识别为不同类别的问题

## 验证方法

1. **检查图像分辨率**：
   ```bash
   find /tmp/vehicle_snapshots -name "*.jpg" -exec identify {} \; | head -5
   ```

2. **检查图像色彩**：
   ```bash
   # 查看最新快照
   ls -lt /tmp/vehicle_snapshots/*.jpg | head -1 | awk '{print $NF}' | xargs file
   ```

3. **检查类别一致性**：
   ```bash
   # 查看数据库中的类别记录
   sqlite3 detection_results.db "SELECT track_id, detected_class, COUNT(*) as count FROM detections GROUP BY track_id, detected_class ORDER BY track_id, count DESC;"
   ```

## 需要重启系统

修复后需要重启系统以应用更改：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
pkill -f "test_system_realtime.py --no-display"
nohup python test_system_realtime.py --no-display > /tmp/vehicle_detection_startup.log 2>&1 &
```

## 注意事项

1. **最小分辨率**：320x240 是最低要求，如果原始裁剪区域更小，会被放大
2. **类别稳定性**：需要至少3-5帧才能稳定类别，新检测的车辆可能在前几帧类别不稳定
3. **文件大小**：提高JPEG质量会增加文件大小，但压缩函数会确保不超过5MB限制

