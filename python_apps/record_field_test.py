#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现场测试视频录制脚本
从主程序的共享缓冲区读取帧并录制视频（不初始化相机）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import time
import argparse
from datetime import datetime
import threading
from pathlib import Path


class FieldTestRecorder:
    """现场测试视频录制器（从共享缓冲区读取）"""
    
    def __init__(self, output_dir="recordings", record_depth=True):
        """
        初始化录制器
        
        Args:
            output_dir: 输出目录
            record_depth: 是否录制深度视频
        """
        self.output_dir = Path(output_dir)
        self.record_depth = record_depth
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建带时间戳的输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"field_test_{timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # 视频写入器
        self.rgb_writer = None
        self.depth_writer = None
        
        # 共享缓冲区文件路径
        self.shared_frame_file = "/tmp/orbbec_shared_frame.npy"
        self.shared_depth_file = "/tmp/orbbec_shared_depth.npy"
        
        # 控制标志
        self.running = False
        self.recording = False
        
        # 统计信息
        self.frame_count = 0
        self.start_time = None
        self.width = None
        self.height = None
        
        print(f"✓ 录制器初始化完成（共享缓冲区模式）")
        print(f"  输出目录: {self.session_dir}")
        print(f"  共享帧文件: {self.shared_frame_file}")
    
    def start_recording(self):
        """开始录制"""
        try:
            # 等待主程序启动并创建共享缓冲区
            print("等待主程序启动并创建共享缓冲区...")
            max_wait = 30  # 最多等待30秒
            waited = 0
            while waited < max_wait:
                if os.path.exists(self.shared_frame_file):
                    # 尝试读取第一帧以确定分辨率
                    try:
                        frame = np.load(self.shared_frame_file)
                        if frame is not None and len(frame.shape) == 3:
                            self.height, self.width = frame.shape[:2]
                            print(f"✓ 检测到共享帧，分辨率: {self.width}x{self.height}")
                            break
                    except:
                        pass
                time.sleep(0.5)
                waited += 0.5
                if waited % 5 == 0:
                    print(f"  等待中... ({int(waited)}秒)")
            
            if self.width is None or self.height is None:
                raise Exception("无法从共享缓冲区获取帧，请确保主程序正在运行")
            
            # 创建视频写入器
            fps = 15  # 录制帧率
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # RGB视频
            rgb_path = self.session_dir / "rgb_video.mp4"
            self.rgb_writer = cv2.VideoWriter(
                str(rgb_path),
                fourcc,
                fps,
                (self.width, self.height)
            )
            if not self.rgb_writer.isOpened():
                raise Exception(f"无法创建RGB视频文件: {rgb_path}")
            print(f"✓ RGB视频: {rgb_path}")
            
            # 深度视频（可选）
            if self.record_depth:
                depth_path = self.session_dir / "depth_video.mp4"
                self.depth_writer = cv2.VideoWriter(
                    str(depth_path),
                    fourcc,
                    fps,
                    (self.width, self.height),
                    isColor=False  # 灰度视频
                )
                if not self.depth_writer.isOpened():
                    print(f"⚠ 无法创建深度视频文件，将跳过深度录制")
                    self.record_depth = False
                else:
                    print(f"✓ 深度视频: {depth_path}")
            
            # 保存元数据
            self._save_metadata(self.width, self.height, fps)
            
            # 开始录制
            self.running = True
            self.recording = True
            self.start_time = time.time()
            self.frame_count = 0
            
            print("\n" + "="*70)
            print("开始录制现场测试视频（从共享缓冲区读取）")
            print("="*70)
            print(f"按 Ctrl+C 停止录制")
            print("="*70 + "\n")
            
            # 录制循环
            self._recording_loop()
            
        except KeyboardInterrupt:
            print("\n收到停止信号，正在结束录制...")
        except Exception as e:
            print(f"\n✗ 录制错误: {e}")
        finally:
            self.stop_recording()
    
    def _recording_loop(self):
        """录制循环"""
        last_fps_time = time.time()
        fps_frame_count = 0
        last_frame_time = 0
        
        while self.running and self.recording:
            try:
                # 从共享缓冲区读取RGB帧
                if not os.path.exists(self.shared_frame_file):
                    time.sleep(0.1)
                    continue
                
                try:
                    # 检查文件修改时间，避免重复读取同一帧
                    frame_mtime = os.path.getmtime(self.shared_frame_file)
                    if frame_mtime <= last_frame_time:
                        time.sleep(0.01)
                        continue
                    last_frame_time = frame_mtime
                    
                    color_frame = np.load(self.shared_frame_file)
                    if color_frame is None or len(color_frame.shape) != 3:
                        time.sleep(0.01)
                        continue
                except Exception as e:
                    time.sleep(0.01)
                    continue
                
                # RGB: 转换为BGR格式（OpenCV要求）
                rgb_frame = color_frame.copy()
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                
                # 添加时间戳到画面
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(
                    bgr_frame,
                    timestamp_str,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
                # 写入RGB视频
                self.rgb_writer.write(bgr_frame)
                
                # 获取并写入深度帧（可选）
                if self.record_depth and self.depth_writer:
                    if os.path.exists(self.shared_depth_file):
                        try:
                            depth_image = np.load(self.shared_depth_file)
                            if depth_image is not None and len(depth_image.shape) == 2:
                                # 转换为8位灰度图
                                valid_mask = (depth_image > 0) & (depth_image < 65535)
                                if valid_mask.any():
                                    depth_min = depth_image[valid_mask].min()
                                    depth_max = depth_image[valid_mask].max()
                                    if depth_max > depth_min:
                                        depth_normalized = np.zeros_like(depth_image, dtype=np.uint8)
                                        depth_normalized[valid_mask] = (
                                            (depth_image[valid_mask] - depth_min) * 255.0 / 
                                            (depth_max - depth_min)
                                        ).astype(np.uint8)
                                    else:
                                        depth_normalized = np.zeros_like(depth_image, dtype=np.uint8)
                                else:
                                    depth_normalized = np.zeros_like(depth_image, dtype=np.uint8)
                                
                                self.depth_writer.write(depth_normalized)
                        except:
                            pass  # 忽略深度处理错误
                
                self.frame_count += 1
                fps_frame_count += 1
                
                # 每5秒打印一次FPS
                current_time = time.time()
                if current_time - last_fps_time >= 5.0:
                    fps = fps_frame_count / (current_time - last_fps_time)
                    elapsed = current_time - self.start_time
                    print(f"[录制中] 帧数: {self.frame_count:6d} | "
                          f"FPS: {fps:5.1f} | "
                          f"时长: {int(elapsed//60):02d}:{int(elapsed%60):02d}")
                    last_fps_time = current_time
                    fps_frame_count = 0
                
                # 控制帧率（避免过快）
                time.sleep(1.0 / 15.0)  # 目标15 FPS
                
            except Exception as e:
                print(f"⚠ 录制循环错误: {e}")
                time.sleep(0.1)
    
    def stop_recording(self):
        """停止录制"""
        self.recording = False
        self.running = False
        
        # 关闭视频写入器
        if self.rgb_writer:
            self.rgb_writer.release()
            print("✓ RGB视频已保存")
        
        if self.depth_writer:
            self.depth_writer.release()
            print("✓ 深度视频已保存")
        
        # 打印统计信息
        if self.start_time:
            elapsed = time.time() - self.start_time
            avg_fps = self.frame_count / elapsed if elapsed > 0 else 0
            print("\n" + "="*70)
            print("录制完成统计")
            print("="*70)
            print(f"总帧数: {self.frame_count}")
            print(f"录制时长: {int(elapsed//60):02d}:{int(elapsed%60):02d}")
            print(f"平均FPS: {avg_fps:.2f}")
            print(f"输出目录: {self.session_dir}")
            print("="*70)
    
    def _save_metadata(self, width, height, fps):
        """保存元数据"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "resolution": f"{width}x{height}",
            "fps": fps,
            "record_depth": self.record_depth,
            "camera": "Orbbec Gemini 335L",
            "mode": "shared_buffer"
        }
        
        import json
        metadata_path = self.session_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 元数据已保存: {metadata_path}")


def main():
    parser = argparse.ArgumentParser(description='现场测试视频录制（从共享缓冲区读取）')
    parser.add_argument('--output-dir', type=str, default='recordings',
                        help='输出目录（默认: recordings）')
    parser.add_argument('--no-depth', action='store_true',
                        help='不录制深度视频（仅录制RGB）')
    parser.add_argument('--duration', type=int, default=0,
                        help='录制时长（秒），0表示持续录制直到手动停止')
    
    args = parser.parse_args()
    
    # 创建录制器
    recorder = FieldTestRecorder(
        output_dir=args.output_dir,
        record_depth=not args.no_depth
    )
    
    # 如果指定了时长，创建定时器
    if args.duration > 0:
        def auto_stop():
            time.sleep(args.duration)
            print(f"\n录制时长达到 {args.duration} 秒，自动停止...")
            recorder.stop_recording()
        
        timer_thread = threading.Thread(target=auto_stop, daemon=True)
        timer_thread.start()
    
    # 开始录制
    try:
        recorder.start_recording()
    except KeyboardInterrupt:
        print("\n录制已停止")


if __name__ == "__main__":
    main()
