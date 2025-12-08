# DeepStream安装指南

## 📋 检测结果

- **平台**: Jetson (R36.4.7)
- **JetPack**: 6.2.1  
- **TensorRT**: ✅ 已安装
- **CUDA**: ✅ 已安装
- **DeepStream**: ❌ 未安装

---

## 🚀 DeepStream安装步骤

### 方法1: APT安装（推荐）

```bash
# JetPack 6.x 对应 DeepStream 7.x

# 1. 更新软件源
sudo apt update

# 2. 安装DeepStream
sudo apt install deepstream-7.0 -y

# 3. 验证安装
deepstream-app --version
```

### 方法2: 手动安装deb包

如果apt安装失败，手动下载安装：

```bash
# 1. 下载DeepStream 7.0 for JetPack 6.x
# https://developer.nvidia.com/deepstream-sdk

# 2. 安装
sudo apt install ./deepstream-7.0_7.0.0-1_arm64.deb

# 3. 安装依赖
sudo apt install \
    libssl3 \
    libgstreamer1.0-0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer-plugins-base1.0-dev \
    libgstrtspserver-1.0-0 \
    libjansson4
```

---

## 🐍 Python绑定安装

DeepStream Python绑定用于自定义处理（HyperLPR集成）：

```bash
# 1. 进入DeepStream Python源码目录
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps

# 2. 安装依赖
sudo apt install python3-gi python3-dev python3-gst-1.0 \
    python-gi-dev git python-dev \
    python3 python3-pip python3.10-dev \
    cmake g++ build-essential \
    libglib2.0-dev libglib2.0-dev-bin \
    libgstreamer1.0-dev \
    libtool m4 autoconf automake \
    libgirepository1.0-dev \
    libcairo2-dev

# 3. 编译安装Python绑定
cd bindings
mkdir build && cd build
cmake ..
make -j$(nproc)
pip3 install ./pyds-*.whl

# 4. 验证
python3 -c "import pyds; print('✓ pyds installed')"
```

---

## 🔧 安装后配置

### 1. 设置环境变量

```bash
# 添加到~/.bashrc
echo 'export LD_LIBRARY_PATH=/opt/nvidia/deepstream/deepstream/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
echo 'export GST_PLUGIN_PATH=/opt/nvidia/deepstream/deepstream/lib/gst-plugins:$GST_PLUGIN_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 2. 验证GStreamer插件

```bash
# 检查DeepStream插件
gst-inspect-1.0 nvinfer
gst-inspect-1.0 nvtracker  
gst-inspect-1.0 nvvideoconvert

# 应该都能找到
```

---

## 📊 DeepStream示例测试

### 运行官方示例

```bash
cd /opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app

# 测试视频检测
deepstream-app -c source1_usb_dec_infer_resnet_int8.txt
```

如果成功运行，说明DeepStream安装正确！

---

## 🎯 下一步

安装完成后：

1. **准备TensorRT引擎**
   ```bash
   bash scripts/prepare_tensorrt.sh
   ```

2. **配置YOLOv11**
   - 编写config_infer_yolov11.txt
   - 自定义解析器（如需要）

3. **集成HyperLPR**
   - Python probe函数
   - 车牌识别逻辑

4. **完整测试**
   - 视频文件测试
   - 实时流测试

---

## 📚 参考资源

- [DeepStream官方文档](https://docs.nvidia.com/metropolis/deepstream/)
- [DeepStream Python Apps](https://github.com/NVIDIA-AI-IOT/deepstream_python_apps)
- [DeepStream论坛](https://forums.developer.nvidia.com/c/accelerated-computing/intelligent-video-analytics/deepstream-sdk/)

---

**预计开发时间**: 1-2天  
**最终性能**: 50-100 FPS (GPU加速)


