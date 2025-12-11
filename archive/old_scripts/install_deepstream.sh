#!/bin/bash

# DeepStream安装脚本（JetPack 6.x）

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          DeepStream安装脚本                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查JetPack
JETPACK_VERSION=$(dpkg -l | grep nvidia-jetpack | awk '{print $3}' | cut -d'+' -f1)
echo "检测到JetPack版本: $JETPACK_VERSION"
echo ""

if [[ "$JETPACK_VERSION" == 6.* ]]; then
    DS_VERSION="7.0"
elif [[ "$JETPACK_VERSION" == 5.* ]]; then
    DS_VERSION="6.4"
else
    echo "⚠ 未知JetPack版本，假设使用DeepStream 7.0"
    DS_VERSION="7.0"
fi

echo "对应DeepStream版本: $DS_VERSION"
echo ""

# 安装DeepStream
echo "步骤1: 安装DeepStream"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "是否安装DeepStream $DS_VERSION? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "已取消"
    exit 0
fi

echo "更新软件源..."
sudo apt update

echo "安装DeepStream $DS_VERSION..."
sudo apt install -y deepstream-${DS_VERSION}

if [ $? -ne 0 ]; then
    echo ""
    echo "✗ APT安装失败"
    echo ""
    echo "请手动安装:"
    echo "  1. 访问 https://developer.nvidia.com/deepstream-sdk"
    echo "  2. 下载对应JetPack版本的deb包"
    echo "  3. sudo apt install ./deepstream-*.deb"
    exit 1
fi

echo ""
echo "步骤2: 安装Python绑定"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 安装Python依赖
sudo apt install -y \
    python3-gi \
    python3-dev \
    python3-gst-1.0 \
    python-gi-dev \
    git \
    cmake \
    g++ \
    build-essential \
    libglib2.0-dev \
    libglib2.0-dev-bin \
    libgstreamer1.0-dev \
    libtool \
    m4 \
    autoconf \
    automake \
    libgirepository1.0-dev \
    libcairo2-dev

# 编译Python绑定
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/bindings

if [ ! -d "build" ]; then
    mkdir build
fi

cd build
cmake ..
make -j$(nproc)

# 安装wheel
pip3 install ./pyds-*.whl

echo ""
echo "步骤3: 验证安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 验证
if command -v deepstream-app &> /dev/null; then
    echo "✓ deepstream-app: $(deepstream-app --version 2>&1 | head -1)"
fi

if python3 -c "import pyds" 2>/dev/null; then
    echo "✓ pyds (Python绑定)"
fi

if python3 -c "import gi; gi.require_version('Gst', '1.0')" 2>/dev/null; then
    echo "✓ GStreamer Python"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✅ DeepStream安装完成                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "下一步:"
echo "  1. 准备TensorRT引擎: bash scripts/prepare_tensorrt.sh"
echo "  2. 测试DeepStream: bash scripts/test_deepstream.sh"
echo "  3. 运行车辆检测: bash run_deepstream.sh"

