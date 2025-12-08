# 自动启动配置指南

## 📋 概述

本文档说明如何配置车辆检测系统的自动启动功能，使系统能够在开机后自动运行。

## 🚀 快速开始

### 1. 安装自动启动服务

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
sudo ./scripts/setup_auto_start.sh
```

这个脚本会：
- 检查所有必要的脚本文件
- 安装 systemd 服务文件
- 启用开机自启动
- 可选择立即启动服务

### 2. 手动管理服务

```bash
# 启动服务
sudo systemctl start vehicle-detection

# 停止服务
sudo systemctl stop vehicle-detection

# 重启服务
sudo systemctl restart vehicle-detection

# 查看服务状态
sudo systemctl status vehicle-detection

# 查看实时日志
sudo journalctl -u vehicle-detection -f

# 禁用开机自启动
sudo systemctl disable vehicle-detection

# 启用开机自启动
sudo systemctl enable vehicle-detection
```

## 📁 文件说明

### 脚本文件

| 文件 | 说明 |
|------|------|
| `scripts/check_hardware.sh` | 硬件检查脚本（相机、路由器、GPU、磁盘） |
| `scripts/check_network.sh` | 网络检查脚本（Cassia路由器、互联网、DNS） |
| `scripts/start_vehicle_detection.sh` | 启动脚本（包含硬件检查、环境配置） |
| `scripts/stop_vehicle_detection.sh` | 停止脚本（优雅关闭、清理临时文件） |
| `scripts/setup_auto_start.sh` | 自动启动安装脚本 |
| `scripts/vehicle-detection.service` | systemd 服务配置文件 |

### 服务配置说明

服务文件 `vehicle-detection.service` 包含以下配置：

- **启动依赖**: 网络和USB设备就绪后启动
- **自动重启**: 服务失败后自动重启（最多5次，间隔10秒）
- **资源限制**: 内存最大4GB，CPU配额200%
- **日志输出**: 输出到 systemd journal
- **超时设置**: 启动超时300秒，停止超时60秒

## 🔍 硬件检查

启动脚本会自动执行硬件检查，检查以下项目：

1. **Orbbec 相机**
   - USB 连接状态
   - 设备权限

2. **Cassia 路由器**
   - 网络连通性（ping）
   - IP 地址（从 config.yaml 读取）

3. **GPU (NVIDIA Jetson)**
   - GPU 可用性
   - TensorRT 库

4. **磁盘空间**
   - 使用率检查（警告阈值80%，错误阈值90%）

5. **模型文件**
   - 检查模型文件是否存在

6. **配置文件**
   - 检查 config.yaml 是否存在

7. **Python 环境**
   - Python 版本
   - 必要的依赖包（cv2, numpy, pycuda）

### 硬件检查失败处理

- **错误（ERROR）**: 系统无法启动，必须修复
- **警告（WARNING）**: 系统可以启动，但功能可能受限

## 🌐 网络检查

网络检查包括：

1. **Cassia 路由器连接**
   - ping 测试
   - 延迟测量

2. **互联网连接**
   - ping 8.8.8.8 测试

3. **DNS 解析**
   - nslookup 测试

4. **网络接口**
   - 活动接口数量

5. **默认网关**
   - 网关可达性

6. **云端服务器**（如果配置）
   - 服务器连接测试

### 网络检查失败处理

网络检查失败不会阻止系统启动，系统将以本地模式运行。

## 📝 日志

### 日志位置

- **启动日志**: `logs/startup.log`
- **系统日志**: systemd journal (`sudo journalctl -u vehicle-detection`)
- **应用日志**: 由 config.yaml 中的 `paths.log_file` 配置

### 查看日志

```bash
# 查看启动日志
tail -f logs/startup.log

# 查看 systemd 日志
sudo journalctl -u vehicle-detection -f

# 查看最近100行日志
sudo journalctl -u vehicle-detection -n 100

# 查看今天的日志
sudo journalctl -u vehicle-detection --since today
```

## ⚙️ 配置修改

### 修改服务配置

如果需要修改服务配置（如用户、工作目录等），编辑服务文件：

```bash
sudo nano /etc/systemd/system/vehicle-detection.service
```

然后重新加载并重启：

```bash
sudo systemctl daemon-reload
sudo systemctl restart vehicle-detection
```

### 修改启动参数

编辑 `scripts/start_vehicle_detection.sh`，修改启动命令：

```bash
# 例如：添加 --no-depth 参数
exec python3 "$PROJECT_ROOT/test_system_realtime.py" --no-display --no-depth
```

## 🧪 测试

### 测试硬件检查

```bash
./scripts/check_hardware.sh
```

### 测试网络检查

```bash
./scripts/check_network.sh
```

### 测试启动脚本

```bash
./scripts/start_vehicle_detection.sh
```

### 测试服务

```bash
# 启动服务
sudo systemctl start vehicle-detection

# 等待几秒后检查状态
sudo systemctl status vehicle-detection

# 查看日志
sudo journalctl -u vehicle-detection -f
```

## 🔧 故障排除

### 服务无法启动

1. **检查服务状态**
   ```bash
   sudo systemctl status vehicle-detection
   ```

2. **查看详细日志**
   ```bash
   sudo journalctl -u vehicle-detection -n 50
   ```

3. **检查硬件**
   ```bash
   ./scripts/check_hardware.sh
   ```

4. **手动运行启动脚本**
   ```bash
   ./scripts/start_vehicle_detection.sh
   ```

### 服务频繁重启

1. **检查资源使用**
   ```bash
   top
   nvidia-smi
   ```

2. **检查磁盘空间**
   ```bash
   df -h
   ```

3. **查看错误日志**
   ```bash
   sudo journalctl -u vehicle-detection --since "10 minutes ago" | grep -i error
   ```

### 硬件检查失败

1. **相机未检测到**
   - 检查 USB 连接
   - 运行 `lsusb` 查看设备
   - 检查权限：`ls -l /dev/video*`

2. **路由器不可访问**
   - 检查网络连接
   - 检查 config.yaml 中的 IP 地址
   - 运行 `ping <cassia_ip>`

3. **GPU 不可用**
   - 检查 Jetson 设备状态
   - 运行 `nvidia-smi` 或 `tegrastats`
   - 检查 TensorRT 安装

## 📊 监控

### 服务状态监控

```bash
# 实时监控服务状态
watch -n 1 'systemctl status vehicle-detection --no-pager'
```

### 资源监控

```bash
# CPU 和内存
top

# GPU（Jetson）
tegrastats

# 磁盘
df -h
```

## 🔐 安全建议

1. **SSH 访问**: 配置 SSH 密钥认证，禁用密码登录
2. **防火墙**: 配置防火墙规则，限制不必要的端口
3. **日志轮转**: 配置日志轮转，防止日志文件过大
4. **定期更新**: 定期更新系统和依赖包

## 📞 支持

如有问题，请查看：
- 项目文档：`docs/PROJECT_DOCUMENTATION.md`
- 故障排除：`docs/TROUBLESHOOTING.md`
- 系统日志：`logs/startup.log`

