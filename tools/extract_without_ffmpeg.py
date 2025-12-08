#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
不依赖ffmpeg的替代方案：尝试从损坏的视频中提取数据
由于缺少moov atom，这个方法可能无法成功，但可以尝试
"""

import sys
import os
import struct
import cv2
import numpy as np
from pathlib import Path


def try_extract_with_opencv(video_path: str, output_dir: str, max_attempts: int = 1000):
    """
    尝试使用OpenCV逐帧读取（即使视频损坏）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("尝试使用OpenCV读取损坏的视频...")
    print("（这可能会失败，因为缺少moov atom）")
    print()
    
    # 尝试不同的方法
    methods = [
        ("标准方法", lambda: cv2.VideoCapture(video_path)),
        ("强制格式", lambda: cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)),
    ]
    
    frames = []
    for method_name, create_cap in methods:
        print(f"尝试方法: {method_name}")
        cap = create_cap()
        
        if cap.isOpened():
            print("  ✅ 可以打开")
            # 尝试读取几帧
            for i in range(max_attempts):
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                    if len(frames) % 10 == 0:
                        print(f"  已读取 {len(frames)} 帧...", end='\r')
                else:
                    break
            cap.release()
            
            if frames:
                print(f"\n  ✅ 成功读取 {len(frames)} 帧")
                break
        else:
            print("  ❌ 无法打开")
    
    if not frames:
        print("\n❌ 所有方法都失败，无法从损坏的视频中提取帧")
        return []
    
    # 保存提取的帧
    print(f"\n保存 {len(frames)} 帧到 {output_path}...")
    saved = []
    for i, frame in enumerate(frames):
        filename = output_path / f"extracted_frame_{i+1:05d}.jpg"
        cv2.imwrite(str(filename), frame)
        saved.append(str(filename))
        if (i + 1) % 10 == 0:
            print(f"  已保存 {i+1}/{len(frames)} 帧...", end='\r')
    print()
    
    return saved


def create_sample_result_images(output_dir: str, num_images: int = 5):
    """
    创建示例结果图（使用纯色背景和文字说明）
    用于演示目的
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"创建 {num_images} 张示例结果图...")
    
    for i in range(num_images):
        # 创建示例图像（1280x720，模拟视频分辨率）
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img.fill(50)  # 深灰色背景
        
        # 添加文字说明
        text = f"Video Frame {i+1} - Detection Result"
        text2 = "Note: Original video file is corrupted (missing moov atom)"
        text3 = "This is a placeholder image for demonstration"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, text, (50, 300), font, 1.5, (255, 255, 255), 2)
        cv2.putText(img, text2, (50, 350), font, 0.7, (200, 200, 200), 2)
        cv2.putText(img, text3, (50, 400), font, 0.7, (200, 200, 200), 2)
        
        # 添加一个示例检测框
        cv2.rectangle(img, (200, 150), (600, 450), (0, 255, 0), 3)
        cv2.putText(img, "Vehicle Detection", (210, 140), font, 0.8, (0, 255, 0), 2)
        
        filename = output_path / f"sample_result_{i+1:02d}.jpg"
        cv2.imwrite(str(filename), img)
        print(f"  ✅ 已创建: {filename.name}")
    
    print(f"\n✅ 创建了 {num_images} 张示例结果图")
    return True


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 extract_without_ffmpeg.py <video_path> [output_dir]")
        print("  python3 extract_without_ffmpeg.py --sample [output_dir] [num_images]")
        sys.exit(1)
    
    if sys.argv[1] == '--sample':
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "sample_result_images"
        num_images = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        create_sample_result_images(output_dir, num_images)
        return 0
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted_frames"
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return 1
    
    print("=" * 60)
    print("不依赖ffmpeg的视频帧提取")
    print("=" * 60)
    print(f"视频文件: {video_path}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)
    print()
    
    # 尝试提取
    extracted = try_extract_with_opencv(video_path, output_dir)
    
    if extracted:
        print()
        print("=" * 60)
        print(f"✅ 成功提取 {len(extracted)} 帧")
        print(f"输出目录: {output_dir}")
        print("=" * 60)
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ 无法从损坏的视频中提取帧")
        print()
        print("建议:")
        print("1. 等待网络恢复后安装ffmpeg:")
        print("   sudo apt install -y ffmpeg")
        print()
        print("2. 或者创建示例结果图（用于演示）:")
        print("   python3 extract_without_ffmpeg.py --sample result_images 5")
        print()
        print("3. 或者使用实时检测生成新结果图（需要相机）:")
        print("   python3 generate_result_images.py --num-images 5")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())



