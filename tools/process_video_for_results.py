#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理视频文件并生成检测结果图
用于从损坏或不完整的视频中提取帧并运行检测算法
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_apps'))

import cv2
import numpy as np
import argparse
from datetime import datetime
import json

# 导入检测相关模块
from tensorrt_yolo_inference import TensorRTInference
from byte_tracker import ByteTracker
from config_loader import get_config

try:
    import hyperlpr3 as lpr3
    LPR_AVAILABLE = True
except ImportError:
    LPR_AVAILABLE = False
    print("⚠ HyperLPR3未安装，车牌识别功能将不可用")

# 自定义模型类别
CUSTOM_CLASSES = {
    0: 'excavator',       # 挖掘机
    1: 'bulldozer',       # 推土机
    2: 'roller',          # 压路机
    3: 'loader',          # 装载机
    4: 'dump-truck',      # 自卸车
    5: 'concrete-mixer',  # 混凝土搅拌车
    6: 'pump-truck',      # 泵车
    7: 'truck',           # 卡车
    8: 'crane',           # 起重机
    9: 'car',             # 小汽车
}

VEHICLE_CLASSES = {
    'excavator': 'construction',
    'bulldozer': 'construction',
    'roller': 'construction',
    'loader': 'construction',
    'dump-truck': 'construction',
    'concrete-mixer': 'construction',
    'pump-truck': 'construction',
    'truck': 'construction',
    'crane': 'construction',
    'car': 'civilian',
}

COLORS = {
    'construction': (0, 140, 255),   # 橙色
    'civilian': (0, 255, 0),          # 绿色
    'unregistered': (0, 0, 255),      # 红色
}


