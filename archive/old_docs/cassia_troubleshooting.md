# Cassia路由器连接故障排除

当前状态：IP配置成功，但ping不通路由器（Destination Host Unreachable）

---

## 🔍 问题诊断

### 当前配置
- **Jetson WiFi**: `192.168.1.26` (连接互联网)
- **Jetson 有线**: `192.168.40.2` (配置成功)
- **Cassia路由器**: `192.168.40.1` (假设的IP，可能不对)
- **问题**: ping 192.168.40.1失败

### 可能的原因

1. ❌ **路由器未通电或网线未连接**
   - 检查路由器电源指示灯
   - 检查网口指示灯
   - 尝试重新插拔网线

2. ❌ **路由器IP不是192.168.40.1**
   - 路由器可能使用其他IP段
   - 常见: `192.168.1.1`, `192.168.0.1`, `10.10.10.1`
   - 需要查找实际IP

3. ❌ **路由器使用DHCP模式**
   - 路由器期望从Jetson获取IP
   - 或Jetson需要从路由器获取IP

4. ❌ **防火墙阻止**
   - iptables规则阻止通信
   - 需要检查防火墙设置

---

## 🚀 快速解决方案

### 方案A：自动诊断（推荐）⭐

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash 快速测试.sh
```

此脚本会自动尝试：
- 固定IP连接（192.168.40.1）
- DHCP自动获取
- 扫描查找路由器

### 方案B：手动排查

#### 步骤1：检查物理连接

```bash
# 查看网口状态
cat /sys/class/net/enP8p1s0/operstate
# 应该显示 "up"

# 查看网线连接（需要ethtool）
sudo ethtool enP8p1s0 | grep "Link detected"
# 应该显示 "Link detected: yes"
```

**如果Link detected: no**
- 网线未插好
- 路由器未通电
- 网口故障

#### 步骤2：尝试DHCP

```bash
# 清除现有IP
sudo ip addr flush dev enP8p1s0

# 尝试DHCP
sudo dhclient -v enP8p1s0

# 查看获得的IP
ip addr show enP8p1s0

# 查看网关
ip route | grep enP8p1s0
```

**如果获得IP**：
- 网关IP很可能就是路由器IP
- 尝试访问网关

#### 步骤3：扫描查找路由器

```bash
bash 查找Cassia路由器.sh
```

或手动扫描：

```bash
# 常见IP
for ip in 1 100 254; do
    echo -n "192.168.40.$ip: "
    timeout 0.5 ping -c 1 192.168.40.$ip > /dev/null 2>&1 && echo "✓" || echo "✗"
done
```

#### 步骤4：通过其他设备确认

使用笔记本直连Cassia路由器：
1. 用网线连接笔记本和路由器
2. 查看笔记本获得的IP（DHCP）
3. 访问路由器Web界面
4. 确认路由器实际IP地址

---

## 📋 根据路由器文档

根据你的PDF文档（蓝牙网关本地调试和使用说明），Cassia路由器可能的配置：

### 出厂默认
- **IP**: 通常是 `192.168.40.1` 或需要DHCP
- **用户名**: `admin`
- **密码**: `admin` 或 `cassia`

### 访问方式
- **Web界面**: `http://路由器IP`
- **API接口**: `http://路由器IP/api`
- **扫描接口**: `http://路由器IP/gap/nodes`

### 工作模式
- **Standalone模式**（本地）：直连设备
- **AC模式**：连接到AC控制器

---

## 🔧 解决方案（按优先级）

### 1️⃣ 最快：运行自动脚本

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash 快速测试.sh
```

### 2️⃣ 如果知道路由器IP

假设找到路由器IP是 `192.168.1.100`：

```bash
# 配置Jetson IP到同网段
sudo ip addr add 192.168.1.50/24 dev enP8p1s0

# 测试连接
ping -c 3 192.168.1.100

# 运行系统
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-local 192.168.1.100
```

### 3️⃣ 使用DHCP

```bash
# 让路由器分配IP
sudo dhclient enP8p1s0

# 查看获得的IP和网关
ip addr show enP8p1s0
ip route | grep enP8p1s0

# 假设网关是10.10.10.1
ping 10.10.10.1

# 运行系统
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-local 10.10.10.1
```

### 4️⃣ 联系厂家或查阅文档

- 查看路由器标签上的默认IP
- 查看随机文档或说明书
- 联系Cassia技术支持
- 查看PDF文档的网络配置章节

---

## 🎯 成功标志

当连接成功时，你应该看到：

```bash
# ping通
PING 192.168.40.1 (192.168.40.1) 56(84) bytes of data.
64 bytes from 192.168.40.1: icmp_seq=1 ttl=64 time=0.5 ms

# HTTP可访问
curl http://192.168.40.1/
# 返回HTML页面或JSON

# API可访问
curl http://192.168.40.1/api
# 返回API信息
```

---

## 📞 需要帮助时

运行详细诊断并提供输出：

```bash
bash 诊断Cassia连接.sh > cassia_diag.txt 2>&1
cat cassia_diag.txt
```

提供这些信息：
1. `ethtool enP8p1s0` 输出
2. `ip addr show enP8p1s0` 输出
3. `ip route` 输出
4. `arp -n` 输出
5. 路由器型号和标签照片

---

## 💡 常见场景

### 场景1：路由器使用DHCP服务器模式

```
Cassia路由器 (192.168.40.1, DHCP服务器)
    ↓
Jetson获取IP (192.168.40.100, 通过DHCP)
```

**解决**：`sudo dhclient enP8p1s0`

### 场景2：路由器使用DHCP客户端模式

```
Jetson (需要配置DHCP服务器)
    ↓
Cassia路由器 (获取IP, 通过DHCP)
```

**解决**：需要配置dnsmasq作为DHCP服务器

### 场景3：固定IP模式

```
Jetson (192.168.40.2, 手动配置)
    ↓
Cassia路由器 (192.168.40.1, 固定)
```

**解决**：确认路由器确实是192.168.40.1

---

**立即行动：运行 `bash 快速测试.sh` 开始诊断！**

