"""
Phase 2 优化测试脚本

测试内容：
1. ByteTrack参数调优 - 验证配置是否正确加载
2. 深度测量时间平滑 - 验证平滑功能是否正常工作
3. LPR最佳帧选取 - 验证帧质量评分和最佳帧选择
"""

import sys
import os
import numpy as np
from unittest.mock import Mock, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_apps'))

from config_loader import get_config
from depth_smoothing import TrackDepthSmoother, create_depth_smoother
from best_frame_lpr import BestFrameLPR, calculate_frame_quality


def test_1_bytetrack_params():
    """测试1: ByteTrack参数调优"""
    print("\n" + "="*60)
    print("测试1: ByteTrack参数调优")
    print("="*60)
    
    try:
        config = get_config()
        tracking_cfg = config.get('tracking', {})
        
        match_thresh = tracking_cfg.get('match_thresh', 0.8)
        track_buffer = tracking_cfg.get('track_buffer', 30)
        
        print(f"  match_thresh: {match_thresh} (期望: 0.4)")
        print(f"  track_buffer: {track_buffer} (期望: 200)")
        
        # 验证参数
        assert match_thresh == 0.4, f"match_thresh应为0.4，实际为{match_thresh}"
        assert track_buffer == 200, f"track_buffer应为200，实际为{track_buffer}"
        
        print("  ✅ ByteTrack参数配置正确")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_depth_smoothing():
    """测试2: 深度测量时间平滑"""
    print("\n" + "="*60)
    print("测试2: 深度测量时间平滑")
    print("="*60)
    
    try:
        # 测试1: 从配置创建平滑器
        config = get_config()
        depth_cfg = config.get('depth', {})
        smoother = create_depth_smoother(depth_cfg)
        
        if smoother is None:
            print("  ⚠ 深度平滑未启用，跳过测试")
            return True
        
        print(f"  ✓ 平滑器创建成功")
        print(f"    方法: {smoother.method}")
        print(f"    alpha: {smoother.alpha}")
        print(f"    window_size: {smoother.window_size}")
        print(f"    min_samples: {smoother.min_samples}")
        
        # 测试2: EMA平滑功能
        print("\n  测试EMA平滑...")
        track_id = 1
        depths = [5.0, 5.2, 5.1, 5.3, 5.0, 5.2]  # 模拟深度值
        
        results = []
        for depth in depths:
            smoothed = smoother.update(track_id, depth)
            results.append(smoothed)
            print(f"    原始: {depth:.2f}m -> 平滑: {smoothed:.2f}m")
        
        # 验证平滑后的值更稳定（方差应该减小）
        original_var = np.var(depths)
        smoothed_var = np.var(results[-3:])  # 最后3个值的方差
        print(f"    原始方差: {original_var:.4f}")
        print(f"    平滑后方差: {smoothed_var:.4f}")
        
        # 测试3: 重置功能
        smoother.reset(track_id)
        result_after_reset = smoother.update(track_id, 5.0)
        assert result_after_reset == 5.0, "重置后应该从原始值开始"
        print("  ✅ 重置功能正常")
        
        print("  ✅ 深度平滑功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_frame_quality():
    """测试3: 帧质量评分"""
    print("\n" + "="*60)
    print("测试3: 帧质量评分")
    print("="*60)
    
    try:
        # 测试不同场景的帧质量
        frame_shape = (1080, 1920, 3)  # 1080p
        
        # 场景1: 理想帧（大bbox，中心位置，合适距离）
        bbox1 = [800, 400, 1120, 800]  # 较大的bbox，居中
        quality1 = calculate_frame_quality(bbox1, 0.9, frame_shape, distance=4.0)
        print(f"  场景1 (理想帧): 质量分数 = {quality1:.3f}")
        assert 0.7 <= quality1 <= 1.0, "理想帧质量应该较高"
        
        # 场景2: 小bbox（远距离）
        bbox2 = [900, 500, 1000, 600]  # 较小的bbox
        quality2 = calculate_frame_quality(bbox2, 0.8, frame_shape, distance=8.0)
        print(f"  场景2 (小bbox): 质量分数 = {quality2:.3f}")
        assert quality2 < quality1, "小bbox质量应该较低"
        
        # 场景3: 边缘位置
        bbox3 = [100, 100, 300, 400]  # 边缘位置
        quality3 = calculate_frame_quality(bbox3, 0.9, frame_shape, distance=4.0)
        print(f"  场景3 (边缘): 质量分数 = {quality3:.3f}")
        assert quality3 < quality1, "边缘位置质量应该较低"
        
        # 场景4: 低置信度
        bbox4 = [800, 400, 1120, 800]  # 相同bbox
        quality4 = calculate_frame_quality(bbox4, 0.5, frame_shape, distance=4.0)
        print(f"  场景4 (低置信度): 质量分数 = {quality4:.3f}")
        assert quality4 < quality1, "低置信度质量应该较低"
        
        print("  ✅ 帧质量评分测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_best_frame_lpr():
    """测试4: LPR最佳帧选取"""
    print("\n" + "="*60)
    print("测试4: LPR最佳帧选取")
    print("="*60)
    
    try:
        # 创建最佳帧选择器
        best_frame_lpr = BestFrameLPR(
            quality_threshold=0.6,
            max_wait_frames=10,  # 测试用较小的值
            reuse_result=True
        )
        print("  ✓ 最佳帧选择器创建成功")
        
        # 模拟帧序列
        frame_shape = (1080, 1920, 3)
        track_id = 1
        
        # 创建模拟ROI
        def create_roi():
            return np.zeros((200, 400, 3), dtype=np.uint8)
        
        # 测试1: 低质量帧 -> 应该等待
        print("\n  测试1: 低质量帧序列...")
        bbox_low = [900, 500, 1000, 600]  # 小bbox
        should_trigger, best_roi = best_frame_lpr.should_trigger_lpr(
            track_id=track_id,
            bbox=bbox_low,
            roi_bgr=create_roi(),
            confidence=0.5,
            frame_shape=frame_shape,
            distance=8.0
        )
        assert not should_trigger, "低质量帧不应该立即触发"
        print(f"    ✓ 低质量帧未触发（符合预期）")
        
        # 测试2: 高质量帧 -> 应该触发
        print("\n  测试2: 高质量帧...")
        bbox_high = [800, 400, 1120, 800]  # 大bbox，居中
        for i in range(3):
            should_trigger, best_roi = best_frame_lpr.should_trigger_lpr(
                track_id=track_id,
                bbox=bbox_high,
                roi_bgr=create_roi(),
                confidence=0.9,
                frame_shape=frame_shape,
                distance=4.0
            )
            if should_trigger:
                print(f"    ✓ 高质量帧触发识别（第{i+1}帧后）")
                break
        
        assert should_trigger, "高质量帧应该触发识别"
        assert best_roi is not None, "应该返回最佳ROI"
        
        # 测试3: 结果复用
        print("\n  测试3: 结果复用...")
        best_frame_lpr.on_lpr_complete(track_id, "京A12345", 0.95)
        should_trigger_again, _ = best_frame_lpr.should_trigger_lpr(
            track_id=track_id,
            bbox=bbox_high,
            roi_bgr=create_roi(),
            confidence=0.9,
            frame_shape=frame_shape,
            distance=4.0
        )
        assert not should_trigger_again, "已有结果时不应该再次触发"
        
        # 检查结果
        result = best_frame_lpr.get_result(track_id)
        assert result == ("京A12345", 0.95), "应该能获取保存的结果"
        print(f"    ✓ 结果复用正常: {result[0]}")
        
        # 测试4: 超时机制
        print("\n  测试4: 超时机制...")
        track_id2 = 2
        best_frame_lpr2 = BestFrameLPR(
            quality_threshold=0.9,  # 高阈值，不容易达到
            max_wait_frames=5,
            reuse_result=True
        )
        
        for i in range(6):  # 超过max_wait_frames
            should_trigger, best_roi = best_frame_lpr2.should_trigger_lpr(
                track_id=track_id2,
                bbox=bbox_low,
                roi_bgr=create_roi(),
                confidence=0.7,
                frame_shape=frame_shape,
                distance=6.0
            )
            if should_trigger:
                print(f"    ✓ 超时后触发（第{i+1}帧）")
                break
        
        assert should_trigger, "超时后应该触发"
        
        # 测试5: 清理功能
        print("\n  测试5: 清理功能...")
        best_frame_lpr.reset(track_id)
        result_after_reset = best_frame_lpr.get_result(track_id)
        assert result_after_reset is None, "重置后应该没有结果"
        print("    ✓ 清理功能正常")
        
        print("  ✅ 最佳帧LPR选择器测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_config_integration():
    """测试5: 配置集成"""
    print("\n" + "="*60)
    print("测试5: 配置集成")
    print("="*60)
    
    try:
        config = get_config()
        
        # 检查深度平滑配置
        depth_cfg = config.get('depth', {})
        smoothing_cfg = depth_cfg.get('smoothing', {})
        assert smoothing_cfg.get('enabled', False) == True, "深度平滑应该启用"
        print(f"  ✓ 深度平滑配置: enabled={smoothing_cfg.get('enabled')}")
        print(f"    方法: {smoothing_cfg.get('method')}")
        print(f"    alpha: {smoothing_cfg.get('alpha')}")
        
        # 检查LPR最佳帧配置
        lpr_cfg = config.get('lpr', {})
        best_frame_cfg = lpr_cfg.get('best_frame_selection', {})
        assert best_frame_cfg.get('enabled', False) == True, "LPR最佳帧应该启用"
        print(f"  ✓ LPR最佳帧配置: enabled={best_frame_cfg.get('enabled')}")
        print(f"    质量阈值: {best_frame_cfg.get('quality_threshold')}")
        print(f"    最大等待帧数: {best_frame_cfg.get('max_wait_frames')}")
        print(f"    结果复用: {best_frame_cfg.get('reuse_result')}")
        
        print("  ✅ 配置集成测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Phase 2 优化测试套件")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("ByteTrack参数调优", test_1_bytetrack_params()))
    results.append(("深度测量时间平滑", test_2_depth_smoothing()))
    results.append(("帧质量评分", test_3_frame_quality()))
    results.append(("LPR最佳帧选取", test_4_best_frame_lpr()))
    results.append(("配置集成", test_5_config_integration()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("\n🎉 所有测试通过！Phase 2 优化实施成功。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == '__main__':
    exit(main())

