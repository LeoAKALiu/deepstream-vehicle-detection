"""配置管理模块 - 存储云端 API 连接信息"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CloudConfig:
    """云端配置"""
    api_base_url: str = "http://123.249.9.250:8000"
    api_key: str = "kS3EhgTObprA48ruPkMg08DRX95x8ftv"
    upload_interval: int = 10  # 上传间隔（秒）
    max_image_size_mb: int = 5  # 最大图片大小
    enable_image_upload: bool = True  # 是否上传图片
    enable_alert_upload: bool = True  # 是否上传警报
    retry_attempts: int = 3  # 重试次数
    retry_delay: float = 2.0  # 重试延迟（秒）
    save_snapshots: bool = True  # 是否保存本地快照


def load_config() -> CloudConfig:
    """
    从环境变量或配置文件加载配置
    
    Returns:
        CloudConfig: 云端配置对象
    """
    return CloudConfig(
        api_base_url=os.getenv("CLOUD_API_URL", "http://your-server-ip:8000"),
        api_key=os.getenv("CLOUD_API_KEY", "your-api-key-here"),
        upload_interval=int(os.getenv("UPLOAD_INTERVAL", "10")),
        max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "5")),
        enable_image_upload=os.getenv("ENABLE_IMAGE_UPLOAD", "true").lower() == "true",
        enable_alert_upload=os.getenv("ENABLE_ALERT_UPLOAD", "true").lower() == "true",
        retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
        retry_delay=float(os.getenv("RETRY_DELAY", "2.0")),
        save_snapshots=os.getenv("SAVE_SNAPSHOTS", "true").lower() == "true",
    )

