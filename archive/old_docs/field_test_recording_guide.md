# 现场测试视频录制说明

## 📹 功能概述

现场测试录制脚本可以在主程序运行的同时，同步录制Orbbec相机的原始RGB和深度视频，方便回到实验室后进行回放分析和查漏补缺。

## 🚀 快速使用

### 方式1：使用集成启动脚本（推荐）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
./start_field_test_with_recording.sh
```

这个脚本会：
1. 自动启动视频录制（后台运行）
2. 等待录制器初始化
3. 启动主检测程序（前台运行）
4. 主程序退出时自动停止录制

### 方式2：手动分别启动

**终端1 - 启动录制**：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
python3 python_apps/record_field_test.py --output-dir recordings
```

**终端2 - 启动主程序**：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
./测试实时系统.sh
```

录制完成后，在终端1按 `Ctrl+C` 停止录制。

## 📁 输出文件结构

录制文件保存在 `recordings/` 目录下，每次录制会创建一个带时间戳的子目录：

```
recordings/
└── field_test_20241104_143022/
    ├── rgb_video.mp4          # RGB视频（带时间戳）
    ├── depth_video.mp4        # 深度视频（灰度，可选）
    ├── metadata.json          # 元数据（分辨率、FPS等）
    └── recording_*.log         # 录制日志（如果使用集成脚本）
```

## ⚙️ 命令行参数

### `record_field_test.py`

```bash
python3 python_apps/record_field_test.py [选项]
```

**选项**：
- `--output-dir DIR`: 输出目录（默认: `recordings`）
- `--no-depth`: 不录制深度视频，仅录制RGB（节省空间）
- `--duration SECONDS`: 自动停止录制时长（秒），0表示持续录制直到手动停止

**示例**：
```bash
# 仅录制RGB视频
python3 python_apps/record_field_test.py --no-depth

# 录制30分钟后自动停止
python3 python_apps/record_field_test.py --duration 1800

# 指定输出目录
python3 python_apps/record_field_test.py --output-dir /mnt/usb/recordings
```

## 📊 录制信息

### 视频规格
- **RGB视频**：
  - 格式：MP4 (H.264)
  - 分辨率：相机原始分辨率（通常1280x720或640x480）
  - 帧率：15 FPS
  - 包含时间戳水印

- **深度视频**：
  - 格式：MP4 (灰度)
  - 分辨率：与RGB相同
  - 帧率：15 FPS
  - 已归一化到0-255范围（用于可视化）

### 元数据文件

`metadata.json` 包含以下信息：
```json
{
  "timestamp": "2024-11-04T14:30:22.123456",
  "resolution": "1280x720",
  "fps": 15,
  "record_depth": true,
  "camera": "Orbbec Gemini 335L"
}
```

## 🔧 技术细节

### 录制流程
1. 初始化Orbbec相机
2. 等待相机稳定（2秒）
3. 获取第一帧确定分辨率
4. 创建视频写入器（RGB + 深度）
5. 循环录制：
   - 获取RGB帧 → 添加时间戳 → 写入RGB视频
   - 获取深度帧 → 归一化处理 → 写入深度视频
6. 按 `Ctrl+C` 停止录制
7. 保存元数据并关闭所有资源

### 性能考虑
- **帧率控制**：目标15 FPS，避免过快录制
- **内存管理**：及时释放帧数据
- **磁盘空间**：深度视频会增加约50%存储空间
- **CPU占用**：录制过程CPU占用较低（主要是I/O操作）

### 注意事项
1. **相机独占**：录制脚本和主程序不能同时使用同一相机
   - 解决方案：使用集成启动脚本，确保正确的启动顺序
   - 或者：主程序使用 `--no-depth` 禁用深度相机，仅录制脚本使用相机

2. **存储空间**：
   - RGB视频：约 50-100 MB/分钟（取决于分辨率）
   - 深度视频：约 30-50 MB/分钟
   - 建议准备至少 10GB 可用空间

3. **录制时长**：
   - 建议单次录制不超过2小时
   - 长时间录制建议分段（每30-60分钟一段）

## 🎬 回放和分析

### 使用VLC或其他播放器
```bash
# 播放RGB视频
vlc recordings/field_test_20241104_143022/rgb_video.mp4

# 播放深度视频
vlc recordings/field_test_20241104_143022/depth_video.mp4
```

### 使用OpenCV分析
```python
import cv2

# 读取RGB视频
cap = cv2.VideoCapture('recordings/field_test_20241104_143022/rgb_video.mp4')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # 处理帧...
    cv2.imshow('RGB', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
```

### 提取关键帧
可以使用FFmpeg提取特定时间点的帧：
```bash
# 提取第30秒的帧
ffmpeg -i rgb_video.mp4 -ss 00:00:30 -vframes 1 frame_30s.jpg
```

## 🐛 故障排除

### 问题1：无法创建视频文件
**症状**：提示"无法创建RGB视频文件"

**解决方案**：
- 检查输出目录权限：`chmod 755 recordings`
- 检查磁盘空间：`df -h`
- 检查文件系统是否支持大文件

### 问题2：录制帧率过低
**症状**：FPS < 10

**解决方案**：
- 检查相机连接和USB带宽
- 降低录制分辨率（如果相机支持）
- 关闭深度录制（`--no-depth`）

### 问题3：深度视频全黑或异常
**症状**：深度视频没有内容或颜色异常

**解决方案**：
- 检查深度相机是否正常工作
- 确认物体在有效深度范围内（0.5-10米）
- 查看录制日志中的错误信息

### 问题4：相机被占用
**症状**：提示"相机启动失败"或"无法获取相机画面"

**解决方案**：
- 确保主程序没有同时使用相机
- 使用集成启动脚本确保正确的启动顺序
- 检查其他程序是否占用相机：`lsof /dev/video*`

## 📝 最佳实践

1. **测试前准备**：
   - 检查存储空间充足
   - 测试录制功能（短时间录制）
   - 确认相机正常工作

2. **现场录制**：
   - 使用集成启动脚本（最简单）
   - 记录测试场景和关键时间点
   - 定期检查录制文件大小

3. **录制后处理**：
   - 及时备份录制文件
   - 重命名有意义的目录名
   - 记录测试场景到README文件

## 🔄 与主程序的协调

### ✅ 当前实现：主程序独占相机，录制从共享缓冲区读取

**架构**：
- **主程序**：独占相机，正常进行检测和深度测量，同时将帧保存到共享缓冲区
- **录制脚本**：从共享缓冲区读取帧，不初始化相机，仅负责录制视频
- **优点**：
  - 主程序功能完整（包括深度测量）
  - 录制脚本不影响主程序性能
  - 无相机冲突问题

**使用**：
```bash
./start_field_test_with_recording.sh
```

**工作原理**：
1. 主程序启动并初始化相机
2. 主程序在每次获取帧后，将帧保存到 `/tmp/orbbec_shared_frame.npy`
3. 录制脚本从共享缓冲区读取帧并录制
4. 主程序退出时，录制脚本自动停止

### 方案2：仅录制，不运行主程序

**特点**：
- 仅录制原始视频，不进行实时检测
- 回到实验室后再分析视频

**使用**：
```bash
python3 python_apps/record_field_test.py --output-dir recordings
```

**注意**：此方案需要主程序先运行以创建共享缓冲区，或者需要修改录制脚本直接初始化相机。

---

**最后更新**: 2024年11月4日

