# API参考文档

本文档记录项目中使用的第三方库的正确API用法。

---

## 1. Cassia本地客户端 API

### 文件
`python_apps/cassia_local_client.py`

### 类: CassiaLocalClient

**初始化**
```python
from cassia_local_client import CassiaLocalClient

client = CassiaLocalClient(
    router_ip='192.168.1.27',  # 路由器IP
    username=None,              # 可选，认证用户名
    password=None               # 可选，认证密码
)
```

**启动/停止扫描**
```python
# 启动后台扫描
client.start()  # ✓ 正确

# 停止扫描
client.stop()   # ✓ 正确
```

**获取信标数据**
```python
# 获取最近的信标
beacons = client.get_beacons(max_age=5.0)
# 返回: [{'mac': x, 'rssi': x, 'name': x, 'distance': x}, ...]

# 查找最近的信标
beacon = client.find_nearest_beacon(
    target_distance=2.5,  # 目标距离（米）
    tolerance=1.0          # 容差（米）
)
# 返回: {'mac': x, 'rssi': x, 'distance': x, 'distance_diff': x} 或 None
```

---

## 2. HyperLPR3 车牌识别 API

### 导入
```python
import hyperlpr3 as lpr3
```

### 类: LicensePlateCatcher

**初始化**
```python
catcher = lpr3.LicensePlateCatcher(
    inference=lpr3.INFER_ONNX_RUNTIME,     # 推理引擎
    detect_level=lpr3.DETECT_LEVEL_LOW,    # 检测精度
    logger_level=3                          # 日志级别
)
```

**推理引擎选项**
```python
lpr3.INFER_ONNX_RUNTIME  # ONNX Runtime（推荐，兼容性好）
lpr3.INFER_MNN           # MNN（更快，但依赖较多）
```

**检测精度选项**
```python
lpr3.DETECT_LEVEL_LOW   # 低精度（快速）
lpr3.DETECT_LEVEL_HIGH  # 高精度（慢速）
```

**识别车牌**
```python
# LicensePlateCatcher是可调用对象，直接调用
results = catcher(image)  # ✓ 正确
# 参数: image - numpy数组 (H, W, 3), BGR格式
# 返回: [Plate对象] 或 []

# 处理结果
if results and len(results) > 0:
    plate = results[0]
    print(f"车牌号: {plate.code}")
    print(f"置信度: {plate.confidence}")
    print(f"颜色: {plate.color}")
    print(f"边界框: {plate.box}")  # [x1, y1, x2, y2]
```

**注意：**
- ✅ 使用 `catcher(image)` 直接调用
- ❌ 不要使用 `catcher.single_recognition(image)`

### Plate对象属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `code` | str | 车牌号字符串 |
| `confidence` | float | 识别置信度 (0-1) |
| `color` | int | 车牌颜色类型 |
| `box` | list | 边界框 [x1, y1, x2, y2] |

**车牌颜色常量**
```python
lpr3.BLUE           # 蓝牌
lpr3.YELLOW_SINGLE  # 黄牌单行
lpr3.YELLOW_DOUBLE  # 黄牌双行
lpr3.GREEN          # 绿牌（新能源）
```

---

## 3. Orbbec深度相机 API

### 文件
`python_apps/orbbec_depth.py`

### 类: OrbbecDepthCamera

**初始化**
```python
from orbbec_depth import OrbbecDepthCamera

camera = OrbbecDepthCamera()
```

**启动/停止**
```python
# 启动相机
camera.start()

# 停止相机
camera.stop()
```

**获取数据**
```python
# 获取RGB帧（自动处理MJPEG解码和格式转换）
rgb_frame = camera.get_color_frame()
# 返回: numpy数组 (H, W, 3), RGB格式 或 None
# 支持格式: MJPG, RGB, BGR（自动转换为RGB）

# 获取指定点深度
depth = camera.get_depth_at_point(x=320, y=240)
# 返回: 深度值（米）或 None

# 获取区域深度统计
stats = camera.get_depth_region_stats(
    bbox=[x1, y1, x2, y2],  # 边界框
    method='median'          # 'mean', 'median', 'min'
)
# 返回: 深度值（米）或 None
```

**注意事项**
- `get_color_frame()` 返回RGB格式（不是BGR）
- MJPEG格式会自动解码
- 所有方法都是线程安全的

---

## 4. pyorbbecsdk API

