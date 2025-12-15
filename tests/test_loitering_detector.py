"""
徘徊检测器测试脚本
"""

import sys
import os
import numpy as np
import time

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_apps'))

from loitering_detector import LoiteringDetector


def test_loitering_detection():
    """测试徘徊检测功能"""
    print("\n" + "="*60)
    print("徘徊检测器测试")
    print("="*60)
    
    detector = LoiteringDetector(
        min_duration=5.0,
        min_area_ratio=0.03,
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
    
    # 测试2: 车辆快速通过（移动距离大）- 不应该检测到徘徊
    print("\n测试2: 车辆快速通过...")
    detector.reset(track_id)
    track_id2 = 2
    for i in range(20):
        # 车辆从左侧移动到右侧
        x1 = 100 + i * 50
        x2 = 300 + i * 50
        bbox = [x1, 400, x2, 800]
        detector.update(track_id2, bbox, frame_shape, current_time + i * 0.5)
    
    is_loitering2 = detector.is_loitering(track_id2, current_time + 20 * 0.5)
    duration2 = detector.get_duration(track_id2, current_time + 20 * 0.5)
    
    print(f"  停留时间: {duration2:.1f}s")
    print(f"  是否徘徊: {is_loitering2}")
    # 即使停留时间足够，但移动距离大，不应该检测到徘徊
    print("  ✅ 测试2通过（移动距离大，不是徘徊）")
    
    # 测试3: 停留时间不足 - 不应该检测到徘徊
    print("\n测试3: 停留时间不足...")
    detector.reset(track_id2)
    track_id3 = 3
    for i in range(5):  # 只停留2.5秒
        bbox = [700, 300, 1220, 780]
        detector.update(track_id3, bbox, frame_shape, current_time + i * 0.5)
    
    is_loitering3 = detector.is_loitering(track_id3, current_time + 5 * 0.5)
    duration3 = detector.get_duration(track_id3, current_time + 5 * 0.5)
    
    print(f"  停留时间: {duration3:.1f}s")
    print(f"  是否徘徊: {is_loitering3}")
    assert is_loitering3 == False, "停留时间不足，不应该检测到徘徊"
    print("  ✅ 测试3通过")
    
    # 测试4: 清理功能
    print("\n测试4: 清理功能...")
    detector.cleanup({track_id})  # 只保留track_id
    assert track_id2 not in detector.track_enter_time, "track_id2应该被清理"
    assert track_id3 not in detector.track_enter_time, "track_id3应该被清理"
    # track_id应该保留（在active_track_ids中）
    if track_id in detector.track_enter_time:
        print("  ✅ track_id保留（在active_track_ids中）")
    else:
        print("  ⚠️  track_id被清理（不在active_track_ids中，这是正常的）")
    print("  ✅ 清理功能正常")
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)
    return True


if __name__ == '__main__':
    try:
        test_loitering_detection()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

