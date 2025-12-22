"""主集成模块 - 连接 AI 检测与云端上传"""

import logging
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from cloud_client import CloudClient
from config import CloudConfig, load_config
from detection_result import DetectionResult

logger = logging.getLogger(__name__)


class SentinelIntegration:
    """Jetson 端集成主类"""
    
    def __init__(self, config: Optional[CloudConfig] = None):
        """
        初始化集成模块
        
        Args:
            config: 云端配置，如果为 None 则从环境变量加载
        """
        self.config = config or load_config()
        
        # 从CloudConfig加载监控截图配置（如果已设置）
        self.monitoring_snapshot_interval = getattr(self.config, 'monitoring_snapshot_interval', 600)
        self.enable_monitoring_snapshot = getattr(self.config, 'enable_monitoring_snapshot', True)
        
        self.cloud_client = CloudClient(self.config)
        self.detection_queue = queue.Queue(maxsize=100)
        self.running = False
        self.upload_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.heartbeat_interval = 300  # 5分钟
        self.device_id = os.getenv("DEVICE_ID", "jetson-01")
        self.stats_callback: Optional[callable] = None  # 用于获取统计信息的回调函数
        self.frame_callback: Optional[callable] = None  # 用于获取当前帧的回调函数
        self.monitoring_snapshot_thread: Optional[threading.Thread] = None
        
        # 设置日志
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    
    def start(self) -> None:
        """启动上传线程和心跳线程"""
        if self.running:
            logger.warning("Integration already running")
            return
        
        self.running = True
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
        
        # #region agent log
        try:
            import json
            with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    'id': f'log_{int(time.time() * 1000)}',
                    'timestamp': int(time.time() * 1000),
                    'location': 'main_integration.py:start',
                    'message': 'Upload thread started',
                    'data': {
                        'thread_alive': self.upload_thread.is_alive() if self.upload_thread else False,
                        'running': self.running,
                        'hypothesisId': 'D'
                    },
                    'sessionId': 'debug-session',
                    'runId': 'run1'
                }) + '\n')
        except: pass
        # #endregion
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        # 启动监控截图线程（如果启用）
        if self.enable_monitoring_snapshot:
            self.monitoring_snapshot_thread = threading.Thread(target=self._monitoring_snapshot_worker, daemon=True)
            self.monitoring_snapshot_thread.start()
            logger.info(f"Monitoring snapshot worker started (interval: {self.monitoring_snapshot_interval}s)")
        
        logger.info("Sentinel integration started")
    
    def stop(self) -> None:
        """停止上传线程"""
        self.running = False
        if self.upload_thread:
            self.upload_thread.join(timeout=5)
        logger.info("Sentinel integration stopped")
    
    def on_detection(self, detection: DetectionResult) -> None:
        """
        当检测到车辆时调用此方法
        
        Args:
            detection: 检测结果
        """
        # #region agent log
        try:
            import json
            with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    'id': f'log_{int(time.time() * 1000)}',
                    'timestamp': int(time.time() * 1000),
                    'location': 'main_integration.py:on_detection',
                    'message': 'Function entry',
                    'data': {
                        'track_id': detection.track_id,
                        'vehicle_type': detection.vehicle_type,
                        'queue_size_before': self.detection_queue.qsize(),
                        'queue_maxsize': self.detection_queue.maxsize,
                        'hypothesisId': 'D'
                    },
                    'sessionId': 'debug-session',
                    'runId': 'run1'
                }) + '\n')
        except: pass
        # #endregion
        try:
            # 添加到上传队列
            self.detection_queue.put_nowait(detection)
            # #region agent log
            try:
                import json
                with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({
                        'id': f'log_{int(time.time() * 1000)}',
                        'timestamp': int(time.time() * 1000),
                        'location': 'main_integration.py:on_detection',
                        'message': 'Detection queued successfully',
                        'data': {
                            'track_id': detection.track_id,
                            'queue_size_after': self.detection_queue.qsize(),
                            'hypothesisId': 'D'
                        },
                        'sessionId': 'debug-session',
                        'runId': 'run1'
                    }) + '\n')
            except: pass
            # #endregion
            logger.debug(f"Detection queued: {detection.vehicle_type} (conf: {detection.confidence:.2f})")
        except queue.Full:
            # #region agent log
            try:
                import json
                with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({
                        'id': f'log_{int(time.time() * 1000)}',
                        'timestamp': int(time.time() * 1000),
                        'location': 'main_integration.py:on_detection',
                        'message': 'Queue is full, dropping detection',
                        'data': {
                            'track_id': detection.track_id,
                            'queue_size': self.detection_queue.qsize(),
                            'hypothesisId': 'D'
                        },
                        'sessionId': 'debug-session',
                        'runId': 'run1'
                    }) + '\n')
            except: pass
            # #endregion
            logger.warning("Detection queue is full, dropping detection")
    
    def _upload_worker(self) -> None:
        """上传工作线程"""
        # #region agent log
        try:
            import json
            with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    'id': f'log_{int(time.time() * 1000)}',
                    'timestamp': int(time.time() * 1000),
                    'location': 'main_integration.py:_upload_worker',
                    'message': 'Upload worker started',
                    'data': {'running': self.running, 'hypothesisId': 'D'},
                    'sessionId': 'debug-session',
                    'runId': 'run1'
                }) + '\n')
        except: pass
        # #endregion
        while self.running:
            try:
                # 从队列获取检测结果（阻塞，最多等待1秒）
                try:
                    detection = self.detection_queue.get(timeout=1.0)
                    # #region agent log
                    try:
                        import json
                        with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({
                                'id': f'log_{int(time.time() * 1000)}',
                                'timestamp': int(time.time() * 1000),
                                'location': 'main_integration.py:_upload_worker',
                                'message': 'Got detection from queue',
                                'data': {
                                    'track_id': detection.track_id,
                                    'vehicle_type': detection.vehicle_type,
                                    'queue_size_after_get': self.detection_queue.qsize(),
                                    'hypothesisId': 'D'
                                },
                                'sessionId': 'debug-session',
                                'runId': 'run1'
                            }) + '\n')
                    except: pass
                    # #endregion
                except queue.Empty:
                    continue
                
                # 先上传图片（如果存在），获取图片URL
                snapshot_url = None
                if detection.image_path and Path(detection.image_path).exists():
                    # #region agent log
                    try:
                        import json
                        with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({
                                'id': f'log_{int(time.time() * 1000)}',
                                'timestamp': int(time.time() * 1000),
                                'location': 'main_integration.py:_upload_worker',
                                'message': 'Before upload_image',
                                'data': {
                                    'track_id': detection.track_id,
                                    'image_path': detection.image_path,
                                    'hypothesisId': 'E'
                                },
                                'sessionId': 'debug-session',
                                'runId': 'run1'
                            }) + '\n')
                    except: pass
                    # #endregion
                    # 先上传图片，获取URL（返回相对路径，格式：YYYY-MM-DD/filename）
                    snapshot_url = self.cloud_client.upload_image(
                        image_path=detection.image_path,
                        alert_id=None  # 先不上传，稍后通过alert_id关联
                    )
                    # #region agent log
                    try:
                        import json
                        with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({
                                'id': f'log_{int(time.time() * 1000)}',
                                'timestamp': int(time.time() * 1000),
                                'location': 'main_integration.py:_upload_worker',
                                'message': 'After upload_image',
                                'data': {
                                    'track_id': detection.track_id,
                                    'snapshot_url': snapshot_url,
                                    'hypothesisId': 'E'
                                },
                                'sessionId': 'debug-session',
                                'runId': 'run1'
                            }) + '\n')
                    except: pass
                    # #endregion
                
                # 上传警报（包含图片URL）
                # 根据云端要求：
                # - snapshot_url: 使用上传接口返回的path（相对路径，格式：YYYY-MM-DD/filename）✅
                # - snapshot_path: 不应使用Jetson端绝对路径，如果snapshot_url存在则设为None
                # - image_path: 不应使用Jetson端绝对路径，如果snapshot_url存在则设为None
                # #region agent log
                try:
                    import json
                    with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({
                            'id': f'log_{int(time.time() * 1000)}',
                            'timestamp': int(time.time() * 1000),
                            'location': 'main_integration.py:_upload_worker',
                            'message': 'Before send_alert',
                            'data': {
                                'track_id': detection.track_id,
                                'vehicle_type': detection.vehicle_type,
                                'hypothesisId': 'E'
                            },
                            'sessionId': 'debug-session',
                            'runId': 'run1'
                        }) + '\n')
                except: pass
                # #endregion
                # #region agent log
                try:
                    import json
                    with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({
                            'id': f'log_{int(time.time() * 1000)}',
                            'timestamp': int(time.time() * 1000),
                            'location': 'main_integration.py:_upload_worker',
                            'message': 'Before send_alert with detected_class',
                            'data': {
                                'track_id': detection.track_id,
                                'detected_class': detection.detected_class,
                                'vehicle_type': detection.vehicle_type,
                                'status': detection.status,
                                'hypothesisId': 'E'
                            },
                            'sessionId': 'debug-session',
                            'runId': 'run1'
                        }) + '\n')
                except: pass
                # #endregion
                alert_id = self.cloud_client.send_alert(
                    vehicle_type=detection.vehicle_type,
                    timestamp=detection.timestamp,
                    detected_class=detection.detected_class,
                    status=detection.status,
                    plate_number=detection.plate_number,
                    confidence=detection.confidence,
                    distance=detection.distance,
                    is_registered=detection.is_registered,
                    track_id=detection.track_id,
                    bbox={
                        "x1": detection.bbox[0],
                        "y1": detection.bbox[1],
                        "x2": detection.bbox[2],
                        "y2": detection.bbox[3]
                    } if detection.bbox and len(detection.bbox) >= 4 else None,
                    beacon_mac=detection.beacon_mac,
                    company=detection.company,
                    environment_code=detection.environment_code,  # 添加环境编码
                    metadata=detection.metadata,
                    snapshot_path=None,  # 必须为null（文档要求）
                    snapshot_url=snapshot_url,  # 使用上传接口返回的相对路径（格式：YYYY-MM-DD/filename）
                    image_path=None  # 必须为null（文档要求）
                )
                
                # #region agent log
                try:
                    import json
                    with open('/home/liubo/Download/deepstream-vehicle-detection/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({
                            'id': f'log_{int(time.time() * 1000)}',
                            'timestamp': int(time.time() * 1000),
                            'location': 'main_integration.py:_upload_worker',
                            'message': 'After send_alert',
                            'data': {
                                'track_id': detection.track_id,
                                'alert_id': alert_id,
                                'hypothesisId': 'E'
                            },
                            'sessionId': 'debug-session',
                            'runId': 'run1'
                        }) + '\n')
                except: pass
                # #endregion
                
                # 如果图片上传成功但alert_id已返回，再次关联图片和alert
                if snapshot_url and alert_id:
                    # 可选：再次上传图片以关联alert_id（如果云端需要）
                    self.cloud_client.upload_image(
                        image_path=detection.image_path,
                        alert_id=alert_id
                    )
                
                # 标记任务完成
                self.detection_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in upload worker: {e}")
    
    def health_check(self) -> bool:
        """
        检查云端连接健康状态
        
        Returns:
            True 如果连接正常，否则 False
        """
        return self.cloud_client.health_check()
    
    def get_queue_size(self) -> int:
        """
        获取当前队列大小
        
        Returns:
            队列中待处理的项目数量
        """
        return self.detection_queue.qsize()
    
    def set_stats_callback(self, callback: Callable[[], Dict[str, Any]]) -> None:
        """
        设置统计信息回调函数
        
        Args:
            callback: 返回统计信息字典的函数
        """
        self.stats_callback = callback
    
    def set_frame_callback(self, callback: Callable[[], Optional[Any]]) -> None:
        """
        设置帧获取回调函数
        
        Args:
            callback: 返回当前帧（numpy数组）的函数，如果没有帧则返回None
        """
        self.frame_callback = callback
    
    def _get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态字典
        """
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_total_mb": memory.total / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
            
            # 尝试获取GPU信息
            try:
                import subprocess
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total',
                     '--format=csv,noheader,nounits'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    gpu_info = result.stdout.strip().split(', ')
                    if len(gpu_info) >= 4:
                        status["gpu_utilization"] = float(gpu_info[0])
                        status["gpu_temperature"] = float(gpu_info[1])
                        status["gpu_memory_used_mb"] = float(gpu_info[2])
                        status["gpu_memory_total_mb"] = float(gpu_info[3])
            except Exception:
                pass
            
            return status
        except ImportError:
            logger.warning("psutil not available, system status limited")
            return {}
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {}
    
    def _heartbeat_worker(self) -> None:
        """心跳工作线程"""
        while self.running:
            try:
                # 获取系统状态
                system_status = self._get_system_status()
                
                # 获取统计信息（如果有回调函数）
                stats = None
                if self.stats_callback:
                    try:
                        stats = self.stats_callback()
                    except Exception as e:
                        logger.warning(f"Error getting stats from callback: {e}")
                
                # 发送心跳
                self.cloud_client.send_heartbeat(
                    device_id=self.device_id,
                    system_status=system_status,
                    stats=stats
                )
                
                # 等待下次心跳
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat worker: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _monitoring_snapshot_worker(self) -> None:
        """监控截图工作线程（定时上传现场高清截图）"""
        import cv2
        import tempfile
        
        while self.running:
            try:
                # 等待指定间隔
                time.sleep(self.monitoring_snapshot_interval)
                
                # 检查是否启用
                if not self.enable_monitoring_snapshot:
                    continue
                
                # 获取当前帧
                if not self.frame_callback:
                    logger.warning("Frame callback not set, skipping monitoring snapshot")
                    continue
                
                try:
                    frame = self.frame_callback()
                    if frame is None:
                        logger.warning("No frame available, skipping monitoring snapshot")
                        continue
                except Exception as e:
                    logger.warning(f"Error getting frame for monitoring snapshot: {e}")
                    continue
                
                # 保存为临时文件（高清，不压缩）
                temp_dir = Path(tempfile.gettempdir())
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_filename = f"monitoring_snapshot_{self.device_id}_{timestamp}.jpg"
                snapshot_path = temp_dir / snapshot_filename
                
                try:
                    # 确保是BGR格式（OpenCV格式）
                    if len(frame.shape) == 3:
                        # 如果是RGB，转换为BGR
                        if frame.shape[2] == 3:
                            # 检查是否是RGB（通过检查第一个像素的通道顺序）
                            # 简单判断：如果第一个像素的R值大于B值，可能是RGB
                            # 但更安全的方法是假设从相机获取的是RGB
                            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if hasattr(cv2, 'COLOR_RGB2BGR') else frame
                        else:
                            frame_bgr = frame
                    else:
                        frame_bgr = frame
                    
                    # 保存为高质量JPEG（quality=95，保持高清）
                    cv2.imwrite(str(snapshot_path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    
                    # 检查文件是否成功创建
                    if not snapshot_path.exists():
                        logger.warning(f"Failed to save monitoring snapshot: {snapshot_path}")
                        continue
                    
                    file_size_mb = snapshot_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Monitoring snapshot saved: {snapshot_path} ({file_size_mb:.2f}MB)")
                    
                    # 上传到云端
                    snapshot_url = self.cloud_client.upload_monitoring_snapshot(
                        image_path=str(snapshot_path),
                        device_id=self.device_id
                    )
                    
                    if snapshot_url:
                        logger.info(f"Monitoring snapshot uploaded successfully: {snapshot_url}")
                    else:
                        logger.warning("Failed to upload monitoring snapshot")
                    
                    # 清理临时文件（可选，如果配置了保存则保留）
                    if not self.config.save_snapshots:
                        try:
                            snapshot_path.unlink()
                        except Exception as e:
                            logger.debug(f"Failed to delete temp snapshot: {e}")
                    
                except Exception as e:
                    logger.error(f"Error saving monitoring snapshot: {e}")
                    # 清理临时文件
                    try:
                        if snapshot_path.exists():
                            snapshot_path.unlink()
                    except Exception:
                        pass
                
            except Exception as e:
                logger.error(f"Error in monitoring snapshot worker: {e}")
                time.sleep(60)  # 出错时等待1分钟再重试

