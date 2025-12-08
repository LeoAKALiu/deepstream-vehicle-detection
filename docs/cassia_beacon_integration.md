# Cassia蓝牙信标集成指南

## 📋 系统架构

```
工程车辆检测
    ↓
计算bbox底边中点
    ↓
Orbbec深度相机 → 精确距离（米）
    ↓
Cassia信标客户端
    ├─ 获取所有信标RSSI
    ├─ RSSI → 距离转换
    ├─ 距离匹配（容差±2.5米）
    └─ 返回最接近的信标MAC
    ↓
    ├─ 匹配成功 → ✓ 已备案车辆（记录MAC）
    └─ 匹配失败 → ⚠️ 未备案车辆入场（报警）
```

---

## 🔧 集成步骤

### 步骤1：安装依赖

```bash
pip3 install aiohttp aiohttp-sse-client -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

### 步骤2：配置Cassia AC

1. **登录AC Web界面**
   - 地址：`http://your-ac-ip`

2. **创建开发者账号**
   - Settings → Developer account for RESTful APIs
   - 创建Key和Secret
   - 记录下来

3. **添加路由器**
   - Gateways → 添加你的蓝牙路由器
   - 记录路由器MAC地址

### 步骤3：配置系统

复制配置文件模板：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
cp cassia_config.example.sh cassia_config.sh
```

编辑 `cassia_config.sh`，填入实际配置：

```bash
CASSIA_AC="http://192.168.1.100"        # 你的AC地址
CASSIA_KEY="admin1"                      # 你的开发者密钥
CASSIA_SECRET="1q2w#E$R"                # 你的开发者密码
CASSIA_ROUTER="CC:1B:E0:E2:E9:B8"      # 你的路由器MAC
```

### 步骤4：测试信标客户端

```bash
cd /home/liubo/Download/deepstream-vehicle-detection/python_apps

# 编辑cassia_beacon_client.py底部的配置
# 然后运行测试
python3 cassia_beacon_client.py
```

应该看到：
```
✓ Cassia认证成功
扫描信标中...

发现 3 个信标:
  MAC: AA:BB:CC:DD:EE:01, RSSI: -45, 距离: 3.16m
  MAC: AA:BB:CC:DD:EE:02, RSSI: -60, 距离: 10.00m
  MAC: AA:BB:CC:DD:EE:03, RSSI: -55, 距离: 7.08m
```

### 步骤5：运行完整系统

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-ac "http://192.168.1.100" \
    --cassia-key "your_key" \
    --cassia-secret "your_secret" \
    --cassia-router "CC:1B:E0:E2:E9:B8"
```

或使用配置脚本：
```bash
bash cassia_config.sh
```

---

## 📊 运行效果

### 启动输出

```
======================================================================
工程机械实时识别系统
======================================================================
GPU: TensorRT推理
CPU: YOLO后处理、跟踪
信标: Cassia蓝牙信标（已配置）
深度: 简单估计（基于bbox高度）
车牌: HyperLPR
======================================================================

✓ TensorRT和PyCUDA可用
✓ HyperLPR初始化成功
✓ Cassia信标客户端启动成功
✓ Cassia认证成功
```

### 实时检测输出

**已备案车辆**：
```
✓ 已备案车辆 ID1: 挖掘机, 信标=AA:BB:CC:DD:EE:01
✓ 已备案车辆 ID3: 自卸车, 信标=AA:BB:CC:DD:EE:02
```

**未备案车辆（报警）**：
```
⚠ 未备案车辆入场! ID2: 推土机, 帧156
⚠ 未备案车辆入场! ID5: 装载机, 帧320
```

**社会车辆**：
```
🚗 社会车辆 ID4: truck, 车牌=京A12345
🚗 社会车辆 ID6: car, 车牌=沪B67890
```

### 最终统计

```
======================================================================
TensorRT车辆检测统计
======================================================================

总帧数: 15398
平均FPS: 28.3

【工程车辆 - 已备案】
  总数: 2 辆

  ID1: excavator       信标=AA:BB:CC:DD:EE:01
  ID3: dump-truck      信标=AA:BB:CC:DD:EE:02

【工程车辆 - 未备案（警告）】
  总数: 2 辆

  ⚠ ID2: bulldozer       帧156
  ⚠ ID5: loader          帧320

【社会车辆 - 车牌识别】
  总数: 2 辆

  ID4: truck      车牌=京A12345
  ID6: car        车牌=沪B67890

======================================================================
```

---

## ⚙️ 参数调整

### RSSI转距离参数

编辑 `cassia_beacon_client.py`:

