# Cassia本地路由器使用指南

本指南介绍如何使用直连到Jetson的Cassia蓝牙路由器（Standalone模式）

---

## 📋 硬件连接

```
Jetson Orin
  ├─ WiFi (wlP7p1s0): 192.168.1.26 → 互联网
  └─ 有线网口 (enP8p1s0): 192.168.40.2 → Cassia路由器 (192.168.40.1)
```

---

## 🔧 步骤1：配置网络

### 运行配置脚本

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

bash 配置Cassia网络.sh
```

### 脚本会自动完成

1. ✅ 给`enP8p1s0`配置IP `192.168.40.2`
2. ✅ 测试与路由器`192.168.40.1`的连接
3. ✅ 测试Cassia API访问

### 预期输出

```
【1. 配置IP地址】
  ✓ IP配置成功: 192.168.40.2

【2. 确认接口状态】
2: enP8p1s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 3c:6d:66:2c:ed:f3 brd ff:ff:ff:ff:ff:ff
    inet 192.168.40.2/24 scope global enP8p1s0

【3. 测试连接】
PING 192.168.40.1 (192.168.40.1) 56(84) bytes of data.
64 bytes from 192.168.40.1: icmp_seq=1 ttl=64 time=0.5 ms
✓ 路由器连接成功！

【4. 测试Cassia API】
...
```

---

## 🧪 步骤2：测试信标扫描

### 单独测试客户端

```bash
cd /home/liubo/Download/deepstream-vehicle-detection/python_apps

python3 cassia_local_client.py
```

### 预期输出

```
连接到Cassia路由器: 192.168.40.1
按Ctrl+C停止

扫描信标中...
发现 3 个信标: [EE:01: -45dBm, 3.2m] [EE:02: -60dBm, 10.0m] [EE:03: -55dBm, 7.1m]

^C
停止扫描...

共发现 3 个信标:
  MAC: AA:BB:CC:DD:EE:01, RSSI: -45, 距离: 3.16m, 名称: iBeacon_01
  MAC: AA:BB:CC:DD:EE:02, RSSI: -60, 距离: 10.00m, 名称: iBeacon_02
  MAC: AA:BB:CC:DD:EE:03, RSSI: -55, 距离: 7.08m, 名称: Unknown
```

---

## 🚀 步骤3：运行完整系统

### 启用本地路由器

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-local 192.168.40.1
```

### 如果路由器需要认证

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-local 192.168.40.1 \
    --cassia-user admin \
    --cassia-pass password
```

### 预期启动输出

```
======================================================================
工程机械实时识别系统
======================================================================
GPU: TensorRT推理
CPU: YOLO后处理、跟踪
信标: Cassia本地路由器 (192.168.40.1)
深度: 简单估计（基于bbox高度）
车牌: HyperLPR
======================================================================

✓ TensorRT和PyCUDA可用
✓ HyperLPR初始化成功
✓ Cassia本地路由器启动成功 (192.168.40.1)
```

---

## 📊 运行效果

### 终端输出

```
新车辆 ID1: 挖掘机 (excavator)
  估计距离: 8.5m
  ✓ 已备案车辆 ID1: excavator, 信标=AA:BB:CC:DD:EE:02

新车辆 ID2: 推土机 (bulldozer)
  估计距离: 5.2m
  ⚠ 未备案车辆入场! ID2: bulldozer, 帧156

新车辆 ID3: 卡车 (truck)
  🚗 社会车辆 ID3: truck, 车牌=京A12345
```

### 最终统计

```
======================================================================
TensorRT车辆检测统计
======================================================================

【工程车辆 - 已备案】
  总数: 2 辆
  
  ID1: excavator       信标=AA:BB:CC:DD:EE:02
  ID5: loader          信标=AA:BB:CC:DD:EE:01

【工程车辆 - 未备案（警告）】
  总数: 1 辆
  
  ⚠ ID2: bulldozer       帧156

【社会车辆 - 车牌识别】
  总数: 1 辆
  
  ID3: truck      车牌=京A12345
```

---

## 🔧 故障排除

### 问题1：无法ping通192.168.40.1

**检查**：
```bash
# 查看有线网口状态
ip addr show enP8p1s0

