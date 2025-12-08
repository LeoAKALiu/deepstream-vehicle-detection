# 服务重启指南

## 当前状态

检测到服务正在运行，需要重启以应用置信度修复。

## 重启方法

### 方法1：使用systemd服务（推荐）⭐

```bash
sudo systemctl restart vehicle-detection
```

### 方法2：使用重启脚本

```bash
bash /tmp/restart_service.sh
```

### 方法3：手动停止并启动

```bash
# 1. 停止systemd服务
sudo systemctl stop vehicle-detection

# 2. 停止所有相关进程
pkill -f test_system_realtime.py

# 3. 确认进程已停止
ps aux | grep test_system_realtime | grep -v grep

# 4. 重新启动服务
sudo systemctl start vehicle-detection
```

## 验证服务状态

### 检查服务是否运行

```bash
sudo systemctl status vehicle-detection
```

### 查看实时日志

```bash
sudo journalctl -u vehicle-detection -f
```

### 查看最近50行日志

```bash
sudo journalctl -u vehicle-detection -n 50
```

## 修复内容

本次重启将应用以下修复：

1. **置信度Bug修复** ✅
   - 修复了ByteTracker和VehicleTracker字段名不一致的问题
   - 现在能正确获取置信度值（不再总是0.0）

2. **图像分辨率优化** ✅
   - 最小分辨率：640×480
   - 最大分辨率：2560
   - JPEG质量：95

## 验证修复效果

重启后，等待15-30分钟，然后检查：

### 1. 检查置信度分布

```sql
SELECT 
    CASE 
        WHEN confidence = 0.0 THEN '0.0'
        WHEN confidence < 0.5 THEN '< 0.5'
        WHEN confidence < 0.7 THEN '0.5-0.7'
        WHEN confidence < 0.9 THEN '0.7-0.9'
        ELSE '>= 0.9'
    END AS range,
    COUNT(*) as count
FROM alerts
WHERE timestamp > datetime('now', '-1 hour')
GROUP BY range;
```

### 2. 检查图像分辨率

- 下载最新的图像文件
- 检查文件大小（应该 > 500KB）
- 检查图像尺寸（应该 >= 640×480）

## 预期结果

修复生效后，应该看到：

- ✅ 大部分记录的置信度在 0.5-1.0 之间
- ✅ 不应该再有大量 0.0 的置信度
- ✅ 平均置信度应该 > 0.5
- ✅ 图像分辨率至少 640×480
- ✅ 文件大小通常在 500KB - 2MB

## 相关文档

- `docs/CONFIDENCE_BUG_FIX.md` - 置信度Bug修复详细说明
- `docs/BUG_FIX_SUMMARY.md` - 修复总结
- `docs/DATA_QUALITY_ISSUE_DIAGNOSIS.md` - 云端团队诊断报告

---

**创建时间**: 2024年12月8日  
**状态**: ⏳ 等待重启服务

