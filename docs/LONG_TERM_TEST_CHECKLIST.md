# 长期测试准备清单

## 📋 测试前检查

### ✅ 1. 系统自启动配置

- [x] Systemd服务已安装并启用
- [x] 启动脚本已配置
- [x] 硬件检查脚本已就绪
- [x] 网络检查脚本已就绪

**验证命令**：
```bash
systemctl is-enabled vehicle-detection  # 应返回 "enabled"
systemctl status vehicle-detection      # 检查服务状态
```

### ✅ 2. 网络配置

- [x] Cassia IP已更新为 `192.168.3.26`
- [x] Jetson IP: `192.168.3.243` (DHCP)
- [x] 网关: `192.168.3.1`
- [x] 外网连接正常
- [x] Cassia连通性测试通过

**验证命令**：
```bash
bash scripts/test_cassia_connectivity.sh
```

### ✅ 3. 硬件检查

- [ ] Orbbec相机连接正常
- [ ] Cassia路由器连接正常
- [ ] GPU可用（TensorRT）
- [ ] 磁盘空间充足（至少20%可用）

**验证命令**：
```bash
bash scripts/check_hardware.sh
bash scripts/check_network.sh
```

### ✅ 4. 配置文件检查

- [x] `config.yaml` 已更新
- [x] Cassia IP配置正确
- [x] 云端配置已设置
- [x] 数据库路径已配置
- [x] 日志路径已配置

**验证命令**：
```bash
grep -A 1 "network:" config.yaml
grep -A 5 "cloud:" config.yaml
```

### ✅ 5. 数据存储配置

- [x] 数据库路径: `detection_results.db`
- [x] 日志路径: `/tmp/vehicle_detection.log`
- [x] 快照目录: `/tmp/vehicle_snapshots`
- [x] 日志轮转已配置

**验证命令**：
```bash
ls -lh detection_results.db 2>/dev/null || echo "数据库文件不存在（首次运行正常）"
df -h /tmp  # 检查/tmp目录空间
```

### ✅ 6. 云端集成

- [x] 云端服务器地址已配置
- [x] API密钥已配置
- [x] 心跳机制已实现
- [x] 报告生成已实现

**验证命令**：
```bash
python3 scripts/test_cloud_connection.py
```

### ✅ 7. 监控和恢复机制

- [x] 看门狗脚本已就绪
- [x] 资源监控脚本已就绪
- [x] 硬件恢复模块已集成
- [x] 网络恢复模块已集成

**验证命令**：
```bash
bash scripts/system_status.sh
```

---

## 🚀 启动长期测试

### 步骤1：最终检查

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 1. 检查服务状态
systemctl status vehicle-detection

# 2. 检查硬件
bash scripts/check_hardware.sh

# 3. 检查网络
bash scripts/check_network.sh

# 4. 检查系统状态
bash scripts/system_status.sh
```

### 步骤2：启动服务

**方式1：使用systemd服务（推荐）**
```bash
sudo systemctl start vehicle-detection
sudo systemctl status vehicle-detection
```

**方式2：手动启动（用于调试）**
```bash
bash scripts/start_vehicle_detection.sh
```

### 步骤3：验证运行状态

```bash
# 查看服务日志
sudo journalctl -u vehicle-detection -f

# 查看系统状态
bash scripts/system_status.sh

# 查看资源使用
bash scripts/monitor_resources.sh
```

---

## 📊 测试期间监控

### 每日检查项

1. **服务状态**
   ```bash
   systemctl status vehicle-detection
   ```

2. **系统资源**
   ```bash
   bash scripts/monitor_resources.sh
   ```

3. **检测统计**
   ```bash
   python3 scripts/generate_daily_report.py
   ```

4. **云端连接**
   ```bash
   # 检查云端心跳是否正常
   # 查看云端服务器日志
   ```

### 每周检查项

1. **数据备份**
   ```bash
   # 备份数据库
   cp detection_results.db backups/detection_results_$(date +%Y%m%d).db
   
   # 备份配置文件
   cp config.yaml backups/config_$(date +%Y%m%d).yaml
   ```

2. **日志清理**
   ```bash
   bash scripts/cleanup_old_data.sh
   ```

3. **性能报告**
   ```bash
   python3 scripts/generate_daily_report.py
   ```

---

## 🔍 故障排查

### 服务无法启动

1. **检查日志**
   ```bash
   sudo journalctl -u vehicle-detection -n 50
   ```

2. **检查硬件**
   ```bash
   bash scripts/check_hardware.sh
   ```

3. **检查网络**
   ```bash
   bash scripts/check_network.sh
   ```

### 服务频繁重启

1. **查看重启原因**
   ```bash
   sudo journalctl -u vehicle-detection --since "1 hour ago" | grep -i error
   ```

2. **检查资源使用**
   ```bash
   bash scripts/monitor_resources.sh
   ```

3. **检查磁盘空间**
   ```bash
   df -h
   ```

### 检测异常

1. **检查相机连接**
   ```bash
   lsusb | grep -i orbbec
   ```

2. **检查Cassia连接**
   ```bash
   ping -c 3 192.168.3.26
   bash scripts/test_cassia_connectivity.sh
   ```

3. **检查模型文件**
   ```bash
   ls -lh models/custom_yolo.engine
   ```

---

## 📝 测试记录

### 测试信息

- **测试开始时间**: _______________
- **测试地点**: 工地
- **测试环境**: 
  - 网络: 4G路由器 (192.168.3.1)
  - Jetson IP: 192.168.3.243
  - Cassia IP: 192.168.3.26

### 每日记录

| 日期 | 运行时间 | 检测数量 | 异常事件 | 备注 |
|------|---------|---------|---------|------|
|      |         |         |         |      |

### 异常事件记录

| 时间 | 事件类型 | 描述 | 处理方式 | 结果 |
|------|---------|------|---------|------|
|      |         |      |         |      |

---

## ✅ 测试完成检查

### 测试结束前

1. **停止服务**
   ```bash
   sudo systemctl stop vehicle-detection
   ```

2. **导出数据**
   ```bash
   # 生成最终报告
   python3 scripts/generate_daily_report.py
   
   # 导出数据库
   sqlite3 detection_results.db ".backup backups/final_backup.db"
   ```

3. **收集日志**
   ```bash
   # 收集系统日志
   sudo journalctl -u vehicle-detection > logs/system_$(date +%Y%m%d).log
   
   # 收集应用日志
   cp /tmp/vehicle_detection.log logs/app_$(date +%Y%m%d).log
   ```

4. **清理临时文件**
   ```bash
   bash scripts/cleanup_old_data.sh
   ```

---

## 📞 支持联系

如有问题，请参考：
- 系统日志: `/tmp/vehicle_detection.log`
- 服务日志: `sudo journalctl -u vehicle-detection`
- 文档: `docs/` 目录

