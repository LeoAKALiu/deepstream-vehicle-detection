#!/bin/bash

# DeepStream安装脚本（修复版）

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          DeepStream安装脚本（修复版）                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检测JetPack版本
JETPACK_VERSION=$(dpkg -l | grep nvidia-jetpack | awk '{print $3}' | cut -d'+' -f1)
echo "检测到JetPack版本: $JETPACK_VERSION"

# 确定DeepStream版本
if [[ "$JETPACK_VERSION" == 6.* ]]; then
    DS_VERSION="7.0"
    DS_DEB_NAME="deepstream-7.0_7.0.0-1_arm64.deb"
    DS_DOWNLOAD_URL="https://developer.nvidia.com/downloads/deepstream-70-jetson-deb"
elif [[ "$JETPACK_VERSION" == 5.* ]]; then
    DS_VERSION="6.4"
    DS_DEB_NAME="deepstream-6.4_6.4.0-1_arm64.deb"
    DS_DOWNLOAD_URL="https://developer.nvidia.com/downloads/deepstream-64-jetson-deb"
else
    echo "不支持的JetPack版本: $JETPACK_VERSION"
    exit 1
fi

echo "对应DeepStream版本: $DS_VERSION"
echo ""

# 检查是否已安装
if dpkg -l | grep -q deepstream; then
    INSTALLED_VERSION=$(dpkg -l | grep deepstream | awk '{print $3}')
    echo "✓ DeepStream已安装: $INSTALLED_VERSION"
    read -p "是否重新安装? (y/n): " reinstall
    if [ "$reinstall" != "y" ]; then
        echo "跳过安装"
        exit 0
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DeepStream安装方法"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "【方法1】手动下载deb包（推荐）"
echo ""
echo "  1. 在浏览器中打开："
echo "     https://developer.nvidia.com/deepstream-getting-started"
echo ""
echo "  2. 选择 'Download' -> 'Jetson' -> DeepStream $DS_VERSION"
echo ""
echo "  3. 下载文件: $DS_DEB_NAME"
echo ""
echo "  4. 保存到: /tmp/"
echo ""
echo "  5. 安装:"
echo "     sudo apt-get install -y /tmp/$DS_DEB_NAME"
echo ""
echo "【方法2】使用已下载的deb包"
echo ""

# 查找已下载的deb包
DEB_FOUND=""
SEARCH_PATHS=(
    "/tmp"
    "$HOME/Downloads"
    "$HOME/下载"
    "/home/liubo/Download"
    "/home/liubo/Downloads"
)

for path in "${SEARCH_PATHS[@]}"; do
    if [ -f "$path/$DS_DEB_NAME" ]; then
        DEB_FOUND="$path/$DS_DEB_NAME"
        echo "  ✓ 找到deb包: $DEB_FOUND"
        break
    fi
    # 也查找通配符匹配
    DEB_FILE=$(find "$path" -maxdepth 1 -name "deepstream-${DS_VERSION}*.deb" 2>/dev/null | head -1)
    if [ -n "$DEB_FILE" ]; then
        DEB_FOUND="$DEB_FILE"
        echo "  ✓ 找到deb包: $DEB_FOUND"
        break
    fi
done

if [ -z "$DEB_FOUND" ]; then
    echo "  ✗ 未找到deb包"
    echo ""
    echo "请先下载deb包："
    echo "  1. 浏览器打开: https://developer.nvidia.com/deepstream-getting-started"
    echo "  2. 下载 DeepStream $DS_VERSION for Jetson"
    echo "  3. 保存到 /tmp/ 或 ~/Downloads/"
    echo "  4. 重新运行此脚本"
    echo ""
    exit 1
fi

echo ""
read -p "是否安装找到的deb包? (y/n): " install_confirm

if [ "$install_confirm" != "y" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "步骤1: 安装依赖"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get update
sudo apt-get install -y \
    libssl3 \
    libssl-dev \
    libgstreamer1.0-0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer-plugins-base1.0-dev \
    libgstrtspserver-1.0-0 \
    libjansson4 \
    libjson-glib-1.0-0

echo "  ✓ 依赖已安装"

echo ""
echo "步骤2: 安装DeepStream"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get install -y "$DEB_FOUND"

if [ $? -eq 0 ]; then
    echo "  ✓ DeepStream已安装"
else
    echo "  ✗ 安装失败"
    exit 1
fi

echo ""
echo "步骤3: 验证安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查DeepStream目录
if [ -d "/opt/nvidia/deepstream/deepstream" ]; then
    echo "  ✓ DeepStream目录存在"
    DS_DIR="/opt/nvidia/deepstream/deepstream"
    
    # 检查版本
    if [ -f "$DS_DIR/version" ]; then
        echo "  ✓ 版本: $(cat $DS_DIR/version)"
    fi
    
    # 检查示例应用
    if [ -f "$DS_DIR/bin/deepstream-app" ]; then
        echo "  ✓ deepstream-app可用"
    fi
else
    echo "  ✗ DeepStream目录不存在"
    exit 1
fi

echo ""
echo "步骤4: 安装Python绑定"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PYDS_PATH="$DS_DIR/sources/deepstream_python_apps"

if [ -d "$PYDS_PATH" ]; then
    cd "$PYDS_PATH"
    
    # 安装依赖
    sudo apt-get install -y python3-gi python3-dev python3-gst-1.0 \
        python-gi-dev git meson \
        python3 python3-pip python3-setuptools python3-wheel \
        libgstrtspserver-1.0-0 libgirepository1.0-dev \
        gobject-introspection gir1.2-gst-rtsp-server-1.0
    
    # 编译安装pyds
    if [ -d "bindings" ]; then
        cd bindings
        
        echo "  编译Python绑定..."
        rm -rf build dist *.egg-info
        
        python3 setup.py build
        sudo python3 setup.py install
        
        if [ $? -eq 0 ]; then
            echo "  ✓ Python绑定已安装"
        else
            echo "  ⚠ Python绑定安装失败（可以稍后手动安装）"
        fi
    fi
else
    echo "  ⚠ Python绑定源码目录不存在"
fi

echo ""
echo "步骤5: 测试安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 测试pyds导入
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('✓ GStreamer OK')" 2>/dev/null || echo "  ⚠ GStreamer测试失败"

python3 -c "import pyds; print('✓ pyds OK')" 2>/dev/null || echo "  ⚠ pyds未安装（需要手动编译）"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✅ DeepStream安装完成                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "DeepStream位置: $DS_DIR"
echo ""
echo "下一步："
echo "  bash /home/liubo/Download/deepstream-vehicle-detection/scripts/prepare_tensorrt.sh"
echo ""


