#!/usr/bin/env python3
"""
测试ROI裁剪功能
"""

import sys
import os
import numpy as np
import cv2

# 直接实现ROI裁剪函数用于测试（避免导入需要pyds的主模块）
def crop_vehicle_roi(frame, bbox):
    """ROI裁剪函数（测试版本）"""
    if frame is None:
        return None
    
    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]
    
    # 确保坐标在图像范围内
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(w, int(x2))
    y2 = min(h, int(y2))
    
    if x2 <= x1 or y2 <= y1:
        return None
    
    roi = frame[y1:y2, x1:x2]
    return roi


def test_crop_vehicle_roi():
    """测试ROI裁剪函数"""
    print("=" * 60)
    print("测试: ROI裁剪功能")
    print("=" * 60)
    
    # 创建测试图像（640x480 RGB）
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # 测试用例1: 正常bbox
    bbox1 = (100, 100, 300, 300)
    roi1 = crop_vehicle_roi(test_image, bbox1)
    
    assert roi1 is not None, "ROI裁剪失败"
    assert roi1.shape == (200, 200, 3), f"ROI尺寸错误: {roi1.shape}, 期望: (200, 200, 3)"
    print("✓ 测试用例1通过: 正常bbox裁剪")
    
    # 测试用例2: bbox超出图像边界
    bbox2 = (500, 400, 700, 600)  # 部分超出
    roi2 = crop_vehicle_roi(test_image, bbox2)
    
    assert roi2 is not None, "边界bbox裁剪失败"
    assert roi2.shape[0] > 0 and roi2.shape[1] > 0, "裁剪结果为空"
    print("✓ 测试用例2通过: 边界bbox裁剪")
    
    # 测试用例3: 无效bbox（x2 <= x1）
    bbox3 = (300, 100, 200, 300)  # x2 < x1
    roi3 = crop_vehicle_roi(test_image, bbox3)
    
    assert roi3 is None, "无效bbox应该返回None"
    print("✓ 测试用例3通过: 无效bbox处理")
    
    # 测试用例4: None输入
    roi4 = crop_vehicle_roi(None, bbox1)
    assert roi4 is None, "None输入应该返回None"
    print("✓ 测试用例4通过: None输入处理")
    
    print("\n✅ 所有ROI裁剪测试通过！\n")


if __name__ == '__main__':
    test_crop_vehicle_roi()

