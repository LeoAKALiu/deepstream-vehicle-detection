#!/usr/bin/env python3
"""
Orbbec深度相机集成模块
用于获取bbox底边中点的真实深度
"""

import numpy as np
import threading
import time

try:
    import pyorbbecsdk as ob
    ORBBEC_AVAILABLE = True
except ImportError:
    ORBBEC_AVAILABLE = False
    print("⚠ pyorbbecsdk未安装，深度功能不可用")


class OrbbecDepthCamera:
    """Orbbec深度相机管理类"""
    
    def __init__(self, invalid_min=0, invalid_max=65535, prefer_uncompressed_format=True):
        """
        初始化Orbbec相机
        
        Args:
            invalid_min: 无效深度最小值（毫米，通常为0）
            invalid_max: 无效深度最大值（毫米，通常为65535）
            prefer_uncompressed_format: 是否优先选择未压缩格式（RGB/BGR而非MJPEG）
                                       True: 优先RGB/BGR（图像质量更好，适合LPR识别）
                                       False: 只考虑分辨率（可能选择MJPEG压缩格式）
        """
        if not ORBBEC_AVAILABLE:
            raise ImportError("pyorbbecsdk未安装")
        
        self.pipeline = None
        self.depth_frame = None
        self.color_frame = None
        self.depth_lock = threading.Lock()
        self.running = False
        self.capture_thread = None
        self.depth_scale = 1.0
        self.invalid_min = invalid_min
        self.invalid_max = invalid_max
        self.align_mode = None  # 记录对齐模式
        self.prefer_uncompressed_format = prefer_uncompressed_format  # 格式偏好
        
    def _select_highest_resolution_profile(self, profile_list, sensor_type_name="流", prefer_uncompressed=True):
        """
        从流配置列表中选择最高分辨率的配置
        
        Args:
            profile_list: 流配置列表
            sensor_type_name: 传感器类型名称（用于日志）
            prefer_uncompressed: 是否优先选择未压缩格式（RGB/BGR而非MJPEG）
        
        Returns:
            最高分辨率的VideoStreamProfile，如果失败返回None
        """
        if not profile_list or profile_list.get_count() == 0:
            return None
        
        best_profile = None
        best_resolution = 0  # width * height
        best_fps = 0
        best_format_score = 0  # 格式优先级分数（未压缩格式更高）
        
        print(f"  📋 可用{sensor_type_name}配置:")
        for i in range(profile_list.get_count()):
            try:
                # 使用get_stream_profile_by_index（正确的API方法名）
                profile = profile_list.get_stream_profile_by_index(i)
                if not profile.is_video_stream_profile():
                    continue
                
                video_profile = profile.as_video_stream_profile()
                width = video_profile.get_width()
                height = video_profile.get_height()
                fps = video_profile.get_fps()
                resolution = width * height
                format_type = video_profile.get_format()
                
                # 格式优先级分数：RGB/BGR > 其他未压缩 > MJPEG
                format_score = 0
                format_name = "未知"
                if format_type == ob.OBFormat.RGB:
                    format_score = 3
                    format_name = "RGB(未压缩)"
                elif format_type == ob.OBFormat.BGR:
                    format_score = 3
                    format_name = "BGR(未压缩)"
                elif format_type == ob.OBFormat.MJPG:
                    format_score = 1
                    format_name = "MJPEG(压缩)"
                else:
                    format_score = 2  # 其他格式，中等优先级
                    format_name = f"格式{format_type}"
                
                print(f"    [{i}] {width}x{height} @ {fps}fps | {format_name} | 分辨率: {resolution} 像素")
                
                # 选择策略：
                # 1. 如果prefer_uncompressed=True，优先选择未压缩格式
                # 2. 格式相同时，选择最高分辨率
                # 3. 格式和分辨率都相同时，选择更高帧率
                should_select = False
                if prefer_uncompressed:
                    # 优先格式分数，然后分辨率，最后帧率
                    if format_score > best_format_score:
                        should_select = True
                    elif format_score == best_format_score:
                        if resolution > best_resolution:
                            should_select = True
                        elif resolution == best_resolution and fps > best_fps:
                            should_select = True
                else:
                    # 只考虑分辨率和帧率
                    if resolution > best_resolution or (resolution == best_resolution and fps > best_fps):
                        should_select = True
                
                if should_select:
                    best_profile = profile
                    best_resolution = resolution
                    best_fps = fps
                    best_format_score = format_score
            except Exception as e:
                print(f"    ⚠ 无法读取配置 [{i}]: {e}")
                continue
        
        if best_profile:
            video_profile = best_profile.as_video_stream_profile()
            format_type = video_profile.get_format()
            format_name = "RGB" if format_type == ob.OBFormat.RGB else \
                         "BGR" if format_type == ob.OBFormat.BGR else \
                         "MJPEG" if format_type == ob.OBFormat.MJPG else f"格式{format_type}"
            print(f"  ✅ 选择配置: {video_profile.get_width()}x{video_profile.get_height()} @ {video_profile.get_fps()}fps | {format_name}")
        
        return best_profile
    
    def start(self):
        """启动相机（使用最高分辨率配置）"""
        try:
            # 创建Pipeline
            self.pipeline = ob.Pipeline()
            
            # 配置流
            config = ob.Config()
            
            # 启用深度流（选择最高分辨率）
            depth_profile_list = self.pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
            if depth_profile_list:
                depth_profile = self._select_highest_resolution_profile(depth_profile_list, "深度流")
                if depth_profile:
                    config.enable_stream(depth_profile)
                    video_profile = depth_profile.as_video_stream_profile()
                    print(f"✓ 深度流已启用: {video_profile.get_width()}x{video_profile.get_height()} @{video_profile.get_fps()}fps")
                else:
                    # 回退到默认配置
                    depth_profile = depth_profile_list.get_default_video_stream_profile()
                    config.enable_stream(depth_profile)
                    print(f"✓ 深度流（默认）: {depth_profile.get_width()}x{depth_profile.get_height()} @{depth_profile.get_fps()}fps")
            
            # 启用彩色流（优先选择未压缩格式RGB/BGR而非MJPEG，用于获得更高图像质量）
            color_profile_list = self.pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
            if color_profile_list:
                # 使用配置的格式偏好（优先RGB/BGR未压缩格式，图像质量更好）
                color_profile = self._select_highest_resolution_profile(
                    color_profile_list, 
                    "彩色流",
                    prefer_uncompressed=self.prefer_uncompressed_format
                )
                if color_profile:
                    config.enable_stream(color_profile)
                    video_profile = color_profile.as_video_stream_profile()
                    format_type = video_profile.get_format()
                    format_name = "RGB(未压缩)" if format_type == ob.OBFormat.RGB else \
                                 "BGR(未压缩)" if format_type == ob.OBFormat.BGR else \
                                 "MJPEG(压缩)" if format_type == ob.OBFormat.MJPG else f"格式{format_type}"
                    print(f"✓ 彩色流已启用: {video_profile.get_width()}x{video_profile.get_height()} @{video_profile.get_fps()}fps | {format_name}")
                else:
                    # 回退到默认配置
                    color_profile = color_profile_list.get_default_video_stream_profile()
                    config.enable_stream(color_profile)
                    print(f"✓ 彩色流（默认）: {color_profile.get_width()}x{color_profile.get_height()} @{color_profile.get_fps()}fps")
            
            # 尝试启用D2C硬件对齐（如果支持），否则使用软件对齐
            align_set = False
            try:
                # 检查是否支持D2C硬件对齐
                if hasattr(ob, 'OBAlignMode') and hasattr(ob.OBAlignMode, 'HW_MODE'):
                    # 尝试使用硬件对齐（性能更好）
                    try:
                        config.set_align_mode(ob.OBAlignMode.HW_MODE)
                        self.align_mode = 'HW_MODE'
                        print("✓ 尝试使用D2C硬件对齐模式")
                        align_set = True
                    except Exception as hw_e:
                        # 硬件对齐失败，回退到软件对齐
                        print(f"  ⚠ 硬件对齐失败: {hw_e}")
                        align_set = False
                
                # 如果硬件对齐失败或不可用，使用软件对齐
                if not align_set:
                    config.set_align_mode(ob.OBAlignMode.SW_MODE)
                    self.align_mode = 'SW_MODE'
                    print("✓ 使用D2C软件对齐模式")
                    align_set = True
                    
            except Exception as e:
                # 如果设置对齐模式失败，尝试不使用对齐
                print(f"⚠ 设置对齐模式失败: {e}，尝试不使用对齐")
                self.align_mode = 'NONE'
            
            # 启动Pipeline（如果对齐设置失败，这里可能会报错，需要捕获）
            try:
                self.pipeline.start(config)
            except Exception as start_e:
                # 如果启动失败且是因为对齐模式，尝试不使用对齐
                if 'd2c' in str(start_e).lower() or 'align' in str(start_e).lower() or 'hardware' in str(start_e).lower():
                    print(f"  ⚠ Pipeline启动失败（可能因对齐模式）: {start_e}")
                    print("  🔄 尝试不使用对齐模式重新启动...")
                    # 重新创建config，不设置对齐模式（仍使用最高分辨率）
                    config = ob.Config()
                    depth_profile_list = self.pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
                    if depth_profile_list:
                        depth_profile = self._select_highest_resolution_profile(depth_profile_list, "深度流")
                        if depth_profile:
                            config.enable_stream(depth_profile)
                        else:
                            depth_profile = depth_profile_list.get_default_video_stream_profile()
                            config.enable_stream(depth_profile)
                    color_profile_list = self.pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
                    if color_profile_list:
                        # 回退模式也使用配置的格式偏好
                        color_profile = self._select_highest_resolution_profile(
                            color_profile_list, 
                            "彩色流",
                            prefer_uncompressed=self.prefer_uncompressed_format
                        )
                        if color_profile:
                            config.enable_stream(color_profile)
                        else:
                            color_profile = color_profile_list.get_default_video_stream_profile()
                            config.enable_stream(color_profile)
                    # 不设置对齐模式
                    self.align_mode = 'NONE'
                    self.pipeline.start(config)
                    print("✓ 使用无对齐模式启动成功")
                else:
                    raise  # 其他错误直接抛出
            
            # 尝试设置相机参数（曝光、增益等，如果支持）
            try:
                device = self.pipeline.get_device()
                sensor_list = device.get_sensor_list()
                
                # 尝试设置彩色传感器参数
                for i in range(sensor_list.get_count()):
                    sensor = sensor_list.get_sensor(i)
                    sensor_type = sensor.get_type()
                    
                    if sensor_type == ob.OBSensorType.COLOR_SENSOR:
                        # 尝试启用自动曝光（如果支持）
                        try:
                            if hasattr(sensor, 'set_bool_property'):
                                # 启用自动曝光
                                sensor.set_bool_property(ob.OBPropertyID.COLOR_AUTO_EXPOSURE, True)
                                print("  ✓ 已启用彩色自动曝光")
                        except Exception as e:
                            pass  # 如果不支持则忽略
                        
                        # 尝试设置曝光范围（如果支持）
                        try:
                            if hasattr(sensor, 'get_int_property_range'):
                                exp_range = sensor.get_int_property_range(ob.OBPropertyID.COLOR_EXPOSURE)
                                if exp_range:
                                    # 使用最大曝光值（更宽容度）
                                    max_exp = exp_range[1]  # (min, max, step)
                                    sensor.set_int_property(ob.OBPropertyID.COLOR_EXPOSURE, max_exp)
                                    print(f"  ✓ 已设置彩色曝光: {max_exp}")
                        except Exception as e:
                            pass  # 如果不支持则忽略
                        
                        # 尝试设置增益（如果支持）
                        try:
                            if hasattr(sensor, 'get_int_property_range'):
                                gain_range = sensor.get_int_property_range(ob.OBPropertyID.COLOR_GAIN)
                                if gain_range:
                                    # 使用中等增益（平衡噪声和灵敏度）
                                    mid_gain = (gain_range[0] + gain_range[1]) // 2
                                    sensor.set_int_property(ob.OBPropertyID.COLOR_GAIN, mid_gain)
                                    print(f"  ✓ 已设置彩色增益: {mid_gain}")
                        except Exception as e:
                            pass  # 如果不支持则忽略
            except Exception as e:
                # 参数设置失败不影响相机使用
                pass
            
            # 启动后台采集线程
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            print("✓ Orbbec相机启动成功（已使用最高分辨率配置）")
            return True
            
        except Exception as e:
            print(f"✗ Orbbec相机启动失败: {e}")
            return False
    
    def stop(self):
        """停止相机"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        if self.pipeline:
            self.pipeline.stop()
        print("✓ Orbbec相机已停止")
    
    def _capture_loop(self):
        """后台采集循环"""
        # 等待相机稳定
        for _ in range(10):
            self.pipeline.wait_for_frames(100)
        
        while self.running:
            try:
                frames = self.pipeline.wait_for_frames(100)
                if frames is None:
                    continue
                
                # 获取深度帧
                depth_frame = frames.get_depth_frame()
                if depth_frame:
                    with self.depth_lock:
                        self.depth_frame = depth_frame
                        self.depth_scale = depth_frame.get_depth_scale()
                
                # 获取彩色帧
                color_frame = frames.get_color_frame()
                if color_frame:
                    with self.depth_lock:
                        self.color_frame = color_frame
                
            except Exception as e:
                if self.running:
                    print(f"⚠ 采集错误: {e}")
                time.sleep(0.1)
    
    def get_color_frame(self):
        """
        获取最新的彩色帧（RGB格式）
        
        Returns:
            numpy数组 (H, W, 3) RGB格式，如果无效返回None
        """
        with self.depth_lock:
            if self.color_frame is None:
                return None
            
            try:
                width = self.color_frame.get_width()
                height = self.color_frame.get_height()
                format_type = self.color_frame.get_format()
                
                # 获取数据
                color_data = np.frombuffer(self.color_frame.get_data(), dtype=np.uint8)
                
                # 根据格式处理
                if format_type == ob.OBFormat.MJPG:
                    # MJPEG压缩格式，需要解码
                    import cv2
                    image = cv2.imdecode(color_data, cv2.IMREAD_COLOR)
                    if image is not None:
                        # BGR -> RGB
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        return image
                elif format_type == ob.OBFormat.RGB:
                    # RGB格式
                    return color_data.reshape((height, width, 3))
                elif format_type == ob.OBFormat.BGR:
                    # BGR格式
                    import cv2
                    image = color_data.reshape((height, width, 3))
                    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:
                    # 尝试作为RGB处理
                    return color_data.reshape((height, width, 3))
                    
            except Exception as e:
                print(f"⚠ 获取彩色帧失败: {e}")
                return None
    
    def get_depth_at_point(self, x, y):
        """
        获取指定点的深度
        
        Args:
            x: 图像x坐标（像素）
            y: 图像y坐标（像素）
        
        Returns:
            depth: 深度值（米），如果无效返回None
        """
        with self.depth_lock:
            if self.depth_frame is None:
                return None
            
            try:
                width = self.depth_frame.get_width()
                height = self.depth_frame.get_height()
                
                # 边界检查
                x = int(np.clip(x, 0, width - 1))
                y = int(np.clip(y, 0, height - 1))
                
                # 获取深度数据
                depth_data = np.frombuffer(self.depth_frame.get_data(), dtype=np.uint16)
                depth_image = depth_data.reshape((height, width))
                
                # 读取深度值
                depth_mm = depth_image[y, x] * self.depth_scale
                
                # 无效深度过滤
                if depth_mm <= 0 or depth_mm > 10000:  # 0-10m有效范围
                    return None
                
                # 转换为米
                depth_m = depth_mm / 1000.0
                return depth_m
                
            except Exception as e:
                print(f"⚠ 获取深度失败: {e}")
                return None
    
    def get_depth_at_bbox_bottom(self, bbox):
        """
        获取bbox底边中点的深度
        
        Args:
            bbox: [x1, y1, x2, y2]
        
        Returns:
            depth: 深度值（米），如果无效返回None
        """
        x1, y1, x2, y2 = bbox
        
        # bbox底边中点
        bottom_center_x = int((x1 + x2) / 2)
        bottom_center_y = int(y2)
        
        return self.get_depth_at_point(bottom_center_x, bottom_center_y)
    
    def get_depth_region_stats(self, bbox, method='median'):
        """
        获取bbox区域的深度统计值（比单点更稳定）
        
        Args:
            bbox: [x1, y1, x2, y2]
            method: 'mean', 'median', 'min'
        
        Returns:
            tuple: (depth, confidence) 或 (None, 0.0)
                - depth: 深度值（米），如果无效返回None
                - confidence: 有效像素比例（0.0-1.0）
        """
        x1, y1, x2, y2 = bbox
        
        with self.depth_lock:
            if self.depth_frame is None:
                return None
            
            try:
                width = self.depth_frame.get_width()
                height = self.depth_frame.get_height()
                
                # 边界检查
                x1 = int(np.clip(x1, 0, width - 1))
                y1 = int(np.clip(y1, 0, height - 1))
                x2 = int(np.clip(x2, 0, width - 1))
                y2 = int(np.clip(y2, 0, height - 1))
                
                if x2 <= x1 or y2 <= y1:
                    return None, 0.0
                
                # 获取深度数据
                depth_data = np.frombuffer(self.depth_frame.get_data(), dtype=np.uint16)
                depth_image = depth_data.reshape((height, width))
                
                # 提取区域
                region = depth_image[y1:y2, x1:x2] * self.depth_scale
                
                # 过滤无效值（使用配置的invalid_min和invalid_max）
                valid_depths = region[(region > self.invalid_min) & (region < self.invalid_max)]
                
                if len(valid_depths) == 0:
                    return None, 0.0
                
                # 计算有效像素比例（用于置信度）
                total_pixels = region.size
                valid_pixel_ratio = len(valid_depths) / total_pixels if total_pixels > 0 else 0.0
                
                # 计算统计值
                if method == 'mean':
                    depth_mm = np.mean(valid_depths)
                elif method == 'median':
                    depth_mm = np.median(valid_depths)
                elif method == 'min':
                    depth_mm = np.min(valid_depths)
                else:
                    depth_mm = np.median(valid_depths)  # 默认中位数
                
                # 转换为米
                depth_m = depth_mm / 1000.0
                return depth_m, valid_pixel_ratio
                
            except Exception as e:
                return None, 0.0
    
    def get_average_depth_at_bbox_bottom(self, bbox, radius=5):
        """
        获取bbox底边中点周围区域的平均深度（更稳定）
        
        Args:
            bbox: [x1, y1, x2, y2]
            radius: 采样半径
        
        Returns:
            depth: 平均深度值（米），如果无效返回None
        """
        x1, y1, x2, y2 = bbox
        
        # bbox底边中点
        center_x = int((x1 + x2) / 2)
        center_y = int(y2)
        
        with self.depth_lock:
            if self.depth_frame is None:
                return None
            
            try:
                width = self.depth_frame.get_width()
                height = self.depth_frame.get_height()
                
                # 获取深度数据
                depth_data = np.frombuffer(self.depth_frame.get_data(), dtype=np.uint16)
                depth_image = depth_data.reshape((height, width))
                
                # 采样区域
                y_min = max(0, center_y - radius)
                y_max = min(height, center_y + radius + 1)
                x_min = max(0, center_x - radius)
                x_max = min(width, center_x + radius + 1)
                
                # 提取区域
                region = depth_image[y_min:y_max, x_min:x_max] * self.depth_scale
                
                # 过滤无效值（使用配置的invalid_min和invalid_max）
                valid_depths = region[(region > self.invalid_min) & (region < self.invalid_max)]
                
                if len(valid_depths) == 0:
                    return None
                
                # 计算中位数（比平均值更稳定）
                depth_mm = np.median(valid_depths)
                depth_m = depth_mm / 1000.0
                
                return depth_m
                
            except Exception as e:
                print(f"⚠ 获取平均深度失败: {e}")
                return None
    
    def get_depth_at_bbox_bottom_robust(self, bbox, window_size=5, outlier_threshold=2.0):
        """
        获取bbox底边中点的鲁棒深度（小窗口中位数+离群值过滤）
        
        Args:
            bbox: [x1, y1, x2, y2]
            window_size: 采样窗口大小（像素，默认5，即5×5窗口）
            outlier_threshold: 离群值阈值（标准差倍数，默认2.0）
        
        Returns:
            tuple: (depth, confidence) 或 (None, 0.0)
                - depth: 深度值（米），如果无效返回None
                - confidence: 有效像素比例（0.0-1.0）
        """
        x1, y1, x2, y2 = bbox
        
        # bbox底边中点
        center_x = int((x1 + x2) / 2)
        center_y = int(y2)
        
        with self.depth_lock:
            if self.depth_frame is None:
                return None, 0.0
            
            try:
                width = self.depth_frame.get_width()
                height = self.depth_frame.get_height()
                
                # 边界检查
                center_x = int(np.clip(center_x, 0, width - 1))
                center_y = int(np.clip(center_y, 0, height - 1))
                
                # 获取深度数据
                depth_data = np.frombuffer(self.depth_frame.get_data(), dtype=np.uint16)
                depth_image = depth_data.reshape((height, width))
                
                # 采样窗口
                half_window = window_size // 2
                y_min = max(0, center_y - half_window)
                y_max = min(height, center_y + half_window + 1)
                x_min = max(0, center_x - half_window)
                x_max = min(width, center_x + half_window + 1)
                
                # 提取窗口区域
                window = depth_image[y_min:y_max, x_min:x_max] * self.depth_scale
                total_pixels = window.size
                
                # 过滤无效值
                valid_mask = (window > self.invalid_min) & (window < self.invalid_max)
                valid_depths = window[valid_mask]
                valid_pixel_ratio = len(valid_depths) / total_pixels if total_pixels > 0 else 0.0
                
                if len(valid_depths) == 0:
                    return None, 0.0
                
                # 离群值过滤（使用IQR方法）
                if len(valid_depths) > 4:  # 需要足够的数据点
                    q1 = np.percentile(valid_depths, 25)
                    q3 = np.percentile(valid_depths, 75)
                    iqr = q3 - q1
                    lower_bound = q1 - outlier_threshold * iqr
                    upper_bound = q3 + outlier_threshold * iqr
                    
                    # 过滤离群值
                    filtered_depths = valid_depths[
                        (valid_depths >= lower_bound) & (valid_depths <= upper_bound)
                    ]
                    
                    if len(filtered_depths) > 0:
                        # 使用中位数（更抗噪）
                        depth_mm = np.median(filtered_depths)
                    else:
                        # 如果过滤后没有数据，使用原始中位数
                        depth_mm = np.median(valid_depths)
                else:
                    # 数据点太少，直接使用中位数
                    depth_mm = np.median(valid_depths)
                
                # 转换为米
                depth_m = depth_mm / 1000.0
                
                return depth_m, valid_pixel_ratio
                
            except Exception as e:
                print(f"⚠ 获取鲁棒深度失败: {e}")
                return None, 0.0


# 使用示例
if __name__ == '__main__':
    if not ORBBEC_AVAILABLE:
        print("请安装pyorbbecsdk: pip3 install pyorbbecsdk --user")
        exit(1)
    
    print("初始化Orbbec相机...")
    camera = OrbbecDepthCamera()
    
    if not camera.start():
        print("相机启动失败")
        exit(1)
    
    print("等待相机稳定...")
    time.sleep(2)
    
    print("\n测试深度读取（10秒）...")
    start_time = time.time()
    
    try:
        while time.time() - start_time < 10:
            # 测试中心点
            depth = camera.get_depth_at_point(320, 240)
            if depth:
                print(f"\r中心点深度: {depth:.3f}m", end='', flush=True)
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n用户中断")
    
    finally:
        camera.stop()
        print("\n\n测试完成")

