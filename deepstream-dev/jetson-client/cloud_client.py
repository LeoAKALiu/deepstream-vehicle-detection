"""云端 API 客户端 - 负责与云端服务器通信"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from PIL import Image
import io

from config import CloudConfig

logger = logging.getLogger(__name__)


class CloudClient:
    """云端 API 客户端"""
    
    def __init__(self, config: CloudConfig):
        """
        初始化云端客户端
        
        Args:
            config: 云端配置
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": config.api_key,
            "Content-Type": "application/json"
        })
        self.base_url = config.api_base_url.rstrip("/")
    
    def send_alert(
        self,
        vehicle_type: str,
        timestamp: datetime,
        detected_class: Optional[str] = None,
        status: Optional[str] = None,
        plate_number: Optional[str] = None,
        confidence: Optional[float] = None,
        distance: Optional[float] = None,
        is_registered: Optional[bool] = None,
        track_id: Optional[int] = None,
        bbox: Optional[dict] = None,
        beacon_mac: Optional[str] = None,
        company: Optional[str] = None,
        environment_code: Optional[str] = None,
        metadata: Optional[dict] = None,
        snapshot_path: Optional[str] = None,
        snapshot_url: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Optional[int]:
        """
        发送警报到云端
        
        Args:
            vehicle_type: 车辆类型（"construction_vehicle" | "social_vehicle"）
            timestamp: 检测时间戳
            detected_class: 检测类别（如 "excavator", "bulldozer", "car"）
            status: 状态（如 "registered", "unregistered", "identified"）
            plate_number: 车牌号（可选）
            confidence: 置信度（0.0-1.0，可选）
            distance: 距离（米，可选）
            is_registered: 是否已备案（可选）
            track_id: 跟踪ID（可选）
            bbox: 边界框（字典，包含 x1, y1, x2, y2）
            beacon_mac: 信标MAC地址（工程车辆）
            company: 所属公司（工程车辆）
            environment_code: 环境编码（工程车辆，来自云端白名单）
            metadata: 元数据（rssi, match_cost等）
            snapshot_path: 本地快照路径（可选）
            snapshot_url: 云端快照URL（可选）
            image_path: 图片路径（可选，备用字段）
            
        Returns:
            警报 ID（如果成功），否则返回 None
        """
        if not self.config.enable_alert_upload:
            logger.debug("Alert upload is disabled")
            return None
        
        alert_data = {
            "timestamp": timestamp.isoformat(),
            "vehicle_type": vehicle_type,
            "detected_class": detected_class,
            "status": status,
            "plate_number": plate_number,
            "confidence": confidence,
            "distance": distance,
            "is_registered": is_registered,
            "track_id": track_id,
            "bbox": bbox,
            "beacon_mac": beacon_mac,
            "company": company,
            "environment_code": environment_code,
            "metadata": metadata,
            "snapshot_path": snapshot_path,
            "snapshot_url": snapshot_url,
            "image_path": image_path
        }
        
        # 移除None值
        alert_data = {k: v for k, v in alert_data.items() if v is not None}
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/alerts",
                    json=alert_data,
                    timeout=10
                )
                response.raise_for_status()
                result = response.json()
                alert_id = result.get("id")
                logger.info(f"Alert sent successfully, ID: {alert_id}")
                return alert_id
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to send alert (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to send alert after {self.config.retry_attempts} attempts")
        return None
    
    def upload_image(
        self,
        image_path: str,
        alert_id: Optional[int] = None
    ) -> Optional[str]:
        """
        上传图片到云端
        
        Args:
            image_path: 图片文件路径
            alert_id: 关联的警报 ID（可选）
            
        Returns:
            图片路径（如果成功），否则返回 None
        """
        if not self.config.enable_image_upload:
            logger.debug("Image upload is disabled")
            return None
        
        try:
            # 检查文件是否存在
            if not Path(image_path).exists():
                logger.warning(f"Image file not found: {image_path}")
                return None
            
            # 检查文件大小
            file_size_mb = Path(image_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_image_size_mb:
                logger.warning(f"Image too large ({file_size_mb:.2f}MB), compressing...")
                image_path = self._compress_image(image_path)
            
            with open(image_path, "rb") as f:
                files = {"file": (Path(image_path).name, f, "image/jpeg")}
                data = {}
                if alert_id:
                    data["alert_id"] = alert_id
                
                for attempt in range(self.config.retry_attempts):
                    try:
                        # 重新设置请求头（multipart/form-data）
                        headers = {"X-API-Key": self.config.api_key}
                        response = requests.post(
                            f"{self.base_url}/api/images",
                            files=files,
                            data=data,
                            headers=headers,
                            timeout=30
                        )
                        response.raise_for_status()
                        result = response.json()
                        image_url = result.get("path") or result.get("url")
                        logger.info(f"Image uploaded successfully: {image_url}")
                        return image_url
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Failed to upload image (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                        if attempt < self.config.retry_attempts - 1:
                            time.sleep(self.config.retry_delay * (attempt + 1))
                            # 重新打开文件
                            f.seek(0)
                        else:
                            logger.error(f"Failed to upload image after {self.config.retry_attempts} attempts")
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
        return None
    
    def _compress_image(self, image_path: str, max_size_mb: Optional[float] = None) -> str:
        """
        压缩图片以减少文件大小（保持最小分辨率）
        
        Args:
            image_path: 原始图片路径
            max_size_mb: 最大文件大小（MB），默认使用配置值
            
        Returns:
            压缩后的图片路径
        """
        if max_size_mb is None:
            max_size_mb = self.config.max_image_size_mb
        
        try:
            img = Image.open(image_path)
            original_size = Path(image_path).stat().st_size / (1024 * 1024)
            
            # 如果文件已经小于限制，直接返回
            if original_size <= max_size_mb:
                return image_path
            
            # 确保最小分辨率（至少640x480，提高前端显示质量）
            min_width, min_height = 640, 480
            if img.width < min_width or img.height < min_height:
                # 如果图片太小，按比例放大到最小尺寸
                scale = max(min_width / img.width, min_height / img.height)
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 如果图片太大，调整尺寸（但保持最小分辨率，支持更高分辨率）
            max_dimension = 2560
            if img.width > max_dimension or img.height > max_dimension:
                ratio = min(max_dimension / img.width, max_dimension / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                # 确保不会缩小到最小尺寸以下
                if new_size[0] < min_width:
                    new_size = (min_width, int(img.height * min_width / img.width))
                if new_size[1] < min_height:
                    new_size = (int(img.width * min_height / img.height), min_height)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 保存为 JPEG 格式（压缩）
            output_path = image_path.replace(".png", ".jpg").replace(".PNG", ".jpg")
            if output_path == image_path:
                output_path = image_path.rsplit(".", 1)[0] + "_compressed.jpg"
            
            # 调整质量直到文件大小符合要求（从95开始，最低到70，保持高质量）
            quality = 95
            while quality >= 70:
                img.save(output_path, "JPEG", quality=quality, optimize=True)
                file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
                if file_size_mb <= max_size_mb:
                    break
                quality -= 5
            
            # 如果仍然太大，进一步缩小尺寸（但保持最小分辨率）
            if quality < 70:
                current_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
                if current_size_mb > max_size_mb:
                    # 按比例缩小，但保持最小分辨率
                    scale = (max_size_mb / current_size_mb) ** 0.5
                    new_size = (max(int(img.width * scale), min_width), max(int(img.height * scale), min_height))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    img.save(output_path, "JPEG", quality=85, optimize=True)  # 使用85质量而不是75
            
            logger.info(f"Image compressed: {Path(image_path).stat().st_size / 1024:.1f}KB -> {Path(output_path).stat().st_size / 1024:.1f}KB (size: {img.width}x{img.height})")
            return output_path
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            return image_path
    
    def health_check(self) -> bool:
        """
        检查云端服务器连接
        
        Returns:
            True 如果服务器可达，否则 False
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def send_heartbeat(
        self,
        device_id: Optional[str] = None,
        system_status: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送心跳到云端
        
        Args:
            device_id: 设备ID（可选）
            system_status: 系统状态字典（CPU、内存、GPU等）
            stats: 检测统计信息（检测数量、FPS等）
            
        Returns:
            True 如果发送成功，否则 False
        """
        heartbeat_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "system_status": system_status or {},
            "stats": stats or {}
        }
        
        # 移除None值
        heartbeat_data = {k: v for k, v in heartbeat_data.items() if v is not None}
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/heartbeat",
                json=heartbeat_data,
                timeout=10
            )
            response.raise_for_status()
            logger.debug("Heartbeat sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to send heartbeat: {e}")
            return False

