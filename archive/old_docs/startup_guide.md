# 🚀 DeepStream应用启动说明

## ⚡ 快速启动（推荐）

### 一键测试

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash 测试DeepStream应用.sh
```

这个脚本会：
1. 检查视频文件
2. 启动DeepStream容器
3. 自动运行Python应用
4. 显示检测结果和统计

---

## 📋 手动启动（用于调试）

### 步骤1：进入容器

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash
```

### 步骤2：检查环境（在容器内）

```bash
# 检查pyds
python3 -c "import pyds; print('✓ pyds可用')"

# 检查文件
ls -lh models/yolov11.engine
ls config/config_infer_yolov11.txt

# 检查GStreamer插件
gst-inspect-1.0 nvstreammux | head -5
```

### 步骤3：运行应用（在容器内）

```bash
# 基础运行
python3 python_apps/deepstream_vehicle_detection.py \
    /workspace/20211216-101333.mp4

# 或启用详细日志
export GST_DEBUG=3
export NVDS_LOG_LEVEL=5
python3 python_apps/deepstream_vehicle_detection.py \
    /workspace/20211216-101333.mp4
```

---

## 🔧 如果遇到问题

### 问题1：pyds导入失败

```bash
# 在容器内安装pyds
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/bindings/
pip3 install ./
```

### 问题2：找不到配置文件

修改Python代码中的路径为绝对路径：
```python
pgie.set_property('config-file-path', 
    '/workspace/deepstream-vehicle-detection/config/config_infer_yolov11.txt')
```

### 问题3：YOLO解析错误

这是预期的，需要查看具体错误信息：
- 如果是"parse-bbox-func-name not found"，需要自定义解析器
- 查看 `开发指南.md` 的"YOLO输出解析"章节

### 问题4：Pipeline启动失败

```bash
# 测试最简pipeline（在容器内）
gst-launch-1.0 \
    filesrc location=/workspace/20211216-101333.mp4 ! \
    h264parse ! \
    nvv4l2decoder ! \
    nvstreammux width=1920 height=1080 batch-size=1 ! \
    nvinfer config-file-path=config/config_infer_yolov11.txt ! \
    nvvideoconvert ! \
    nvdsosd ! \
    fakesink
```

---

## 📊 预期输出

### 正常运行时

```
═══════════════════════════════════════
DeepStream车辆检测系统
═══════════════════════════════════════
输入: /workspace/20211216-101333.mp4
═══════════════════════════════════════

✓ HyperLPR未安装

启动DeepStream应用...
  创建GStreamer elements...
  ✓ Elements创建成功
  链接pipeline...
  ✓ Pipeline构建完成
  添加probe函数...
  ✓ Probe添加成功
  启动pipeline...
  ✓ Pipeline运行中...

按Ctrl+C停止

新车辆 ID1: 挖掘机 (excavator), 帧123
新车辆 ID2: 卡车 (truck), 帧156
...

视频结束

═══════════════════════════════════════
DeepStream检测统计
═══════════════════════════════════════

【工程车辆】
  总数: 15 辆

  挖掘机        :    5 辆 (33.3%)
  装载机        :    3 辆 (20.0%)
  自卸车        :    7 辆 (46.7%)

【车牌识别】
  未识别到

═══════════════════════════════════════
```

### 性能指标

- **FPS**: 50-100 FPS（目标）
- **GPU使用率**: 80-95%
- **内存占用**: ~2GB
- **延迟**: <50ms

---

## 🐛 调试模式

### 启用所有日志

```bash
# 在容器内
export GST_DEBUG=4
export NVDS_LOG_LEVEL=6
export G_MESSAGES_DEBUG=all

python3 python_apps/deepstream_vehicle_detection.py video.mp4 2>&1 | tee debug.log
```

### 单独测试TensorRT引擎

```bash
# 在容器内
/usr/src/tensorrt/bin/trtexec \
    --loadEngine=models/yolov11.engine \
    --verbose \
    --dumpOutput \
    --dumpProfile
```

### 查看DeepStream示例

```bash
# 在容器内
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/deepstream-test1/

# 使用官方模型测试（验证环境）
python3 deepstream_test_1.py /opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.h264

# 使用我们的模型测试
python3 deepstream_test_1.py /workspace/20211216-101333.mp4
```

---

## 🎯 下一步优化

### 1. 如果检测正常，但跟踪不稳定

调整 `config/config_tracker_NvDCF_accuracy.yml`:
```yaml
minDetectorConfidence: 0.4  # 降低阈值
maxTargetPerStream: 100     # 增加最大跟踪数
```

### 2. 如果性能不够

#### 选项A：降低分辨率
```python
streammux.set_property('width', 1280)   # 从1920降低
streammux.set_property('height', 720)   # 从1080降低
```

#### 选项B：跳帧检测
```ini
# config/config_infer_yolov11.txt
interval=2  # 每3帧检测1次
```

#### 选项C：调整batch-size
```ini
# config/config_infer_yolov11.txt
batch-size=2  # 批处理
```

### 3. 如果需要车牌识别

```bash
# 在容器内安装HyperLPR
pip3 install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple hyperlpr3
```

然后参考 `开发指南.md` 的"HyperLPR集成"章节。

---

## 📚 参考文档

- **README.md** - 项目概览
- **开发指南.md** - 详细开发指南
- **今日成果与明日计划.md** - 开发进度

---

## 💡 提示

1. **首次运行**：预期会有一些问题需要调试
2. **最大挑战**：YOLO输出解析器适配
3. **最简测试**：先用 `gst-launch-1.0` 测试pipeline
4. **参考示例**：容器内的 `/opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/apps/`

**祝你好运！🚀**

如有问题，请查看错误信息并参考 `开发指南.md` 故障排除章节。