# 应该看到:
#   inet 192.168.40.2/24 scope global enP8p1s0
```

**解决**：
```bash
# 重新配置
sudo ip addr add 192.168.40.2/24 dev enP8p1s0
sudo ip link set enP8p1s0 up
ping 192.168.40.1
```

### 问题2：扫描不到信标

**可能原因**：
- 信标未通电
- 信标距离太远
- 路由器未启动扫描

**检查API**：
```bash
# 手动测试扫描API
curl "http://192.168.40.1/gap/nodes?event=1&active=1&filter_rssi=-90"

# 应该看到SSE流输出
```

### 问题3：API需要认证

**错误信息**：
```
401 Unauthorized
```

**解决**：
```bash
# 添加认证参数
python3 python_apps/tensorrt_yolo_inference.py \
    VIDEO \
    --engine models/yolov11_host.engine \
    --cassia-local 192.168.40.1 \
    --cassia-user admin \
    --cassia-pass yourpassword
```

### 问题4：SSE连接断开

**错误信息**：
```
⚠ SSE连接错误: Connection closed
```

**原因**：正常现象，客户端会自动重连

**手动重启**：Ctrl+C 后重新运行程序

---

## ⚙️ 参数调整

### RSSI转距离参数

编辑 `cassia_local_client.py` 第50-51行：

```python
self.tx_power = -59  # 信标发射功率
    # iBeacon: -59 dBm
    # Eddystone: -20 dBm
    # 根据你的信标规格调整

self.path_loss_exponent = 2.5  # 路径衰减指数
    # 空旷室外: 2.0-2.5
    # 工地环境: 2.5-3.0
    # 室内: 3.0-4.0
```

### 距离匹配容差

在主程序运行时，容差为`2.5米`（可在代码中修改）

### 扫描RSSI阈值

编辑 `cassia_local_client.py` 第69行：

```python
params = {
    'filter_rssi': -90,  # 只扫描RSSI > -90的设备
    'active': 1,
    'event': 1
}
```

---

## 📝 网络配置持久化

上面的IP配置在重启后会丢失。要持久化配置：

### 方法1：使用netplan（推荐）

编辑 `/etc/netplan/01-network-manager-all.yaml`:

```yaml
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    enP8p1s0:
      addresses:
        - 192.168.40.2/24
      dhcp4: no
```

应用配置：
```bash
sudo netplan apply
```

### 方法2：使用systemd服务

创建 `/etc/systemd/system/cassia-network.service`:

```ini
[Unit]
Description=Configure Cassia Router Network
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ip addr add 192.168.40.2/24 dev enP8p1s0
ExecStart=/sbin/ip link set enP8p1s0 up
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable cassia-network
sudo systemctl start cassia-network
```

---

## 🎯 快速参考

### 完整运行命令

```bash
# 1. 配置网络（首次或重启后）
bash /home/liubo/Download/deepstream-vehicle-detection/配置Cassia网络.sh

# 2. 测试信标扫描（可选）
cd /home/liubo/Download/deepstream-vehicle-detection/python_apps
python3 cassia_local_client.py

# 3. 运行完整系统
cd /home/liubo/Download/deepstream-vehicle-detection
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-local 192.168.40.1
```

### 对比：AC模式 vs 本地模式

| 特性 | AC模式 | 本地模式 |
|------|--------|----------|
| **部署** | 需要AC控制器 | 直连路由器 |
| **认证** | OAuth2 (Key/Secret) | Basic Auth或无 |
| **API** | `AC_URL/api` | `ROUTER_IP` |
| **路由器选择** | 通过MAC指定 | 单一路由器 |
| **适用场景** | 多路由器，云管理 | 单路由器，本地 |

**本项目使用：本地模式** ✅

---

## 📄 相关文档

- `README-完整版.md` - 系统总览
- `Cassia信标集成指南.md` - AC模式（已废弃）
- `系统逻辑说明.md` - 系统架构
- `在Jetson上运行.md` - 运行说明

---

**最后更新**: 2025-10-27  
**版本**: 2.0 (本地路由器模式)  
**状态**: 生产就绪

