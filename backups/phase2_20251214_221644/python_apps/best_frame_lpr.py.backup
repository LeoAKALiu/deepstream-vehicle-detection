"""
LPR最佳帧选取模块 (Phase 2优化)

实现帧质量评分机制，等待最佳帧出现后再触发识别，提升识别成功率。
"""

import numpy as np
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TrackInfo:
    """跟踪信息"""
    best_quality: float = 0.0
    best_frame_data: Optional[Tuple] = None  # (roi_bgr, bbox, distance, frame_shape)
    best_frame_id: int = 0
    frame_count: int = 0
    recognition_done: bool = False  # 是否已完成识别


def calculate_frame_quality(
    bbox: Tuple[float, float, float, float],
    confidence: float,
    frame_shape: Tuple[int, int, int],
    distance: Optional[float] = None
) -> float:
    """
    计算帧质量分数
    
    Args:
        bbox: 边界框 [x1, y1, x2, y2]
        confidence: 检测置信度 (0-1)
        frame_shape: 帧形状 (height, width, channels)
        distance: 距离（米），可选
    
    Returns:
        score: 0-1之间，越高越好
    """
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = bbox
    
    # 1. BBox面积（越大越好，但不要太大）
    bbox_area = (x2 - x1) * (y2 - y1)
    frame_area = w * h
    area_ratio = bbox_area / frame_area if frame_area > 0 else 0.0
    # 理想占比30%，超过此值不会额外加分
    area_score = min(area_ratio / 0.3, 1.0)
    
    # 2. 检测置信度
    conf_score = confidence
    
    # 3. 位置分数（中心区域更好）
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
    center_dist = ((center_x - w/2)**2 + (center_y - h/2)**2) ** 0.5
    max_dist = ((w/2)**2 + (h/2)**2) ** 0.5
    position_score = 1.0 - (center_dist / max_dist) * 0.5 if max_dist > 0 else 1.0  # 中心区域得分更高
    
    # 4. 距离分数（如果有深度信息，3-6米最佳）
    distance_score = 1.0
    if distance is not None:
        if 3.0 <= distance <= 6.0:
            distance_score = 1.0
        elif distance < 3.0:
            distance_score = max(0.5, distance / 3.0)
        else:
            distance_score = max(0.5, 1.0 - (distance - 6.0) / 10.0)
    
    # 加权平均
    total_score = (
        0.3 * area_score +
        0.3 * conf_score +
        0.2 * position_score +
        0.2 * distance_score
    )
    
    return total_score


class BestFrameLPR:
    """
    最佳帧LPR选择器
    
    为每个track维护帧质量历史，等待最佳帧出现后再触发识别。
    """
    
    def __init__(self, quality_threshold=0.6, max_wait_frames=30, reuse_result=True):
        """
        初始化最佳帧选择器
        
        Args:
            quality_threshold: 质量分数阈值，达到此值后立即触发
            max_wait_frames: 最多等待帧数，超时后使用当前最佳帧
            reuse_result: 识别成功后是否复用结果
        """
        self.quality_threshold = quality_threshold
        self.max_wait_frames = max_wait_frames
        self.reuse_result = reuse_result
        self.track_queue: Dict[int, TrackInfo] = {}
        self.recognition_results: Dict[int, Tuple[str, float]] = {}  # {track_id: (plate_number, confidence)}
    
    def should_trigger_lpr(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        roi_bgr: np.ndarray,
        confidence: float,
        frame_shape: Tuple[int, int, int],
        distance: Optional[float] = None
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """
        判断是否应该触发LPR识别
        
        Args:
            track_id: 跟踪ID
            bbox: 边界框
            roi_bgr: 车辆ROI（BGR格式）
            confidence: 检测置信度
            frame_shape: 帧形状
            distance: 距离（米），可选
        
        Returns:
            (should_trigger, best_roi): 是否触发，最佳帧的ROI
        """
        # 如果已完成识别且启用结果复用，直接返回False
        if self.reuse_result and track_id in self.recognition_results:
            return False, None
        
        # 计算当前帧质量
        quality = calculate_frame_quality(bbox, confidence, frame_shape, distance)
        
        if track_id not in self.track_queue:
            # 新track，加入队列
            self.track_queue[track_id] = TrackInfo()
            self.track_queue[track_id].best_frame_data = (roi_bgr.copy(), bbox, distance, frame_shape)
            self.track_queue[track_id].best_quality = quality
            self.track_queue[track_id].frame_count = 1
            self.track_queue[track_id].best_frame_id = 0
        else:
            # 更新队列中的最佳帧
            info = self.track_queue[track_id]
            
            if quality > info.best_quality:
                info.best_quality = quality
                info.best_frame_data = (roi_bgr.copy(), bbox, distance, frame_shape)
                info.best_frame_id = info.frame_count
            
            info.frame_count += 1
        
        info = self.track_queue[track_id]
        
        # 触发条件
        if info.best_quality >= self.quality_threshold:
            # 质量达到阈值，使用最佳帧
            best_roi = info.best_frame_data[0]
            info.recognition_done = True
            return True, best_roi
        elif info.frame_count >= self.max_wait_frames:
            # 超时，使用当前最佳帧
            if info.best_frame_data:
                best_roi = info.best_frame_data[0]
                info.recognition_done = True
                return True, best_roi
            else:
                # 没有最佳帧，使用当前帧
                info.recognition_done = True
                return True, roi_bgr.copy()
        
        # 继续等待
        return False, None
    
    def on_lpr_complete(self, track_id: int, plate_number: Optional[str], confidence: float):
        """
        识别完成后调用
        
        Args:
            track_id: 跟踪ID
            plate_number: 识别到的车牌号，如果失败则为None
            confidence: 识别置信度
        """
        if track_id in self.track_queue:
            self.track_queue[track_id].recognition_done = True
        
        if plate_number and self.reuse_result:
            # 保存识别结果
            self.recognition_results[track_id] = (plate_number, confidence)
    
    def get_result(self, track_id: int) -> Optional[Tuple[str, float]]:
        """
        获取识别结果（如果已识别）
        
        Args:
            track_id: 跟踪ID
        
        Returns:
            (plate_number, confidence) 或 None
        """
        return self.recognition_results.get(track_id)
    
    def reset(self, track_id: int):
        """重置指定track"""
        if track_id in self.track_queue:
            del self.track_queue[track_id]
        if track_id in self.recognition_results:
            del self.recognition_results[track_id]
    
    def cleanup(self, active_track_ids: set):
        """清理已结束的track"""
        expired_tracks = set(self.track_queue.keys()) - active_track_ids
        for track_id in expired_tracks:
            self.reset(track_id)

