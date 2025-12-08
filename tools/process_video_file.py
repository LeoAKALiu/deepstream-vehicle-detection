#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理视频文件生成检测结果图
支持从视频文件（包括损坏的视频）中提取帧并运行检测
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_apps'))

import cv2
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime

# 导入检测模块
from test_system_realtime import TensorRTInference, RealtimeVehicleDetection
from config_loader import get_config


def try_repair_video(input_path: str, output_path: str) -> bool:
    """
    尝试修复损坏的视频文件
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
    
    Returns:
        是否成功
    """
    try:
        import subprocess
        # 使用ffmpeg尝试修复
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c', 'copy',  # 直接复制流，不重新编码
            '-movflags', '+faststart',  # 将moov atom移到文件开头
            output_path,
            '-y'  # 覆盖输出文件
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0:
            return True
        else:
            print(f"修复失败: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
            return False
    except FileNotFoundError:
        print("⚠️  ffmpeg未安装，无法修复视频")
        return False
    except Exception as e:
        print(f"修复过程出错: {e}")
        return False


def extract_frames_from_video(video_path: str, output_dir: str, max_frames: int = 100) -> list:
    """
    从视频文件中提取帧
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        max_frames: 最大提取帧数
    
    Returns:
        提取的帧列表
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ 无法打开视频文件: {video_path}")
        print("   尝试修复视频...")
        
        # 尝试修复
        repaired_path = str(Path(video_path).with_suffix('.repaired.mp4'))
        if try_repair_video(video_path, repaired_path):
            print(f"✅ 视频修复成功: {repaired_path}")
            cap = cv2.VideoCapture(repaired_path)
            if not cap.isOpened():
                print("❌ 修复后的视频仍无法打开")
                return []
        else:
            print("❌ 视频修复失败")
            return []
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频信息:")
    print(f"  分辨率: {width}x{height}")
    print(f"  帧率: {fps:.2f} fps")
    print(f"  总帧数: {total_frames}")
    print()
    
    if total_frames == 0:
        print("⚠️  视频文件可能损坏，尝试逐帧读取...")
        # 尝试逐帧读取
        frame_count = 0
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1
            if frame_count % 10 == 0:
                print(f"  已提取 {frame_count} 帧...", end='\r')
        print()
    else:
        # 均匀提取帧
        step = max(1, total_frames // max_frames)
        frame_indices = list(range(0, total_frames, step))[:max_frames]
        
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                print(f"  提取帧 {i+1}/{len(frame_indices)}: 第{frame_idx}帧", end='\r')
            else:
                break
        print()
    
    cap.release()
    print(f"✅ 成功提取 {len(frames)} 帧")
    return frames


def process_video_with_detection(
    video_path: str,
    output_dir: str = "result_images",
    num_images: int = 5,
    config_path: str = None
):
    """
    从视频文件生成检测结果图
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        num_images: 需要生成的图片数量
        config_path: 配置文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("从视频文件生成检测结果图")
    print("=" * 60)
    print(f"视频文件: {video_path}")
    print(f"输出目录: {output_path.absolute()}")
    print(f"目标数量: {num_images} 张")
    print("=" * 60)
    print()
    
    # 提取帧
    print("步骤1: 提取视频帧...")
    frames = extract_frames_from_video(video_path, str(output_path / "extracted_frames"), max_frames=num_images * 10)
    
    if len(frames) == 0:
        print("❌ 无法从视频中提取帧")
        return False
    
    print(f"✅ 提取了 {len(frames)} 帧")
    print()
    
    # 初始化检测系统
    print("步骤2: 初始化检测系统...")
    try:
        config = get_config(config_path)
        detection_cfg = config.get_detection()
        engine_path = detection_cfg.get('model_path', 'models/custom_yolo.engine')
        
        if not os.path.exists(engine_path):
            print(f"❌ 模型文件不存在: {engine_path}")
            return False
        
        inference = TensorRTInference(
            engine_path=engine_path,
            conf_threshold=detection_cfg.get('conf_threshold', 0.7),
            iou_threshold=detection_cfg.get('iou_threshold', 0.5)
        )
        print("✅ 检测系统初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("步骤3: 处理帧并生成结果图...")
    
    # 处理帧
    saved_count = 0
    for i, frame in enumerate(frames):
        if saved_count >= num_images:
            break
        
        # 预处理
        input_data = inference.preprocess(frame)
        
        # 推理
        output = inference.infer(input_data)
        
        # 后处理
        boxes, confidences, class_ids = inference.postprocess(output)
        
        # 只保存有检测结果的帧
        if len(boxes) > 0:
            # 绘制检测框
            result_frame = frame.copy()
            for j, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Class {cls_id} {conf:.2f}"
                cv2.putText(result_frame, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_result_{saved_count+1:02d}_{timestamp}.jpg"
            filepath = output_path / filename
            cv2.imwrite(str(filepath), cv2.cvtColor(result_frame, cv2.COLOR_RGB2BGR))
            
            saved_count += 1
            print(f"✅ [{saved_count}/{num_images}] 已保存: {filename} (检测到 {len(boxes)} 个目标)")
    
    print()
    print("=" * 60)
    print(f"结果总结:")
    print(f"  处理帧数: {len(frames)}")
    print(f"  生成图片: {saved_count}/{num_images}")
    print(f"  输出目录: {output_path.absolute()}")
    if saved_count > 0:
        print(f"\n生成的图片文件:")
        for img_file in sorted(output_path.glob("detection_result_*.jpg")):
            size_mb = img_file.stat().st_size / 1024 / 1024
            print(f"  - {img_file.name} ({size_mb:.2f} MB)")
    print("=" * 60)
    
    return saved_count > 0


def main():
    parser = argparse.ArgumentParser(description="从视频文件生成检测结果图")
    parser.add_argument(
        "video_path",
        help="视频文件路径"
    )
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
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径 (默认: config.yaml)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"❌ 视频文件不存在: {args.video_path}")
        return 1
    
    success = process_video_with_detection(
        video_path=args.video_path,
        output_dir=args.output_dir,
        num_images=args.num_images,
        config_path=args.config
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())



