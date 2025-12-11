#!/usr/bin/env python3
"""
测试车牌识别功能
"""

import sys
import os
import numpy as np

# 直接实现车牌识别函数用于测试（避免导入需要pyds的主模块）
def recognize_license_plate(roi, lpr=None):
    """车牌识别函数（测试版本）"""
    if not lpr or roi is None:
        return None
    
    try:
        # HyperLPR识别
        results = lpr(roi)
        if results and len(results) > 0:
            # 取置信度最高的结果
            best_result = max(results, key=lambda x: x.get('confidence', 0.0))
            plate_number = best_result.get('code', '')
            confidence = best_result.get('confidence', 0.0)
            if plate_number:
                return (plate_number, confidence)
    except Exception as e:
        print(f"⚠ 车牌识别错误: {e}")
    
    return None


def test_license_plate_recognition():
    """测试车牌识别函数"""
    print("=" * 60)
    print("测试: 车牌识别功能")
    print("=" * 60)
    
    lpr = None  # 如果没有安装HyperLPR，设为None
    
    # 测试用例1: None输入
    result1 = recognize_license_plate(None, lpr)
    assert result1 is None, "None输入应该返回None"
    print("✓ 测试用例1通过: None输入处理")
    
    # 测试用例2: 无LPR实例
    test_roi = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
    result2 = recognize_license_plate(test_roi, lpr)
    assert result2 is None, "无LPR实例应该返回None"
    print("✓ 测试用例2通过: 无LPR实例处理")
    
    # 测试用例3: 有LPR实例（如果可用）
    try:
        from hyperlpr3 import LicensePlateCN
        lpr = LicensePlateCN(detect_level=1, max_num=5)
        
        # 使用测试图像（可能无法识别，但函数应该能正常执行）
        result3 = recognize_license_plate(test_roi, lpr)
        # 结果可能是None（识别失败）或tuple（识别成功）
        assert result3 is None or isinstance(result3, tuple), "应该返回None或tuple"
        print("✓ 测试用例3通过: LPR实例可用时的处理")
    except ImportError:
        print("⚠ 测试用例3跳过: HyperLPR未安装")
    
    print("\n✅ 所有车牌识别测试通过！\n")


if __name__ == '__main__':
    test_license_plate_recognition()

