"""
BLE信标智能过滤模块
实现多级过滤策略和置信度评分
"""

import yaml
import time
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import os
import numpy as np


class BeaconFilter:
    """BLE信标智能过滤器"""
    
    def __init__(self, config_path: str, camera_id: str = "camera_01", cloud_whitelist_manager=None):
        """
        初始化过滤器
        
        Args:
            config_path: 白名单配置文件路径（如果使用云端白名单，可以为None）
            camera_id: 当前摄像头ID
            cloud_whitelist_manager: 云端白名单管理器（可选，如果提供则优先使用云端白名单）
        """
        self.camera_id = camera_id
        self.cloud_whitelist_manager = cloud_whitelist_manager
        self.use_cloud_whitelist = cloud_whitelist_manager is not None
        
        # 如果使用云端白名单，配置文件是可选的
        if self.use_cloud_whitelist:
            print("  📡 使用云端信标白名单")
            # 仍然加载配置文件以获取其他配置参数
            if config_path and os.path.exists(config_path):
                self.config = self._load_config(config_path)
            else:
                # 使用默认配置
                self.config = {
                    'global_config': {},
                    'cameras': {camera_id: {}}
                }
        else:
            # 使用本地配置文件
            self.config = self._load_config(config_path)
        
        # 配置参数
        self.global_config = self.config.get('global_config', {})
        self.camera_config = self.config['cameras'].get(camera_id, {})
        
        # RSSI阈值
        rssi_thresholds = self.global_config.get('rssi_thresholds', {})
        self.rssi_threshold = self.camera_config.get('rssi_threshold', rssi_thresholds.get('default', -70))
        
        # 距离匹配配置
        distance_config = self.global_config.get('distance_match', {})
        self.distance_tolerance = distance_config.get('tolerance', 3.0)
        self.depth_priority = distance_config.get('depth_priority', True)
        
        # 时间窗口配置
        time_config = self.global_config.get('time_window', {})
        self.min_duration = time_config.get('min_duration', 3.0)
        self.history_size = time_config.get('history_size', 100)
        
        # 置信度阈值
        self.confidence_threshold = self.global_config.get('confidence_threshold', 0.6)
        
        # 多目标匹配配置
        multi_target_cfg = self.global_config.get('multi_target_match', {})
        self.multi_target_enabled = multi_target_cfg.get('enabled', True)
        self.match_cost_threshold = multi_target_cfg.get('match_cost_threshold', 5.0)
        self.time_stability_weight = multi_target_cfg.get('time_stability_weight', 0.3)
        self.stability_window = multi_target_cfg.get('stability_window', 3.0)
        
        # 白名单（激活的信标MAC地址集合）
        self.whitelist = self._build_whitelist()
        
        # 信标历史记录（用于时间窗口过滤）
        # {mac: [(timestamp, rssi, distance), ...]}
        self.beacon_history = defaultdict(list)
        
        print(f"✅ 信标过滤器初始化成功")
        print(f"   📹 摄像头: {self.camera_config.get('name', camera_id)}")
        print(f"   📝 白名单: {len(self.whitelist)} 个信标 ({'云端' if self.use_cloud_whitelist else '本地'})")
        print(f"   📡 RSSI阈值: {self.rssi_threshold} dBm")
        print(f"   📏 距离容差: {self.distance_tolerance} m")
        print(f"   ⏱️  时间窗口: {self.min_duration} s")
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _build_whitelist(self) -> Dict[str, dict]:
        """构建白名单字典（优先使用云端白名单）"""
        # 如果使用云端白名单，从云端获取
        if self.use_cloud_whitelist and self.cloud_whitelist_manager:
            try:
                cloud_whitelist = self.cloud_whitelist_manager.get_whitelist_dict()
                if cloud_whitelist:
                    print(f"  ✅ 从云端获取白名单: {len(cloud_whitelist)} 个信标")
                    return cloud_whitelist
                else:
                    print(f"  ⚠️  云端白名单为空，尝试使用本地配置")
            except Exception as e:
                print(f"  ⚠️  获取云端白名单失败: {e}，使用本地配置")
        
        # 使用本地配置文件
        whitelist = {}
        beacons = self.camera_config.get('beacons', [])
        
        for beacon in beacons:
            if beacon.get('active', True):  # 只包含激活的信标
                mac = beacon['mac'].upper()
                whitelist[mac] = {
                    'vehicle_type': beacon.get('vehicle_type', 'unknown'),
                    'plate_number': beacon.get('plate_number', ''),
                    'company': beacon.get('company', ''),
                    'notes': beacon.get('notes', '')
                }
        
        return whitelist
    
    def refresh_whitelist(self):
        """刷新白名单（从云端重新获取）"""
        if self.use_cloud_whitelist and self.cloud_whitelist_manager:
            self.whitelist = self._build_whitelist()
            print(f"  ✅ 白名单已刷新: {len(self.whitelist)} 个信标")
    
    def filter_beacons(
        self, 
        scanned_beacons: List[Dict],
        camera_depth: Optional[float] = None,
        bbox: Optional[Tuple] = None
    ) -> List[Dict]:
        """
        多级过滤信标
        
        Args:
            scanned_beacons: Cassia扫描到的所有信标
            camera_depth: 相机测得的深度（米）
            bbox: 车辆边界框 (x1, y1, x2, y2)
        
        Returns:
            过滤后的信标列表，包含置信度评分
        """
        current_time = time.time()
        
        # 第1级：白名单过滤
        whitelisted = self._filter_by_whitelist(scanned_beacons)
        if not whitelisted:
            return []
        
        print(f"   🔍 [过滤器] 白名单过滤: {len(scanned_beacons)} → {len(whitelisted)} 个信标")
        
        # 第2级：RSSI阈值过滤
        rssi_filtered = self._filter_by_rssi(whitelisted)
        if not rssi_filtered:
            return []
        
        print(f"   📡 [过滤器] RSSI过滤 (>{self.rssi_threshold}dBm): {len(whitelisted)} → {len(rssi_filtered)} 个信标")
        
        # 第3级：距离匹配过滤（如果有深度信息）
        if camera_depth is not None and camera_depth > 0:
            distance_filtered = self._filter_by_distance(rssi_filtered, camera_depth)
            if distance_filtered:
                print(f"   📏 [过滤器] 距离匹配 (±{self.distance_tolerance}m): {len(rssi_filtered)} → {len(distance_filtered)} 个信标")
                rssi_filtered = distance_filtered
            else:
                print(f"   ⚠️  [过滤器] 距离匹配无结果，使用RSSI结果")
        
        # 第4级：更新历史记录
        self._update_history(rssi_filtered, current_time)
        
        # 第5级：时间窗口过滤
        persistent = self._filter_by_time_window(rssi_filtered, current_time)
        if persistent:
            print(f"   ⏱️  [过滤器] 时间窗口 (>{self.min_duration}s): {len(rssi_filtered)} → {len(persistent)} 个信标")
            rssi_filtered = persistent
        else:
            print(f"   ⏱️  [过滤器] 无持续信标，使用瞬时结果")
        
        # 第6级：计算匹配置信度
        scored_beacons = self._calculate_confidence(rssi_filtered, camera_depth)
        
        # 按置信度排序
        scored_beacons.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 输出最终结果
        if scored_beacons:
            print(f"   ✅ [过滤器] 最终匹配: {len(scored_beacons)} 个信标")
            for beacon in scored_beacons:
                print(f"      • MAC={beacon['mac']}, 置信度={beacon['confidence']:.2f}, "
                      f"RSSI={beacon['rssi']}dBm, 距离≈{beacon['distance']:.1f}m")
        
        return scored_beacons
    
    def _filter_by_whitelist(self, beacons: List[Dict]) -> List[Dict]:
        """白名单过滤"""
        filtered = []
        for beacon in beacons:
            mac = beacon.get('mac', '').upper()
            if mac in self.whitelist:
                # 添加车辆信息
                beacon_info = self.whitelist[mac].copy()
                beacon_info.update(beacon)
                filtered.append(beacon_info)
        return filtered
    
    def _filter_by_rssi(self, beacons: List[Dict]) -> List[Dict]:
        """RSSI阈值过滤"""
        return [b for b in beacons if b.get('rssi', -100) > self.rssi_threshold]
    
    def _filter_by_distance(self, beacons: List[Dict], camera_depth: float) -> List[Dict]:
        """距离匹配过滤"""
        filtered = []
        for beacon in beacons:
            beacon_distance = beacon.get('distance', 0)
            if beacon_distance > 0:
                distance_diff = abs(beacon_distance - camera_depth)
                if distance_diff < self.distance_tolerance:
                    beacon['distance_diff'] = distance_diff
                    filtered.append(beacon)
        return filtered
    
    def _update_history(self, beacons: List[Dict], current_time: float):
        """更新信标历史记录"""
        for beacon in beacons:
            mac = beacon['mac']
            history = self.beacon_history[mac]
            
            # 添加新记录
            history.append({
                'timestamp': current_time,
                'rssi': beacon['rssi'],
                'distance': beacon.get('distance', 0)
            })
            
            # 限制历史记录大小
            if len(history) > self.history_size:
                history.pop(0)
    
    def _filter_by_time_window(self, beacons: List[Dict], current_time: float) -> List[Dict]:
        """时间窗口过滤：只保留持续出现的信标"""
        persistent = []
        
        for beacon in beacons:
            mac = beacon['mac']
            history = self.beacon_history.get(mac, [])
            
            if not history:
                continue
            
            # 计算持续时间
            first_seen = history[0]['timestamp']
            duration = current_time - first_seen
            
            if duration >= self.min_duration:
                beacon['duration'] = duration
                beacon['first_seen'] = first_seen
                persistent.append(beacon)
        
        return persistent
    
    def _calculate_confidence(
        self, 
        beacons: List[Dict], 
        camera_depth: Optional[float] = None
    ) -> List[Dict]:
        """
        计算匹配置信度
        
        置信度因素：
        1. RSSI强度 (0-0.3)
        2. 距离匹配度 (0-0.4)
        3. 持续时间 (0-0.3)
        """
        scored = []
        
        for beacon in beacons:
            score = 0.0
            
            # 1. RSSI评分（越强越好）
            rssi = beacon.get('rssi', -100)
            if rssi > -50:
                rssi_score = 0.3
            elif rssi > -60:
                rssi_score = 0.25
            elif rssi > -70:
                rssi_score = 0.2
            elif rssi > -80:
                rssi_score = 0.15
            else:
                rssi_score = 0.1
            score += rssi_score
            
            # 2. 距离匹配评分（越接近越好）
            if camera_depth is not None and 'distance_diff' in beacon:
                distance_diff = beacon['distance_diff']
                if distance_diff < 1.0:
                    distance_score = 0.4
                elif distance_diff < 2.0:
                    distance_score = 0.3
                elif distance_diff < 3.0:
                    distance_score = 0.2
                else:
                    distance_score = 0.1
                score += distance_score
            else:
                # 没有深度信息，给予中等评分
                score += 0.2
            
            # 3. 持续时间评分（越久越好）
            duration = beacon.get('duration', 0)
            if duration >= 10.0:
                time_score = 0.3
            elif duration >= 5.0:
                time_score = 0.25
            elif duration >= 3.0:
                time_score = 0.2
            else:
                # 瞬时检测，给予较低评分
                time_score = 0.1
            score += time_score
            
            # 4. 时间稳定度惩罚（RSSI/距离波动大则惩罚）
            stability_penalty = self._calculate_time_stability_penalty(beacon)
            score -= stability_penalty * self.time_stability_weight
            score = max(0.0, score)  # 确保分数不为负
            
            beacon['confidence'] = score
            beacon['rssi_score'] = rssi_score
            beacon['distance_score'] = score - rssi_score - time_score
            beacon['time_score'] = time_score
            
            scored.append(beacon)
        
        return scored
    
    def _calculate_time_stability_penalty(self, beacon: Dict) -> float:
        """
        计算时间稳定度惩罚
        
        Args:
            beacon: 信标信息
            
        Returns:
            惩罚值（0.0-1.0），波动越大惩罚越高
        """
        mac = beacon.get('mac', '')
        if mac not in self.beacon_history:
            return 0.0  # 无历史数据，不惩罚
        
        history = self.beacon_history[mac]
        if len(history) < 2:
            return 0.0  # 历史数据不足，不惩罚
        
        # 获取时间窗口内的数据
        import time
        current_time = time.time()
        
        # 处理历史记录格式（可能是字典或元组）
        window_data = []
        for record in history:
            if isinstance(record, dict):
                # 字典格式: {'timestamp': t, 'rssi': rssi, 'distance': dist}
                t = record.get('timestamp', 0)
                rssi = record.get('rssi', -100)
                dist = record.get('distance', 0)
            elif isinstance(record, (list, tuple)) and len(record) >= 3:
                # 元组格式: (t, rssi, dist)
                t, rssi, dist = record[0], record[1], record[2]
            else:
                continue  # 跳过无效格式
            
            # 确保时间戳是数值类型
            if isinstance(t, str):
                try:
                    t = float(t)
                except (ValueError, TypeError):
                    continue  # 跳过无效时间戳
            
            # 检查是否在时间窗口内
            if isinstance(t, (int, float)) and current_time - t <= self.stability_window:
                window_data.append((t, rssi, dist))
        
        if len(window_data) < 2:
            return 0.0  # 窗口内数据不足
        
        # 计算RSSI标准差
        rssi_values = [rssi for _, rssi, _ in window_data]
        if len(rssi_values) > 1:
            rssi_std = np.std(rssi_values)
            # RSSI标准差 > 10dBm 认为不稳定
            rssi_penalty = min(1.0, rssi_std / 10.0)
        else:
            rssi_penalty = 0.0
        
        # 计算距离标准差（如果有距离信息）
        dist_values = [dist for _, _, dist in window_data if isinstance(dist, (int, float)) and dist > 0]
        if len(dist_values) > 1:
            dist_std = np.std(dist_values)
            # 距离标准差 > 2m 认为不稳定
            dist_penalty = min(1.0, dist_std / 2.0)
        else:
            dist_penalty = 0.0
        
        # 综合惩罚（取较大值）
        penalty = max(rssi_penalty, dist_penalty)
        return penalty
    
    def get_best_match(
        self, 
        scanned_beacons: List[Dict],
        camera_depth: Optional[float] = None,
        bbox: Optional[Tuple] = None
    ) -> Optional[Dict]:
        """
        获取最佳匹配信标
        
        Returns:
            最佳匹配的信标，如果无匹配则返回None
        """
        filtered = self.filter_beacons(scanned_beacons, camera_depth, bbox)
        
        if not filtered:
            return None
        
        # 返回置信度最高的
        best = filtered[0]
        
        if best['confidence'] < self.confidence_threshold:
            print(f"   ⚠️  [过滤器] 最佳匹配置信度过低: {best['confidence']:.2f} < {self.confidence_threshold}")
            return None
        
        return best
    
    def match_multiple_targets(
        self,
        vehicles: List[Dict],  # [{track_id, bbox, camera_depth, detected_class}, ...]
        scanned_beacons: List[Dict]
    ) -> List[Dict]:
        """
        多目标-多信标匈牙利算法匹配（按车辆类型分组，确保信标数量限制）
        
        核心逻辑：
        1. 按车辆类型分组（excavator, loader等）
        2. 对于每种类型，统计检测到的车辆数量和扫描到的信标数量
        3. 如果信标数量 < 车辆数量，只能匹配信标数量个车辆，多余的标记为未备案
        4. 信标数量是更可靠的参考，确保每个信标最多只匹配一个车辆
        
        Args:
            vehicles: 车辆列表，每个车辆包含track_id, bbox, camera_depth, detected_class
            scanned_beacons: 扫描到的所有信标
            
        Returns:
            匹配结果列表，每个元素包含 {track_id, beacon_info, cost, matched}
        """
        if not self.multi_target_enabled or len(vehicles) == 0 or len(scanned_beacons) == 0:
            # 如果禁用多目标匹配或数据不足，使用单目标匹配
            results = []
            for vehicle in vehicles:
                best_match = self.get_best_match(
                    scanned_beacons,
                    camera_depth=vehicle.get('camera_depth'),
                    bbox=vehicle.get('bbox')
                )
                results.append({
                    'track_id': vehicle.get('track_id'),
                    'beacon_info': best_match,
                    'cost': None if best_match is None else 0.0,
                    'matched': best_match is not None
                })
            return results
        
        # 过滤信标（只保留白名单中的）
        filtered_beacons = []
        for beacon in scanned_beacons:
            mac = beacon.get('mac', '').upper()
            if mac in self.whitelist:
                # 添加白名单中的车辆类型信息
                beacon_info = self.whitelist[mac].copy()
                beacon_info.update(beacon)
                filtered_beacons.append(beacon_info)
        
        if len(filtered_beacons) == 0:
            # 无有效信标，返回未匹配
            print(f"  ⚠️  [匹配] 无有效信标，所有车辆标记为未备案")
            return [{
                'track_id': v.get('track_id'),
                'beacon_info': None,
                'cost': None,
                'matched': False
            } for v in vehicles]
        
        # 按车辆类型分组
        from collections import defaultdict
        vehicles_by_type = defaultdict(list)
        for i, vehicle in enumerate(vehicles):
            detected_class = vehicle.get('detected_class', 'unknown')
            # 标准化车辆类型名称（excavator, loader, dump-truck等）
            normalized_type = detected_class.replace('-', '_').lower()
            vehicles_by_type[normalized_type].append((i, vehicle))
        
        beacons_by_type = defaultdict(list)
        for j, beacon in enumerate(filtered_beacons):
            beacon_type = beacon.get('vehicle_type', 'unknown')
            # 标准化信标类型名称
            normalized_type = beacon_type.replace('-', '_').lower()
            beacons_by_type[normalized_type].append((j, beacon))
        
        # 打印统计信息
        print(f"\n  📊 [匹配] 车辆与信标统计:")
        for vtype in set(list(vehicles_by_type.keys()) + list(beacons_by_type.keys())):
            vehicle_count = len(vehicles_by_type.get(vtype, []))
            beacon_count = len(beacons_by_type.get(vtype, []))
            if vehicle_count > 0 or beacon_count > 0:
                print(f"    {vtype}: {vehicle_count} 辆车, {beacon_count} 个信标")
                if vehicle_count > beacon_count:
                    print(f"      ⚠️  车辆数量({vehicle_count}) > 信标数量({beacon_count})，将标记 {vehicle_count - beacon_count} 辆车为未备案")
        
        # 按类型分组匹配
        all_results = [None] * len(vehicles)  # 预分配结果列表
        used_beacon_indices = set()  # 记录已使用的信标索引（全局）
        
        for vtype, vehicle_list in vehicles_by_type.items():
            type_beacons = beacons_by_type.get(vtype, [])
            
            if len(type_beacons) == 0:
                # 该类型无信标，所有车辆标记为未备案
                print(f"  ⚠️  [匹配] {vtype} 类型无信标，{len(vehicle_list)} 辆车标记为未备案")
                for orig_idx, vehicle in vehicle_list:
                    all_results[orig_idx] = {
                        'track_id': vehicle.get('track_id'),
                        'beacon_info': None,
                        'cost': None,
                        'matched': False
                    }
                continue
            
            # 该类型有信标，进行匹配
            type_vehicles = [v for _, v in vehicle_list]
            type_beacon_list = [b for _, b in type_beacons]
            
            # 如果车辆数量 > 信标数量，只匹配信标数量个车辆
            if len(type_vehicles) > len(type_beacon_list):
                print(f"  ⚠️  [匹配] {vtype} 类型: {len(type_vehicles)} 辆车 > {len(type_beacon_list)} 个信标")
                print(f"      只能匹配 {len(type_beacon_list)} 辆车，其余标记为未备案")
                # 只匹配前N个车辆（N=信标数量）
                vehicles_to_match = type_vehicles[:len(type_beacon_list)]
                vehicles_unmatched = type_vehicles[len(type_beacon_list):]
            else:
                vehicles_to_match = type_vehicles
                vehicles_unmatched = []
            
            # 对需要匹配的车辆构建代价矩阵
            num_vehicles = len(vehicles_to_match)
            num_beacons = len(type_beacon_list)
            cost_matrix = np.full((num_vehicles, num_beacons), np.inf)
            
            for i, vehicle in enumerate(vehicles_to_match):
                vehicle_depth = vehicle.get('camera_depth')
                if vehicle_depth is None:
                    continue  # 无深度信息，跳过
                
                for j, beacon in enumerate(type_beacon_list):
                    # 计算距离代价
                    beacon_distance = beacon.get('distance', 0)
                    distance_cost = abs(vehicle_depth - beacon_distance)
                    
                    # 计算时间稳定度惩罚
                    stability_penalty = self._calculate_time_stability_penalty(beacon)
                    stability_cost = stability_penalty * self.stability_window
                    
                    # 总代价
                    total_cost = distance_cost + stability_cost
                    cost_matrix[i, j] = total_cost
            
            # 使用匈牙利算法进行最优匹配
            try:
                from scipy.optimize import linear_sum_assignment
                row_indices, col_indices = linear_sum_assignment(cost_matrix)
                
                # 构建匹配结果
                matched_pairs = {}
                for i, j in zip(row_indices, col_indices):
                    cost = cost_matrix[i, j]
                    # 检查代价是否超过阈值
                    if cost <= self.match_cost_threshold:
                        matched_pairs[i] = (j, cost)
                
                # 处理匹配成功的车辆
                for i, vehicle in enumerate(vehicles_to_match):
                    orig_idx = vehicle_list[i][0]  # 获取原始索引
                    if i in matched_pairs:
                        j, cost = matched_pairs[i]
                        beacon_info = type_beacon_list[j].copy()
                        beacon_info['match_cost'] = cost
                        all_results[orig_idx] = {
                            'track_id': vehicle.get('track_id'),
                            'beacon_info': beacon_info,
                            'cost': cost,
                            'matched': True
                        }
                        print(f"    ✅ [匹配] Track {vehicle.get('track_id')} -> {vtype} (信标: {beacon_info.get('mac', 'Unknown')}, 代价: {cost:.2f})")
                    else:
                        all_results[orig_idx] = {
                            'track_id': vehicle.get('track_id'),
                            'beacon_info': None,
                            'cost': None,
                            'matched': False
                        }
                        print(f"    ❌ [匹配] Track {vehicle.get('track_id')} -> {vtype} (无匹配，代价过高)")
                
                # 处理未匹配的车辆（车辆数量 > 信标数量的情况）
                for vehicle in vehicles_unmatched:
                    # 找到原始索引
                    orig_idx = None
                    for idx, (orig_i, v) in enumerate(vehicle_list):
                        if v.get('track_id') == vehicle.get('track_id'):
                            orig_idx = orig_i
                            break
                    if orig_idx is not None:
                        all_results[orig_idx] = {
                            'track_id': vehicle.get('track_id'),
                            'beacon_info': None,
                            'cost': None,
                            'matched': False
                        }
                        print(f"    ⚠️  [匹配] Track {vehicle.get('track_id')} -> {vtype} (未匹配，信标数量不足)")
                
            except ImportError:
                # scipy不可用，回退到贪心算法
                print(f"  ⚠️  [匹配] scipy不可用，使用贪心算法进行匹配")
                matched_results = self._greedy_match(vehicles_to_match, type_beacon_list, cost_matrix)
                # 将结果映射回原始索引
                for idx, result in enumerate(matched_results):
                    orig_idx = vehicle_list[idx][0]
                    all_results[orig_idx] = result
                # 处理未匹配的车辆
                for vehicle in vehicles_unmatched:
                    orig_idx = None
                    for idx, (orig_i, v) in enumerate(vehicle_list):
                        if v.get('track_id') == vehicle.get('track_id'):
                            orig_idx = orig_i
                            break
                    if orig_idx is not None:
                        all_results[orig_idx] = {
                            'track_id': vehicle.get('track_id'),
                            'beacon_info': None,
                            'cost': None,
                            'matched': False
                        }
        
        # 确保所有车辆都有结果
        for i, vehicle in enumerate(vehicles):
            if all_results[i] is None:
                all_results[i] = {
                    'track_id': vehicle.get('track_id'),
                    'beacon_info': None,
                    'cost': None,
                    'matched': False
                }
        
        return all_results
    
    def _greedy_match(
        self,
        vehicles: List[Dict],
        beacons: List[Dict],
        cost_matrix: np.ndarray
    ) -> List[Dict]:
        """贪心匹配算法（scipy不可用时的回退方案）"""
        num_vehicles = len(vehicles)
        num_beacons = len(beacons)
        matched_vehicles = set()
        matched_beacons = set()
        results = []
        
        # 按代价排序所有可能的匹配
        matches = []
        for i in range(num_vehicles):
            for j in range(num_beacons):
                cost = cost_matrix[i, j]
                if cost < np.inf and cost <= self.match_cost_threshold:
                    matches.append((i, j, cost))
        
        matches.sort(key=lambda x: x[2])  # 按代价排序
        
        # 贪心选择
        for i, j, cost in matches:
            if i not in matched_vehicles and j not in matched_beacons:
                matched_vehicles.add(i)
                matched_beacons.add(j)
                beacon_info = beacons[j].copy()
                beacon_info['match_cost'] = cost
                results.append({
                    'track_id': vehicles[i].get('track_id'),
                    'beacon_info': beacon_info,
                    'cost': cost,
                    'matched': True
                })
        
        # 添加未匹配的车辆
        for i, vehicle in enumerate(vehicles):
            if i not in matched_vehicles:
                results.append({
                    'track_id': vehicle.get('track_id'),
                    'beacon_info': None,
                    'cost': None,
                    'matched': False
                })
        
        return results
    
    def get_whitelist_info(self) -> Dict:
        """获取白名单信息"""
        return {
            'camera_id': self.camera_id,
            'camera_name': self.camera_config.get('name', 'Unknown'),
            'beacon_count': len(self.whitelist),
            'beacons': self.whitelist
        }
    
    def reload_config(self, config_path: str):
        """重新加载配置（用于动态更新白名单）"""
        self.config = self._load_config(config_path)
        self.camera_config = self.config['cameras'].get(self.camera_id, {})
        self.whitelist = self._build_whitelist()
        print(f"✅ 配置已重新加载，白名单: {len(self.whitelist)} 个信标")


