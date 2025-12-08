# Jetson 端开发指南

## 概述

本文档说明如何在 Jetson 边缘设备上开发客户端，将检测到的车辆警报和监控快照发送到云端仪表板。

## 架构流程

```
Jetson 设备
    ├─ 视频采集 (Camera)
    ├─ AI 检测 (YOLO/TensorRT)
    ├─ 数据采集 (车辆信息、置信度)
    └─ 云端上传模块
        ├─ 发送警报 (JSON) → POST /api/alerts
        └─ 上传图片 → POST /api/images
```

## 核心功能模块

### 1. 配置管理模块

**文件**: `config.py`

```python
"""配置管理模块 - 存储云端 API 连接信息"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CloudConfig:
    """云端配置"""
    api_base_url: str = "http://your-server-ip:8000"
    api_key: str = "your-api-key-here"
    upload_interval: int = 10  # 上传间隔（秒）
    max_image_size_mb: int = 5  # 最大图片大小
    enable_image_upload: bool = True  # 是否上传图片
    enable_alert_upload: bool = True  # 是否上传警报
    retry_attempts: int = 3  # 重试次数
    retry_delay: float = 2.0  # 重试延迟（秒）


def load_config() -> CloudConfig:
    """从环境变量或配置文件加载配置"""
    return CloudConfig(
        api_base_url=os.getenv("CLOUD_API_URL", "http://your-server-ip:8000"),
        api_key=os.getenv("CLOUD_API_KEY", "your-api-key-here"),
        upload_interval=int(os.getenv("UPLOAD_INTERVAL", "10")),
        max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "5")),
        enable_image_upload=os.getenv("ENABLE_IMAGE_UPLOAD", "true").lower() == "true",
        enable_alert_upload=os.getenv("ENABLE_ALERT_UPLOAD", "true").lower() == "true",
    )
```

### 2. 云端通信模块

**文件**: `cloud_client.py`

```python
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
        plate_number: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> Optional[int]:
        """
        发送警报到云端
        
        Args:
            vehicle_type: 车辆类型（如 "Excavator", "Bulldozer"）
            timestamp: 检测时间戳
            plate_number: 车牌号（可选）
            confidence: 置信度（0.0-1.0，可选）
            
        Returns:
            警报 ID（如果成功），否则返回 None
        """
        if not self.config.enable_alert_upload:
            logger.debug("Alert upload is disabled")
            return None
        
        alert_data = {
            "timestamp": timestamp.isoformat(),
            "vehicle_type": vehicle_type,
            "plate_number": plate_number,
            "confidence": confidence
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/alerts",
                    json=alert_data,
                    timeout=10
                )
                response.raise_for_status()
                alert_id = response.json().get("id")
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
                        response = self.session.post(
                            f"{self.base_url}/api/images",
                            files=files,
                            data=data,
                            timeout=30
                        )
                        response.raise_for_status()
                        result = response.json()
                        image_url = result.get("path")
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
        压缩图片以减少文件大小
        
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
            
            # 如果图片太大，调整尺寸
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                ratio = min(max_dimension / img.width, max_dimension / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 保存为 JPEG 格式（压缩）
            output_path = image_path.replace(".png", ".jpg").replace(".PNG", ".jpg")
            if output_path == image_path:
                output_path = image_path.rsplit(".", 1)[0] + "_compressed.jpg"
            
            # 调整质量直到文件大小符合要求
            quality = 85
            while quality > 10:
                img.save(output_path, "JPEG", quality=quality, optimize=True)
                file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
                if file_size_mb <= max_size_mb:
                    break
                quality -= 10
            
            logger.info(f"Image compressed: {Path(image_path).stat().st_size / 1024:.1f}KB -> {Path(output_path).stat().st_size / 1024:.1f}KB")
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
```

### 3. 检测结果数据结构

**文件**: `detection_result.py`

```python
"""检测结果数据结构"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class DetectionResult:
    """车辆检测结果"""
    vehicle_type: str  # 车辆类型
    confidence: float  # 置信度 (0.0-1.0)
    plate_number: Optional[str] = None  # 车牌号
    timestamp: Optional[datetime] = None  # 检测时间
    image_path: Optional[str] = None  # 快照路径
    bbox: Optional[tuple] = None  # 边界框 (x1, y1, x2, y2)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 规范化车辆类型
        vehicle_type_map = {
            "excavator": "Excavator",
            "bulldozer": "Bulldozer",
            "crane": "Crane",
            "dump_truck": "Dump Truck",
            "loader": "Loader",
            "truck": "Dump Truck",
        }
        self.vehicle_type = vehicle_type_map.get(
            self.vehicle_type.lower(),
            self.vehicle_type.title()
        )
```

### 4. 主集成模块

**文件**: `main_integration.py`

