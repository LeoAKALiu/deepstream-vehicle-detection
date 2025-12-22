"""
Phase 2 徘徊检测集成测试
"""

import sys
import os
import numpy as np
import time

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_apps'))

from loitering_detector import LoiteringDetector
from config_loader import get_config


def test_config_integration():
    """测试配置集成"""
    print("\n" + "="*60)
    print("配置集成测试")
    print("="*60)
    
    config = get_config()
    alert_cfg = config.get('alert', {}).get('loitering', {})
    
    assert alert_cfg.get('enabled', True) == True, "徘徊检测应该启用"
    assert alert_cfg.get('min_duration', 10.0) == 10.0, "最少停留时间应为10.0秒"
    assert alert_cfg.get('min_area_ratio', 0.05) == 0.05, "最小画面占比应为0.05"
    assert alert_cfg.get('min_movement_ratio', 0.1) == 0.1, "最小移动比例应为0.1"
    assert alert_cfg.get('apply_to_unregistered_only', True) == True, "应该只对未备案车辆应用"
    
    # 从配置创建检测器
    detector = LoiteringDetector(
        min_duration=alert_cfg.get('min_duration', 10.0),
        min_area_ratio=alert_cfg.get('min_area_ratio', 0.05),
        min_movement_ratio=alert_cfg.get('min_movement_ratio', 0.1)
    )
    
    assert detector.min_duration == 10.0, "检测器参数应该正确"
    assert detector.min_area_ratio == 0.05, "检测器参数应该正确"
    assert detector.min_movement_ratio == 0.1, "检测器参数应该正确"
    
    print("✅ 配置集成测试通过")
    return True


def test_loitering_logic():
    """测试徘徊判定逻辑"""
    print("\n" + "="*60)
    print("徘徊判定逻辑测试")
    print("="*60)
    
    detector = LoiteringDetector(
        min_duration=5.0,  # 使用较短的测试时间
        min_area_ratio=0.03,  # 降低阈值便于测试
        min_movement_ratio=0.1
    )
    
    track_id = 1
    frame_shape = (1080, 1920, 3)
    current_time = time.time()
    
    # 测试1: 车辆停留（几乎不动）- 应该检测到徘徊
    print("\n测试1: 车辆停留（几乎不动）...")
    for i in range(20):
        bbox = [700, 300, 1220, 780]  # 较大的固定位置
        detector.update(track_id, bbox, frame_shape, current_time + i * 0.5)
    
    is_loitering = detector.is_loitering(track_id, current_time + 20 * 0.5)
    duration = detector.get_duration(track_id, current_time + 20 * 0.5)
    
    print(f"  停留时间: {duration:.1f}s")
    print(f"  是否徘徊: {is_loitering}")
    assert is_loitering == True, "应该检测到徘徊"
    print("  ✅ 测试1通过")
    
    # 测试2: 停留时间不足
    print("\n测试2: 停留时间不足...")
    detector.reset(track_id)
    track_id2 = 2
    for i in range(5):  # 只停留2.5秒
        bbox = [700, 300, 1220, 780]
        detector.update(track_id2, bbox, frame_shape, current_time + i * 0.5)
    
    is_loitering2 = detector.is_loitering(track_id2, current_time + 5 * 0.5)
    duration2 = detector.get_duration(track_id2, current_time + 5 * 0.5)
    
    print(f"  停留时间: {duration2:.1f}s")
    print(f"  是否徘徊: {is_loitering2}")
    assert is_loitering2 == False, "停留时间不足，不应该检测到徘徊"
    print("  ✅ 测试2通过")
    
    # 测试3: 画面占比太小
    print("\n测试3: 画面占比太小...")
    detector.reset(track_id2)
    track_id3 = 3
    for i in range(20):
        bbox = [10, 10, 50, 50]  # 很小的bbox，画面占比很小
        detector.update(track_id3, bbox, frame_shape, current_time + i * 0.5)
    
    is_loitering3 = detector.is_loitering(track_id3, current_time + 20 * 0.5)
    duration3 = detector.get_duration(track_id3, current_time + 20 * 0.5)
    
    print(f"  停留时间: {duration3:.1f}s")
    print(f"  是否徘徊: {is_loitering3}")
    assert is_loitering3 == False, "画面占比太小，不应该检测到徘徊"
    print("  ✅ 测试3通过")
    
    print("\n✅ 徘徊判定逻辑测试全部通过")
    return True


def test_cleanup_functionality():
    """测试清理功能"""
    print("\n" + "="*60)
    print("清理功能测试")
    print("="*60)
    
    detector = LoiteringDetector()
    frame_shape = (1080, 1920, 3)
    current_time = time.time()
    
    # 创建多个track
    for track_id in [1, 2, 3]:
        for i in range(10):
            bbox = [700, 300, 1220, 780]
            detector.update(track_id, bbox, frame_shape, current_time + i * 0.5)
    
    # 检查所有track都存在
    assert 1 in detector.track_enter_time, "track 1应该存在"
    assert 2 in detector.track_enter_time, "track 2应该存在"
    assert 3 in detector.track_enter_time, "track 3应该存在"
    
    # 清理track 2和3
    detector.cleanup({1})  # 只保留track 1
    
    assert 1 in detector.track_enter_time, "track 1应该保留"
    assert 2 not in detector.track_enter_time, "track 2应该被清理"
    assert 3 not in detector.track_enter_time, "track 3应该被清理"
    
    print("✅ 清理功能测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Phase 2 徘徊检测模块集成测试")
    print("="*70)
    
    try:
        # 测试1: 配置集成
        test_config_integration()
        
        # 测试2: 徘徊判定逻辑
        test_loitering_logic()
        
        # 测试3: 清理功能
        test_cleanup_functionality()
        
        print("\n" + "="*70)
        print("✅ 所有测试通过！")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)








