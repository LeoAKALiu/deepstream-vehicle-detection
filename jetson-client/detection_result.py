"""检测结果数据结构"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class DetectionResult:
    """车辆检测结果"""
    vehicle_type: str  # 车辆类型: "construction_vehicle" | "social_vehicle"
    confidence: float  # 置信度 (0.0-1.0)
    detected_class: Optional[str] = None  # 检测类别: "excavator", "bulldozer", "car" 等
    status: Optional[str] = None  # 状态: "registered", "unregistered", "identified" 等
    plate_number: Optional[str] = None  # 车牌号
    timestamp: Optional[datetime] = None  # 检测时间
    image_path: Optional[str] = None  # 快照路径
    bbox: Optional[tuple] = None  # 边界框 (x1, y1, x2, y2)
    track_id: Optional[int] = None  # 跟踪ID
    distance: Optional[float] = None  # 距离（米）
    is_registered: Optional[bool] = None  # 是否已备案
    beacon_mac: Optional[str] = None  # 信标MAC地址（工程车辆）
    company: Optional[str] = None  # 所属公司（工程车辆）
    environment_code: Optional[str] = None  # 环境编码（工程车辆，来自云端白名单）
    metadata: Optional[dict] = None  # 元数据（rssi, match_cost等）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 保持 vehicle_type 原值，不进行转换
        # vehicle_type 应该已经是 "construction_vehicle" 或 "social_vehicle"