```python
"""主集成模块 - 连接 AI 检测与云端上传"""

import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

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
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def start(self):
        """启动上传线程"""
        if self.running:
            logger.warning("Integration already running")
            return
        
        self.running = True
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
        logger.info("Sentinel integration started")
    
    def stop(self):
        """停止上传线程"""
        self.running = False
        if self.upload_thread:
            self.upload_thread.join(timeout=5)
        logger.info("Sentinel integration stopped")
    
    def on_detection(self, detection: DetectionResult):
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
    
    def _upload_worker(self):
        """上传工作线程"""
        while self.running:
            try:
                # 从队列获取检测结果（阻塞，最多等待1秒）
                try:
                    detection = self.detection_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 上传警报
                alert_id = self.cloud_client.send_alert(
                    vehicle_type=detection.vehicle_type,
                    timestamp=detection.timestamp,
                    plate_number=detection.plate_number,
                    confidence=detection.confidence
                )
                
                # 上传图片（如果存在）
                if detection.image_path and Path(detection.image_path).exists():
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
```

### 5. 使用示例

**文件**: `example_usage.py`

```python
"""使用示例 - 展示如何集成到现有的 AI 检测代码中"""

from datetime import datetime
from pathlib import Path

from main_integration import SentinelIntegration
from detection_result import DetectionResult


def example_with_yolo_detection():
    """示例：与 YOLO 检测集成"""
    # 1. 初始化集成模块
    integration = SentinelIntegration()
    integration.start()
    
    # 2. 模拟 AI 检测循环
    # （在实际代码中，这里会是你的 YOLO/TensorRT 检测循环）
    while True:
        # 假设这是你的检测结果
        detection = DetectionResult(
            vehicle_type="Excavator",
            confidence=0.95,
            plate_number="ABC-1234",  # 如果有 OCR 识别
            timestamp=datetime.now(),
            image_path="/path/to/snapshot.jpg"  # 保存的快照路径
        )
        
        # 3. 发送检测结果到云端
        integration.on_detection(detection)
        
        # 你的其他处理逻辑...
        # time.sleep(1)


def example_with_tensorrt():
    """示例：与 TensorRT 检测集成"""
    from main_integration import SentinelIntegration
    from detection_result import DetectionResult
    import cv2
    
    integration = SentinelIntegration()
    integration.start()
    
    # 假设你已经加载了 TensorRT 模型
    # trt_model = load_tensorrt_model("vehicle_detector.trt")
    
    cap = cv2.VideoCapture(0)  # 或视频文件路径
    
    frame_count = 0
    upload_interval = 30  # 每30帧上传一次（控制上传频率）
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # 运行检测
        # detections = trt_model.detect(frame)
        
        # 模拟检测结果
        if frame_count % upload_interval == 0:
            # 保存快照
            snapshot_path = f"/tmp/snapshot_{frame_count}.jpg"
            cv2.imwrite(snapshot_path, frame)
            
            detection = DetectionResult(
                vehicle_type="Bulldozer",
                confidence=0.88,
                timestamp=datetime.now(),
                image_path=snapshot_path
            )
            
            integration.on_detection(detection)
        
        # 显示画面（可选）
        # cv2.imshow("Detection", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break
    
    cap.release()
    integration.stop()


def example_minimal():
    """最小化使用示例"""
    from main_integration import SentinelIntegration
    from detection_result import DetectionResult
    
    # 初始化并启动
    integration = SentinelIntegration()
    integration.start()
    
    # 当检测到车辆时
    detection = DetectionResult(
        vehicle_type="Crane",
        confidence=0.92
    )
    integration.on_detection(detection)
    
    # 程序退出时
    integration.stop()
```

## 目录结构

建议的 Jetson 端项目结构：

```
jetson-sentinel-client/
├── config.py              # 配置管理
├── cloud_client.py        # 云端 API 客户端
├── detection_result.py    # 检测结果数据结构
├── main_integration.py    # 主集成模块
├── example_usage.py       # 使用示例
├── requirements.txt       # Python 依赖
├── .env                   # 环境变量配置（不要提交到 Git）
└── README.md             # 说明文档
```

## 依赖安装

**requirements.txt**:

```txt
requests>=2.31.0
Pillow>=10.0.0
opencv-python>=4.8.0  # 如果需要图像处理
numpy>=1.24.0  # 通常 AI 框架需要
```

安装命令：

```bash
pip install -r requirements.txt
```

## 配置说明

### 环境变量配置

创建 `.env` 文件：

```bash
# 云端服务器地址
CLOUD_API_URL=http://your-server-ip:8000

# API 密钥（从云端服务器 .env 文件中获取）
CLOUD_API_KEY=your-secure-api-key-here

# 上传间隔（秒）
UPLOAD_INTERVAL=10

# 最大图片大小（MB）
MAX_IMAGE_SIZE_MB=5

# 是否启用图片上传
ENABLE_IMAGE_UPLOAD=true

# 是否启用警报上传
ENABLE_ALERT_UPLOAD=true
```

