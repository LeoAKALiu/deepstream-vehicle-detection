# 转换自定义YOLOv11模型指南

## 当前情况

- ✅ 已有训练好的模型：`/home/liubo/Download/best.pt`
- ✅ 包含工程车辆和社会车辆类别
- ⚠️ 需要转换为TensorRT引擎

---

## 转换流程

```
best.pt → best.onnx → custom_yolo.engine
```

---

## 方案A：在Jetson上转换（推荐尝试）

### 步骤1：修复PyTorch依赖

```bash
# 检查libcudnn
ls -la /usr/lib/aarch64-linux-gnu/libcudnn*

# 如果缺少libcudnn.so.8，创建软链接
sudo ln -sf /usr/lib/aarch64-linux-gnu/libcudnn.so.9 /usr/lib/aarch64-linux-gnu/libcudnn.so.8

# 或者更新LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
```

### 步骤2：导出ONNX

```bash
cd /home/liubo/Download

# 方法1：使用yolo命令
yolo export model=best.pt format=onnx simplify=True imgsz=640

# 方法2：使用Python脚本
python3 << 'EOF'
from ultralytics import YOLO

model = YOLO('best.pt')
model.export(format='onnx', simplify=True, imgsz=640)
print("✓ ONNX导出成功: best.onnx")
EOF
```

### 步骤3：转换TensorRT

```bash
cd /home/liubo/Download

# 使用trtexec转换
/usr/src/tensorrt/bin/trtexec \
    --onnx=best.onnx \
    --saveEngine=custom_yolo.engine \
    --fp16 \
    --workspace=4096

# 或者如果trtexec在PATH中
trtexec \
    --onnx=best.onnx \
    --saveEngine=custom_yolo.engine \
    --fp16 \
    --workspace=4096
```

### 步骤4：复制到项目

```bash
cp custom_yolo.engine /home/liubo/Download/deepstream-vehicle-detection/models/
```

---

## 方案B：在其他PC上转换（如果Jetson有问题）

### 在PC上操作（需要有GPU和CUDA）

**步骤1：导出ONNX**
```bash
# 在有PyTorch的PC上
cd /path/to/best.pt

# 安装ultralytics
pip install ultralytics

# 导出ONNX
yolo export model=best.pt format=onnx simplify=True imgsz=640

# 得到 best.onnx
```

**步骤2：传输到Jetson**
```bash
# 在PC上
scp best.onnx liubo@<jetson-ip>:/home/liubo/Download/

# 或使用U盘传输
```

**步骤3：在Jetson上转换TensorRT**
```bash
cd /home/liubo/Download

trtexec \
    --onnx=best.onnx \
    --saveEngine=custom_yolo.engine \
    --fp16 \
    --workspace=4096
```

---

## 方案C：快速修复脚本（Jetson）

创建修复脚本：

```bash
cat > /home/liubo/Download/export_onnx.sh << 'EOFSCRIPT'
#!/bin/bash

echo "修复libcudnn依赖..."
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

echo "导出ONNX模型..."
cd /home/liubo/Download

python3 << 'EOF'
import sys
sys.path.insert(0, '/home/liubo/.local/lib/python3.10/site-packages')

try:
    from ultralytics import YOLO
    print("✓ ultralytics导入成功")
    
    model = YOLO('best.pt')
    print("✓ 模型加载成功")
    
    # 导出ONNX
    model.export(format='onnx', simplify=True, imgsz=640)
    print("✓ ONNX导出成功: best.onnx")
    
except Exception as e:
    print(f"✗ 导出失败: {e}")
    import traceback
    traceback.print_exc()
EOF

echo "转换TensorRT引擎..."
if [ -f "best.onnx" ]; then
    trtexec \
        --onnx=best.onnx \
        --saveEngine=custom_yolo.engine \
        --fp16 \
        --workspace=4096 \
        --verbose
    
    if [ -f "custom_yolo.engine" ]; then
        echo "✓ TensorRT引擎生成成功"
        cp custom_yolo.engine /home/liubo/Download/deepstream-vehicle-detection/models/
        echo "✓ 已复制到项目目录"
    fi
fi

EOFSCRIPT

chmod +x /home/liubo/Download/export_onnx.sh
```

运行：
```bash
bash /home/liubo/Download/export_onnx.sh
```

---

## 更新系统使用新模型

### 方法1：直接指定引擎文件

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

python3 test_system_realtime.py --engine models/custom_yolo.engine
```

### 方法2：替换默认引擎

```bash
cd /home/liubo/Download/deepstream-vehicle-detection/models

# 备份原模型
mv yolov11_host.engine yolov11_host.engine.backup

# 使用新模型
ln -s custom_yolo.engine yolov11_host.engine
```

---

## 验证新模型

### 检查类别数

```bash
# 创建验证脚本
python3 << 'EOF'
import tensorrt as trt
import numpy as np

engine_path = 'models/custom_yolo.engine'

logger = trt.Logger(trt.Logger.WARNING)
with open(engine_path, 'rb') as f:
    runtime = trt.Runtime(logger)
    engine = runtime.deserialize_cuda_engine(f.read())

print(f"✓ 引擎加载成功")

# 获取输出shape
if hasattr(engine, 'get_binding_name'):
    for i in range(engine.num_bindings):
        name = engine.get_binding_name(i)
        shape = engine.get_binding_shape(i)
        print(f"  {name}: {shape}")
        if not engine.binding_is_input(i):
            num_classes = shape[1] - 4  # 减去4个bbox坐标
            print(f"  → 检测类别数: {num_classes}")
else:
    for i in range(engine.num_io_tensors):
        name = engine.get_tensor_name(i)
        shape = engine.get_tensor_shape(name)
        print(f"  {name}: {shape}")
        if engine.get_tensor_mode(name) != trt.TensorIOMode.INPUT:
            num_classes = shape[1] - 4
            print(f"  → 检测类别数: {num_classes}")
EOF
```

---

## 故障排除

### 问题1：libcudnn版本不匹配
```bash
# 解决方法1：创建软链接
sudo ln -sf /usr/lib/aarch64-linux-gnu/libcudnn.so.9 /lib/aarch64-linux-gnu/libcudnn.so.8

# 解决方法2：设置环境变量
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
```

### 问题2：trtexec未找到
```bash
# 查找trtexec
find /usr -name trtexec 2>/dev/null

# 添加到PATH
export PATH=/usr/src/tensorrt/bin:$PATH
```

### 问题3：ONNX导出失败
```bash
# 在其他PC上导出ONNX，然后传输到Jetson
# 只在Jetson上进行TensorRT转换
```

---

## 预期结果

转换成功后应该看到：

```
✓ best.onnx (30-50MB)
✓ custom_yolo.engine (15-30MB)
```

运行系统：
```bash
cd /home/liubo/Download/deepstream-vehicle-detection
python3 test_system_realtime.py --engine models/custom_yolo.engine
```

应该能够检测到：
- ✅ 工程车辆（挖掘机、推土机等）
- ✅ 社会车辆（小汽车）

---

## 下一步

1. 首先尝试方案C的快速脚本
2. 如果失败，尝试方案A的手动步骤
3. 如果还失败，使用方案B（在PC上导出ONNX）
4. 转换成功后，更新系统配置
5. 重新测试完整系统

---

**现在让我们开始转换！**





