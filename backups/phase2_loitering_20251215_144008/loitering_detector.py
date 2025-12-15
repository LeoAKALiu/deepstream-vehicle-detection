"""
徘徊检测模块 (Phase 2优化)

实现车辆徘徊判定，减少路过车辆的误报。
只对"未备案"车辆应用徘徊判定，已备案车辆立即报警。
"""

import numpy as np
from typing import Optional, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass
import time


@dataclass
class TrackPosition:
    """跟踪位置信息"""
    timestamp: float
    bbox_center: Tuple[float, float]  # (x, y)
    area: float  # 画面占比 (0-1)


class LoiteringDetector:
    """
    徘徊检测器
    
    检测车辆是否满足徘徊条件：
    1. 停留时间 >= min_duration
    2. 画面占比 >= min_area_ratio
    3. 移动距离 < min_movement_ratio（归一化）
    """
    
    def __init__(
        self,
        min_duration: float = 10.0,
        min_area_ratio: float = 0.05,
        min_movement_ratio: float = 0.1
    ):
        """
        初始化徘徊检测器
        
        Args:
            min_duration: 最少停留时间（秒）
            min_area_ratio: 最小画面占比（0-1），太小可能是边缘路过
            min_movement_ratio: 最小移动比例（归一化，0-1），小于此值认为是徘徊
        """
        self.min_duration = min_duration
        self.min_area_ratio = min_area_ratio
        self.min_movement_ratio = min_movement_ratio
        
        # 为每个track_id维护位置历史
        self.track_enter_time: Dict[int, float] = {}  # {track_id: enter_timestamp}
        self.track_positions: Dict[int, list] = defaultdict(list)  # {track_id: [TrackPosition, ...]}
        
        # 最大保留位置数量（防止内存无限增长）
        self.max_positions = 100
    
    def update(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        frame_shape: Tuple[int, int, int],
        current_time: Optional[float] = None
    ):
        """
        更新跟踪信息
        
        Args:
            track_id: 跟踪ID
            bbox: 边界框 [x1, y1, x2, y2]
            frame_shape: 帧形状 (height, width, channels)
            current_time: 当前时间戳（秒），如果为None则使用time.time()
        """
        if current_time is None:
            current_time = time.time()
        
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = bbox
        
        # 计算中心点和面积
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        bbox_area = (x2 - x1) * (y2 - y1)
        frame_area = w * h
        area_ratio = bbox_area / frame_area if frame_area > 0 else 0.0
        
        # 记录进入时间
        if track_id not in self.track_enter_time:
            self.track_enter_time[track_id] = current_time
            self.track_positions[track_id] = []
        
        # 添加位置信息
        position = TrackPosition(
            timestamp=current_time,
            bbox_center=(center_x, center_y),
            area=area_ratio
        )
        self.track_positions[track_id].append(position)
        
        # 限制历史长度
        if len(self.track_positions[track_id]) > self.max_positions:
            self.track_positions[track_id].pop(0)
    
    def is_loitering(
        self,
        track_id: int,
        current_time: Optional[float] = None
    ) -> bool:
        """
        判断是否满足徘徊条件
        
        Args:
            track_id: 跟踪ID
            current_time: 当前时间戳（秒），如果为None则使用time.time()
        
        Returns:
            bool: 如果满足徘徊条件返回True，否则返回False
        """
        if current_time is None:
            current_time = time.time()
        
        # 检查是否是新track
        if track_id not in self.track_enter_time:
            return False
        
        # 检查停留时间
        duration = current_time - self.track_enter_time[track_id]
        if duration < self.min_duration:
            return False  # 停留时间不足
        
        # 检查位置历史
        positions = self.track_positions[track_id]
        if len(positions) < 10:
            return False  # 位置历史不足
        
        # 检查画面占比（太小可能是边缘路过）
        recent_areas = [pos.area for pos in positions[-10:]]
        avg_area = np.mean(recent_areas)
        if avg_area < self.min_area_ratio:
            return False  # 画面占比太小，可能是路过
        
        # 检查移动距离（如果移动距离很小，说明是徘徊）
        recent_positions = [pos.bbox_center for pos in positions[-10:]]
        positions_array = np.array(recent_positions)
        
        # 计算最大移动距离（归一化）
        if len(positions_array) > 1:
            movement_x = np.max(positions_array[:, 0]) - np.min(positions_array[:, 0])
            movement_y = np.max(positions_array[:, 1]) - np.min(positions_array[:, 1])
            max_movement = np.sqrt(movement_x**2 + movement_y**2)
            
            # 归一化：使用frame宽度作为参考（假设frame宽度约为1920像素）
            # 如果最大移动距离小于frame宽度的min_movement_ratio倍，认为是徘徊
            # 例如：frame宽度1920，min_movement_ratio=0.1，则移动距离<192像素认为是徘徊
            frame_width_ref = 1920.0  # 参考frame宽度
            normalized_movement = max_movement / frame_width_ref if frame_width_ref > 0 else 0.0
            
            # 如果移动距离很小，说明是徘徊
            if normalized_movement < self.min_movement_ratio:
                return True
        
        return False
    
    def reset(self, track_id: int):
        """
        重置指定track的徘徊检测状态
        
        Args:
            track_id: 跟踪ID
        """
        if track_id in self.track_enter_time:
            del self.track_enter_time[track_id]
        if track_id in self.track_positions:
            del self.track_positions[track_id]
    
    def cleanup(self, active_track_ids: set):
        """
        清理已结束的track
        
        Args:
            active_track_ids: 当前活跃的track ID集合
        """
        expired_tracks = (
            set(self.track_enter_time.keys()) |
            set(self.track_positions.keys())
        ) - active_track_ids
        
        for track_id in expired_tracks:
            self.reset(track_id)
    
    def get_duration(self, track_id: int, current_time: Optional[float] = None) -> float:
        """
        获取指定track的停留时间
        
        Args:
            track_id: 跟踪ID
            current_time: 当前时间戳（秒）
        
        Returns:
            float: 停留时间（秒），如果track不存在返回0.0
        """
        if current_time is None:
            current_time = time.time()
        
        if track_id not in self.track_enter_time:
            return 0.0
        
        return current_time - self.track_enter_time[track_id]