### 从代码中配置

```python
from config import CloudConfig
from main_integration import SentinelIntegration

config = CloudConfig(
    api_base_url="http://192.168.1.100:8000",
    api_key="your-api-key",
    upload_interval=10,
    enable_image_upload=True
)

integration = SentinelIntegration(config)
integration.start()
```

## 最佳实践

### 1. 错误处理

- **网络错误**: 实现重试机制（已包含在 CloudClient 中）
- **队列满**: 监控队列大小，必要时丢弃旧数据
- **磁盘空间**: 定期清理本地快照文件

### 2. 性能优化

- **批量上传**: 如果检测频率很高，考虑批量上传
- **图片压缩**: 自动压缩大图片（已实现）
- **异步上传**: 使用后台线程上传，不阻塞检测循环

### 3. 资源管理

- **内存**: 及时释放不需要的图片数据
- **磁盘**: 定期清理本地快照（上传成功后删除）
- **网络**: 限制上传频率，避免占用过多带宽

### 4. 监控和日志

```python
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/sentinel_client.log"),
        logging.StreamHandler()
    ]
)
```

### 5. 本地快照管理

```python
def save_snapshot(frame, output_dir: str = "/tmp/snapshots") -> str:
    """保存快照并返回路径"""
    from datetime import datetime
    import cv2
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/snapshot_{timestamp}.jpg"
    cv2.imwrite(path, frame)
    return path


def cleanup_old_snapshots(directory: str, max_age_hours: int = 24):
    """清理旧的快照文件"""
    from datetime import datetime, timedelta
    from pathlib import Path
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    for file_path in Path(directory).glob("*.jpg"):
        if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
            file_path.unlink()
```

## 测试

### 1. 测试云端连接

```python
from cloud_client import CloudClient
from config import CloudConfig

config = CloudConfig(
    api_base_url="http://your-server:8000",
    api_key="your-api-key"
)
client = CloudClient(config)

# 测试连接
if client.health_check():
    print("✅ Cloud server is reachable")
else:
    print("❌ Cannot reach cloud server")
```

### 2. 测试发送警报

```python
from datetime import datetime
from cloud_client import CloudClient
from config import CloudConfig

config = CloudConfig(
    api_base_url="http://your-server:8000",
    api_key="your-api-key"
)
client = CloudClient(config)

# 发送测试警报
alert_id = client.send_alert(
    vehicle_type="Excavator",
    timestamp=datetime.now(),
    confidence=0.95
)
print(f"Alert ID: {alert_id}")
```

### 3. 测试上传图片

```python
from cloud_client import CloudClient
from config import CloudConfig

config = CloudConfig(
    api_base_url="http://your-server:8000",
    api_key="your-api-key"
)
client = CloudClient(config)

# 上传测试图片
image_path = client.upload_image("/path/to/test_image.jpg")
print(f"Image uploaded: {image_path}")
```

## 故障排查

### 常见问题

1. **连接超时**
   - 检查服务器 IP 地址和端口是否正确
   - 检查防火墙设置
   - 确认服务器服务正在运行

2. **认证失败**
   - 验证 API_KEY 是否正确
   - 检查请求头是否正确设置

3. **图片上传失败**
   - 检查文件大小是否超过限制
   - 验证文件路径是否正确
   - 检查磁盘空间是否充足

4. **队列阻塞**
   - 增加队列大小
   - 检查网络连接
   - 考虑降低上传频率

## 与现有代码集成

### 集成到 YOLOv5/YOLOv8

```python
# 在你的 YOLO 检测循环中
from main_integration import SentinelIntegration
from detection_result import DetectionResult

integration = SentinelIntegration()
integration.start()

# 在检测循环中
for detection in model(frame):
    if detection.conf > 0.5:  # 置信度阈值
        result = DetectionResult(
            vehicle_type=detection.class_name,
            confidence=float(detection.conf),
            timestamp=datetime.now()
        )
        integration.on_detection(result)
```

### 集成到 TensorRT 推理

```python
# 类似的方式集成到 TensorRT 推理流程
```

## 下一步

1. **实现车牌识别**: 添加 OCR 模块识别车牌号
2. **轨迹跟踪**: 避免重复上传同一车辆
3. **本地缓存**: 网络断开时缓存数据，恢复后上传
4. **性能监控**: 添加性能指标收集

## 支持

如有问题，请检查：
1. 云端服务器日志: `docker-compose logs backend`
2. Jetson 端日志: `/var/log/sentinel_client.log`
3. 网络连接: `ping your-server-ip`
4. API 健康状态: 访问 `http://your-server:8000/health`

