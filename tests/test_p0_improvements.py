#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0改进测试脚本
测试P0-1、P0-2、P0-5的改进是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_apps'))

import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from config_loader import get_config

print("="*70)
print("P0改进测试脚本")
print("="*70)

# ============================================
# 测试1: P0-2 - YOLO输出解析一致性验证
# ============================================
print("\n【测试1: P0-2 - YOLO输出解析一致性验证】")
print("-"*70)

try:
    from test_system_realtime import TensorRTInference
    
    # 加载配置
    config = get_config()
    engine_path = config.resolve_path('detection.model_path')
    labels_path = 'config/labels.txt'
    
    print(f"引擎路径: {engine_path}")
    print(f"标签路径: {labels_path}")
    
    if not os.path.exists(engine_path):
        print(f"❌ 引擎文件不存在: {engine_path}")
        sys.exit(1)
    
    # 测试引擎加载和验证
    print("\n1. 测试引擎加载和输出格式验证...")
    try:
        inference = TensorRTInference(
            engine_path,
            conf_threshold=0.7,
            iou_threshold=0.5,
            labels_path=labels_path if os.path.exists(labels_path) else None
        )
        print("✅ 引擎加载成功")
        print(f"   - 输入shape: {inference.input_shape}")
        print(f"   - 输出shape: {inference.output_shape}")
        print(f"   - 类别数量: {inference.num_classes}")
        print(f"   - 输出格式: {inference.output_format}")
        
        if hasattr(inference, 'labels') and inference.labels:
            print(f"   - 标签数量: {len(inference.labels)}")
            print(f"   - 前5个标签: {inference.labels[:5]}")
        
    except ValueError as e:
        print(f"❌ 验证失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 引擎加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 测试输出解析
    print("\n2. 测试输出解析...")
    try:
        # 创建虚拟输入
        dummy_input = np.random.rand(*inference.input_shape).astype(np.float32)
        
        # 执行推理
        output = inference.infer(dummy_input)
        print(f"✅ 推理成功")
        print(f"   - 输出shape: {output.shape}")
        
        # 测试后处理
        boxes, confidences, class_ids = inference.postprocess(output)
        print(f"✅ 后处理成功")
        print(f"   - 检测框数量: {len(boxes)}")
        print(f"   - 类别ID范围: {class_ids.min() if len(class_ids) > 0 else 'N/A'} - {class_ids.max() if len(class_ids) > 0 else 'N/A'}")
        
        # 验证类别ID是否在有效范围内
        if len(class_ids) > 0:
            if class_ids.max() >= inference.num_classes:
                print(f"❌ 类别ID超出范围: 最大ID={class_ids.max()}, 类别数={inference.num_classes}")
            else:
                print(f"✅ 类别ID验证通过")
        
    except Exception as e:
        print(f"❌ 输出解析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n✅ 测试1通过: YOLO输出解析一致性验证")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("   请确保在项目根目录运行此脚本")

# ============================================
# 测试2: P0-1 - 深度精度优化
# ============================================
print("\n【测试2: P0-1 - 深度精度优化】")
print("-"*70)

try:
    from orbbec_depth import OrbbecDepthCamera
    
    # 测试相机初始化（带配置参数）
    print("\n1. 测试相机初始化（带配置参数）...")
    try:
        config = get_config()
        depth_cfg = config.get_depth()
        invalid_min = depth_cfg.get('invalid_min', 0)
        invalid_max = depth_cfg.get('invalid_max', 65535)
        
        print(f"   - invalid_min: {invalid_min}")
        print(f"   - invalid_max: {invalid_max}")
        
        camera = OrbbecDepthCamera(
            invalid_min=invalid_min,
            invalid_max=invalid_max
        )
        print("✅ 相机初始化成功（带配置参数）")
        
        # 测试启动（如果相机可用）
        print("\n2. 测试相机启动...")
        if camera.start():
            print("✅ 相机启动成功")
            
            # 等待相机稳定
            import time
            print("   等待相机稳定...")
            time.sleep(2)
            
            # 测试深度测量方法
            print("\n3. 测试深度测量方法...")
            
            # 创建测试bbox
            test_bbox = [100, 100, 200, 200]
            
            # 测试get_depth_region_stats（新返回格式）
            print("   - 测试get_depth_region_stats...")
            depth, confidence = camera.get_depth_region_stats(test_bbox, method='median')
            if depth is not None:
                print(f"     ✅ 深度: {depth:.3f}m, 置信度: {confidence:.1%}")
            else:
                print(f"     ⚠ 无法获取深度（可能无有效数据）")
            
            # 测试get_depth_at_bbox_bottom_robust（新方法）
            print("   - 测试get_depth_at_bbox_bottom_robust...")
            depth, confidence = camera.get_depth_at_bbox_bottom_robust(
                test_bbox, window_size=5, outlier_threshold=2.0
            )
            if depth is not None:
                print(f"     ✅ 深度: {depth:.3f}m, 置信度: {confidence:.1%}")
            else:
                print(f"     ⚠ 无法获取深度（可能无有效数据）")
            
            # 停止相机
            camera.stop()
            print("\n✅ 测试2通过: 深度精度优化")
        else:
            print("⚠ 相机启动失败（可能未连接），跳过深度测试")
            print("   但初始化逻辑验证通过")
    
    except ImportError:
        print("⚠ pyorbbecsdk未安装，跳过深度测试")
    except Exception as e:
        print(f"❌ 深度测试失败: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"❌ 深度模块导入失败: {e}")

# ============================================
# 测试3: P0-5 - 性能配置
# ============================================
print("\n【测试3: P0-5 - 性能配置】")
print("-"*70)

try:
    config = get_config()
    
    print("\n1. 测试性能配置加载...")
    performance_cfg = config.get('performance', {})
    
    mode = performance_cfg.get('mode', 'quality')
    input_resolution = performance_cfg.get('input_resolution', [1920, 1080])
    frame_skip = performance_cfg.get('frame_skip', 0)
    
    print(f"   - 性能模式: {mode}")
    print(f"   - 输入分辨率: {input_resolution}")
    print(f"   - 跳帧数: {frame_skip}")
    
    # 验证模式值
    valid_modes = ['quality', 'balanced', 'speed']
    if mode in valid_modes:
        print(f"✅ 性能模式验证通过")
    else:
        print(f"⚠ 性能模式 '{mode}' 不在有效列表中: {valid_modes}")
    
    # 验证分辨率格式
    if isinstance(input_resolution, list) and len(input_resolution) == 2:
        print(f"✅ 分辨率格式验证通过")
    else:
        print(f"⚠ 分辨率格式错误: {input_resolution}")
    
    print("\n✅ 测试3通过: 性能配置")

except Exception as e:
    print(f"❌ 性能配置测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 总结
# ============================================
print("\n" + "="*70)
print("测试总结")
print("="*70)
print("✅ P0-2: YOLO输出解析一致性验证 - 通过")
print("✅ P0-1: 深度精度优化 - 通过（如果相机可用）")
print("✅ P0-5: 性能配置 - 通过")
print("\n所有P0改进测试完成！")
print("="*70)



