# 置信度Bug修复说明

## 问题发现

**日期**: 2024年12月8日  
**问题**: 云端收到的所有检测记录的置信度都是 0.0

## 根本原因

代码中存在字段名不一致的问题：

1. **ByteTracker** 返回的 tracks 字典中，置信度字段名为 `'score'`
2. **VehicleTracker** 返回的 tracks 字典中，置信度字段名为 `'confidence'`
3. 代码中统一使用 `track.get('confidence', 0.0)` 获取置信度
4. 当使用 ByteTracker 时，由于字段名不匹配，总是返回默认值 0.0

## 代码位置

### ByteTracker 返回格式

```python
# python_apps/byte_tracker.py 第340-347行
tracks_dict[track.track_id] = {
    'bbox': track.bbox,
    'class': track.class_id,
    'last_seen': track.frame_id,
    'processed': track.processed,
    'score': track.score,  # ⚠️ 字段名是 'score'
    'hits': track.hits
}
```

### VehicleTracker 返回格式

```python
# test_system_realtime.py 第895-903行
current_tracks[best_track_id] = {
    'bbox': box,
    'class': stable_class,
    'confidence': stable_confidence,  # ✅ 字段名是 'confidence'
    'last_seen': frame_id,
    'processed': track['processed'],
    'class_history': track['class_history'],
    'confidence_history': track['confidence_history']
}
```

### 问题代码

```python
# test_system_realtime.py 第2069行（修复前）
detection_confidence = track.get('confidence', 0.0)  # ❌ ByteTracker没有'confidence'字段
```

## 修复方案

统一处理两种跟踪器的字段名差异：

```python
# 修复后：兼容两种跟踪器
detection_confidence = track.get('confidence', track.get('score', 0.0))
```

这样：
- 如果使用 VehicleTracker（有 'confidence' 字段），直接返回
- 如果使用 ByteTracker（有 'score' 字段），会尝试获取 'score'
- 如果都没有，返回默认值 0.0

## 修复位置

修复了以下3处：

1. **第2069行** - 工程车辆批量处理时的置信度获取
2. **第2088行** - 社会车辆异步识别时的置信度获取
3. **第2126行** - 同步处理时的置信度获取

## 验证方法

修复后，应该看到：

1. **置信度分布**：
   - ✅ 大部分记录的置信度在 0.5-1.0 之间
   - ✅ 不应该再有大量 0.0 的置信度
   - ✅ 平均置信度应该 > 0.5

2. **代码检查**：
   ```bash
   # 检查修复后的代码
   grep -n "track.get('confidence', track.get('score'" test_system_realtime.py
   ```

3. **运行时验证**：
   ```python
   # 添加调试输出（临时）
   print(f"DEBUG: track keys = {track.keys()}")
   print(f"DEBUG: detection_confidence = {detection_confidence}")
   ```

## 相关文件

- `test_system_realtime.py` - 主检测程序（已修复）
- `python_apps/byte_tracker.py` - ByteTracker实现
- `docs/DATA_QUALITY_ISSUE_DIAGNOSIS.md` - 云端团队诊断报告
- `docs/DATA_QUALITY_ISSUE_CONFIRMATION.md` - 问题确认报告

---

**修复时间**: 2024年12月8日  
**状态**: ✅ 已修复  
**下一步**: 重启服务并验证修复效果


