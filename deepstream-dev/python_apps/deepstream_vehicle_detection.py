#!/usr/bin/env python3
"""
DeepStream车辆检测系统 - 开发版本
- GPU加速检测（TensorRT）
- NvDCF目标跟踪
- HyperLPR车牌识别
- Orbbec深度相机集成
- Cassia蓝牙信标集成
- 云端数据上传
"""

import sys
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import pyds
import numpy as np
import cv2
from collections import defaultdict
from typing import Optional, Tuple, Dict, List

# 尝试导入cupy用于GPU加速（可选）
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None

# 导入依赖模块
sys.path.insert(0, '/home/liubo/Download/deepstream-vehicle-detection/deepstream-dev/python_apps')
try:
    from orbbec_depth import OrbbecDepthCamera
    ORBBEC_AVAILABLE = True
except ImportError:
    ORBBEC_AVAILABLE = False
    print("⚠ Orbbec深度相机模块未找到")

try:
    from cassia_local_client import CassiaLocalClient
    CASSIA_AVAILABLE = True
except ImportError:
    CASSIA_AVAILABLE = False
    print("⚠ Cassia客户端模块未找到")

try:
    from beacon_filter import BeaconFilter
    BEACON_FILTER_AVAILABLE = True
except ImportError:
    BEACON_FILTER_AVAILABLE = False
    print("⚠ 信标过滤器模块未找到")

try:
    from hyperlpr3 import LicensePlateCN
    HYPERLPR_AVAILABLE = True
except ImportError:
    HYPERLPR_AVAILABLE = False
    print("⚠ HyperLPR未安装")

# 导入云端集成
sys.path.insert(0, '/home/liubo/Download/deepstream-vehicle-detection/deepstream-dev/jetson-client')
try:
    from main_integration import SentinelIntegration
    from detection_result import DetectionResult
    from config import CloudConfig
    CLOUD_AVAILABLE = True
except ImportError:
    CLOUD_AVAILABLE = False
    print("⚠ 云端集成模块未找到")


# 车辆类别
CONSTRUCTION_VEHICLES = {
    0: ('excavator', '挖掘机'),
    1: ('bulldozer', '推土机'),
    2: ('roller', '压路机'),
    3: ('loader', '装载机'),
    4: ('dump-truck', '自卸车'),
    5: ('concrete-mixer', '混凝土搅拌车'),
    6: ('pump-truck', '泵车'),
    7: ('crane', '起重机'),
}

CIVILIAN_VEHICLES = {
    8: ('truck', '卡车'),
    9: ('car', '轿车'),
}


