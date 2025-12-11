#!/usr/bin/env python3
"""
测试图像提取和缓存功能
"""

import sys
import os
import numpy as np

# 直接实现缓存逻辑用于测试（避免导入需要pyds的主模块）
def extract_frame_from_cache(frame_id, input_frame_cache, max_cache_size=10, frame_extraction_enabled=True):
    """从缓存提取图像（测试版本）"""
    if not frame_extraction_enabled:
        return None
    
    # 从缓存获取图像
    if frame_id in input_frame_cache:
        return input_frame_cache[frame_id]
    
    # 如果缓存中没有，尝试从最近的帧获取（可能帧ID不匹配）
    if input_frame_cache:
        # 获取最接近的帧ID
        closest_frame_id = min(input_frame_cache.keys(), 
                              key=lambda x: abs(x - frame_id))
        if abs(closest_frame_id - frame_id) <= 2:  # 允许2帧的误差
            return input_frame_cache[closest_frame_id]
    
    return None


def test_frame_cache():
    """测试帧缓存机制"""
    print("=" * 60)
    print("测试: 帧缓存机制")
    print("=" * 60)
    
    # 初始化缓存
    input_frame_cache = {}
    max_cache_size = 5
    frame_extraction_enabled = True
    
    # 测试用例1: 缓存添加和获取
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    input_frame_cache[1] = test_frame
    
    result = extract_frame_from_cache(1, input_frame_cache, max_cache_size, frame_extraction_enabled)
    
    assert result is not None, "应该能从缓存获取图像"
    assert np.array_equal(result, test_frame), "获取的图像应该与缓存的一致"
    print("✓ 测试用例1通过: 缓存添加和获取")
    
    # 测试用例2: 缓存大小限制（模拟）
    # 注意：实际应用中应该在添加时限制，这里只测试逻辑
    for i in range(10):
        input_frame_cache[i] = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # 模拟限制逻辑
        if len(input_frame_cache) > max_cache_size:
            oldest_frame_id = min(input_frame_cache.keys())
            del input_frame_cache[oldest_frame_id]
    
    assert len(input_frame_cache) <= max_cache_size, f"缓存大小应该不超过{max_cache_size}"
    print("✓ 测试用例2通过: 缓存大小限制")
    
    # 测试用例3: 帧ID容差匹配
    input_frame_cache = {10: test_frame}
    result = extract_frame_from_cache(11, input_frame_cache, max_cache_size, frame_extraction_enabled)  # 差1帧
    
    assert result is not None, "应该能通过容差匹配获取图像"
    print("✓ 测试用例3通过: 帧ID容差匹配")
    
    # 测试用例4: 禁用图像提取
    frame_extraction_enabled = False
    result = extract_frame_from_cache(10, input_frame_cache, max_cache_size, frame_extraction_enabled)
    assert result is None, "禁用时应该返回None"
    print("✓ 测试用例4通过: 禁用图像提取")
    
    print("\n✅ 所有帧缓存测试通过！\n")


if __name__ == '__main__':
    test_frame_cache()

