"""
深度测量时间平滑模块 (Phase 2优化)

实现深度测量值的时间维度平滑，减少波动，提升稳定性。
"""

import numpy as np
from typing import Optional, Dict
from collections import defaultdict


class TrackDepthSmoother:
    """
    跟踪目标的深度平滑器
    
    使用指数移动平均(EMA)或滑动窗口平均来平滑深度测量值。
    """
    
    def __init__(self, method='ema', alpha=0.7, window_size=5, min_samples=3):
        """
        初始化深度平滑器
        
        Args:
            method: 平滑方法 'ema' (指数移动平均) 或 'median' (滑动中位数)
            alpha: EMA系数 (0-1)，值越大对新值权重越高
            window_size: 滑动窗口大小（用于median方法）
            min_samples: 最小样本数，达到此数量后才开始平滑
        """
        self.method = method
        self.alpha = alpha
        self.window_size = window_size
        self.min_samples = min_samples
        
        # 为每个track_id维护深度历史
        self.track_depths: Dict[int, list] = defaultdict(list)
        self.track_smoothed: Dict[int, Optional[float]] = {}  # 存储上一次的平滑值
    
    def update(self, track_id: int, raw_depth: Optional[float]) -> Optional[float]:
        """
        更新深度值并返回平滑后的结果
        
        Args:
            track_id: 跟踪ID
            raw_depth: 原始深度值（米），如果无效则为None
        
        Returns:
            平滑后的深度值（米），如果无效或样本不足则返回None
        """
        # 如果原始深度无效，不记录，但可以返回上一次的平滑值（可选）
        if raw_depth is None:
            return self.track_smoothed.get(track_id, None)
        
        # 添加新值到历史
        history = self.track_depths[track_id]
        history.append(raw_depth)
        
        # 限制历史长度
        max_history = max(self.window_size * 2, 20)  # 保留足够的历史
        if len(history) > max_history:
            history.pop(0)
        
        # 如果样本不足，返回原始值
        if len(history) < self.min_samples:
            return raw_depth
        
        # 根据方法进行平滑
        if self.method == 'ema':
            smoothed = self._ema_smooth(history, track_id)
        elif self.method == 'median':
            smoothed = self._median_smooth(history)
        else:
            # 默认返回原始值
            smoothed = raw_depth
        
        # 保存平滑值
        self.track_smoothed[track_id] = smoothed
        
        return smoothed
    
    def _ema_smooth(self, history: list, track_id: int) -> float:
        """指数移动平均"""
        if len(history) == self.min_samples:
            # 初始值：使用前N个值的中位数
            initial = np.median(history[:self.min_samples])
            self.track_smoothed[track_id] = initial
            return initial
        
        # EMA: smoothed = alpha * new + (1-alpha) * previous
        previous_smoothed = self.track_smoothed.get(track_id, history[-2])
        current_value = history[-1]
        
        smoothed = self.alpha * current_value + (1 - self.alpha) * previous_smoothed
        return smoothed
    
    def _median_smooth(self, history: list) -> float:
        """滑动窗口中位数"""
        # 使用最近的window_size个值
        recent_values = history[-self.window_size:]
        return float(np.median(recent_values))
    
    def reset(self, track_id: int):
        """重置指定track的深度历史"""
        if track_id in self.track_depths:
            del self.track_depths[track_id]
        if track_id in self.track_smoothed:
            del self.track_smoothed[track_id]
    
    def clear(self):
        """清空所有历史"""
        self.track_depths.clear()
        self.track_smoothed.clear()


def create_depth_smoother(config: dict) -> Optional[TrackDepthSmoother]:
    """
    根据配置创建深度平滑器
    
    Args:
        config: 配置字典，包含smoothing相关配置
    
    Returns:
        TrackDepthSmoother实例，如果未启用则返回None
    """
    smoothing_cfg = config.get('smoothing', {})
    if not smoothing_cfg.get('enabled', False):
        return None
    
    method = smoothing_cfg.get('method', 'ema')
    alpha = smoothing_cfg.get('alpha', 0.7)
    window_size = smoothing_cfg.get('window_size', 5)
    min_samples = smoothing_cfg.get('min_samples', 3)
    
    return TrackDepthSmoother(
        method=method,
        alpha=alpha,
        window_size=window_size,
        min_samples=min_samples
    )

