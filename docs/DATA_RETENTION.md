# 系统数据留存清单

## 📊 数据留存概览

系统在运行过程中会保存以下类型的数据：

---

## 1. 检测结果数据库

### 位置
- **文件路径**: `detection_results.db` (项目根目录)
- **数据库类型**: SQLite
- **当前大小**: 28KB (已有数据)

### 存储内容
- ✅ 检测时间戳
- ✅ 跟踪ID (track_id)
- ✅ 车辆类型 (vehicle_type)
- ✅ 检测类别 (detected_class)
- ✅ 状态 (status: registered/unregistered/civilian)
- ✅ 信标MAC地址 (beacon_mac)
- ✅ 车牌号 (plate_number)
- ✅ 所属公司 (company)
- ✅ 距离 (distance)
- ✅ 置信度 (confidence)
- ✅ 边界框坐标 (bbox_x1, bbox_y1, bbox_x2, bbox_y2)
- ✅ 快照路径 (snapshot_path)
- ✅ 元数据 (metadata: JSON格式，包含RSSI、匹配代价等)

### 查看方法
```bash
# 查看数据库大小
ls -lh detection_results.db

# 查看记录数
sqlite3 detection_results.db "SELECT COUNT(*) FROM detections;"

# 查看最近10条记录
sqlite3 detection_results.db "SELECT * FROM detections ORDER BY timestamp DESC LIMIT 10;"

# 导出为CSV
sqlite3 detection_results.db ".mode csv" ".output detections.csv" "SELECT * FROM detections;"
```

### 清理策略
- 默认保留所有数据
- 可通过 `cleanup_old_data.sh` 脚本按时间清理
- 建议定期备份

---

## 2. 应用日志文件

### 位置
- **主日志**: `/tmp/vehicle_detection.log`
- **告警日志**: `/tmp/vehicle_alerts.json`
- **启动日志**: `logs/startup.log`

### 存储内容
- ✅ 系统启动/停止事件
- ✅ 检测事件详情
- ✅ 错误和警告信息
- ✅ 性能指标（FPS、延迟等）
- ✅ 硬件状态变化
- ✅ 网络连接状态

### 日志配置
- **日志级别**: INFO (可在config.yaml中修改)
- **文件大小限制**: 10MB (单个文件)
- **备份数量**: 5个 (自动轮转)
- **日志轮转**: 已配置logrotate

### 查看方法
```bash
# 查看主日志
tail -f /tmp/vehicle_detection.log

# 查看告警日志
cat /tmp/vehicle_alerts.json | jq .

# 查看启动日志
tail -f logs/startup.log

# 查看systemd日志
sudo journalctl -u vehicle-detection -f
```

### 清理策略
- 自动轮转（logrotate）
- 保留30天日志
- 自动压缩旧日志

---

## 3. 车辆快照图片

### 位置
- **目录**: `/tmp/vehicle_snapshots/`
- **文件格式**: JPG
- **命名规则**: `snapshot_{track_id}_{timestamp}.jpg`

### 存储内容
- ✅ 检测到的车辆图片（裁剪后）
- ✅ 包含边界框扩展区域（10%边距）
- ✅ 每辆车保存一张快照

### 配置
- **保存开关**: `config.yaml` → `cloud.save_snapshots: true`
- **上传开关**: `config.yaml` → `cloud.enable_image_upload: true`
- **最大大小**: 5MB (上传前自动压缩)

### 查看方法
```bash
# 查看快照目录
ls -lh /tmp/vehicle_snapshots/

# 统计快照数量
find /tmp/vehicle_snapshots -name "*.jpg" | wc -l

# 查看最新快照
ls -lt /tmp/vehicle_snapshots/ | head -5
```

### 清理策略
- 默认保留7天（可在cleanup脚本中配置）
- 磁盘空间不足时自动清理
- 已上传的快照可提前清理

---

## 4. 性能报告文件

### 位置
- **目录**: `reports/`
- **文件格式**: JSON
- **命名规则**:
  - 日报: `daily_report_YYYYMMDD.json`
  - 周报: `weekly_report_YYYYMMDD.json`
  - 月报: `monthly_report_YYYYMM.json`

### 存储内容
- ✅ 总检测数
- ✅ 总车辆数
- ✅ 已备案/未备案车辆统计
- ✅ 车辆类型分布
- ✅ 时间分布（按小时）
- ✅ 检测率（次/小时）
- ✅ 系统统计信息

### 生成方法
```bash
# 生成日报
python3 scripts/generate_daily_report.py

# 查看报告
cat reports/daily_report_*.json | jq .
```

### 清理策略
- 建议保留所有报告（文件较小）
- 可按需手动清理

---

## 5. 系统监控日志

### 位置
- **看门狗日志**: `logs/watchdog.log`
- **资源监控日志**: `logs/resource_monitor.log`
- **清理日志**: `logs/cleanup.log`

### 存储内容
- ✅ 看门狗监控事件
- ✅ 资源使用情况（CPU、内存、GPU、磁盘）
- ✅ 数据清理操作记录
- ✅ 告警和错误信息

### 查看方法
```bash
# 查看看门狗日志
tail -f logs/watchdog.log

# 查看资源监控日志
tail -f logs/resource_monitor.log

# 查看清理日志
tail -f logs/cleanup.log
```

