#!/bin/bash
# 在DeepStream容器中查找并配置pyds

echo "查找pyds位置..."

# 可能的pyds位置
PYDS_PATHS=(
    "/opt/nvidia/deepstream/deepstream/lib"
    "/opt/nvidia/deepstream/deepstream-7.0/lib"
    "/opt/nvidia/deepstream/deepstream/lib/pyds"
    "/usr/lib/python3/dist-packages"
    "/usr/local/lib/python3.10/dist-packages"
)

FOUND_PYDS=""

for path in "${PYDS_PATHS[@]}"; do
    if [ -d "$path" ]; then
        # 检查是否包含pyds
        if find "$path" -name "*pyds*" 2>/dev/null | grep -q .; then
            echo "  找到pyds相关文件: $path"
            FOUND_PYDS="$path"
            export PYTHONPATH="$path:$PYTHONPATH"
        fi
    fi
done

# 尝试直接查找pyds.so
echo ""
echo "搜索pyds.so文件..."
PYDS_SO=$(find /opt/nvidia/deepstream /usr -name "pyds*.so" 2>/dev/null | head -1)

if [ -n "$PYDS_SO" ]; then
    PYDS_DIR=$(dirname "$PYDS_SO")
    echo "  找到: $PYDS_SO"
    echo "  目录: $PYDS_DIR"
    export PYTHONPATH="$PYDS_DIR:$PYTHONPATH"
fi

# 显示PYTHONPATH
echo ""
echo "PYTHONPATH设置为:"
echo "$PYTHONPATH" | tr ':' '\n' | sed 's/^/  /'

# 测试导入
echo ""
echo "测试导入pyds..."
if python3 -c "import pyds; print('✓ pyds可用，版本:', pyds.__version__ if hasattr(pyds, '__version__') else 'unknown')" 2>/dev/null; then
    exit 0
else
    echo "✗ pyds仍然不可用"
    echo ""
    echo "尝试列出可用的Python绑定..."
    find /opt/nvidia/deepstream -name "*.so" -o -name "*.py" 2>/dev/null | grep -i "py" | head -10
    exit 1
fi

