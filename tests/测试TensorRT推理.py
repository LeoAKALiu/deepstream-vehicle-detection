#!/usr/bin/env python3
"""
快速测试TensorRT引擎是否正常工作
"""

import time
import numpy as np

try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    print("✓ TensorRT和PyCUDA可用")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    exit(1)

# 加载引擎
engine_path = "models/yolov11_host.engine"
print(f"\n加载引擎: {engine_path}")

logger = trt.Logger(trt.Logger.WARNING)

with open(engine_path, 'rb') as f:
    engine_data = f.read()

runtime = trt.Runtime(logger)
engine = runtime.deserialize_cuda_engine(engine_data)

if engine is None:
    print("✗ 引擎加载失败")
    exit(1)

print("✓ 引擎加载成功")

# 获取输入输出信息
input_name = engine.get_tensor_name(0)
output_name = engine.get_tensor_name(1)
input_shape = engine.get_tensor_shape(input_name)
output_shape = engine.get_tensor_shape(output_name)

print(f"  输入: {input_name} {list(input_shape)}")
print(f"  输出: {output_name} {list(output_shape)}")

# 创建执行上下文
context = engine.create_execution_context()
print("✓ 执行上下文创建成功")

# 分配GPU内存
input_size = trt.volume(input_shape) * 4  # float32
output_size = trt.volume(output_shape) * 4

d_input = cuda.mem_alloc(input_size)
d_output = cuda.mem_alloc(output_size)
stream = cuda.Stream()

print(f"✓ GPU内存分配完成")
print(f"  输入: {input_size / 1024 / 1024:.1f} MB")
print(f"  输出: {output_size / 1024 / 1024:.1f} MB")

# 准备测试数据
print("\n准备测试数据...")
input_data = np.random.randn(*input_shape).astype(np.float32)
print(f"✓ 测试数据: {input_data.shape}")

# 执行推理
print("\n执行推理...")
cuda.memcpy_htod_async(d_input, input_data, stream)

context.set_tensor_address(input_name, int(d_input))
context.set_tensor_address(output_name, int(d_output))

start = time.time()
context.execute_async_v3(stream_handle=stream.handle)
stream.synchronize()
elapsed = time.time() - start

output_data = np.empty(output_shape, dtype=np.float32)
cuda.memcpy_dtoh_async(output_data, d_output, stream)
stream.synchronize()

print(f"✓ 推理成功！")
print(f"  耗时: {elapsed*1000:.2f} ms")
print(f"  输出形状: {output_data.shape}")
print(f"  输出范围: [{output_data.min():.3f}, {output_data.max():.3f}]")

# 多次测试性能
print("\n性能测试（10次）...")
times = []
for i in range(10):
    cuda.memcpy_htod_async(d_input, input_data, stream)
    context.set_tensor_address(input_name, int(d_input))
    context.set_tensor_address(output_name, int(d_output))
    
    start = time.time()
    context.execute_async_v3(stream_handle=stream.handle)
    stream.synchronize()
    elapsed = time.time() - start
    times.append(elapsed)

avg_time = np.mean(times) * 1000
fps = 1.0 / np.mean(times)

print(f"✓ 平均推理时间: {avg_time:.2f} ms")
print(f"✓ 预期FPS: {fps:.1f}")

print("\n" + "="*60)
print("🎉 TensorRT引擎工作正常！")
print("="*60)

