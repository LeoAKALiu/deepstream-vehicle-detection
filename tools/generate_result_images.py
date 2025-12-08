#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成检测结果图 - 用于客户展示
运行检测算法并自动保存带检测框的结果图
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_apps'))

import cv2
import numpy as np
import time
import argparse
from datetime import datetime
from pathlib import Path

# 导入主程序模块
from test_system_realtime import RealtimeVehicleDetection


def generate_result_images(
    output_dir: str = "result_images",
    num_images: int = 5,
    capture_interval: int = 10,  # 每10秒捕获一张
    min_detections: int = 1,  # 至少检测到1个目标才保存
    max_wait_time: int = 300,  # 最多等待5分钟
    config_path: str = None
):
    """
    运行检测算法并生成结果图
    
    Args:
        output_dir: 输出目录
        num_images: 需要生成的图片数量
        capture_interval: 捕获间隔（秒）
        min_detections: 最少检测目标数才保存
        max_wait_time: 最大等待时间（秒）
        config_path: 配置文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"=" * 60)
    print(f"生成检测结果图")
    print(f"=" * 60)
    print(f"输出目录: {output_path.absolute()}")
    print(f"目标数量: {num_images} 张")
    print(f"捕获间隔: {capture_interval} 秒")
    print(f"最小检测数: {min_detections}")
    print(f"最大等待: {max_wait_time} 秒")
    print(f"=" * 60)
    print()
    
    # 初始化检测系统
    print("初始化检测系统...")
    try:
        detector = RealtimeVehicleDetection(no_display=True, config_path=config_path)
        print("✅ 检测系统初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("开始检测，等待捕获机会...")
    print("提示: 确保相机已连接，场景中有车辆")
    print("按 Ctrl+C 停止")
    print()
    
    # 捕获状态
    captured_count = 0
    last_capture_time = 0
    start_time = time.time()
    frame_count = 0
    
    # 修改detector的run方法以支持帧保存
    # 由于run()是主循环，我们需要在循环中添加保存逻辑
    # 创建一个包装器来拦截draw_results的调用
    
    original_draw = detector.draw_results
    
    def draw_results_with_save(image, tracks, alerts_dict):
        """包装draw_results以添加保存功能"""
        nonlocal captured_count, last_capture_time, start_time, frame_count
        
        # 调用原始绘制方法
        result_frame = original_draw(image, tracks, alerts_dict)
        
        # 检查是否应该保存
        current_time = time.time()
        elapsed = current_time - start_time
        num_detections = len(tracks) if tracks else 0
        
        # 检查超时
        if elapsed > max_wait_time and captured_count == 0:
            print(f"\n⏰ 达到最大等待时间 ({max_wait_time}秒)，停止捕获")
            return result_frame
        
        # 检查是否满足捕获条件
        should_capture = (
            num_detections >= min_detections and
            (current_time - last_capture_time) >= capture_interval and
            captured_count < num_images
        )
        
        if should_capture:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_result_{captured_count+1:02d}_{timestamp}.jpg"
            filepath = output_path / filename
            
            # 保存图片（转换为BGR格式）
            bgr_frame = cv2.cvtColor(result_frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(filepath), bgr_frame)
            
            captured_count += 1
            last_capture_time = current_time
            
            print(f"✅ [{captured_count}/{num_images}] 已保存: {filename}")
            print(f"   检测到 {num_detections} 个目标, 耗时 {elapsed:.1f}秒")
            
            if captured_count >= num_images:
                print(f"\n✅ 已完成！已生成 {captured_count} 张结果图")
        
        # 显示进度（每30帧）
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"进度: 已捕获 {captured_count}/{num_images}, "
                  f"当前检测 {num_detections} 个目标, "
                  f"运行时间 {elapsed:.1f}秒", end='\r')
        
        return result_frame
    
    # 替换draw_results方法
    detector.draw_results = draw_results_with_save
    
    try:
        # 运行主循环
        detector.run()
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 60)
    print(f"结果总结:")
    print(f"  生成图片: {captured_count}/{num_images}")
    print(f"  输出目录: {output_path.absolute()}")
    if captured_count > 0:
        print(f"\n生成的图片文件:")
        for i, img_file in enumerate(sorted(output_path.glob("*.jpg")), 1):
            size_mb = img_file.stat().st_size / 1024 / 1024
            print(f"  {i}. {img_file.name} ({size_mb:.2f} MB)")
    print("=" * 60)
    
    return captured_count > 0


def main():
    parser = argparse.ArgumentParser(description="生成检测结果图")
    parser.add_argument(
        "--output-dir", "-o",
        default="result_images",
        help="输出目录 (默认: result_images)"
    )
    parser.add_argument(
        "--num-images", "-n",
        type=int,
        default=5,
        help="需要生成的图片数量 (默认: 5)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=10,
        help="捕获间隔（秒） (默认: 10)"
    )
    parser.add_argument(
        "--min-detections", "-m",
        type=int,
        default=1,
        help="最少检测目标数才保存 (默认: 1)"
    )
    parser.add_argument(
        "--max-wait", "-w",
        type=int,
        default=300,
        help="最大等待时间（秒） (默认: 300)"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径 (默认: config.yaml)"
    )
    
    args = parser.parse_args()
    
    success = generate_result_images(
        output_dir=args.output_dir,
        num_images=args.num_images,
        capture_interval=args.interval,
        min_detections=args.min_detections,
        max_wait_time=args.max_wait,
        config_path=args.config
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
