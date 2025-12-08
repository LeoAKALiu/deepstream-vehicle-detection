#!/usr/bin/env python3
"""
测试Orbbec Gemini 335L相机
"""

import sys
import numpy as np
import cv2

try:
    import pyorbbecsdk as ob
    print("✓ pyorbbecsdk导入成功")
except ImportError as e:
    print(f"✗ 无法导入pyorbbecsdk: {e}")
    print("请安装: pip3 install pyorbbecsdk --user")
    sys.exit(1)


def main():
    print("="*70)
    print("Orbbec Gemini 335L 相机测试")
    print("="*70)
    
    # 创建Pipeline
    print("\n【1. 初始化相机】")
    try:
        pipeline = ob.Pipeline()
        print("  ✓ Pipeline创建成功")
    except Exception as e:
        print(f"  ✗ 创建Pipeline失败: {e}")
        print("\n可能的原因:")
        print("  1. 相机未连接")
        print("  2. USB权限问题（运行: sudo bash 配置Orbbec权限.sh）")
        print("  3. 其他程序占用相机")
        return
    
    # 获取设备信息
    try:
        device = pipeline.get_device()
        device_info = device.get_device_info()
        print(f"  设备名称: {device_info.get_name()}")
        print(f"  PID: {device_info.get_pid()}")
        print(f"  VID: {device_info.get_vid()}")
        print(f"  UID: {device_info.get_uid()}")
        print(f"  序列号: {device_info.get_serial_number()}")
        print(f"  固件版本: {device_info.get_firmware_version()}")
    except Exception as e:
        print(f"  ⚠ 获取设备信息失败: {e}")
    
    # 配置流
    print("\n【2. 配置数据流】")
    try:
        config = ob.Config()
        
        # 启用彩色流
        try:
            color_profile_list = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
            if color_profile_list:
                color_profile = color_profile_list.get_default_video_stream_profile()
                print(f"  彩色流: {color_profile.get_width()}x{color_profile.get_height()} @{color_profile.get_fps()}fps")
                config.enable_stream(color_profile)
        except Exception as e:
            print(f"  ⚠ 彩色流配置失败: {e}")
        
        # 启用深度流
        try:
            depth_profile_list = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
            if depth_profile_list:
                depth_profile = depth_profile_list.get_default_video_stream_profile()
                print(f"  深度流: {depth_profile.get_width()}x{depth_profile.get_height()} @{depth_profile.get_fps()}fps")
                config.enable_stream(depth_profile)
        except Exception as e:
            print(f"  ⚠ 深度流配置失败: {e}")
        
        # 启用对齐（使用软件模式，更兼容）
        config.set_align_mode(ob.OBAlignMode.SW_MODE)
        print("  ✓ 深度对齐到彩色（软件模式）")
        
        # 启动Pipeline
        pipeline.start(config)
        print("  ✓ 相机启动成功")
        
    except Exception as e:
        print(f"  ✗ 配置失败: {e}")
        pipeline.stop()
        return
    
    # 采集帧
    print("\n【3. 采集测试帧】")
    color_image = None
    depth_image = None
    depth_scale = 1.0
    
    try:
        # 等待几帧让相机稳定
        print("  等待相机稳定...")
        for i in range(5):
            frames = pipeline.wait_for_frames(100)
        
        # 尝试多次获取有效的RGB和深度帧
        print("  开始采集RGB和深度帧...")
        for attempt in range(10):
            frames = pipeline.wait_for_frames(1000)
            if frames is None:
                print(f"    尝试 {attempt+1}/10: 未获取到帧")
                continue
            
            # 尝试获取彩色帧
            if color_image is None:
                color_frame = frames.get_color_frame()
                if color_frame:
                    width = color_frame.get_width()
                    height = color_frame.get_height()
                    format_type = color_frame.get_format()
                    data_size = color_frame.get_data_size()
                    print(f"    尝试 {attempt+1}/10: ✓ 彩色帧 {width}x{height}, 格式={format_type}, 大小={data_size}")
                    
                    # 转换为numpy数组
                    color_data = np.frombuffer(color_frame.get_data(), dtype=np.uint8)
                    
                    # 根据格式处理
                    expected_size = width * height * 3
                    if data_size == expected_size:
                        # RGB或BGR格式
                        color_image = color_data.reshape((height, width, 3))
                    elif data_size == width * height * 2:
                        # YUYV或类似格式，需要转换
                        print(f"      需要格式转换...")
                        yuyv = color_data.reshape((height, width, 2))
                        color_image = cv2.cvtColor(yuyv, cv2.COLOR_YUV2RGB_YUYV)
                    else:
                        # 可能是MJPEG或其他压缩格式
                        print(f"      检测到压缩格式，尝试解码...")
                        color_image = cv2.imdecode(color_data, cv2.IMREAD_COLOR)
                        if color_image is not None:
                            color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            
            # 尝试获取深度帧
            if depth_image is None:
                depth_frame = frames.get_depth_frame()
                if depth_frame:
                    width = depth_frame.get_width()
                    height = depth_frame.get_height()
                    depth_scale = depth_frame.get_depth_scale()
                    print(f"    尝试 {attempt+1}/10: ✓ 深度帧 {width}x{height}")
                    
                    # 转换为numpy数组
                    depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
                    depth_image = depth_data.reshape((height, width))
            
            # 如果都获取到了就退出
            if color_image is not None and depth_image is not None:
                print(f"\n  ✓ 成功获取RGB和深度帧！")
                break
        
        # 保存RGB图像
        if color_image is not None:
            rgb_path = "/home/liubo/Download/orbbec_rgb_test.jpg"
            cv2.imwrite(rgb_path, cv2.cvtColor(color_image, cv2.COLOR_RGB2BGR))
            print(f"\n【RGB图像】")
            print(f"  ✓ 图像shape: {color_image.shape}")
            print(f"  ✓ 已保存: {rgb_path}")
        else:
            print(f"\n【RGB图像】")
            print(f"  ✗ 未能获取彩色帧")
        
        # 保存深度图
        if depth_image is not None:
            print(f"\n【深度图像】")
            print(f"  ✓ 图像shape: {depth_image.shape}")
            print(f"  ✓ 深度范围: {depth_image.min()} - {depth_image.max()}")
            
            # 深度统计
            cy, cx = depth_image.shape[0] // 2, depth_image.shape[1] // 2
            center_depth = depth_image[cy, cx] * depth_scale
            print(f"  ✓ 中心点深度: {center_depth:.2f} mm ({center_depth/1000:.2f} m)")
            
            # 保存原始深度数据（16位PNG）
            depth_raw_path = "/home/liubo/Download/orbbec_depth_raw.png"
            cv2.imwrite(depth_raw_path, depth_image)
            print(f"  ✓ 原始深度图已保存: {depth_raw_path}")
            
            # 保存可视化深度图（伪彩色JPG）
            depth_normalized = np.zeros_like(depth_image, dtype=np.uint8)
            # 排除无效深度值（0和65535）
            valid_mask = (depth_image > 0) & (depth_image < 65535)
            if valid_mask.any():
                depth_min = depth_image[valid_mask].min()
                depth_max = depth_image[valid_mask].max()
                print(f"  ✓ 有效深度范围: {depth_min} - {depth_max} mm")
                
                depth_normalized[valid_mask] = np.clip(
                    255 * (depth_image[valid_mask] - depth_min) / (depth_max - depth_min + 1e-6), 
                    0, 255
                ).astype(np.uint8)
            
            depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
            depth_vis_path = "/home/liubo/Download/orbbec_depth_colormap.jpg"
            cv2.imwrite(depth_vis_path, depth_colormap)
            print(f"  ✓ 可视化深度图已保存: {depth_vis_path}")
        else:
            print(f"\n【深度图像】")
            print(f"  ✗ 未能获取深度帧")
        
        # 总结
        print("\n【测试结果】")
        if color_image is not None and depth_image is not None:
            print("  ✓ 相机工作正常！")
            print("  ✓ RGB和深度数据均已保存")
        elif color_image is not None or depth_image is not None:
            print("  ⚠ 相机部分功能正常")
        else:
            print("  ✗ 相机采集失败")
        
    except Exception as e:
        print(f"  ✗ 采集失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        pipeline.stop()
        print("\n【4. 相机已停止】")
    
    print("\n" + "="*70)
    print("测试完成！")
    print("="*70)


if __name__ == '__main__':
    main()
