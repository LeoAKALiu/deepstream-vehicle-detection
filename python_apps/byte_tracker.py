#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ByteTrack跟踪器实现
基于论文: ByteTrack: Multi-Object Tracking by Associating Every Detection Box
核心思想: 利用低置信度检测框提升跟踪稳定性
"""

import numpy as np
from collections import defaultdict
from typing import List, Tuple, Dict, Optional


class STrack:
    """单个跟踪目标"""
    
    def __init__(self, bbox: np.ndarray, score: float, class_id: int, track_id: int, frame_id: int):
        """
        初始化跟踪目标
        
        Args:
            bbox: [x1, y1, x2, y2]
            score: 检测置信度
            class_id: 类别ID
            track_id: 跟踪ID
            frame_id: 当前帧ID
        """
        self.bbox = bbox.copy()
        self.score = score
        self.class_id = class_id
        self.track_id = track_id
        self.frame_id = frame_id
        self.state = 'Tracked'  # Tracked, Lost, Removed
        self.hits = 1  # 连续匹配次数
        self.time_since_update = 0
        self.processed = False  # 是否已处理（用于报警）
    
    def update(self, bbox: np.ndarray, score: float, frame_id: int):
        """更新跟踪目标"""
        self.bbox = bbox.copy()
        self.score = score
        self.frame_id = frame_id
        self.hits += 1
        self.time_since_update = 0
        self.state = 'Tracked'
    
    def mark_lost(self):
        """标记为丢失"""
        self.state = 'Lost'
        self.time_since_update += 1
    
    def mark_removed(self):
        """标记为移除"""
        self.state = 'Removed'


class ByteTracker:
    """ByteTrack跟踪器"""
    
    def __init__(self, 
                 track_thresh: float = 0.5,
                 high_thresh: float = 0.6,
                 match_thresh: float = 0.8,
                 frame_rate: int = 30,
                 track_buffer: int = 30):
        """
        初始化ByteTrack跟踪器
        
        Args:
            track_thresh: 跟踪阈值（低于此值的检测框也会被使用）
            high_thresh: 高置信度阈值（用于第一次匹配）
            match_thresh: IoU匹配阈值
            frame_rate: 帧率（用于时间相关计算）
            track_buffer: 跟踪缓冲区大小（最大消失帧数）
        """
        self.track_thresh = track_thresh
        self.high_thresh = high_thresh
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        self.track_buffer = track_buffer
        
        self.tracked_stracks: List[STrack] = []  # 正在跟踪的目标
        self.lost_stracks: List[STrack] = []      # 丢失的目标
        self.removed_stracks: List[STrack] = []   # 已移除的目标
        
        self.frame_id = 0
        self.next_id = 1
    
    def compute_iou(self, box1: np.ndarray, box2: np.ndarray) -> float:
        """计算IoU（向量化版本，支持批量计算）"""
        if isinstance(box1, np.ndarray) and box1.ndim == 1:
            # 单个box计算
            x1_min, y1_min, x1_max, y1_max = box1
            x2_min, y2_min, x2_max, y2_max = box2
            
            inter_x_min = max(x1_min, x2_min)
            inter_y_min = max(y1_min, y2_min)
            inter_x_max = min(x1_max, x2_max)
            inter_y_max = min(y1_max, y2_max)
            
            if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
                return 0.0
            
            inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
            box1_area = (x1_max - x1_min) * (y1_max - y1_min)
            box2_area = (x2_max - x2_min) * (y2_max - y2_min)
            union_area = box1_area + box2_area - inter_area
            
            return inter_area / union_area if union_area > 0 else 0.0
        else:
            # 批量计算（向量化）
            return self._compute_iou_batch(box1, box2)
    
    def _compute_iou_batch(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """批量计算IoU矩阵（向量化实现）"""
        # boxes1: [N, 4], boxes2: [M, 4]
        # 返回: [N, M]
        
        # 扩展维度进行广播
        boxes1 = boxes1[:, None, :]  # [N, 1, 4]
        boxes2 = boxes2[None, :, :]   # [1, M, 4]
        
        # 计算交集
        inter_x_min = np.maximum(boxes1[:, :, 0], boxes2[:, :, 0])
        inter_y_min = np.maximum(boxes1[:, :, 1], boxes2[:, :, 1])
        inter_x_max = np.minimum(boxes1[:, :, 2], boxes2[:, :, 2])
        inter_y_max = np.minimum(boxes1[:, :, 3], boxes2[:, :, 3])
        
        # 交集面积
        inter_w = np.maximum(0, inter_x_max - inter_x_min)
        inter_h = np.maximum(0, inter_y_max - inter_y_min)
        inter_area = inter_w * inter_h
        
        # 各自面积
        boxes1_area = (boxes1[:, :, 2] - boxes1[:, :, 0]) * (boxes1[:, :, 3] - boxes1[:, :, 1])
        boxes2_area = (boxes2[:, :, 2] - boxes2[:, :, 0]) * (boxes2[:, :, 3] - boxes2[:, :, 1])
        
        # 并集面积
        union_area = boxes1_area + boxes2_area - inter_area
        
        # IoU
        iou = np.where(union_area > 0, inter_area / union_area, 0.0)
        return iou
    
    def iou_distance(self, tracks: List[STrack], detections: List[STrack]) -> np.ndarray:
        """计算IoU距离矩阵（向量化实现）"""
        if len(tracks) == 0 or len(detections) == 0:
            return np.zeros((len(tracks), len(detections)))
        
        # 批量提取bbox
        track_boxes = np.array([track.bbox for track in tracks])  # [N, 4]
        det_boxes = np.array([det.bbox for det in detections])    # [M, 4]
        
        # 向量化计算IoU矩阵
        iou_matrix = self._compute_iou_batch(track_boxes, det_boxes)  # [N, M]
        
        # 转换为距离矩阵（1 - IoU）
        cost_matrix = 1.0 - iou_matrix
        
        return cost_matrix
    
    def linear_assignment(self, cost_matrix: np.ndarray, thresh: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        线性分配（使用scipy的匈牙利算法，更准确）
        如果scipy不可用，回退到贪心算法
        """
        if cost_matrix.size == 0:
            return np.array([]), np.array([]), np.array([])
        
        try:
            # 尝试使用scipy的匈牙利算法（更准确）
            from scipy.optimize import linear_sum_assignment
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            # 过滤：只保留代价低于阈值的匹配
            matches = []
            for i, j in zip(row_indices, col_indices):
                if cost_matrix[i, j] <= (1.0 - thresh):
                    matches.append((i, j))
            
            matches = np.array(matches) if matches else np.array([]).reshape(0, 2)
            matched_rows = set(matches[:, 0]) if len(matches) > 0 else set()
            matched_cols = set(matches[:, 1]) if len(matches) > 0 else set()
            
            unmatched_tracks = np.array([i for i in range(len(cost_matrix)) if i not in matched_rows])
            unmatched_dets = np.array([j for j in range(cost_matrix.shape[1]) if j not in matched_cols])
            
            return matches, unmatched_tracks, unmatched_dets
            
        except ImportError:
            # 回退到贪心算法（如果scipy不可用）
            matches = []
            unmatched_tracks = list(range(len(cost_matrix)))
            unmatched_dets = list(range(cost_matrix.shape[1]))
            
            # 贪心匹配
            while True:
                if len(unmatched_tracks) == 0 or len(unmatched_dets) == 0:
                    break
                
                # 找到最小代价
                min_cost = float('inf')
                min_i, min_j = -1, -1
                
                for i in unmatched_tracks:
                    for j in unmatched_dets:
                        if cost_matrix[i, j] < min_cost:
                            min_cost = cost_matrix[i, j]
                            min_i, min_j = i, j
                
                # 如果最小代价超过阈值，停止匹配
                if min_cost > (1.0 - thresh):
                    break
                
                matches.append((min_i, min_j))
                unmatched_tracks.remove(min_i)
                unmatched_dets.remove(min_j)
            
            matches = np.array(matches) if matches else np.array([]).reshape(0, 2)
            unmatched_tracks = np.array(unmatched_tracks)
            unmatched_dets = np.array(unmatched_dets)
            
            return matches, unmatched_tracks, unmatched_dets
    
    def update(self, boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, frame_id: int) -> Dict[int, Dict]:
        """
        更新跟踪
        
        Args:
            boxes: 检测框 [N, 4] (x1, y1, x2, y2)
            scores: 置信度 [N]
            class_ids: 类别ID [N]
            frame_id: 帧ID
        
        Returns:
            tracks字典 {track_id: {'bbox': ..., 'class': ..., 'processed': ...}}
        """
        self.frame_id = frame_id
        
        # 分离高置信度和低置信度检测
        high_mask = scores >= self.high_thresh
        low_mask = (scores >= self.track_thresh) & (scores < self.high_thresh)
        
        detections_high = []
        detections_low = []
        
        for i, (box, score, cls_id) in enumerate(zip(boxes, scores, class_ids)):
            if high_mask[i]:
                detections_high.append(STrack(box, score, cls_id, -1, frame_id))
            elif low_mask[i]:
                detections_low.append(STrack(box, score, cls_id, -1, frame_id))
        
        # 按类别分组跟踪
        tracks_by_class = defaultdict(list)
        for track in self.tracked_stracks:
            tracks_by_class[track.class_id].append(track)
        
        detections_high_by_class = defaultdict(list)
        for det in detections_high:
            detections_high_by_class[det.class_id].append(det)
        
        detections_low_by_class = defaultdict(list)
        for det in detections_low:
            detections_low_by_class[det.class_id].append(det)
        
        # 对每个类别分别进行跟踪
        new_tracked_stracks = []
        new_lost_stracks = []
        
        all_class_ids = set(tracks_by_class.keys()) | set(detections_high_by_class.keys()) | set(detections_low_by_class.keys())
        
        for class_id in all_class_ids:
            class_tracks = tracks_by_class[class_id]
            class_dets_high = detections_high_by_class[class_id]
            class_dets_low = detections_low_by_class[class_id]
            
            # 第一次匹配：高置信度检测与已跟踪目标
            if len(class_tracks) > 0 and len(class_dets_high) > 0:
                cost_matrix = self.iou_distance(class_tracks, class_dets_high)
                matches, unmatched_tracks, unmatched_dets = self.linear_assignment(cost_matrix, self.match_thresh)
                
                # 更新匹配的跟踪
                for m in matches:
                    track_idx, det_idx = m
                    class_tracks[track_idx].update(
                        class_dets_high[det_idx].bbox,
                        class_dets_high[det_idx].score,
                        frame_id
                    )
                    new_tracked_stracks.append(class_tracks[track_idx])
                
                # 未匹配的跟踪和检测
                unmatched_tracks_list = [class_tracks[i] for i in unmatched_tracks]
                unmatched_dets_high = [class_dets_high[i] for i in unmatched_dets]
            else:
                unmatched_tracks_list = class_tracks
                unmatched_dets_high = class_dets_high
            
            # 第二次匹配：低置信度检测与未匹配的跟踪（ByteTrack的核心创新）
            if len(unmatched_tracks_list) > 0 and len(class_dets_low) > 0:
                cost_matrix = self.iou_distance(unmatched_tracks_list, class_dets_low)
                matches, unmatched_tracks, unmatched_dets = self.linear_assignment(cost_matrix, self.match_thresh)
                
                # 更新匹配的跟踪
                for m in matches:
                    track_idx, det_idx = m
                    unmatched_tracks_list[track_idx].update(
                        class_dets_low[det_idx].bbox,
                        class_dets_low[det_idx].score,
                        frame_id
                    )
                    new_tracked_stracks.append(unmatched_tracks_list[track_idx])
                
                # 剩余的未匹配跟踪
                unmatched_tracks_list = [unmatched_tracks_list[i] for i in unmatched_tracks]
            
            # 处理未匹配的跟踪（标记为丢失或移除）
            for track in unmatched_tracks_list:
                track.mark_lost()
                if track.time_since_update < self.track_buffer:
                    new_lost_stracks.append(track)
                else:
                    track.mark_removed()
                    self.removed_stracks.append(track)
            
            # 为未匹配的高置信度检测创建新跟踪
            for det in unmatched_dets_high:
                det.track_id = self.next_id
                det.processed = False  # 新track未处理
                self.next_id += 1
                new_tracked_stracks.append(det)
        
        # 更新跟踪列表
        self.tracked_stracks = new_tracked_stracks
        self.lost_stracks = new_lost_stracks
        
        # 转换为字典格式（兼容原有接口）
        tracks_dict = {}
        for track in self.tracked_stracks:
            tracks_dict[track.track_id] = {
                'bbox': track.bbox,
                'class': track.class_id,
                'last_seen': track.frame_id,
                'processed': track.processed,
                'score': track.score,
                'hits': track.hits
            }
        
        return tracks_dict
    
    def get_tracks(self) -> Dict[int, Dict]:
        """获取当前所有跟踪（兼容接口）"""
        tracks_dict = {}
        for track in self.tracked_stracks:
            tracks_dict[track.track_id] = {
                'bbox': track.bbox,
                'class': track.class_id,
                'last_seen': track.frame_id,
                'processed': track.processed,
                'score': track.score,
                'hits': track.hits
            }
        return tracks_dict
    
    def mark_processed(self, track_id: int):
        """标记track为已处理（兼容接口）"""
        for track in self.tracked_stracks:
            if track.track_id == track_id:
                track.processed = True
                break

