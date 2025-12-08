#!/bin/bash

# DeepStream环境检查

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          DeepStream环境检查                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查Jetson版本
echo "【Jetson版本】"
if [ -f /etc/nv_tegra_release ]; then
    cat /etc/nv_tegra_release | head -1
else
    echo "⚠ 非Jetson平台"
fi
echo ""

# 检查JetPack
echo "【JetPack版本】"
if command -v jetson_release &> /dev/null; then
    jetson_release -v
else
    echo "  检查nvidia-jetpack包..."
    dpkg -l | grep nvidia-jetpack | head -1
fi
echo ""

# 检查DeepStream
echo "【DeepStream状态】"
if command -v deepstream-app &> /dev/null; then
    DS_VERSION=$(deepstream-app --version 2>&1 | grep -i version | head -1)
    echo "  ✓ DeepStream已安装: $DS_VERSION"
    DS_INSTALLED=true
else
    echo "  ✗ DeepStream未安装"
    DS_INSTALLED=false
fi
echo ""

# 检查TensorRT
echo "【TensorRT】"
if command -v trtexec &> /dev/null; then
    TRT_VERSION=$(trtexec --help 2>&1 | grep "TensorRT version" | head -1)
    echo "  ✓ TensorRT: $TRT_VERSION"
    echo "  路径: $(which trtexec)"
elif [ -f /usr/src/tensorrt/bin/trtexec ]; then
    echo "  ✓ TensorRT: /usr/src/tensorrt/bin/trtexec"
else
    echo "  ✗ TensorRT未找到"
fi
echo ""

# 检查CUDA
echo "【CUDA】"
if [ -d /usr/local/cuda ]; then
    CUDA_VERSION=$(cat /usr/local/cuda/version.json 2>/dev/null | grep cuda_version | cut -d'"' -f4)
    echo "  ✓ CUDA: $CUDA_VERSION"
else
    echo "  ⚠ CUDA路径未找到"
fi
echo ""

# Python绑定
echo "【Python绑定】"
if python3 -c "import pyds" 2>/dev/null; then
    echo "  ✓ pyds (DeepStream Python绑定)"
else
    echo "  ✗ pyds未安装"
fi

if python3 -c "import gi; gi.require_version('Gst', '1.0')" 2>/dev/null; then
    echo "  ✓ GStreamer Python绑定"
else
    echo "  ✗ GStreamer Python绑定未安装"
fi
echo ""

# 总结
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              检查总结                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [ "$DS_INSTALLED" = true ]; then
    echo "✅ DeepStream已就绪，可以开始开发"
    echo ""
    echo "下一步:"
    echo "  1. 准备TensorRT引擎: bash scripts/prepare_tensorrt.sh"
    echo "  2. 配置YOLOv11解析器"
    echo "  3. 编写DeepStream应用"
else
    echo "⚠ 需要安装DeepStream"
    echo ""
    echo "安装步骤:"
    echo ""
    echo "1. 检查JetPack版本"
    echo "   dpkg -l | grep nvidia-jetpack"
    echo ""
    echo "2. 安装DeepStream (根据JetPack版本)"
    echo "   # JetPack 6.x"
    echo "   sudo apt install deepstream-7.0"
    echo ""
    echo "   # 或下载deb包"
    echo "   # https://developer.nvidia.com/deepstream-sdk"
    echo ""
    echo "3. 安装Python绑定"
    echo "   cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps"
    echo "   sudo python3 setup.py install"
    echo ""
    echo "4. 重新运行此脚本验证"
fi

