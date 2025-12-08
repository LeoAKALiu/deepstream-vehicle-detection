# 长期测试快速启动指南

## 🚀 一键启动

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash scripts/start_long_term_test.sh
```

这个脚本会自动：
1. ✅ 检查系统服务配置
2. ✅ 检查硬件连接
3. ✅ 检查网络连接
4. ✅ 检查配置文件
5. ✅ 检查磁盘空间
6. ✅ 启动服务

---

## 📋 手动启动步骤

### 1. 检查系统状态

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 检查服务状态
systemctl status vehicle-detection

# 检查硬件
bash scripts/check_hardware.sh

# 检查网络
bash scripts/check_network.sh
bash scripts/test_cassia_connectivity.sh

# 查看系统状态
bash scripts/system_status.sh
```

### 2. 启动服务

```bash
# 使用systemd服务（推荐）
sudo systemctl start vehicle-detection

# 查看启动状态
sudo systemctl status vehicle-detection

# 查看实时日志
sudo journalctl -u vehicle-detection -f
```

### 3. 验证运行

```bash
# 查看服务状态
sudo systemctl status vehicle-detection

# 查看系统资源
bash scripts/monitor_resources.sh

# 查看检测统计（运行一段时间后）
python3 scripts/generate_daily_report.py
```

---

## 📊 日常监控

### 查看服务状态

```bash
sudo systemctl status vehicle-detection
```

### 查看实时日志

```bash
sudo journalctl -u vehicle-detection -f
```

### 查看系统状态

```bash
bash scripts/system_status.sh
```

### 查看资源使用

```bash
bash scripts/monitor_resources.sh
```

### 生成日报

```bash
python3 scripts/generate_daily_report.py
```

---

## 🔧 服务管理

### 启动/停止/重启

```bash
sudo systemctl start vehicle-detection    # 启动
sudo systemctl stop vehicle-detection     # 停止
sudo systemctl restart vehicle-detection  # 重启
```

### 查看日志

```bash
# 实时日志
sudo journalctl -u vehicle-detection -f

# 最近50行
sudo journalctl -u vehicle-detection -n 50

# 最近1小时
sudo journalctl -u vehicle-detection --since "1 hour ago"
```

### 禁用/启用自启动

```bash
sudo systemctl disable vehicle-detection  # 禁用自启动
sudo systemctl enable vehicle-detection   # 启用自启动
```

---

## 🆘 故障排查

### 服务无法启动

```bash
# 1. 查看错误日志
sudo journalctl -u vehicle-detection -n 50

# 2. 检查硬件
bash scripts/check_hardware.sh

# 3. 检查网络
bash scripts/check_network.sh

# 4. 手动启动查看错误
bash scripts/start_vehicle_detection.sh
```

### 服务频繁重启

```bash
# 查看重启原因
sudo journalctl -u vehicle-detection --since "1 hour ago" | grep -i error

# 检查资源使用
bash scripts/monitor_resources.sh

# 检查磁盘空间
df -h
```

### 检测异常

```bash
# 检查相机
lsusb | grep -i orbbec

# 检查Cassia
ping -c 3 192.168.3.26
bash scripts/test_cassia_connectivity.sh

# 检查模型文件
ls -lh models/custom_yolo.engine
```

---

## 📝 测试记录

### 记录测试开始

```bash
# 记录测试开始时间
echo "测试开始: $(date)" >> test_log.txt

# 记录系统状态
bash scripts/system_status.sh >> test_log.txt
```

### 每日检查

1. 服务状态
2. 系统资源
3. 检测统计
4. 异常事件

### 测试结束

```bash
# 停止服务
sudo systemctl stop vehicle-detection

# 生成最终报告
python3 scripts/generate_daily_report.py

# 备份数据
cp detection_results.db backups/detection_results_$(date +%Y%m%d).db
```

---

## ✅ 当前配置状态

- ✅ Systemd服务已启用
- ✅ Cassia IP: 192.168.3.26
- ✅ 云端集成已配置
- ✅ 心跳机制已启用
- ✅ 报告生成已配置
- ✅ 硬件恢复已集成
- ✅ 网络恢复已集成

---

## 📚 相关文档

- 详细检查清单: `docs/LONG_TERM_TEST_CHECKLIST.md`
- 网络配置: `docs/SITE_DEPLOYMENT_NETWORK.md`
- 自动启动配置: `docs/AUTO_START_SETUP.md`
- 云端集成: `docs/CLOUD_DEBUGGING_GUIDE.md`