def extract_frames_from_video(video_path: str, output_dir: str, max_frames: int = 50, interval: int = 30) -> list:
    """
    从视频中提取帧（即使视频损坏也尝试）
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        max_frames: 最大提取帧数
        interval: 帧间隔
    
    Returns:
        提取的帧列表
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"⚠ 无法打开视频，尝试强制读取...")
        # 尝试使用不同的后端
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print(f"❌ 完全无法打开视频文件: {video_path}")
        return []
    
    frames = []
    frame_count = 0
    saved_count = 0
    
    print(f"开始提取帧...")
    
    while saved_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # 按间隔保存帧
        if frame_count % interval == 0:
            frame_path = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            frames.append((frame_count, frame_path, frame))
            saved_count += 1
            print(f"  保存帧 {frame_count}: {frame_path}")
    
    cap.release()
    print(f"✅ 共提取 {saved_count} 帧")
    return frames


def process_frame_with_detection(frame: np.ndarray, inference: TensorRTInference, 
                                 tracker: ByteTracker, frame_id: int, config: dict) -> tuple:
    """
    对单帧进行检测和跟踪
    
    Returns:
        (result_frame, detections_info)
    """
    # 预处理
    input_h, input_w = config['detection']['input_resolution']
    frame_resized = cv2.resize(frame, (input_w, input_h))
    input_data = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    input_data = input_data.astype(np.float32) / 255.0
    input_data = np.transpose(input_data, (2, 0, 1))
    input_data = np.expand_dims(input_data, axis=0)
    
    # 推理
    output = inference.infer(input_data)
    boxes, confidences, class_ids = inference.postprocess(output)
    
    # 转换到原图坐标
    h, w = frame.shape[:2]
    scale_x = w / input_w
    scale_y = h / input_h
    
    boxes_scaled = []
    for box in boxes:
        x1, y1, x2, y2 = box
        boxes_scaled.append([
            int(x1 * scale_x),
            int(y1 * scale_y),
            int(x2 * scale_x),
            int(y2 * scale_y)
        ])
    
    # 跟踪
    detections = []
    for i, (box, conf, cls_id) in enumerate(zip(boxes_scaled, confidences, class_ids)):
        x1, y1, x2, y2 = box
        detections.append([x1, y1, x2, y2, conf, cls_id])
    
    tracks = tracker.update(np.array(detections), frame)
    
    # 绘制结果
    result_frame = frame.copy()
    detections_info = []
    
    for track in tracks:
        track_id = int(track[4])
        x1, y1, x2, y2 = map(int, track[:4])
        cls_id = int(track[5])
        
        class_name = CUSTOM_CLASSES.get(cls_id, 'unknown')
        vehicle_type = VEHICLE_CLASSES.get(class_name, 'unknown')
        
        # 选择颜色
        if vehicle_type == 'construction':
            color = COLORS['construction']
        elif vehicle_type == 'civilian':
            color = COLORS['civilian']
        else:
            color = (128, 128, 128)
        
        # 绘制边界框
        cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)
        
        # 标签
        label = f"{class_name} ID:{track_id}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(result_frame, (x1, y1 - label_size[1] - 10), 
                     (x1 + label_size[0], y1), color, -1)
        cv2.putText(result_frame, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        detections_info.append({
            'track_id': track_id,
            'class': class_name,
            'vehicle_type': vehicle_type,
            'bbox': [x1, y1, x2, y2],
            'confidence': float(track[4])
        })
    
    return result_frame, detections_info


def main():
    parser = argparse.ArgumentParser(description='处理视频并生成检测结果图')
    parser.add_argument('--video', type=str, required=True, help='视频文件路径')
    parser.add_argument('--output', type=str, default='./results', help='输出目录')
    parser.add_argument('--max-frames', type=int, default=20, help='最大处理帧数')
    parser.add_argument('--interval', type=int, default=30, help='帧间隔')
    parser.add_argument('--model', type=str, default='models/custom_yolo.engine', help='模型文件路径')
    parser.add_argument('--labels', type=str, default='config/labels.txt', help='标签文件路径')
    
    args = parser.parse_args()
    
    # 加载配置
    config = get_config()
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(args.output, f"video_results_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 输出目录: {output_dir}")
    
    # 初始化检测器
    print("🔧 初始化检测器...")
    # 获取输入分辨率
    input_resolution = config.get('detection', {}).get('input_resolution', [640, 640])
    input_shape = (input_resolution[0], input_resolution[1])
    inference = TensorRTInference(args.model, input_shape=input_shape)
    
    # 初始化跟踪器
    tracker_config = config.get('tracking', {})
    tracker = ByteTracker(
        track_thresh=tracker_config.get('track_thresh', 0.6),
        high_thresh=tracker_config.get('high_thresh', 0.7),
        match_thresh=tracker_config.get('match_thresh', 0.7),
        track_buffer=tracker_config.get('track_buffer', 50),
        frame_rate=30
    )
    
    # 提取帧
    print(f"\n📹 处理视频: {args.video}")
    frames_dir = os.path.join(output_dir, "extracted_frames")
    frames = extract_frames_from_video(args.video, frames_dir, args.max_frames, args.interval)
    
    if not frames:
        print("❌ 无法从视频中提取帧")
        return
    
    # 处理每一帧
    print(f"\n🔍 运行检测算法...")
    results_dir = os.path.join(output_dir, "detection_results")
    os.makedirs(results_dir, exist_ok=True)
    
    all_detections = []
    
    for idx, (frame_num, frame_path, frame) in enumerate(frames):
        print(f"  处理帧 {idx+1}/{len(frames)} (原帧号: {frame_num})...")
        
        result_frame, detections_info = process_frame_with_detection(
            frame, inference, tracker, frame_num, config
        )
        
        # 保存结果图
        result_path = os.path.join(results_dir, f"result_frame_{frame_num:06d}.jpg")
        cv2.imwrite(result_path, result_frame)
        
        all_detections.append({
            'frame': frame_num,
            'detections': detections_info
        })
        
        print(f"    ✅ 保存结果: {result_path} (检测到 {len(detections_info)} 个目标)")
    
    # 保存检测结果JSON
    results_json = os.path.join(output_dir, "detections.json")
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(all_detections, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 处理完成!")
    print(f"  结果图目录: {results_dir}")
    print(f"  检测结果JSON: {results_json}")
    print(f"  共处理 {len(frames)} 帧")
    
    # 统计信息
    total_detections = sum(len(d['detections']) for d in all_detections)
    construction_count = sum(1 for d in all_detections 
                            for det in d['detections'] 
                            if det['vehicle_type'] == 'construction')
    civilian_count = sum(1 for d in all_detections 
                        for det in d['detections'] 
                        if det['vehicle_type'] == 'civilian')
    
    print(f"\n📊 统计信息:")
    print(f"  总检测数: {total_detections}")
    print(f"  工程车辆: {construction_count}")
    print(f"  社会车辆: {civilian_count}")


if __name__ == '__main__':
    main()

