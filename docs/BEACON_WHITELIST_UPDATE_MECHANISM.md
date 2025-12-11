# 信标白名单更新机制说明

## 📋 更新机制概述

信标白名单支持从云端API实时获取，具有以下更新机制：

### 1. 自动更新（后台线程）

- **更新间隔**: 默认60秒（可在`config.yaml`中配置）
- **更新方式**: 后台线程定期从云端API获取最新白名单
- **更新位置**: `test_system_realtime.py` 中的 `update_whitelist_periodically()` 函数

### 2. 按需更新（检测时）

- **触发时机**: 当检测到工程车辆并需要匹配信标时
- **更新条件**: 如果距离上次更新超过更新间隔，会自动更新
- **更新位置**: `BeaconWhitelistManager.match_beacon()` 方法

### 3. 强制更新（手动刷新）

- **触发方式**: 调用 `BeaconFilter.refresh_whitelist(force_update=True)`
- **使用场景**: 需要立即获取最新配置时

---

## ⚙️ 配置说明

### config.yaml

```yaml
cloud:
  beacon_whitelist_update_interval: 60  # 更新间隔（秒），默认60秒（1分钟）
  enable_cloud_whitelist: true          # 是否启用云端白名单
```

### 更新间隔建议

- **实时性要求高**: 30-60秒（推荐60秒）
- **平衡性能**: 60-120秒
- **减少网络请求**: 300秒（5分钟）

---

## 🔍 如何查看最新配置

### 1. 检查更新状态

查看日志中的白名单更新信息：

```bash
tail -f /tmp/vehicle_detection.log | grep "白名单"
```

### 2. 查看当前白名单

在代码中可以通过以下方式查看：

```python
# 获取白名单统计信息
stats = cloud_whitelist_manager.get_stats()
print(f"总信标数: {stats['total_beacons']}")
print(f"最后更新时间: {stats['last_update_time']}")
print(f"更新间隔: {stats['update_interval']}秒")
```

### 3. 手动强制更新

如果需要立即获取最新配置，可以：

1. **重启服务**（最简单）:
   ```bash
   sudo systemctl restart vehicle-detection
   ```

2. **在代码中调用**（如果支持）:
   ```python
   beacon_filter.refresh_whitelist(force_update=True)
   ```

---

## 🐛 常见问题

### Q1: 前端配置了信标，但Jetson端没有看到

**可能原因**:
1. 更新间隔太长，需要等待
2. API调用失败（网络问题、API密钥错误等）
3. 白名单更新线程未启动

**解决方法**:
1. 检查日志: `tail -f /tmp/vehicle_detection.log | grep "白名单"`
2. 检查配置: 确认 `enable_cloud_whitelist: true` 和 `beacon_whitelist_update_interval` 设置
3. 重启服务: `sudo systemctl restart vehicle-detection`
4. 缩短更新间隔: 将 `beacon_whitelist_update_interval` 改为 60 秒

### Q2: 更新间隔已经设置很短，但还是看不到最新配置

**可能原因**:
1. API调用失败但没有明显错误
2. 白名单数据格式不正确
3. MAC地址格式不匹配

**解决方法**:
1. 检查API连接: 确认 `api_base_url` 和 `api_key` 正确
2. 查看详细日志: 检查是否有API错误信息
3. 验证MAC地址格式: 确保云端存储的MAC地址格式正确（XX:XX:XX:XX:XX:XX）

### Q3: 如何确认白名单是否从云端获取

**检查方法**:
1. 查看启动日志: 应该看到 "✅ 云端白名单管理器初始化成功"
2. 查看白名单数量: 启动时显示 "📝 白名单: N 个信标 (云端)"
3. 查看更新日志: 定期更新时应该看到 "✅ 白名单已自动更新"

---

## 📊 更新流程

```
1. 前端配置信标
   ↓
2. 数据保存到云端数据库
   ↓
3. Jetson端后台线程定期请求 /api/beacons
   ↓
4. 获取最新白名单数据
   ↓
5. 更新本地缓存
   ↓
6. 更新BeaconFilter中的白名单
   ↓
7. 下次检测时使用最新白名单匹配
```

---

## 🔧 优化建议

### 1. 缩短更新间隔

如果前端配置后需要立即生效，可以：
- 将 `beacon_whitelist_update_interval` 设置为 30-60 秒
- 注意：过短的间隔会增加网络请求，可能影响性能

### 2. 添加手动刷新接口

可以添加一个API接口或命令行工具，允许手动触发白名单更新：

```python
# 在代码中添加
def force_refresh_whitelist():
    if self.cloud_whitelist_manager:
        self.cloud_whitelist_manager.fetch_whitelist()
        if self.beacon_filter:
            self.beacon_filter.refresh_whitelist(force_update=False)
```

### 3. 添加更新通知

可以在更新成功时记录更详细的日志，包括：
- 更新前后的信标数量
- 新增/删除的信标MAC地址
- 更新时间戳

---

## 📝 相关文件

- `jetson-client/beacon_whitelist.py` - 白名单管理器
- `python_apps/beacon_filter.py` - 信标过滤器
- `test_system_realtime.py` - 主程序（包含更新线程）
- `config.yaml` - 配置文件

---

**最后更新**: 2025-12-09  
**版本**: v1.1


