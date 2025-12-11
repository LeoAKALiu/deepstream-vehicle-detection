#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "              DeepStream环境诊断"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

sudo docker run -it --rm --runtime nvidia --network host \
    -v /home/liubo/Download:/workspace \
    -w /workspace/deepstream-vehicle-detection \
    nvcr.io/nvidia/deepstream:7.0-triton-multiarch \
    bash -c "
        echo '【1. DeepStream版本】'
        if [ -f /opt/nvidia/deepstream/deepstream/version ]; then
            cat /opt/nvidia/deepstream/deepstream/version
        else
            echo '  未找到版本文件'
        fi
        echo ''
        
        echo '【2. DeepStream目录结构】'
        ls -la /opt/nvidia/deepstream/ 2>/dev/null || echo '  目录不存在'
        echo ''
        
        echo '【3. 查找pyds文件】'
        echo '  搜索.so文件...'
        find /opt/nvidia/deepstream /usr/lib /usr/local/lib -name '*pyds*.so' 2>/dev/null | head -10
        echo ''
        echo '  搜索.py文件...'
        find /opt/nvidia/deepstream /usr/lib /usr/local/lib -name '*pyds*.py' 2>/dev/null | head -10
        echo ''
        
        echo '【4. Python环境】'
        python3 --version
        echo '  Python路径:'
        python3 -c 'import sys; print(\"\\n\".join(sys.path))'
        echo ''
        
        echo '【5. 可用的Python包】'
        python3 -c 'import gi; print(\"✓ gi (GObject Introspection)\")'
        python3 -c 'import gi; gi.require_version(\"Gst\", \"1.0\"); from gi.repository import Gst; print(\"✓ GStreamer\", Gst.version_string())'
        echo ''
        
        echo '【6. DeepStream GStreamer插件】'
        gst-inspect-1.0 nvstreammux 2>&1 | head -5
        echo ''
        gst-inspect-1.0 nvinfer 2>&1 | head -5
        echo ''
        gst-inspect-1.0 nvtracker 2>&1 | head -5
        echo ''
        
        echo '【7. DeepStream示例应用】'
        ls -la /opt/nvidia/deepstream/deepstream*/sources/ 2>/dev/null | grep -i python || echo '  未找到Python示例'
        echo ''
        
        echo '【8. 尝试不同方式导入pyds】'
        
        echo '  方式1: 直接导入'
        python3 -c 'import pyds' 2>&1 | head -3
        echo ''
        
        echo '  方式2: 设置PYTHONPATH后导入'
        PYTHONPATH=/opt/nvidia/deepstream/deepstream/lib:\$PYTHONPATH python3 -c 'import pyds' 2>&1 | head -3
        echo ''
        
        echo '  方式3: 查找并添加到路径'
        PYDS_PATH=\$(find /opt/nvidia/deepstream -name 'pyds*.so' 2>/dev/null | head -1 | xargs dirname)
        if [ -n \"\$PYDS_PATH\" ]; then
            echo \"  找到pyds路径: \$PYDS_PATH\"
            PYTHONPATH=\$PYDS_PATH:\$PYTHONPATH python3 -c 'import pyds; print(\"✓ 成功！\")' 2>&1
        else
            echo '  未找到pyds.so'
        fi
        echo ''
        
        echo '【9. 测试基础GStreamer pipeline】'
        echo '  测试最简pipeline...'
        timeout 5 gst-launch-1.0 videotestsrc num-buffers=10 ! fakesink 2>&1 | grep -i 'setting pipeline' || echo '  Pipeline测试完成'
        echo ''
        
        echo '═══════════════════════════════════════════════════════════════════'
        echo '  诊断完成'
        echo '═══════════════════════════════════════════════════════════════════'
    "

