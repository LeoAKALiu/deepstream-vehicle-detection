# pyorbbecsdk API 快速参考

本文档列出了pyorbbecsdk的正确API用法，基于实际安装的版本。

---

## 📦 Pipeline

### 创建和配置

```python
import pyorbbecsdk as ob

# 创建Pipeline
pipeline = ob.Pipeline()

# 获取设备
device = pipeline.get_device()

# 获取流配置列表
color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)

# 创建配置
config = ob.Config()

# 启用流
config.enable_stream(color_profile)
config.enable_stream(depth_profile)

# 设置对齐模式
config.set_align_mode(ob.OBAlignMode.HW_MODE)

# 启动
pipeline.start(config)

# 获取帧
frames = pipeline.wait_for_frames(timeout_ms)

# 停止
pipeline.stop()
```

### Pipeline方法

- `get_device()` - 获取设备对象
- `get_stream_profile_list(sensor_type)` - 获取传感器的流配置列表
- `start(config)` - 启动管道
- `stop()` - 停止管道
- `wait_for_frames(timeout_ms)` - 等待帧数据
- `get_config()` - 获取当前配置
- `get_camera_param()` - 获取相机参数
- `enable_frame_sync()` - 启用帧同步
- `disable_frame_sync()` - 禁用帧同步

---

## 📱 DeviceInfo

### 获取设备信息

```python
device = pipeline.get_device()
device_info = device.get_device_info()

# 所有方法都以 get_ 开头
name = device_info.get_name()
pid = device_info.get_pid()
vid = device_info.get_vid()
uid = device_info.get_uid()
serial = device_info.get_serial_number()
firmware = device_info.get_firmware_version()
hardware = device_info.get_hardware_version()
conn_type = device_info.get_connection_type()
device_type = device_info.get_device_type()
min_sdk = device_info.get_supported_min_sdk_version()
```

### DeviceInfo方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_name()` | str | 设备名称 |
| `get_pid()` | int | 产品ID |
| `get_vid()` | int | 供应商ID |
| `get_uid()` | str | 唯一ID |
| `get_serial_number()` | str | 序列号 |
| `get_firmware_version()` | str | 固件版本 |
| `get_hardware_version()` | str | 硬件版本 |
| `get_connection_type()` | str | 连接类型 |
| `get_device_type()` | str | 设备类型 |
| `get_supported_min_sdk_version()` | str | 最小SDK版本 |

---

## 🎥 VideoStreamProfile

### 获取流信息

```python
profile_list = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
profile = profile_list.get_default_video_stream_profile()

# 所有方法都以 get_ 开头
width = profile.get_width()
height = profile.get_height()
fps = profile.get_fps()
format = profile.get_format()
stream_type = profile.get_type()
```

### VideoStreamProfile方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_width()` | int | 宽度（像素） |
| `get_height()` | int | 高度（像素） |
| `get_fps()` | int | 帧率 |
| `get_format()` | OBFormat | 格式 |
| `get_type()` | OBStreamType | 流类型 |
| `get_intrinsic()` | OBCameraIntrinsic | 内参 |
| `get_distortion()` | OBCameraDistortion | 畸变 |
| `is_video_stream_profile()` | bool | 是否视频流 |
| `as_video_stream_profile()` | VideoStreamProfile | 转换为视频流 |

---

## 🎨 Config

### 配置管道

```python
config = ob.Config()

# 启用流
config.enable_stream(profile)

# 设置对齐模式
config.set_align_mode(ob.OBAlignMode.HW_MODE)
```

---

## 🔄 OBAlignMode（对齐模式）

```python
# 可用模式
ob.OBAlignMode.HW_MODE    # 硬件对齐（推荐）
ob.OBAlignMode.SW_MODE    # 软件对齐
ob.OBAlignMode.DISABLE    # 禁用对齐
```

### 说明

- **HW_MODE**: 使用硬件加速对齐，性能最好，推荐使用
- **SW_MODE**: 软件对齐，兼容性好但性能较低
- **DISABLE**: 不对齐，深度和彩色图独立

---

## 📡 OBSensorType（传感器类型）

```python
ob.OBSensorType.COLOR_SENSOR      # 彩色传感器
ob.OBSensorType.DEPTH_SENSOR      # 深度传感器
ob.OBSensorType.IR_SENSOR         # 红外传感器
ob.OBSensorType.LEFT_IR_SENSOR    # 左红外
ob.OBSensorType.RIGHT_IR_SENSOR   # 右红外
ob.OBSensorType.GYRO_SENSOR       # 陀螺仪
ob.OBSensorType.ACCEL_SENSOR      # 加速度计
ob.OBSensorType.UNKNOWN_SENSOR    # 未知
```

