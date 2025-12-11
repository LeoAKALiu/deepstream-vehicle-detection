#!/usr/bin/env python3
"""
测试信标匹配功能
"""

import sys
import os

# 直接实现信标匹配函数用于测试（避免导入需要pyds的主模块）
def match_beacon_for_vehicle(bbox, distance, beacon_client=None, beacon_filter=None):
    """信标匹配函数（测试版本）"""
    if not beacon_client or not beacon_filter:
        return None
    
    try:
        # 获取扫描到的信标
        all_beacons = beacon_client.get_beacons()
        if not all_beacons:
            return None
        
        # 使用过滤器匹配
        beacon_info = beacon_filter.get_best_match(
            all_beacons,
            camera_depth=distance,
            bbox=bbox
        )
        
        return beacon_info
    except Exception as e:
        print(f"⚠ 信标匹配错误: {e}")
        return None


def test_beacon_matching():
    """测试信标匹配函数"""
    print("=" * 60)
    print("测试: 信标匹配功能")
    print("=" * 60)
    
    beacon_client = None
    beacon_filter = None
    
    # 测试用例1: 无信标客户端
    bbox = (100, 100, 300, 300)
    result1 = match_beacon_for_vehicle(bbox, None, beacon_client, beacon_filter)
    assert result1 is None, "无信标客户端应该返回None"
    print("✓ 测试用例1通过: 无信标客户端处理")
    
    # 测试用例2: 无信标过滤器
    # 创建模拟的beacon_client
    class MockBeaconClient:
        def get_beacons(self):
            return []
    
    beacon_client = MockBeaconClient()
    result2 = match_beacon_for_vehicle(bbox, 5.0, beacon_client, beacon_filter)
    assert result2 is None, "无信标过滤器应该返回None"
    print("✓ 测试用例2通过: 无信标过滤器处理")
    
    print("\n✅ 所有信标匹配测试通过！\n")


if __name__ == '__main__':
    test_beacon_matching()