```python
self.tx_power = -59  # 信标发射功率
    # 需要根据你实际使用的信标调整
    # 常见值: -59 dBm (iBeacon)

self.path_loss_exponent = 2.5  # 路径衰减指数
    # 室外空旷: 2.0-2.5
    # 室内: 2.5-4.0
    # 工地环境: 建议2.5-3.0
```

### 距离匹配容差

编辑 `tensorrt_yolo_inference.py` 第543行:

```python
beacon = self.beacon_client.find_nearest_beacon(distance, tolerance=2.5)
    # tolerance: 距离容差（米）
    # 值越大，匹配越宽松
    # 建议: 2.0-3.0米
```

### IoU跟踪阈值

编辑 `tensorrt_yolo_inference.py` 第359行:

```python
self.iou_threshold = 0.3  # IoU阈值
    # 值越大，跟踪越严格
    # 建议: 0.3-0.5
```

### 消失时间

编辑 `tensorrt_yolo_inference.py` 第360行:

```python
self.max_disappeared = 30  # 最大消失帧数
    # 约1秒 (30帧 / 30fps)
    # 建议: 30-60帧
```

---

## 🔬 调试技巧

### 调试1：查看信标数据

在系统运行时，信标数据会实时更新。可以添加调试输出：

编辑 `match_beacon()` 函数：

```python
def match_beacon(self, distance, class_id):
    if self.beacon_client is None:
        return None
    
    # 查看所有信标
    beacons = self.beacon_client.get_beacons()
    print(f"  [调试] 当前信标数: {len(beacons)}")
    for b in beacons:
        print(f"    MAC={b['mac']}, RSSI={b['rssi']}, 距离={b['distance']:.2f}m")
    
    beacon = self.beacon_client.find_nearest_beacon(distance, tolerance=2.5)
    # ...
```

### 调试2：测试信标扫描

单独运行信标客户端：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection/python_apps

# 编辑cassia_beacon_client.py最后的配置
# 运行
python3 cassia_beacon_client.py
```

### 调试3：调整RSSI参数

根据实际环境调整：

1. **测量实际距离**：放置信标在已知距离（如5米）
2. **观察RSSI值**：运行扫描查看RSSI
3. **反推参数**：使用公式 `d = 10^((TxPower - RSSI) / (10 * n))` 反推TxPower和n

---

## 🚀 快速开始

### 不启用信标（当前）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine
```

所有工程车辆显示"未备案"

### 启用信标

```bash
python3 python_apps/tensorrt_yolo_inference.py \
    ../20211216-101333.mp4 \
    --engine models/yolov11_host.engine \
    --cassia-ac "http://192.168.1.100" \
    --cassia-key "your_key" \
    --cassia-secret "your_secret" \
    --cassia-router "CC:1B:E0:E2:E9:B8"
```

根据信标匹配结果区分已备案/未备案

---

## 📝 检查清单

在启用信标前，确认：

- [ ] Cassia AC可访问（`ping ac-ip`）
- [ ] 开发者账号已创建
- [ ] 路由器已添加到AC
- [ ] 路由器在线（AC Web界面查看）
- [ ] 信标在路由器覆盖范围内
- [ ] 已安装aiohttp和aiohttp-sse-client
- [ ] 测试过cassia_beacon_client.py能扫描到信标

---

## 💡 常见问题

### 问题1：认证失败

**错误**：`Auth failed: Unauthorized`

**解决**：
- 检查CASSIA_KEY和CASSIA_SECRET是否正确
- 在AC Web界面重新生成密钥

### 问题2：扫描不到信标

**可能原因**：
- 路由器离线
- 信标距离太远（RSSI < -90）
- filter_rssi阈值太高

**解决**：
- 调低filter_rssi（在cassia_beacon_client.py第92行）
- 检查路由器状态

### 问题3：距离不准确

**原因**：RSSI转距离参数不准确

**解决**：
- 实际测量调整tx_power和path_loss_exponent
- 或直接使用Orbbec深度相机

### 问题4：匹配率低

**原因**：tolerance太小

**解决**：
- 增大tolerance（2.5 → 3.5米）
- 或改进距离估计方法

---

## 🎯 下一步

1. **配置Cassia**：填写cassia_config.sh
2. **测试扫描**：运行cassia_beacon_client.py
3. **调整参数**：根据实际环境调整RSSI参数
4. **集成深度相机**：使用Orbbec获取精确距离
5. **生产部署**：完整测试后部署

---

**参考文档**：
- Cassia SDK: https://github.com/CassiaNetworks/CassiaSDKGuide/wiki
- API文档: https://github.com/CassiaNetworks/CassiaSDKGuide/wiki/RESTful-API

**本地SDK示例**：
- `/home/liubo/Download/CassiaSDKGuide-master/python_examples/`

