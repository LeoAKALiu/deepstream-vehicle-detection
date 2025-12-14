#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 优化测试脚本
测试：
1. 硬编码阈值移除 - 验证配置读取
2. 信标匹配时空一致性 - 验证连续帧匹配锁定
3. 配置参数正确性
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'python_apps'))

import yaml
import time
from typing import Optional

# 导入配置加载器
try:
    from config_loader import get_config
except ImportError:
    # 如果在python_apps目录中
    sys.path.insert(0, project_root)
    from config_loader import get_config

# 导入信标匹配跟踪器
from python_apps.beacon_match_tracker import BeaconMatchTracker


def test_config_loading():
    """测试1: 验证配置读取是否正确"""
    print("="*70)
    print("测试1: 配置读取测试")
    print("="*70)
    
    try:
        config = get_config()
        
        # 测试tracking配置
        tracking_cfg = config.get_tracking()
        min_track_confidence = tracking_cfg.get('min_track_confidence', None)
        print(f"✓ tracking.min_track_confidence: {min_track_confidence}")
        assert min_track_confidence is not None, "min_track_confidence 应该存在于配置中"
        assert 0.0 <= min_track_confidence <= 1.0, "min_track_confidence 应该在 0.0-1.0 范围内"
        
        # 测试alert_dedup配置
        alert_dedup_cfg = config.get('alert_dedup', {})
        time_window = alert_dedup_cfg.get('time_window', None)
        iou_threshold = alert_dedup_cfg.get('iou_threshold', None)
        position_time_window = alert_dedup_cfg.get('position_time_window', None)
        
        print(f"✓ alert_dedup.time_window: {time_window}")
        print(f"✓ alert_dedup.iou_threshold: {iou_threshold}")
        print(f"✓ alert_dedup.position_time_window: {position_time_window}")
        
        assert time_window is not None, "time_window 应该存在于配置中"
        assert iou_threshold is not None, "iou_threshold 应该存在于配置中"
        assert position_time_window is not None, "position_time_window 应该存在于配置中"
        assert 0.0 <= iou_threshold <= 1.0, "iou_threshold 应该在 0.0-1.0 范围内"
        
        # 测试beacon_match配置
        beacon_match_cfg = config.get('beacon_match', {})
        temporal_consistency = beacon_match_cfg.get('temporal_consistency', {})
        enabled = temporal_consistency.get('enabled', None)
        min_consistent_frames = temporal_consistency.get('min_consistent_frames', None)
        max_distance_error = temporal_consistency.get('max_distance_error', None)
        
        print(f"✓ beacon_match.temporal_consistency.enabled: {enabled}")
        print(f"✓ beacon_match.temporal_consistency.min_consistent_frames: {min_consistent_frames}")
        print(f"✓ beacon_match.temporal_consistency.max_distance_error: {max_distance_error}")
        
        assert enabled is not None, "temporal_consistency.enabled 应该存在于配置中"
        assert min_consistent_frames is not None, "min_consistent_frames 应该存在于配置中"
        assert max_distance_error is not None, "max_distance_error 应该存在于配置中"
        
        print("\n✅ 测试1通过：所有配置项都正确加载\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_beacon_match_tracker():
    """测试2: 验证信标匹配时空一致性跟踪器"""
    print("="*70)
    print("测试2: 信标匹配时空一致性跟踪器")
    print("="*70)
    
    try:
        # 创建跟踪器（使用配置默认值）
        tracker = BeaconMatchTracker(
            min_consistent_frames=5,
            max_distance_error=1.0,
            reset_on_track_end=True
        )
        
        track_id = 1
        beacon_mac = "AA:BB:CC:DD:EE:FF"
        distance = 5.0
        match_cost = 2.5
        
        # 测试：前4帧匹配，应该不锁定
        print(f"\n步骤1: 连续4帧匹配同一信标（应该不锁定）")
        for i in range(4):
            locked = tracker.update_match(track_id, beacon_mac, distance, match_cost)
            print(f"  帧{i+1}: locked={locked}")
            assert locked is None, f"前{tracker.min_consistent_frames-1}帧应该不锁定"
        
        # 测试：第5帧匹配，应该锁定
        print(f"\n步骤2: 第5帧匹配（应该锁定）")
        locked = tracker.update_match(track_id, beacon_mac, distance, match_cost)
        print(f"  帧5: locked={locked}")
        assert locked == beacon_mac, "第5帧应该锁定匹配"
        
        # 测试：锁定后继续匹配，应该返回锁定的信标
        print(f"\n步骤3: 锁定后继续匹配（应该返回锁定信标）")
        for i in range(3):
            locked = tracker.update_match(track_id, beacon_mac, distance + 0.1, match_cost)
            print(f"  后续帧{i+1}: locked={locked}")
            assert locked == beacon_mac, "锁定后应该继续返回锁定信标"
        
        # 测试：匹配不一致时，锁定仍然有效
        print(f"\n步骤4: 匹配不一致（锁定仍然有效）")
        different_beacon = "FF:EE:DD:CC:BB:AA"
        locked = tracker.update_match(track_id, different_beacon, distance, match_cost)
        print(f"  不同信标: locked={locked}")
        assert locked == beacon_mac, f"即使当前帧匹配不同信标，锁定仍然有效 (期望: {beacon_mac}, 实际: {locked})"
        
        # 测试：匹配失败（None）时，锁定仍然有效
        print(f"\n步骤4b: 匹配失败（None）时（锁定仍然有效）")
        locked = tracker.update_match(track_id, None, distance, match_cost)
        print(f"  匹配失败: locked={locked}")
        assert locked == beacon_mac, f"即使当前帧匹配失败，锁定仍然有效 (期望: {beacon_mac}, 实际: {locked})"
        
        # 测试：重置track
        print(f"\n步骤5: 重置track")
        tracker.reset(track_id)
        locked_after_reset = tracker.get_locked_beacon(track_id)
        print(f"  重置后: locked={locked_after_reset}")
        assert locked_after_reset is None, "重置后应该没有锁定信标"
        
        # 测试：距离误差过大时，不满足锁定条件
        print(f"\n步骤6: 距离误差过大（应该不满足锁定条件）")
        tracker2 = BeaconMatchTracker(
            min_consistent_frames=3,
            max_distance_error=1.0,
            reset_on_track_end=True
        )
        track_id2 = 2
        
        # 前2帧正常距离
        for i in range(2):
            tracker2.update_match(track_id2, beacon_mac, 5.0, match_cost)
        
        # 第3帧距离误差过大
        locked = tracker2.update_match(track_id2, beacon_mac, 7.0, match_cost)  # 距离差2.0 > 1.0
        print(f"  距离误差过大: locked={locked}")
        assert locked is None, "距离误差过大时应该不锁定"
        
        # 测试：cleanup功能
        print(f"\n步骤7: 清理已结束track")
        active_tracks = {3, 4, 5}  # track_id2不在活跃列表中
        tracker2.cleanup(active_tracks)
        locked_after_cleanup = tracker2.get_locked_beacon(track_id2)
        print(f"  清理后: locked={locked_after_cleanup}")
        assert locked_after_cleanup is None, "清理后应该没有锁定信标"
        
        print("\n✅ 测试2通过：信标匹配时空一致性跟踪器工作正常\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_config_default_values():
    """测试3: 验证默认值是否正确"""
    print("="*70)
    print("测试3: 默认值验证")
    print("="*70)
    
    try:
        config = get_config()
        
        tracking_cfg = config.get_tracking()
        min_track_confidence = tracking_cfg.get('min_track_confidence', 0.7)
        
        alert_dedup_cfg = config.get('alert_dedup', {})
        time_window = alert_dedup_cfg.get('time_window', 30.0)
        iou_threshold = alert_dedup_cfg.get('iou_threshold', 0.5)
        position_time_window = alert_dedup_cfg.get('position_time_window', 10.0)
        
        beacon_match_cfg = config.get('beacon_match', {})
        temporal_consistency = beacon_match_cfg.get('temporal_consistency', {})
        enabled = temporal_consistency.get('enabled', True)
        min_consistent_frames = temporal_consistency.get('min_consistent_frames', 5)
        max_distance_error = temporal_consistency.get('max_distance_error', 1.0)
        
        print(f"当前配置值:")
        print(f"  min_track_confidence: {min_track_confidence} (期望: 0.7)")
        print(f"  alert_dedup.time_window: {time_window} (期望: 30.0)")
        print(f"  alert_dedup.iou_threshold: {iou_threshold} (期望: 0.5)")
        print(f"  alert_dedup.position_time_window: {position_time_window} (期望: 10.0)")
        print(f"  beacon_match.temporal_consistency.enabled: {enabled} (期望: True)")
        print(f"  beacon_match.temporal_consistency.min_consistent_frames: {min_consistent_frames} (期望: 5)")
        print(f"  beacon_match.temporal_consistency.max_distance_error: {max_distance_error} (期望: 1.0)")
        
        # 验证默认值（允许用户修改，只打印提醒）
        if min_track_confidence != 0.7:
            print(f"  ⚠ min_track_confidence 已修改为 {min_track_confidence}")
        if time_window != 30.0:
            print(f"  ⚠ alert_dedup.time_window 已修改为 {time_window}")
        if iou_threshold != 0.5:
            print(f"  ⚠ alert_dedup.iou_threshold 已修改为 {iou_threshold}")
        if position_time_window != 10.0:
            print(f"  ⚠ alert_dedup.position_time_window 已修改为 {position_time_window}")
        if not enabled:
            print(f"  ⚠ beacon_match.temporal_consistency.enabled 已禁用")
        if min_consistent_frames != 5:
            print(f"  ⚠ beacon_match.temporal_consistency.min_consistent_frames 已修改为 {min_consistent_frames}")
        if max_distance_error != 1.0:
            print(f"  ⚠ beacon_match.temporal_consistency.max_distance_error 已修改为 {max_distance_error}")
        
        print("\n✅ 测试3通过：默认值验证完成\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_config():
    """测试4: 验证跟踪器与配置的集成"""
    print("="*70)
    print("测试4: 跟踪器与配置集成测试")
    print("="*70)
    
    try:
        config = get_config()
        
        # 从配置读取参数
        beacon_match_cfg = config.get('beacon_match', {}).get('temporal_consistency', {})
        enabled = beacon_match_cfg.get('enabled', True)
        min_consistent_frames = beacon_match_cfg.get('min_consistent_frames', 5)
        max_distance_error = beacon_match_cfg.get('max_distance_error', 1.0)
        reset_on_track_end = beacon_match_cfg.get('reset_on_track_end', True)
        
        if enabled:
            # 使用配置参数创建跟踪器
            tracker = BeaconMatchTracker(
                min_consistent_frames=min_consistent_frames,
                max_distance_error=max_distance_error,
                reset_on_track_end=reset_on_track_end
            )
            
            print(f"✓ 使用配置参数创建跟踪器:")
            print(f"  min_consistent_frames={tracker.min_consistent_frames}")
            print(f"  max_distance_error={tracker.max_distance_error}")
            print(f"  reset_on_track_end={tracker.reset_on_track_end}")
            
            # 验证跟踪器使用正确的配置值
            assert tracker.min_consistent_frames == min_consistent_frames
            assert tracker.max_distance_error == max_distance_error
            assert tracker.reset_on_track_end == reset_on_track_end
            
            print("\n✅ 测试4通过：跟踪器与配置集成正常\n")
        else:
            print("⚠ 时空一致性已禁用，跳过集成测试\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试4失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("Phase 1 优化测试套件")
    print("="*70 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("配置读取测试", test_config_loading()))
    results.append(("信标匹配跟踪器测试", test_beacon_match_tracker()))
    results.append(("默认值验证", test_config_default_values()))
    results.append(("配置集成测试", test_integration_with_config()))
    
    # 汇总结果
    print("="*70)
    print("测试结果汇总")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    print("="*70 + "\n")
    
    if failed == 0:
        print("🎉 所有测试通过！Phase 1 优化实施成功。\n")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息。\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