---

## 🖼️ FrameSet

### 获取帧数据

```python
frames = pipeline.wait_for_frames(1000)  # timeout 1000ms

if frames:
    # 获取彩色帧
    color_frame = frames.get_color_frame()
    
    # 获取深度帧
    depth_frame = frames.get_depth_frame()
    
    # 获取红外帧
    ir_frame = frames.get_ir_frame()
```

---

## 🎞️ Frame

### 读取帧信息

```python
# 彩色帧
color_frame = frames.get_color_frame()
if color_frame:
    width = color_frame.get_width()
    height = color_frame.get_height()
    data = color_frame.get_data()  # bytes
    
    # 转换为numpy
    import numpy as np
    color_image = np.frombuffer(data, dtype=np.uint8)
    color_image = color_image.reshape((height, width, 3))

# 深度帧
depth_frame = frames.get_depth_frame()
if depth_frame:
    width = depth_frame.get_width()
    height = depth_frame.get_height()
    data = depth_frame.get_data()  # bytes
    value_scale = depth_frame.get_value_scale()  # mm单位
    
    # 转换为numpy
    depth_image = np.frombuffer(data, dtype=np.uint16)
    depth_image = depth_image.reshape((height, width))
    
    # 转换为米
    depth_m = depth_image * value_scale / 1000.0
```

### Frame方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_width()` | int | 宽度 |
| `get_height()` | int | 高度 |
| `get_data()` | bytes | 原始数据 |
| `get_format()` | OBFormat | 格式 |
| `get_type()` | OBFrameType | 帧类型 |
| `get_timestamp()` | int | 时间戳 |
| `get_value_scale()` | float | 深度值缩放 |

---

## 💡 完整示例

```python
import pyorbbecsdk as ob
import numpy as np

# 1. 创建Pipeline
pipeline = ob.Pipeline()

# 2. 配置
config = ob.Config()

# 启用彩色流
color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
color_profile = color_profiles.get_default_video_stream_profile()
config.enable_stream(color_profile)
print(f"彩色: {color_profile.get_width()}x{color_profile.get_height()} @{color_profile.get_fps()}fps")

# 启用深度流
depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
depth_profile = depth_profiles.get_default_video_stream_profile()
config.enable_stream(depth_profile)
print(f"深度: {depth_profile.get_width()}x{depth_profile.get_height()} @{depth_profile.get_fps()}fps")

# 启用对齐
config.set_align_mode(ob.OBAlignMode.HW_MODE)

# 3. 启动
pipeline.start(config)

# 4. 采集
try:
    while True:
        frames = pipeline.wait_for_frames(1000)
        if frames is None:
            continue
        
        # 彩色
        color_frame = frames.get_color_frame()
        if color_frame:
            data = color_frame.get_data()
            h, w = color_frame.get_height(), color_frame.get_width()
            color_image = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3))
        
        # 深度
        depth_frame = frames.get_depth_frame()
        if depth_frame:
            data = depth_frame.get_data()
            h, w = depth_frame.get_height(), depth_frame.get_width()
            scale = depth_frame.get_value_scale()
            depth_image = np.frombuffer(data, dtype=np.uint16).reshape((h, w))
            depth_m = depth_image * scale / 1000.0
            
            # 中心点深度
            cy, cx = h // 2, w // 2
            print(f"中心深度: {depth_m[cy, cx]:.3f}m")

except KeyboardInterrupt:
    pass

finally:
    pipeline.stop()
```

---

## ⚠️ 常见错误

### 错误1：AttributeError

```python
# ✗ 错误
device_info.name()
profile.width()

# ✓ 正确
device_info.get_name()
profile.get_width()
```

**所有获取属性的方法都以`get_`开头！**

### 错误2：对齐模式错误

```python
# ✗ 错误
config.set_align_mode(ob.OBAlignMode.ALIGN_D2C_HW_MODE)

# ✓ 正确
config.set_align_mode(ob.OBAlignMode.HW_MODE)
```

### 错误3：numpy转换

```python
# ✗ 错误 - 忘记reshape
data = frame.get_data()
image = np.frombuffer(data, dtype=np.uint8)  # 一维数组！

# ✓ 正确
data = frame.get_data()
h, w = frame.get_height(), frame.get_width()
image = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3))
```

---

## 📚 参考资源

- **官方GitHub**: https://github.com/orbbec/pyorbbecsdk
- **设备支持**: Gemini 335L (完全支持)
- **Python版本**: 3.8-3.13

---

**版本**: pyorbbecsdk (当前安装版本)  
**最后更新**: 2025-10-27