# 工具函数
def rssi_to_distance(rssi: int, tx_power: int = -59) -> float:
    """
    根据RSSI估算距离
    
    Args:
        rssi: 接收信号强度指示
        tx_power: 发射功率（1米处的RSSI值）
    
    Returns:
        估算距离（米）
    """
    if rssi == 0:
        return -1.0
    
    ratio = (tx_power - rssi) / (10 * 2.0)
    return pow(10, ratio)


def format_beacon_info(beacon: Dict) -> str:
    """格式化信标信息用于显示"""
    lines = []
    lines.append(f"MAC: {beacon.get('mac', 'Unknown')}")
    lines.append(f"车辆类型: {beacon.get('vehicle_type', 'Unknown')}")
    
    if beacon.get('plate_number'):
        lines.append(f"车牌号: {beacon['plate_number']}")
    
    if beacon.get('company'):
        lines.append(f"所属: {beacon['company']}")
    
    lines.append(f"RSSI: {beacon.get('rssi', 0)} dBm")
    lines.append(f"距离: {beacon.get('distance', 0):.1f} m")
    
    if 'confidence' in beacon:
        lines.append(f"置信度: {beacon['confidence']:.2f}")
    
    return " | ".join(lines)


if __name__ == '__main__':
    # 测试代码
    config_path = '../beacon_whitelist.yaml'
    
    # 初始化过滤器
    beacon_filter = BeaconFilter(config_path, camera_id='camera_01')
    
    # 获取白名单信息
    whitelist_info = beacon_filter.get_whitelist_info()
    print(f"\n📋 当前白名单信息:")
    print(f"   摄像头: {whitelist_info['camera_name']}")
    print(f"   信标数量: {whitelist_info['beacon_count']}")
    if whitelist_info['beacon_count'] > 0:
        print(f"   已注册信标:")
        for mac, info in whitelist_info['beacons'].items():
            print(f"      • {mac} - {info['vehicle_type']}")
    
    # 模拟扫描结果 - 使用白名单中的实际MAC地址
    # 如果白名单为空，使用示例数据
    if whitelist_info['beacon_count'] > 0:
        # 使用白名单中的第一个MAC地址
        first_mac = list(whitelist_info['beacons'].keys())[0]
        mock_beacons = [
            {'mac': first_mac, 'rssi': -65, 'distance': 8.5},  # 白名单中的信标
            {'mac': first_mac.replace('45', 'AA'), 'rssi': -55, 'distance': 5.2},  # 另一个信标（模拟）
            {'mac': 'XX:XX:XX:XX:XX:XX', 'rssi': -45, 'distance': 3.0},  # 不在白名单
            {'mac': 'YY:YY:YY:YY:YY:YY', 'rssi': -85, 'distance': 25.0},  # RSSI太弱
        ]
        camera_depth = 8.2  # 与第一个信标距离接近
        print(f"\n✅ 使用白名单MAC进行测试: {first_mac}")
    else:
        # 白名单为空，使用示例数据
        mock_beacons = [
            {'mac': 'AA:BB:CC:DD:EE:01', 'rssi': -65, 'distance': 8.5},
            {'mac': 'AA:BB:CC:DD:EE:02', 'rssi': -55, 'distance': 5.2},
            {'mac': 'AA:BB:CC:DD:EE:99', 'rssi': -45, 'distance': 3.0},
            {'mac': 'AA:BB:CC:DD:EE:03', 'rssi': -85, 'distance': 25.0},
        ]
        camera_depth = 5.5
        print(f"\n⚠️  白名单为空，使用示例数据测试")
    
    print("\n" + "="*60)
    print("测试多级过滤")
    print("="*60)
    print(f"\n模拟场景:")
    print(f"  • 相机深度: {camera_depth:.1f} m")
    print(f"  • 扫描到 {len(mock_beacons)} 个信标")
    
    # 第一次过滤（无持续时间）
    print("\n【第1次扫描】")
    result1 = beacon_filter.filter_beacons(mock_beacons, camera_depth)
    if result1:
        print(f"\n   匹配到 {len(result1)} 个信标（持续时间不足）")
    
    # 模拟3秒后再次扫描
    time.sleep(3.5)
    print("\n【第2次扫描（3.5秒后）】")
    result2 = beacon_filter.filter_beacons(mock_beacons, camera_depth)
    if result2:
        print(f"\n   匹配到 {len(result2)} 个持续信标 ✅")
    
    # 获取最佳匹配
    print("\n" + "="*60)
    print("获取最佳匹配")
    print("="*60)
    best = beacon_filter.get_best_match(mock_beacons, camera_depth)
    if best:
        print(f"\n✅ 最佳匹配:")
        print(f"   {format_beacon_info(best)}")
        print(f"\n   评分详情:")
        print(f"      RSSI评分: {best.get('rssi_score', 0):.2f}")
        print(f"      距离评分: {best.get('distance_score', 0):.2f}")
        print(f"      时间评分: {best.get('time_score', 0):.2f}")
        print(f"      总分: {best.get('confidence', 0):.2f}")
    else:
        print("\n❌ 无有效匹配")
        print("\n💡 可能原因:")
        print("   1. 白名单中没有信标")
        print("   2. RSSI阈值太严格")
        print("   3. 持续时间不足")
        print("   4. 置信度低于阈值")
        print(f"\n   当前配置:")
        print(f"      RSSI阈值: {beacon_filter.rssi_threshold} dBm")
        print(f"      距离容差: {beacon_filter.distance_tolerance} m")
        print(f"      持续时间: {beacon_filter.min_duration} s")
        print(f"      置信度阈值: {beacon_filter.confidence_threshold}")


