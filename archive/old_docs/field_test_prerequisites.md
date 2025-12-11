# 现场测试前必做事项

## 🚨 紧急：必须在现场测试前完成

### 1. 网络配置（必须完成）

#### 1.1 配置Jetson静态IP
```bash
sudo nmcli con mod "Wired connection 2" \
  ipv4.method manual \
  ipv4.addresses 192.168.1.3/24 \
  ipv4.gateway "" \
  ipv4.dns "" \
  ipv4.never-default yes

sudo nmcli con mod "Wired connection 2" \
  ipv4.routes "192.168.1.2/32 0.0.0.0"

sudo nmcli con down "Wired connection 2"
sudo nmcli con up "Wired connection 2"
```

#### 1.2 验证网络连通性
```bash
# 检查IP配置
ip addr show enP8p1s0

# 检查路由
ip route | grep 192.168.1.2

# 测试连通性
ping -c 4 192.168.1.2
```

**预期结果**：
- `enP8p1s0` 显示 `192.168.1.3/24`
- 路由表包含 `192.168.1.2 dev enP8p1s0`
- `ping` 成功（< 5ms延迟）

---

### 2. 更新Cassia IP地址（已完成 ✅）

所有关键脚本已更新：
- ✅ `test_system_realtime.py` → `192.168.1.2`
- ✅ `test_ble_beacon.sh` → `192.168.1.2`
- ✅ `test_realtime_system.sh` → `192.168.1.2`
- ✅ `run_full_system.sh` → `192.168.1.2`

**验证**：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
grep -r "192.168.1.2" test_system_realtime.py test_*.sh run_*.sh
```

---

### 3. 信标白名单配置（必须完成）

#### 3.1 确认现场信标信息
编辑 `beacon_whitelist.yaml`，确保包含所有现场信标：

```yaml
cameras:
  camera_01:
    beacons:
      - mac: "45:C6:6A:F2:46:19"  # 现场信标1
        vehicle_type: "excavator"
        active: true
      - mac: "XX:XX:XX:XX:XX:XX"  # 现场信标2（如有）
        vehicle_type: "truck"
        active: true
```

#### 3.2 验证白名单
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
python3 -c "
import yaml
with open('beacon_whitelist.yaml') as f:
    config = yaml.safe_load(f)
    beacons = config['cameras']['camera_01']['beacons']
    print(f'已配置 {len(beacons)} 个信标:')
    for b in beacons:
        print(f'  - {b[\"mac\"]} ({b[\"vehicle_type\"]})')
"
```

---

### 4. 功能测试（建议完成）

#### 4.1 单模块测试
```bash
# 测试Orbbec相机
cd /home/liubo/Download/deepstream-vehicle-detection
python3 python_apps/test_orbbec.py

# 测试BLE信标
./测试BLE信标.sh

# 测试信标过滤器
./测试信标过滤器.sh
```

#### 4.2 完整系统测试
```bash
./test_realtime_system.sh
```

**预期结果**：
- 相机画面正常显示
- 能检测到车辆
- 能扫描到信标
- 信标匹配正常

---

### 5. 模型文件检查（必须完成）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
ls -lh models/custom_yolo.engine
```

**预期结果**：
- 文件存在
- 文件大小约 54MB
- 文件权限可读

---

### 6. Python依赖检查（必须完成）

```bash
python3 -c "
import sys
modules = [
    'pyorbbecsdk', 'hyperlpr3', 'tensorrt', 
    'pycuda', 'cv2', 'numpy', 'PIL', 'yaml', 
    'aiohttp', 'aiohttp_sse_client'
]
missing = []
for m in modules:
    try:
        __import__(m)
        print(f'✓ {m}')
    except ImportError:
        print(f'✗ {m} (缺失)')
        missing.append(m)
if missing:
    print(f'\n缺失模块: {missing}')
    sys.exit(1)
"
```

---

## 📋 快速检查清单

在出发前，快速运行以下命令：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 1. 网络检查
echo "【网络检查】"
ping -c 1 -W 2 192.168.1.2 && echo "✓ Cassia可达" || echo "✗ Cassia不可达"

# 2. 模型检查
echo "【模型检查】"
[ -f models/custom_yolo.engine ] && echo "✓ 模型文件存在" || echo "✗ 模型文件缺失"

# 3. 配置文件检查
echo "【配置检查】"
[ -f beacon_whitelist.yaml ] && echo "✓ 白名单文件存在" || echo "✗ 白名单文件缺失"
grep -q "192.168.1.2" test_system_realtime.py && echo "✓ IP地址已更新" || echo "✗ IP地址未更新"

# 4. Python依赖检查
echo "【依赖检查】"
python3 -c "import pyorbbecsdk, hyperlpr3, tensorrt" 2>/dev/null && echo "✓ 核心依赖正常" || echo "✗ 核心依赖缺失"

# 5. 相机检查
echo "【相机检查】"
ls /dev/video* 2>/dev/null && echo "✓ 相机设备存在" || echo "✗ 相机设备未识别"
```

---

## 🎯 现场部署步骤

1. **连接硬件**
   - Jetson电源
   - Orbbec相机USB
   - 网线（Jetson ↔ PoE路由器）
   - Cassia路由器电源和网线

2. **启动设备**
   - 先启动Cassia路由器（等待1分钟）
   - 再启动Jetson

3. **验证连接**
   ```bash
   ping -c 4 192.168.1.2
   ```

4. **启动系统**
   ```bash
   cd /home/liubo/Download/deepstream-vehicle-detection
   ./test_realtime_system.sh
   ```

---

## ⚠️ 常见问题快速修复

### 问题1：Cassia无法连接
```bash
# 检查网络
ping -c 4 192.168.1.2

# 检查SSE接口
curl -N 'http://192.168.1.2/gap/nodes?event=1' --max-time 5
```

### 问题2：相机无法识别
```bash
# 检查设备
ls -l /dev/video*

# 重新配置权限
./配置Orbbec权限.sh
```

### 问题3：模型加载失败
```bash
# 检查模型文件
ls -lh models/custom_yolo.engine

# 检查TensorRT
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

---

**最后更新**: 2024年11月4日


