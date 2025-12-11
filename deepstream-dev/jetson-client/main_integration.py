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
        self.cloud_client = CloudClient(self.config)
        self.detection_queue = queue.Queue(maxsize=100)
        self.running = False
        self.upload_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.heartbeat_interval = 300  # 5分钟
        self.device_id = os.getenv("DEVICE_ID", "jetson-01")
        self.stats_callback: Optional[callable] = None  # 用于获取统计信息的回调函数
        
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
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
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
        try:
            # 添加到上传队列
            self.detection_queue.put_nowait(detection)
            logger.debug(f"Detection queued: {detection.vehicle_type} (conf: {detection.confidence:.2f})")
        except queue.Full:
            logger.warning("Detection queue is full, dropping detection")
    
    def _upload_worker(self) -> None:
        """上传工作线程"""
        while self.running:
            try:
                # 从队列获取检测结果（阻塞，最多等待1秒）
                try:
                    detection = self.detection_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 先上传图片（如果存在），获取图片URL
                snapshot_url = None
                if detection.image_path and Path(detection.image_path).exists():
                    # 先上传图片，获取URL
                    snapshot_url = self.cloud_client.upload_image(
                        image_path=detection.image_path,
                        alert_id=None  # 先不上传，稍后通过alert_id关联
                    )
                
                # 上传警报（包含图片URL）
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
                    snapshot_path=detection.image_path,  # 本地路径
                    snapshot_url=snapshot_url,  # 云端URL
                    image_path=detection.image_path  # 备用字段
                )
                
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

