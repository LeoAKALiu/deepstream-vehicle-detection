# 置信度修复 - 系统重启确认

## 重启时间
2024-12-07 21:30

## 修复内容
已应用置信度传递修复，修复了以下问题：
1. ✅ 跟踪器保存检测置信度到 track
2. ✅ Alert 创建时使用检测置信度
3. ✅ 工程车辆传递检测置信度
4. ✅ 社会车辆添加检测置信度

## 重启状态
- ✅ 检测程序已重启
- ✅ 程序正在运行
- ⚠️ 注意：heartbeat API 返回 404（这是正常的，如果云端未实现该接口）

## 验证方法

### 1. 检查程序运行状态
```bash
ps aux | grep test_system_realtime.py | grep -v grep
```

### 2. 检查日志
```bash
tail -f /tmp/vehicle_detection_restart.log
```

### 3. 云端验证（等待 10-15 分钟后）
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

## 预期结果

修复后，云端应该能够收到正确的检测置信度：
- ✅ 置信度应该在 0.5-1.0 之间（根据检测阈值 0.5）
- ✅ 不应该再有大量 0.0 的置信度
- ✅ 置信度应该与检测质量相关

## 注意事项

1. **置信度来源**：
   - 所有车辆（工程车辆和社会车辆）都使用 YOLO 模型输出的检测置信度
   - 信标匹配置信度仅用于信标匹配质量评估，不用于检测置信度

2. **置信度稳定性**：
   - 跟踪器使用最近10帧的置信度历史
   - 使用最高置信度作为稳定值，避免单帧波动

3. **向后兼容**：
   - 如果 track 中没有置信度（旧数据），会使用默认值 0.0
   - 新检测的车辆都会有正确的置信度

## 相关文件
- `CONFIDENCE_FIX.md`：详细修复说明
- `test_system_realtime.py`：主检测程序（已修复）

