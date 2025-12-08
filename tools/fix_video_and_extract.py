#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
尝试修复损坏的MP4视频并提取帧
当moov atom缺失时，尝试重建或直接从数据中提取
"""

import sys
import os
import subprocess
import struct
from pathlib import Path


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def try_ffmpeg_repair(input_path: str, output_path: str) -> bool:
    """使用ffmpeg修复视频"""
    if not check_ffmpeg():
        return False
    
    try:
        print("尝试使用ffmpeg修复视频...")
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c', 'copy',
            '-movflags', '+faststart',
            output_path,
            '-y'
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            print("✅ ffmpeg修复成功")
            return True
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            if 'moov atom' in stderr.lower():
                print("⚠️  ffmpeg也无法修复（moov atom完全缺失）")
            else:
                print(f"⚠️  ffmpeg修复失败: {stderr[:200]}")
            return False
    except Exception as e:
        print(f"⚠️  ffmpeg修复过程出错: {e}")
        return False


def extract_with_ffmpeg(input_path: str, output_dir: str, num_frames: int = 10) -> list:
    """使用ffmpeg直接从损坏的视频中提取帧（不依赖moov atom）"""
    if not check_ffmpeg():
        return []
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        print("尝试使用ffmpeg直接从数据流中提取帧...")
        # 使用 -vsync 0 和 -frame_pts 来尝试提取帧
        # -err_detect ignore_err 忽略错误
        output_pattern = str(output_path / "frame_%05d.jpg")
        
        cmd = [
            'ffmpeg',
            '-err_detect', 'ignore_err',  # 忽略错误
            '-i', input_path,
            '-vsync', '0',  # 不进行帧同步
            '-frames:v', str(num_frames),  # 提取指定数量的帧
            '-q:v', '2',  # 高质量
            output_pattern,
            '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if result.returncode == 0:
            extracted = list(output_path.glob("frame_*.jpg"))
            if extracted:
                print(f"✅ 成功提取 {len(extracted)} 帧")
                return [str(f) for f in sorted(extracted)]
        
        # 如果失败，尝试另一种方法：指定时间范围
        print("尝试方法2: 指定时间范围提取...")
        cmd2 = [
            'ffmpeg',
            '-err_detect', 'ignore_err',
            '-i', input_path,
            '-ss', '0',  # 从开始
            '-t', '10',  # 提取10秒
            '-vsync', '0',
            '-q:v', '2',
            output_pattern,
            '-y'
        ]
        
        result2 = subprocess.run(cmd2, capture_output=True, timeout=60)
        extracted = list(output_path.glob("frame_*.jpg"))
        if extracted:
            print(f"✅ 方法2成功提取 {len(extracted)} 帧")
            return [str(f) for f in sorted(extracted)]
        
        return []
        
    except Exception as e:
        print(f"⚠️  ffmpeg提取失败: {e}")
        return []


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fix_video_and_extract.py <video_path> [output_dir]")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted_frames"
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("修复并提取视频帧")
    print("=" * 60)
    print(f"视频文件: {video_path}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)
    print()
    
    # 方法1: 尝试修复
    repaired_path = str(Path(video_path).with_suffix('.repaired.mp4'))
    if try_ffmpeg_repair(video_path, repaired_path):
        print(f"✅ 修复后的视频: {repaired_path}")
        print("   可以使用修复后的视频进行后续处理")
        return 0
    
    # 方法2: 直接提取帧
    print()
    print("尝试直接从损坏的视频中提取帧...")
    extracted_frames = extract_with_ffmpeg(video_path, output_dir, num_frames=20)
    
    if extracted_frames:
        print()
        print("=" * 60)
        print(f"✅ 成功提取 {len(extracted_frames)} 帧")
        print(f"输出目录: {output_dir}")
        print("=" * 60)
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ 无法从损坏的视频中提取帧")
        print()
        print("建议:")
        print("1. 安装ffmpeg: sudo apt install ffmpeg")
        print("2. 如果视频是在录制过程中断的，可能需要重新录制")
        print("3. 或者使用实时检测生成新的结果图")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())