### 导入
```python
import pyorbbecsdk as ob
```

### 核心类和方法

**Pipeline**
```python
pipeline = ob.Pipeline()
device = pipeline.get_device()
```

**Config**
```python
config = ob.Config()

# 启用流
config.enable_stream(profile)

# 设置对齐模式
config.set_align_mode(ob.OBAlignMode.SW_MODE)  # 软件对齐
config.set_align_mode(ob.OBAlignMode.HW_MODE)  # 硬件对齐（需分辨率匹配）
```

**Frame对象**
```python
# 通用方法
width = frame.get_width()
height = frame.get_height()
format_type = frame.get_format()
data = frame.get_data()
data_size = frame.get_data_size()

# DepthFrame特有
depth_scale = depth_frame.get_depth_scale()

# ColorFrame
color_data = color_frame.get_data()
```

**格式转换**
```python
# MJPEG解码（如果相机输出MJPEG）
if color_frame.get_format() == ob.OBFormat.MJPG:
    import cv2
    data = np.frombuffer(color_frame.get_data(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
```

---

## 5. TensorRT API

### 兼容TensorRT 8.x和10.x

**加载引擎**
```python
import tensorrt as trt

logger = trt.Logger(trt.Logger.WARNING)
with open(engine_path, 'rb') as f:
    runtime = trt.Runtime(logger)
    engine = runtime.deserialize_cuda_engine(f.read())

context = engine.create_execution_context()
```

**获取绑定信息（兼容版本）**
```python
# TensorRT 8.x
if hasattr(engine, 'get_binding_name'):
    for i in range(engine.num_bindings):
        name = engine.get_binding_name(i)
        shape = engine.get_binding_shape(i)
        is_input = engine.binding_is_input(i)

# TensorRT 10.x
else:
    for i in range(engine.num_io_tensors):
        name = engine.get_tensor_name(i)
        shape = engine.get_tensor_shape(name)
        mode = engine.get_tensor_mode(name)
        is_input = (mode == trt.TensorIOMode.INPUT)
```

**执行推理（兼容版本）**
```python
# TensorRT 8.x
if hasattr(context, 'execute_async_v2'):
    context.execute_async_v2(
        bindings=[int(input_buffer), int(output_buffer)],
        stream_handle=stream.handle
    )

# TensorRT 10.x
else:
    context.set_tensor_address(input_name, int(input_buffer))
    context.set_tensor_address(output_name, int(output_buffer))
    context.execute_async_v3(stream_handle=stream.handle)
```

---

## 常见错误和修复

### 错误1: AttributeError: 'CassiaLocalClient' object has no attribute 'start_scan'
**修复**: 使用 `start()` 和 `stop()` 而不是 `start_scan()` 和 `stop_scan()`

### 错误2: AttributeError: module 'hyperlpr3' has no attribute 'LicensePlateCNN'
**修复**: 使用 `LicensePlateCatcher` 而不是 `LicensePlateCNN`

### 错误3: 'DepthFrame' object has no attribute 'get_value_scale'
**修复**: 使用 `get_depth_scale()` 而不是 `get_value_scale()`

### 错误4: 'VideoStreamProfile' object has no attribute 'width'
**修复**: 所有属性访问都需要 `get_` 前缀，如 `get_width()`

### 错误5: 'OBAlignMode' has no attribute 'ALIGN_D2C_HW_MODE'
**修复**: 使用 `SW_MODE` 或 `HW_MODE` 而不是 `ALIGN_D2C_HW_MODE`

### 错误6: 'OrbbecDepthCamera' object has no attribute 'get_color_frame'
**修复**: 已添加 `get_color_frame()` 方法（返回RGB格式，自动处理MJPEG解码）

### 错误7: 'LicensePlateCatcher' object has no attribute 'single_recognition'
**修复**: 使用 `catcher(image)` 直接调用，而不是 `catcher.single_recognition(image)`

---

## 版本信息

| 库 | 版本 | 说明 |
|---|------|------|
| TensorRT | 10.3.0 | Jetson预装 |
| pyorbbecsdk | latest | pip安装 |
| hyperlpr3 | latest | pip安装 |
| opencv-python | 4.x | pip安装 |

---

## 更新日志

- 2025-11-03: 创建文档，记录正确的API用法
- 修复Cassia客户端方法名
- 修复HyperLPR3 API调用
- 添加pyorbbecsdk完整API参考

