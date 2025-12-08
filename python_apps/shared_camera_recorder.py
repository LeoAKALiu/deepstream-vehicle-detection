#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享相机录制脚本
与主程序共享Orbbec相机实例，同时录制RGB和深度视频
使用共享内存或文件锁机制避免冲突
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
import fcntl  # 文件锁

from orbbec_depth import OrbbecDepthCamera


class SharedCameraRecorder:
    """共享相机录制器（与主程序共享相机）"""
    
    def __init__(self, output_dir="recordings", record_depth=True, lock_file="/tmp/orbbec_camera.lock"):
        """
        初始化录制器
        
        Args:
            output_dir: 输出目录
            record_depth: 是否录制深度视频
            lock_file: 相机锁文件路径
        """
        self.output_dir = Path(output_dir)
        self.record_depth = record_depth
        self.lock_file = lock_file
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建带时间戳的输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"field_test_{timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # 视频写入器
        self.rgb_writer = None
        self.depth_writer = None
        
        # 相机（共享）
        self.depth_camera = None
        self.lock_fd = None
        
        # 控制标志
        self.running = False
        self.recording = False
        
        # 统计信息
        self.frame_count = 0
        self.start_time = None
        
        print(f"✓ 共享录制器初始化完成")
        print(f"  输出目录: {self.session_dir}")
        print(f"  锁文件: {self.lock_file}")
    
    def _acquire_lock(self):
        """获取相机锁"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 写入PID
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            print(f"✓ 已获取相机锁")
            return True
        except (IOError, OSError) as e:
            print(f"✗ 无法获取相机锁: {e}")
            print(f"  可能相机已被其他进程占用")
            return False
    
    def _release_lock(self):
        """释放相机锁"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                os.remove(self.lock_file)
                print("✓ 已释放相机锁")
            except:
                pass
    
    def start_recording(self):
        """开始录制"""
        try:
            # 获取锁
            if not self._acquire_lock():
                raise Exception("无法获取相机锁，可能已被占用")
            
            # 初始化相机
            self.depth_camera = OrbbecDepthCamera()
            if not self.depth_camera.start():
                raise Exception("相机启动失败")
            
            # 等待相机稳定
            print("等待相机稳定...")
            time.sleep(2)
            
            # 获取第一帧以确定分辨率
            for _ in range(30):
                color_frame = self.depth_camera.get_color_frame()
                if color_frame is not None:
                    break
                time.sleep(0.1)
            
            if color_frame is None:
                raise Exception("无法获取相机画面")
            
            height, width = color_frame.shape[:2]
            print(f"✓ 相机分辨率: {width}x{height}")
            
            # 创建视频写入器
            fps = 15
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # RGB视频
            rgb_path = self.session_dir / "rgb_video.mp4"
            self.rgb_writer = cv2.VideoWriter(
                str(rgb_path),
                fourcc,
                fps,
                (width, height)
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
                    (width, height),
                    isColor=False
                )
                if not self.depth_writer.isOpened():
                    print(f"⚠ 无法创建深度视频文件，将跳过深度录制")
                    self.record_depth = False
                else:
                    print(f"✓ 深度视频: {depth_path}")
            
            # 保存元数据
            self._save_metadata(width, height, fps)
            
            # 创建共享帧缓冲区（用于主程序读取）
            shared_frame_file = "/tmp/orbbec_shared_frame.npy"
            self.shared_frame_file = shared_frame_file
            
            # 开始录制
            self.running = True
            self.recording = True
            self.start_time = time.time()
            self.frame_count = 0
            
            print("\n" + "="*70)
            print("开始录制现场测试视频（共享相机模式）")
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
        
        while self.running and self.recording:
            try:
                # 获取RGB帧
                color_frame = self.depth_camera.get_color_frame()
                if color_frame is None:
                    time.sleep(0.01)
                    continue
                
                # 保存共享帧（供主程序读取）
                try:
                    np.save(self.shared_frame_file, color_frame)
                except:
                    pass  # 忽略保存错误
                
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
                    with self.depth_camera.depth_lock:
                        depth_frame = self.depth_camera.depth_frame
                    if depth_frame is not None:
                        try:
                            width = depth_frame.get_width()
                            height = depth_frame.get_height()
                            depth_data = np.frombuffer(
                                depth_frame.get_data(),
                                dtype=np.uint16
                            )
                            depth_image = depth_data.reshape((height, width))
                            
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
                            
                        except Exception as e:
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
                
                # 控制帧率
                time.sleep(1.0 / 15.0)
                
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
        
        # 停止相机
        if self.depth_camera:
            self.depth_camera.stop()
            print("✓ 相机已停止")
        
        # 释放锁
        self._release_lock()
        
        # 清理共享文件
        try:
            if os.path.exists(self.shared_frame_file):
                os.remove(self.shared_frame_file)
        except:
            pass
        
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
            "mode": "shared_camera"
        }
        
        import json
        metadata_path = self.session_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 元数据已保存: {metadata_path}")


def main():
    parser = argparse.ArgumentParser(description='现场测试视频录制（共享相机模式）')
    parser.add_argument('--output-dir', type=str, default='recordings',
                        help='输出目录（默认: recordings）')
    parser.add_argument('--no-depth', action='store_true',
                        help='不录制深度视频')
    parser.add_argument('--duration', type=int, default=0,
                        help='录制时长（秒），0表示持续录制')
    
    args = parser.parse_args()
    
    recorder = SharedCameraRecorder(
        output_dir=args.output_dir,
        record_depth=not args.no_depth
    )
    
    if args.duration > 0:
        def auto_stop():
            time.sleep(args.duration)
            print(f"\n录制时长达到 {args.duration} 秒，自动停止...")
            recorder.stop_recording()
        
        timer_thread = threading.Thread(target=auto_stop, daemon=True)
        timer_thread.start()
    
    try:
        recorder.start_recording()
    except KeyboardInterrupt:
        print("\n录制已停止")


if __name__ == "__main__":
    main()