### 清理策略
- 自动轮转
- 保留30天

---

## 6. 临时文件

### 位置
- **共享RGB帧**: `/tmp/orbbec_shared_frame.npy`
- **共享深度帧**: `/tmp/orbbec_shared_depth.npy`

### 存储内容
- ✅ 当前帧的RGB数据（NumPy数组）
- ✅ 当前帧的深度数据（NumPy数组）
- ✅ 用于录制脚本共享数据

### 特点
- 实时更新（每次检测后）
- 临时文件（程序退出后删除）
- 不占用大量空间（单帧数据）

### 清理策略
- 程序启动时自动清理
- 程序退出时自动删除

---

## 7. Systemd服务日志

### 位置
- **日志系统**: systemd journal
- **查看命令**: `journalctl -u vehicle-detection`

### 存储内容
- ✅ 服务启动/停止事件
- ✅ 标准输出和错误输出
- ✅ 系统级日志

### 查看方法
```bash
# 实时查看
sudo journalctl -u vehicle-detection -f

# 查看最近50行
sudo journalctl -u vehicle-detection -n 50

# 查看最近1小时
sudo journalctl -u vehicle-detection --since "1 hour ago"

# 导出日志
sudo journalctl -u vehicle-detection > service_log.txt
```

### 清理策略
- systemd自动管理
- 默认保留一定时间（取决于系统配置）

---

## 📁 数据文件位置汇总

| 数据类型 | 路径 | 大小估算 | 保留策略 |
|---------|------|---------|---------|
| 检测数据库 | `detection_results.db` | ~1KB/条记录 | 永久保留（建议备份） |
| 应用日志 | `/tmp/vehicle_detection.log` | ~10MB/文件 | 30天，自动轮转 |
| 告警日志 | `/tmp/vehicle_alerts.json` | ~1KB/条告警 | 30天 |
| 车辆快照 | `/tmp/vehicle_snapshots/*.jpg` | ~100KB/张 | 7天，可配置 |
| 性能报告 | `reports/*.json` | ~10KB/份 | 永久保留 |
| 监控日志 | `logs/*.log` | ~1MB/文件 | 30天，自动轮转 |
| 临时文件 | `/tmp/orbbec_shared_*.npy` | ~10MB | 程序运行时 |

---

## 💾 数据大小估算

### 单日数据量（假设）
- **检测记录**: 100条 → ~100KB
- **日志文件**: ~10MB
- **快照图片**: 50张 → ~5MB
- **报告文件**: ~10KB
- **总计**: ~15MB/天

### 月度数据量
- **检测记录**: 3000条 → ~3MB
- **日志文件**: ~300MB（轮转后）
- **快照图片**: 1500张 → ~150MB（7天保留）
- **报告文件**: ~300KB
- **总计**: ~450MB/月

---

## 🔧 数据管理命令

### 查看数据统计
```bash
# 查看数据库记录数
sqlite3 detection_results.db "SELECT COUNT(*) FROM detections;"

# 查看快照数量
find /tmp/vehicle_snapshots -name "*.jpg" | wc -l

# 查看磁盘使用
du -sh detection_results.db /tmp/vehicle_snapshots reports/ logs/
```

### 清理旧数据
```bash
# 运行清理脚本
bash scripts/cleanup_old_data.sh

# 手动清理快照（保留7天）
find /tmp/vehicle_snapshots -name "*.jpg" -mtime +7 -delete
```

### 备份数据
```bash
# 备份数据库
cp detection_results.db backups/detection_results_$(date +%Y%m%d).db

# 备份报告
tar -czf backups/reports_$(date +%Y%m%d).tar.gz reports/

# 备份日志
tar -czf backups/logs_$(date +%Y%m%d).tar.gz logs/
```

---

## ⚠️ 注意事项

1. **/tmp目录清理**
   - `/tmp` 目录可能在系统重启后清空
   - 建议将重要数据保存到项目目录

2. **磁盘空间监控**
   - 定期检查磁盘使用率
   - 使用 `cleanup_old_data.sh` 自动清理

3. **数据备份**
   - 定期备份数据库文件
   - 重要快照建议单独保存

4. **云端上传**
   - 快照和告警会上传到云端
   - 本地保留取决于 `cloud.save_snapshots` 配置

---

## 📊 当前数据状态

运行以下命令查看当前数据状态：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

echo "=== 数据库 ==="
ls -lh detection_results.db 2>/dev/null || echo "不存在"
sqlite3 detection_results.db "SELECT COUNT(*) FROM detections;" 2>/dev/null || echo "无记录"

echo ""
echo "=== 日志文件 ==="
ls -lh /tmp/vehicle_detection.log /tmp/vehicle_alerts.json 2>/dev/null | awk '{print $9, $5}' || echo "不存在"

echo ""
echo "=== 快照 ==="
du -sh /tmp/vehicle_snapshots 2>/dev/null || echo "目录不存在"
find /tmp/vehicle_snapshots -name "*.jpg" 2>/dev/null | wc -l | awk '{print "快照数量: "$1}'

echo ""
echo "=== 报告 ==="
ls -lh reports/*.json 2>/dev/null | wc -l | awk '{print "报告数量: "$1}' || echo "无报告"

echo ""
echo "=== 监控日志 ==="
du -sh logs/ 2>/dev/null || echo "目录不存在"
```