class DeepStreamVehicleDetection:
    """DeepStream车辆检测应用 - 完整功能版本"""
    
    def __init__(self, source, config_path=None):
        """
        初始化DeepStream车辆检测应用
        
        Args:
            source: 输入源（视频文件路径或'camera'）
            config_path: 配置文件路径（可选）
        """
        self.source = source
        self.config_path = config_path or "/home/liubo/Download/deepstream-vehicle-detection/config.yaml"
        
        # 加载配置
        self.config = self._load_config()
        
        # 统计
        self.stats = {
            'construction': defaultdict(int),
            'civilian_plates': [],
            'frame_count': 0,
        }
        
        self.tracked_vehicles = {}  # {object_id: vehicle_info}
        self.seen_plates = set()
        
        # 性能监控
        self.enable_performance_monitor = self.config.get('performance', {}).get(
            'enable_performance_monitor', True
        )
        self.fps_update_interval = self.config.get('performance', {}).get(
            'fps_update_interval', 30  # 每30帧更新一次FPS
        )
        
        # FPS计算
        self.frame_times = []  # 存储最近N帧的时间戳
        self.max_frame_times = 30  # 最多保存30帧的时间用于FPS计算
        self.current_fps = 0.0
        self.last_fps_update_frame = 0
        self.start_time = time.time()
        self.last_frame_time = time.time()
        
        # 性能统计
        self.performance_stats = {
            'total_frames': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'max_processing_time': 0.0,
            'min_processing_time': float('inf'),
        }
        
        # HyperLPR
        self.lpr = None
        if HYPERLPR_AVAILABLE:
            try:
                self.lpr = LicensePlateCN(detect_level=1, max_num=5)
                self.logger.info("HyperLPR初始化成功")
            except Exception as e:
                self.logger.error(f"HyperLPR初始化失败: {e}")
        
        # Orbbec深度相机
        self.depth_camera = None
        if ORBBEC_AVAILABLE:
            try:
                self.depth_camera = OrbbecDepthCamera()
                if self.depth_camera.start():
                    self.logger.info("Orbbec深度相机初始化成功")
                else:
                    self.logger.warning("Orbbec深度相机启动失败")
                    self.depth_camera = None
            except Exception as e:
                self.logger.error(f"Orbbec深度相机初始化失败: {e}")
                self.depth_camera = None
        
        # Cassia蓝牙信标
        self.beacon_client = None
        self.beacon_filter = None
        if CASSIA_AVAILABLE and BEACON_FILTER_AVAILABLE:
            try:
                # 从配置文件读取Cassia IP
                cassia_ip = self.config.get('cassia', {}).get('ip', '192.168.3.26')
                self.beacon_client = CassiaLocalClient(cassia_ip)
                if self.beacon_client.start():
                    self.logger.info(f"Cassia客户端初始化成功 (IP: {cassia_ip})")
                    
                    # 初始化信标过滤器
                    beacon_whitelist_path = self.config.get('beacon_whitelist', {}).get(
                        'path', 
                        '/home/liubo/Download/deepstream-vehicle-detection/beacon_whitelist.yaml'
                    )
                    self.beacon_filter = BeaconFilter(beacon_whitelist_path)
                    self.logger.info("信标过滤器初始化成功")
                else:
                    self.logger.warning("Cassia客户端启动失败")
                    self.beacon_client = None
            except Exception as e:
                self.logger.error(f"Cassia客户端初始化失败: {e}")
                self.beacon_client = None
        
        # 云端集成
        self.cloud_integration = None
        if CLOUD_AVAILABLE:
            cloud_cfg = self.config.get('cloud', {})
            if cloud_cfg.get('enabled', False):
                try:
                    # 从配置文件读取云端配置
                    cloud_config = CloudConfig(
                        api_base_url=cloud_cfg.get('api_base_url', 'http://123.249.9.250:8000'),
                        api_key=cloud_cfg.get('api_key', '')
                    )
                    self.cloud_integration = SentinelIntegration(cloud_config)
                    self.logger.info("云端集成初始化成功")
                except Exception as e:
                    self.logger.error(f"云端集成初始化失败: {e}")
                    self.cloud_integration = None
            else:
                self.logger.info("云端集成已禁用（配置文件中enabled=false）")
        
        # GStreamer
        Gst.init(None)
        
        # 帧缓存（用于ROI提取）
        self.frame_cache = {}  # {frame_id: frame_data}
        self.max_cache_size = 10
        
        # 图像提取相关
        self.input_frame_cache = {}  # 缓存输入帧用于ROI提取
        self.frame_extraction_enabled = True  # 是否启用图像提取
        
        # GPU优化配置
        self.enable_gpu_roi_extraction = self.config.get('performance', {}).get(
            'enable_gpu_roi_extraction', True
        )  # 是否启用GPU ROI提取
        self.use_cpu_conversion = self.config.get('performance', {}).get(
            'use_cpu_conversion', False
        )  # 是否使用CPU转换（fallback选项）
        
        # 检查GPU可用性
        if self.enable_gpu_roi_extraction and not CUPY_AVAILABLE:
            self.logger.warning("cupy未安装，GPU ROI提取将不可用，回退到CPU模式")
            self.enable_gpu_roi_extraction = False
            self.use_cpu_conversion = True
        
        if self.enable_gpu_roi_extraction:
            self.logger.info("✓ GPU ROI提取已启用")
        else:
            self.logger.info("⚠ 使用CPU ROI提取模式")
        
        # 异步处理配置
        self.enable_async_processing = self.config.get('performance', {}).get(
            'enable_async_processing', True
        )  # 是否启用异步处理
        self.async_workers = self.config.get('performance', {}).get(
            'async_workers', 4
        )  # 异步处理线程数
        
        # 异步处理组件
        if self.enable_async_processing:
            self.executor = ThreadPoolExecutor(max_workers=self.async_workers, thread_name_prefix="ROI-Processor")
            self.roi_result_queue = queue.Queue(maxsize=100)  # ROI处理结果队列
            self.pending_rois = {}  # {object_id: Future} 跟踪待处理的ROI
            self.logger.info(f"✓ 异步处理已启用（{self.async_workers}个工作线程）")
        else:
            self.executor = None
            self.roi_result_queue = None
            self.pending_rois = {}
            self.logger.info("⚠ 使用同步处理模式")
        
        # Pipeline元素引用（在build_pipeline中设置）
        self.nvvidconv_cpu = None
    
    def _extract_frame_from_buffer(self, gst_buffer, frame_meta) -> Optional[np.ndarray]:
        """
        从缓存或buffer提取图像数据
        
        Args:
            gst_buffer: GStreamer buffer（当前未使用，从缓存获取）
            frame_meta: 帧元数据（用于获取帧ID）
            
        Returns:
            numpy数组表示的图像，如果失败返回None
        """
        if not self.frame_extraction_enabled:
            return None
        
        try:
            frame_id = frame_meta.frame_num
            
            # 从缓存获取图像
            if frame_id in self.input_frame_cache:
                return self.input_frame_cache[frame_id]
            
            # 如果缓存中没有，尝试从最近的帧获取（可能帧ID不匹配）
            if self.input_frame_cache:
                # 获取最接近的帧ID
                closest_frame_id = min(self.input_frame_cache.keys(), 
                                      key=lambda x: abs(x - frame_id))
                if abs(closest_frame_id - frame_id) <= 2:  # 允许2帧的误差
                    return self.input_frame_cache[closest_frame_id]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"图像提取错误: {e}")
            return None
    
    def _extract_roi_from_gpu(self, gst_buffer, frame_meta, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """
        从GPU内存直接提取ROI区域（GPU优化版本）
        
        注意：由于DeepStream的NvBufSurface在Python中直接访问较复杂，
        此方法尝试使用多种策略，如果都失败则返回None，由调用者回退到CPU方法。
        
        Args:
            gst_buffer: GStreamer buffer
            frame_meta: 帧元数据
            bbox: 边界框 (x1, y1, x2, y2)
            
        Returns:
            裁剪后的ROI图像（CPU numpy数组），如果失败返回None
        """
        if not self.enable_gpu_roi_extraction or not CUPY_AVAILABLE:
            return None
        
        try:
            # 获取图像尺寸
            width = frame_meta.source_frame_width
            height = frame_meta.source_frame_height
            
            # 计算ROI坐标
            x1, y1, x2, y2 = bbox
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(width, int(x2))
            y2 = min(height, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            # 方法1: 尝试从缓存的GPU帧中提取（如果之前已提取到GPU）
            # 这需要先有完整的GPU帧缓存机制
            
            # 方法2: 尝试使用GStreamer buffer map（如果buffer支持）
            # 注意：对于NvBufSurface，map可能返回CPU副本，但仍比每帧转换快
            success, map_info = gst_buffer.map(Gst.MapFlags.READ)
            if success:
                try:
                    # 获取caps以确定格式
                    # 注意：这里假设buffer已经可以map，可能是CPU副本
                    # 但至少避免了nvvidconv_cpu的额外转换步骤
                    frame_data = np.frombuffer(map_info.data, dtype=np.uint8)
                    
                    # 假设RGB格式（3通道）
                    channels = 3
                    expected_size = width * height * channels
                    
                    if len(frame_data) >= expected_size:
                        # 重塑为图像数组
                        frame = frame_data[:expected_size].reshape((height, width, channels))
                        
                        # 在GPU上执行ROI裁剪（如果数据量大，GPU裁剪更快）
                        if frame.size > 100000:  # 大于100KB，使用GPU加速
                            frame_gpu = cp.asarray(frame)
                            roi_gpu = frame_gpu[y1:y2, x1:x2]
                            roi = cp.asnumpy(roi_gpu)
                        else:
                            # 小图像直接在CPU上裁剪更快
                            roi = frame[y1:y2, x1:x2]
                        
                        return roi
                except Exception as e:
                    self.logger.debug(f"Buffer map提取失败: {e}")
                finally:
                    gst_buffer.unmap(map_info)
            
            # 如果所有方法都失败，返回None，由调用者回退到CPU方法
            return None
            
        except Exception as e:
            self.logger.debug(f"GPU ROI提取失败: {e}")
            return None
    
    def _crop_vehicle_roi(self, frame: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """
        裁剪车辆ROI区域（CPU版本，也支持GPU数组）
        
        Args:
            frame: 原始图像（numpy数组或cupy数组）
            bbox: 边界框 (x1, y1, x2, y2)
            
        Returns:
            裁剪后的ROI图像，如果失败返回None
        """
        if frame is None:
            return None
        
        # 检查是否是cupy数组（GPU数组）
        is_gpu_array = CUPY_AVAILABLE and hasattr(frame, '__cuda_array_interface__')
        
        x1, y1, x2, y2 = bbox
        
        # 获取图像尺寸
        if is_gpu_array:
            h, w = frame.shape[:2]
        else:
            h, w = frame.shape[:2]
        
        # 确保坐标在图像范围内
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(w, int(x2))
        y2 = min(h, int(y2))
        
        if x2 <= x1 or y2 <= y1:
            return None
        
        # 执行ROI裁剪
        if is_gpu_array:
            # GPU数组裁剪（在GPU上执行）
            roi_gpu = frame[y1:y2, x1:x2]
            # 转换为CPU numpy数组（仅在需要时）
            roi = cp.asnumpy(roi_gpu)
        else:
            # CPU数组裁剪
            roi = frame[y1:y2, x1:x2]
        
        return roi
    
    def _recognize_license_plate(self, roi: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        识别车牌号
        
        Args:
            roi: 车辆ROI图像
            
        Returns:
            (车牌号, 置信度) 元组，如果识别失败返回None
        """
        if not self.lpr or roi is None:
            return None
        
        try:
            # HyperLPR识别
            results = self.lpr(roi)
            if results and len(results) > 0:
                # 取置信度最高的结果
                best_result = max(results, key=lambda x: x.get('confidence', 0.0))
                plate_number = best_result.get('code', '')
                confidence = best_result.get('confidence', 0.0)
                if plate_number:
                    return (plate_number, confidence)
        except Exception as e:
            self.logger.warning(f"车牌识别错误: {e}")
        
        return None
    
    def _process_roi_async(self, object_id: int, roi: np.ndarray, vehicle_info: Dict) -> None:
        """
        异步处理ROI和车牌识别
        
        Args:
            object_id: 对象ID
            roi: ROI图像
            vehicle_info: 车辆信息字典（会被更新）
        """
        try:
            # 执行车牌识别（在后台线程中）
            plate_result = self._recognize_license_plate(roi)
            
            # 将结果放入队列
            result = {
                'object_id': object_id,
                'plate_result': plate_result,
                'vehicle_info': vehicle_info
            }
            
            # 非阻塞方式放入队列
            try:
                self.roi_result_queue.put_nowait(result)
            except queue.Full:
                self.logger.warning(f"ROI结果队列已满，丢弃结果（object_id: {object_id}）")
                
        except Exception as e:
            self.logger.error(f"异步ROI处理错误（object_id: {object_id}）: {e}")
    
    def _check_async_results(self) -> None:
        """
        检查并处理异步ROI识别结果（非阻塞）
        应该在probe函数中定期调用
        """
        if not self.enable_async_processing or not self.roi_result_queue:
            return
        
        # 处理所有可用的结果（非阻塞）
        processed_count = 0
        max_process = 10  # 每次最多处理10个结果，避免阻塞太久
        
        while processed_count < max_process:
            try:
                result = self.roi_result_queue.get_nowait()
                object_id = result['object_id']
                plate_result = result['plate_result']
                vehicle_info = result['vehicle_info']
                
                # 更新车辆信息
                if plate_result:
                    plate_number, plate_confidence = plate_result
                    vehicle_info['plate_number'] = plate_number
                    vehicle_info['status'] = 'identified'
                    self.logger.info(f"  [异步] 车牌识别完成 ID{object_id}: {plate_number} (置信度: {plate_confidence:.2f})")
                else:
                    vehicle_info['status'] = 'failed'
                    self.logger.debug(f"  [异步] 车牌识别失败 ID{object_id}")
                
                # 更新跟踪的车辆信息
                if object_id in self.tracked_vehicles:
                    self.tracked_vehicles[object_id].update(vehicle_info)
                
                # 保存到数据库和上传（如果需要）
                self._save_to_database(vehicle_info)
                self._upload_detection_result(vehicle_info)
                
                processed_count += 1
                
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"处理异步结果错误: {e}")
        
        # 清理已完成的Future
        completed_ids = []
        for obj_id, future in self.pending_rois.items():
            if future.done():
                completed_ids.append(obj_id)
        
        for obj_id in completed_ids:
            del self.pending_rois[obj_id]
    
    def _get_vehicle_distance(self, bbox: Tuple[float, float, float, float], frame_id: int) -> Optional[Tuple[float, float]]:
        """
        获取车辆距离
        
        Args:
            bbox: 边界框
            frame_id: 帧ID（用于同步深度数据）
            
        Returns:
            (距离, 置信度) 元组，如果失败返回None
        """
        if not self.depth_camera:
            return None
        
        try:
            # 计算bbox底边中点
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2
            cy = y2  # 底边中点
            
            # 获取深度
            distance, confidence = self.depth_camera.get_depth_at_bbox_bottom_robust(
                bbox, window_size=5, outlier_threshold=2.0
            )
            
            return (distance, confidence) if distance else None
        except Exception as e:
            self.logger.warning(f"距离测量错误: {e}")
            return None
    
    def _match_beacon_for_vehicle(self, bbox: Tuple[float, float, float, float], distance: Optional[float]) -> Optional[Dict]:
        """
        为车辆匹配信标
        
        Args:
            bbox: 边界框
            distance: 车辆距离（米）
            
        Returns:
            信标匹配信息，如果未匹配返回None
        """
        if not self.beacon_client or not self.beacon_filter:
            return None
        
        try:
            # 获取扫描到的信标
            all_beacons = self.beacon_client.get_beacons()
            if not all_beacons:
                return None
            
            # 使用过滤器匹配
            beacon_info = self.beacon_filter.get_best_match(
                all_beacons,
                camera_depth=distance,
                bbox=bbox
            )
            
            return beacon_info
        except Exception as e:
            self.logger.warning(f"信标匹配错误: {e}")
            return None
    
    def _save_to_database(self, vehicle_info: Dict) -> None:
        """
        保存检测结果到数据库
        
        Args:
            vehicle_info: 车辆信息字典
        """
        if not self.detection_db:
            return
        
        try:
            from datetime import datetime
            
            # 转换为数据库格式
            detection_dict = {
                'timestamp': datetime.now().isoformat(),
                'track_id': vehicle_info.get('track_id'),
                'vehicle_type': vehicle_info.get('vehicle_type', 'unknown'),
                'detected_class': vehicle_info.get('detected_class'),
                'status': vehicle_info.get('status'),
                'beacon_mac': vehicle_info.get('beacon_mac'),
                'plate_number': vehicle_info.get('plate_number'),
                'company': vehicle_info.get('company'),
                'distance': vehicle_info.get('distance'),
                'confidence': vehicle_info.get('confidence', 0.0),
                'bbox': vehicle_info.get('bbox'),
                'snapshot_path': vehicle_info.get('snapshot_path'),
                'metadata': vehicle_info.get('metadata', {})
            }
            
            self.detection_db.insert_detection(detection_dict)
        except Exception as e:
            self.logger.error(f"保存到数据库失败: {e}")
    
    def _upload_detection_result(self, vehicle_info: Dict) -> None:
        """
        上传检测结果到云端
        
        Args:
            vehicle_info: 车辆信息字典
        """
        if not self.cloud_integration:
            return
        
        try:
            from datetime import datetime
            
            # 创建DetectionResult对象
            detection_result = DetectionResult(
                vehicle_type=vehicle_info.get('vehicle_type', 'unknown'),
                detected_class=vehicle_info.get('detected_class'),
                status=vehicle_info.get('status'),
                confidence=vehicle_info.get('confidence', 0.0),
                plate_number=vehicle_info.get('plate_number'),
                timestamp=datetime.now(),
                image_path=vehicle_info.get('image_path'),
                bbox=vehicle_info.get('bbox'),
                track_id=vehicle_info.get('track_id'),
                distance=vehicle_info.get('distance'),
                is_registered=vehicle_info.get('is_registered'),
                beacon_mac=vehicle_info.get('beacon_mac'),
                company=vehicle_info.get('company'),
                environment_code=vehicle_info.get('environment_code'),
                metadata=vehicle_info.get('metadata')
            )
            
            # 添加到上传队列
            self.cloud_integration.on_detection(detection_result)
        except Exception as e:
            self.logger.error(f"上传检测结果错误: {e}")
    
    def build_pipeline(self):
        """构建GStreamer pipeline"""
        
        self.logger.info("构建DeepStream pipeline...")
        
        # 创建pipeline
        pipeline = Gst.Pipeline()
        
        if not pipeline:
            raise RuntimeError("无法创建pipeline")
        
        # 创建elements
        self.logger.debug("创建GStreamer elements...")
        
        # Source
        if self.source == 'camera':
            # V4L2相机源
            source = Gst.ElementFactory.make("v4l2src", "source")
            source.set_property('device', '/dev/video0')
        else:
            # 文件源
            source = Gst.ElementFactory.make("filesrc", "source")
            source.set_property('location', self.source)
        
        # Decoder
        if self.source == 'camera':
            decoder = Gst.ElementFactory.make("nvarguscamerasrc", "decoder")
        else:
            decoder = Gst.ElementFactory.make("nvurisrcbin", "decoder")
            decoder.set_property('uri', self.source)
        
        # Streammux
        streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
        streammux.set_property('batch-size', 1)
        streammux.set_property('width', 1920)
        streammux.set_property('height', 1080)
        
        # CPU转换元素（用于图像提取）- GPU优化：仅在需要时启用
        # 注意：这个元素将NvBufSurface转换为CPU可访问格式
        # 但会增加延迟，优先使用GPU直接访问方法
        # 只有在需要ROI提取且GPU方法不可用时才启用
        self.nvvidconv_cpu = None
        need_cpu_conversion = (
            self.lpr is not None and  # 需要车牌识别
            not self.enable_gpu_roi_extraction and  # GPU方法不可用
            self.use_cpu_conversion  # 配置允许使用CPU转换
        )
        
        if need_cpu_conversion:
            self.logger.info("使用CPU转换模式（性能较低，建议启用GPU优化）")
            self.nvvidconv_cpu = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv_cpu")
            if self.nvvidconv_cpu:
                # 设置为CPU内存类型（2 = CPU memory）
                try:
                    self.nvvidconv_cpu.set_property("nvbuf-memory-type", 2)
                except:
                    # 如果属性不存在，使用默认值
                    pass
        else:
            if self.lpr is not None:
                if self.enable_gpu_roi_extraction:
                    self.logger.info("✓ 使用GPU ROI提取（高性能模式）")
                else:
                    self.logger.warning("⚠ 车牌识别已禁用CPU转换，ROI提取可能不可用")
            else:
                self.logger.info("✓ 无需ROI提取，跳过CPU转换（最佳性能）")
        
        # Primary GIE (YOLOv11)
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        pgie.set_property('config-file-path', 'config/config_infer_yolov11.txt')
        
        # Tracker
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        tracker.set_property('tracker-width', 640)
        tracker.set_property('tracker-height', 480)
        tracker.set_property('ll-lib', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so')
        tracker.set_property('ll-config-file', 'config/config_tracker.txt')
        
        # Video converter
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")
        
        # OSD
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        
        # Sink
        if self.source == 'camera':
            sink = Gst.ElementFactory.make("nveglglessink", "sink")
        else:
            nvvidconv2 = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv2")
            capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
            caps = Gst.Caps.from_string("video/x-raw, format=I420")
            capsfilter.set_property("caps", caps)
            encoder = Gst.ElementFactory.make("avenc_mpeg4", "encoder")
            encoder.set_property("bitrate", 2000000)
            h264parser2 = Gst.ElementFactory.make("mpeg4videoparse", "h264parser2")
            muxer = Gst.ElementFactory.make("qtmux", "muxer")
            sink = Gst.ElementFactory.make("filesink", "sink")
            sink.set_property("location", "output.mp4")
        
        # 添加到pipeline
        pipeline.add(source)
        pipeline.add(decoder)
        pipeline.add(streammux)
        if self.nvvidconv_cpu:
            pipeline.add(self.nvvidconv_cpu)
        pipeline.add(pgie)
        pipeline.add(tracker)
        pipeline.add(nvvidconv)
        pipeline.add(nvosd)
        pipeline.add(sink)
        
        if self.source != 'camera':
            pipeline.add(nvvidconv2)
            pipeline.add(capsfilter)
            pipeline.add(encoder)
            pipeline.add(h264parser2)
            pipeline.add(muxer)
        
        # 链接elements
        source.link(decoder)
        decoder.link(streammux)
        
        # 如果使用CPU转换元素，在streammux和pgie之间插入
        if self.nvvidconv_cpu:
            streammux.link(self.nvvidconv_cpu)
            self.nvvidconv_cpu.link(pgie)
        else:
            streammux.link(pgie)
        
        pgie.link(tracker)
        tracker.link(nvvidconv)
        nvvidconv.link(nvosd)
        
        if self.source == 'camera':
            nvosd.link(sink)
        else:
            nvosd.link(nvvidconv2)
            nvvidconv2.link(capsfilter)
            capsfilter.link(encoder)
            encoder.link(h264parser2)
            h264parser2.link(muxer)
            muxer.link(sink)
        
        self.logger.info("Pipeline构建完成")
        
        return pipeline
    
    def extract_input_frame_probe(self, pad, info, u_data):
        """
        nvvidconv_cpu src pad的probe函数
        在这里提取原始输入帧（已转换为CPU可访问格式）
        
        注意：此时图像已通过nvvidconv_cpu转换为CPU memory
        可以尝试使用GStreamer的map功能提取图像数据
        """
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return Gst.PadProbeReturn.OK
        
        try:
            # 获取batch metadata
            batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
            if not batch_meta:
                return Gst.PadProbeReturn.OK
            
            # 遍历帧
            l_frame = batch_meta.frame_meta_list
            while l_frame is not None:
                try:
                    frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
                    frame_id = frame_meta.frame_num
                    width = frame_meta.source_frame_width
                    height = frame_meta.source_frame_height
                    
                    # 尝试提取图像数据
                    # 方法：使用GStreamer的map功能
                    success, map_info = gst_buffer.map(Gst.MapFlags.READ)
                    if success:
                        try:
                            # 获取caps以确定格式
                            caps = pad.get_current_caps()
                            if caps:
                                structure = caps.get_structure(0)
                                format_str = structure.get_string("format")
                                
                                # 根据格式提取数据
                                if format_str in ["RGB", "BGR", "RGBA", "BGRA"]:
                                    channels = 3 if format_str in ["RGB", "BGR"] else 4
                                    frame_data = np.frombuffer(map_info.data, dtype=np.uint8)
                                    
                                    # 重塑为图像数组
                                    if len(frame_data) >= width * height * channels:
                                        frame = frame_data[:width * height * channels].reshape((height, width, channels))
                                        
                                        # 如果是BGR格式，转换为RGB（OpenCV默认BGR）
                                        if format_str == "BGR" or format_str == "BGRA":
                                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                        
                                        # 缓存图像（限制缓存大小）
                                        if len(self.input_frame_cache) >= self.max_cache_size:
                                            # 删除最旧的帧
                                            oldest_frame_id = min(self.input_frame_cache.keys())
                                            del self.input_frame_cache[oldest_frame_id]
                                        
                                        self.input_frame_cache[frame_id] = frame.copy()
                                        
                                elif format_str == "I420" or format_str == "NV12":
                                    # YUV格式，需要转换
                                    # 这里简化处理，实际可能需要更复杂的转换
                                    frame_data = np.frombuffer(map_info.data, dtype=np.uint8)
                                    # TODO: 实现YUV到RGB的转换
                                    pass
                                    
                        finally:
                            gst_buffer.unmap(map_info)
                    
                except StopIteration:
                    break
                except Exception as e:
                    # 记录错误但不中断pipeline
                    self.logger.debug(f"图像提取错误（帧{frame_id}）: {e}")
                
                try:
                    l_frame = l_frame.next
                except StopIteration:
                    break
                    
        except Exception as e:
            # 记录错误但不中断pipeline
            self.logger.debug(f"extract_input_frame_probe错误: {e}")
        
        return Gst.PadProbeReturn.OK
    
    def pgie_sink_pad_buffer_probe(self, pad, info, u_data):
        """
        Primary GIE sink pad的probe函数（备用方案）
        如果nvvidconv_cpu不可用，使用此probe
        
        注意：此时图像仍在GPU memory，提取较复杂
        """
        # 备用方案：暂时不实现，优先使用extract_input_frame_probe
        return Gst.PadProbeReturn.OK
    
    def osd_sink_pad_buffer_probe(self, pad, info, u_data):
        """
        OSD sink pad的probe函数
        在这里处理检测结果和跟踪数据
        """
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return Gst.PadProbeReturn.OK
        
        # 获取batch metadata
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break
            
            self.stats['frame_count'] += 1
            frame_number = frame_meta.frame_num
            
            # 检查并处理异步ROI识别结果（非阻塞）
            if self.enable_async_processing:
                self._check_async_results()
            
            # 提取当前帧的图像数据（用于ROI裁剪）
            # 注意：由于DeepStream使用NvBufSurface，直接提取复杂
            # 当前使用简化方案：在需要时从缓存获取或使用其他方法
            frame = self._extract_frame_from_buffer(gst_buffer, frame_meta)
            
            # 遍历对象
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                
                # 获取信息
                class_id = obj_meta.class_id
                object_id = obj_meta.object_id  # 跟踪ID
                confidence = obj_meta.confidence
                
                # 获取bbox
                bbox = (
                    obj_meta.rect_params.left,
                    obj_meta.rect_params.top,
                    obj_meta.rect_params.left + obj_meta.rect_params.width,
                    obj_meta.rect_params.top + obj_meta.rect_params.height
                )
                
                # 新车辆
                if object_id not in self.tracked_vehicles:
                    vehicle_info = {
                        'track_id': object_id,
                        'class_id': class_id,
                        'detected_class': None,
                        'vehicle_type': None,
                        'status': 'unregistered',
                        'confidence': confidence,
                        'bbox': bbox,
                        'distance': None,
                        'beacon_mac': None,
                        'company': None,
                        'environment_code': None,
                        'plate_number': None,
                        'is_registered': False
                    }
                    
                    if class_id in CONSTRUCTION_VEHICLES:
                        # 工程车辆
                        vtype, cn_name = CONSTRUCTION_VEHICLES[class_id]
                        vehicle_info['detected_class'] = vtype
                        vehicle_info['vehicle_type'] = 'construction_vehicle'
                        self.stats['construction'][vtype] += 1
                        self.logger.info(f"新工程车辆 ID{object_id}: {cn_name} ({vtype}), 帧{frame_number}")
                        
                        # 测量距离
                        distance, depth_confidence = self._get_vehicle_distance(bbox, frame_number) or (None, None)
                        if distance:
                            vehicle_info['distance'] = distance
                            self.logger.debug(f"  距离: {distance:.2f} m")
                        
                        # 匹配信标
                        beacon_info = self._match_beacon_for_vehicle(bbox, distance)
                        if beacon_info:
                            vehicle_info['beacon_mac'] = beacon_info.get('mac')
                            vehicle_info['company'] = beacon_info.get('company')
                            vehicle_info['environment_code'] = beacon_info.get('environment_code')
                            vehicle_info['status'] = 'registered'
                            vehicle_info['is_registered'] = True
                            self.logger.info(f"  信标匹配: {vehicle_info['beacon_mac']}")
                        else:
                            vehicle_info['status'] = 'unregistered'
                            vehicle_info['is_registered'] = False
                            self.logger.debug(f"  未匹配到信标")
                        
                        # 保存车辆信息
                        self.tracked_vehicles[object_id] = vehicle_info
                        
                        # 保存到数据库
                        self._save_to_database(vehicle_info)
                        
                        # 上传检测结果
                        self._upload_detection_result(vehicle_info)
                    
                    elif class_id in CIVILIAN_VEHICLES and self.lpr:
                        # 社会车辆：尝试识别车牌
                        vtype, cn_name = CIVILIAN_VEHICLES[class_id]
                        vehicle_info['detected_class'] = vtype
                        vehicle_info['vehicle_type'] = 'social_vehicle'
                        self.logger.info(f"新社会车辆 ID{object_id}: {cn_name} ({vtype}), 帧{frame_number}")
                        
                        # GPU优化：优先使用GPU ROI提取
                        roi = None
                        
                        # 方法1: 尝试GPU直接提取（高性能）
                        if self.enable_gpu_roi_extraction:
                            roi = self._extract_roi_from_gpu(gst_buffer, frame_meta, bbox)
                            if roi is not None:
                                self.logger.debug(f"  ✓ 使用GPU ROI提取")
                        
                        # 方法2: 如果GPU方法失败，尝试从缓存的CPU帧提取
                        if roi is None and frame is not None:
                            roi = self._crop_vehicle_roi(frame, bbox)
                            if roi is not None:
                                self.logger.debug(f"  ✓ 使用CPU缓存ROI提取")
                        
                        # 执行车牌识别（异步或同步）
                        if roi is not None and roi.size > 0:
                            if self.enable_async_processing and self.executor:
                                # 异步处理：不阻塞主pipeline
                                vehicle_info['status'] = 'processing'  # 标记为处理中
                                future = self.executor.submit(
                                    self._process_roi_async, 
                                    object_id, 
                                    roi.copy(),  # 复制ROI，避免引用问题
                                    vehicle_info
                                )
                                self.pending_rois[object_id] = future
                                self.logger.debug(f"  [异步] 车牌识别任务已提交 ID{object_id}")
                            else:
                                # 同步处理：阻塞但立即返回结果
                                plate_result = self._recognize_license_plate(roi)
                                if plate_result:
                                    plate_number, plate_confidence = plate_result
                                    vehicle_info['plate_number'] = plate_number
                                    vehicle_info['status'] = 'identified'
                                    self.logger.info(f"  车牌: {plate_number} (置信度: {plate_confidence:.2f})")
                                else:
                                    vehicle_info['status'] = 'failed'
                                    self.logger.debug(f"  车牌识别失败")
                        else:
                            vehicle_info['status'] = 'failed'
                            if not self.enable_gpu_roi_extraction and not self.use_cpu_conversion:
                                self.logger.warning(f"  无法提取ROI（建议启用GPU优化或CPU转换）")
                            else:
                                self.logger.debug(f"  无法提取ROI（图像数据不可用）")
                        
                        # 保存车辆信息（即使异步处理中也会保存基本信息）
                        self.tracked_vehicles[object_id] = vehicle_info
                        
                        # 同步处理时立即保存和上传，异步处理时由_check_async_results处理
                        if not self.enable_async_processing or not self.executor:
                            # 保存到数据库
                            self._save_to_database(vehicle_info)
                            
                            # 上传检测结果
                            self._upload_detection_result(vehicle_info)
                
                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break
            
            # 性能监控：计算FPS
            if self.enable_performance_monitor:
                current_time = time.time()
                frame_interval = current_time - self.last_frame_time
                self.last_frame_time = current_time
                
                # 记录帧时间
                self.frame_times.append(frame_interval)
                if len(self.frame_times) > self.max_frame_times:
                    self.frame_times.pop(0)
                
                # 定期更新FPS（避免每帧都计算）
                if (frame_number - self.last_fps_update_frame) >= self.fps_update_interval:
                    if len(self.frame_times) > 0:
                        avg_interval = sum(self.frame_times) / len(self.frame_times)
                        self.current_fps = 1.0 / avg_interval if avg_interval > 0 else 0.0
                    self.last_fps_update_frame = frame_number
                
                # 更新性能统计
                self.performance_stats['total_frames'] += 1
                self.performance_stats['total_processing_time'] += frame_interval
                self.performance_stats['avg_processing_time'] = (
                    self.performance_stats['total_processing_time'] / 
                    self.performance_stats['total_frames']
                )
                if frame_interval > self.performance_stats['max_processing_time']:
                    self.performance_stats['max_processing_time'] = frame_interval
                if frame_interval < self.performance_stats['min_processing_time']:
                    self.performance_stats['min_processing_time'] = frame_interval
            
            # Display metadata
            display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
            display_meta.num_labels = 1
            py_nvosd_text_params = display_meta.text_params[0]
            
            # 统计信息显示（包含FPS）
            if self.enable_performance_monitor:
                stats_text = (
                    f"跟踪: {len(self.tracked_vehicles)} | "
                    f"帧: {frame_number} | "
                    f"FPS: {self.current_fps:.1f}"
                )
            else:
                stats_text = f"跟踪: {len(self.tracked_vehicles)} | 帧: {frame_number}"
            py_nvosd_text_params.display_text = stats_text
            py_nvosd_text_params.x_offset = 10
            py_nvosd_text_params.y_offset = 12
            py_nvosd_text_params.font_params.font_name = "Serif"
            py_nvosd_text_params.font_params.font_size = 14
            py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 0.0, 1.0)
            py_nvosd_text_params.set_bg_clr = 1
            py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 0.5)
            
            pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
            
            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        
        return Gst.PadProbeReturn.OK
    
    def run(self):
        """运行DeepStream应用"""
        
        print("\n启动DeepStream应用...")
        
        # 构建pipeline
        pipeline = self.build_pipeline()
        
        # 添加probe
        print("  添加probe函数...")
        
        # 在CPU转换元素之后添加probe用于提取原始输入帧（用于ROI裁剪）
        if self.nvvidconv_cpu:
            nvvidconv_cpu_src_pad = self.nvvidconv_cpu.get_static_pad("src")
            if nvvidconv_cpu_src_pad:
                nvvidconv_cpu_src_pad.add_probe(Gst.PadProbeType.BUFFER, 
                                               self.extract_input_frame_probe, 0)
                print("  ✓ CPU转换元素probe添加成功（用于图像提取）")
        else:
            # 如果没有CPU转换元素，尝试在nvinfer之前添加probe（用于GPU提取）
            if self.enable_gpu_roi_extraction:
                pgie = pipeline.get_by_name("primary-inference")
                if pgie:
                    pgie_sink_pad = pgie.get_static_pad("sink")
                    if pgie_sink_pad:
                        pgie_sink_pad.add_probe(Gst.PadProbeType.BUFFER, 
                                               self.pgie_sink_pad_buffer_probe, 0)
                        print("  ✓ PGI sink pad probe添加成功（用于GPU图像提取）")
            else:
                print("  ⚠ 未启用图像提取probe（无需ROI提取或GPU优化未启用）")
        
        # 在OSD之后添加probe用于处理检测结果
        nvosd = pipeline.get_by_name("onscreendisplay")
        if nvosd:
            nvosd_sink_pad = nvosd.get_static_pad("sink")
            if nvosd_sink_pad:
                nvosd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, 
                                        self.osd_sink_pad_buffer_probe, 0)
                print("  ✓ OSD sink pad probe添加成功")
        
        # 创建主循环
        loop = GLib.MainLoop()
        
        # 设置pipeline状态
        self.logger.info("设置pipeline状态...")
        pipeline.set_state(Gst.State.PLAYING)
        
        try:
            self.logger.info("DeepStream应用运行中...")
            self.logger.info("按 Ctrl+C 退出")
            loop.run()
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在停止应用...")
        finally:
            # 清理资源
            self.logger.info("清理资源...")
            pipeline.set_state(Gst.State.NULL)
            
            # 关闭异步处理
            if self.enable_async_processing and self.executor:
                self.logger.info("关闭异步处理线程池...")
                # 等待所有待处理的任务完成（最多等待5秒）
                import time
                start_time = time.time()
                while self.pending_rois and (time.time() - start_time) < 5.0:
                    self._check_async_results()
                    time.sleep(0.1)
                
                # 关闭线程池
                self.executor.shutdown(wait=True, timeout=2.0)
                self.logger.info("异步处理线程池已关闭")
            
            if self.depth_camera:
                self.depth_camera.stop()
            
            if self.beacon_client:
                self.beacon_client.stop()
            
            # 输出性能统计
            if self.enable_performance_monitor and self.performance_stats['total_frames'] > 0:
                self.logger.info("=" * 60)
                self.logger.info("性能统计:")
                self.logger.info(f"  总帧数: {self.performance_stats['total_frames']}")
                self.logger.info(f"  平均FPS: {self.current_fps:.2f}")
                self.logger.info(f"  平均处理时间: {self.performance_stats['avg_processing_time']*1000:.2f} ms")
                self.logger.info(f"  最大处理时间: {self.performance_stats['max_processing_time']*1000:.2f} ms")
                if self.performance_stats['min_processing_time'] != float('inf'):
                    self.logger.info(f"  最小处理时间: {self.performance_stats['min_processing_time']*1000:.2f} ms")
                self.logger.info("=" * 60)
            
            self.logger.info("应用已停止")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DeepStream车辆检测应用')
    parser.add_argument('source', help='输入源（视频文件路径或"camera"）')
    parser.add_argument('--config', help='配置文件路径（可选）')
    
    args = parser.parse_args()
    
    app = DeepStreamVehicleDetection(args.source, args.config)
    app.run()


if __name__ == '__main__':
    main()
