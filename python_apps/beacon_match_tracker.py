"""
信标匹配时空一致性跟踪器
实现连续帧匹配验证，避免信号波动导致的闪烁式误报
"""

from typing import Dict, Optional, Tuple
from collections import defaultdict
import time


class MatchHistory:
    """单个track的匹配历史"""
    
    def __init__(self):
        self.matches = []  # [(timestamp, beacon_mac, distance, match_cost), ...]
        self.locked_beacon_mac = None  # 已锁定的信标MAC
        self.locked_distance = None  # 锁定时的距离
        self.locked_at = None  # 锁定时间
    
    def add_match(self, beacon_mac: str, distance: float, match_cost: float) -> None:
        """添加一次匹配结果"""
        self.matches.append((time.time(), beacon_mac, distance, match_cost))
    
    def is_locked(self) -> bool:
        """检查是否已锁定"""
        return self.locked_beacon_mac is not None
    
    def get_locked_beacon(self) -> Optional[str]:
        """获取已锁定的信标MAC"""
        return self.locked_beacon_mac
    
    def has_consistent_match(
        self, 
        min_frames: int, 
        max_distance_error: float
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否有连续一致的匹配
        
        Args:
            min_frames: 最小连续帧数
            max_distance_error: 最大距离误差（米）
            
        Returns:
            (是否有连续匹配, 匹配的信标MAC)
        """
        if len(self.matches) < min_frames:
            return False, None
        
        # 检查最近min_frames次匹配是否都是同一个信标
        recent_matches = self.matches[-min_frames:]
        beacon_macs = [m[1] for m in recent_matches]  # 提取信标MAC
        
        # 所有匹配必须是同一个信标
        if len(set(beacon_macs)) != 1:
            return False, None
        
        consistent_beacon = beacon_macs[0]
        
        # 检查距离误差
        distances = [m[2] for m in recent_matches]
        if len(distances) > 1:
            distances = [d for d in distances if d is not None]
            if len(distances) > 1:
                min_dist = min(distances)
                max_dist = max(distances)
                if max_dist - min_dist > max_distance_error:
                    return False, None
        
        return True, consistent_beacon
    
    def lock(self, beacon_mac: str, distance: float) -> None:
        """锁定匹配关系"""
        self.locked_beacon_mac = beacon_mac
        self.locked_distance = distance
        self.locked_at = time.time()
    
    def reset(self) -> None:
        """重置匹配历史"""
        self.matches.clear()
        self.locked_beacon_mac = None
        self.locked_distance = None
        self.locked_at = None


class BeaconMatchTracker:
    """
    信标匹配时空一致性跟踪器
    
    只有当连续N帧都匹配到同一个信标，且距离误差在阈值内时，才锁定匹配关系。
    这可以避免信号波动导致的"闪烁"式误报。
    """
    
    def __init__(
        self,
        min_consistent_frames: int = 5,
        max_distance_error: float = 1.0,
        reset_on_track_end: bool = True
    ):
        """
        初始化跟踪器
        
        Args:
            min_consistent_frames: 最小连续匹配帧数
            max_distance_error: 最大距离误差（米）
            reset_on_track_end: 跟踪结束时是否重置
        """
        self.min_consistent_frames = min_consistent_frames
        self.max_distance_error = max_distance_error
        self.reset_on_track_end = reset_on_track_end
        self.track_matches: Dict[int, MatchHistory] = defaultdict(MatchHistory)
    
    def update_match(
        self,
        track_id: int,
        beacon_mac: Optional[str],
        distance: Optional[float],
        match_cost: Optional[float]
    ) -> Optional[str]:
        """
        更新匹配结果
        
        Args:
            track_id: 跟踪ID
            beacon_mac: 匹配到的信标MAC（如果匹配失败则为None）
            distance: 车辆距离（米）
            match_cost: 匹配代价
            
        Returns:
            如果已锁定匹配关系，返回信标MAC；否则返回None
        """
        history = self.track_matches[track_id]
        
        # 如果已锁定，检查当前匹配是否与锁定的一致
        if history.is_locked():
            if beacon_mac == history.locked_beacon_mac:
                # 匹配一致，保持锁定
                if distance is not None:
                    # 更新距离（平滑）
                    if history.locked_distance is None:
                        history.locked_distance = distance
                    else:
                        # 简单滑动平均
                        alpha = 0.7
                        history.locked_distance = (
                            alpha * history.locked_distance + (1 - alpha) * distance
                        )
                return history.locked_beacon_mac
            else:
                # 匹配不一致，如果差异太大，可能需要重置
                # 这里先保持锁定，实际应用中可能需要更复杂的逻辑
                # 返回已锁定的信标，即使当前帧匹配不一致
                return history.locked_beacon_mac
        
        # 如果当前帧匹配失败，不记录
        if beacon_mac is None:
            # 如果已锁定，即使当前帧匹配失败，也返回锁定信标
            if history.is_locked():
                return history.locked_beacon_mac
            return None
        
        # 添加匹配记录
        history.add_match(beacon_mac, distance, match_cost)
        
        # 检查是否满足锁定条件
        has_consistent, consistent_beacon = history.has_consistent_match(
            self.min_consistent_frames,
            self.max_distance_error
        )
        
        if has_consistent and consistent_beacon:
            # 满足条件，锁定匹配
            avg_distance = sum(
                m[2] for m in history.matches[-self.min_consistent_frames:] if m[2] is not None
            ) / max(1, sum(1 for m in history.matches[-self.min_consistent_frames:] if m[2] is not None))
            
            history.lock(consistent_beacon, avg_distance if avg_distance else distance)
            print(f"  🔒 [信标匹配] Track#{track_id} 锁定信标: {consistent_beacon} (连续{self.min_consistent_frames}帧匹配)")
            return consistent_beacon
        
        # 尚未满足锁定条件
        return None
    
    def get_locked_beacon(self, track_id: int) -> Optional[str]:
        """
        获取已锁定的信标MAC（不更新匹配）
        
        Args:
            track_id: 跟踪ID
            
        Returns:
            已锁定的信标MAC，如果未锁定则返回None
        """
        if track_id not in self.track_matches:
            return None
        
        history = self.track_matches[track_id]
        return history.get_locked_beacon()
    
    def reset(self, track_id: int) -> None:
        """
        重置指定track的匹配历史
        
        Args:
            track_id: 跟踪ID
        """
        if track_id in self.track_matches:
            self.track_matches[track_id].reset()
            del self.track_matches[track_id]
    
    def cleanup(self, active_track_ids: set) -> None:
        """
        清理不再活跃的track匹配历史
        
        Args:
            active_track_ids: 当前活跃的track ID集合
        """
        if not self.reset_on_track_end:
            return
        
        expired_tracks = set(self.track_matches.keys()) - active_track_ids
        for track_id in expired_tracks:
            self.reset(track_id)

