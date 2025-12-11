"""
信标白名单管理模块 - 从云端API获取和管理信标白名单
"""

import logging
import time
import re
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class BeaconEntry:
    """信标白名单条目"""
    id: int
    beacon_number: int
    mac_address: str
    machine_type: str
    environment_code: str
    registration_date: str
    equipment_owner: Optional[str] = None
    
    def __post_init__(self):
        """标准化MAC地址格式"""
        self.mac_address = self._normalize_mac(self.mac_address)
    
    @staticmethod
    def _normalize_mac(mac: str) -> str:
        """标准化MAC地址格式为 XX:XX:XX:XX:XX:XX（大写）"""
        # 移除所有分隔符，转换为大写
        mac_clean = mac.upper().replace('-', ':').replace(' ', '')
        # 如果格式正确，直接返回
        if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', mac_clean):
            return mac_clean
        # 如果是不带分隔符的12位十六进制，添加冒号
        if re.match(r'^[0-9A-F]{12}$', mac_clean):
            return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])
        # 如果格式不正确，尝试修复
        logger.warning(f"Invalid MAC address format: {mac}, attempting to normalize")
        return mac_clean
    
    def to_dict(self) -> Dict:
        """转换为字典格式（兼容BeaconFilter）"""
        return {
            'vehicle_type': self.machine_type,
            'plate_number': '',  # 云端暂时没有车牌号字段
            'company': self.equipment_owner or '',  # equipment_owner 映射为 company
            'environment_code': self.environment_code,  # 环境编码
            'notes': f"环境编码: {self.environment_code}"
        }


class BeaconWhitelistManager:
    """信标白名单管理器 - 从云端API获取白名单"""
    
    def __init__(self, api_base_url: str, api_key: str, update_interval: int = 300):
        """
        初始化白名单管理器
        
        Args:
            api_base_url: 云端API地址
            api_key: API密钥
            update_interval: 更新间隔（秒），默认5分钟
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.update_interval = update_interval
        self.whitelist: Dict[str, BeaconEntry] = {}  # MAC地址 -> BeaconEntry
        self.last_update_time: Optional[datetime] = None
        self.last_update_success: bool = False
        
        # 创建HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })
        
        logger.info(f"BeaconWhitelistManager initialized: API={self.api_base_url}, update_interval={update_interval}s")
    
    def fetch_whitelist(self, max_retries: int = 3, retry_delay: float = 5.0) -> bool:
        """
        从云端获取信标白名单
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        
        Returns:
            bool: 是否成功
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    f"{self.api_base_url}/api/beacons",
                    timeout=10
                )
                response.raise_for_status()
                
                beacons_data = response.json()
                
                # 验证数据格式
                if not isinstance(beacons_data, list):
                    logger.error(f"Invalid response format: expected list, got {type(beacons_data)}")
                    return False
                
                new_whitelist = {}
                valid_count = 0
                
                for beacon_data in beacons_data:
                    # 验证必需字段
                    if not self._validate_beacon_data(beacon_data):
                        continue
                    
                    try:
                        entry = BeaconEntry(
                            id=beacon_data["id"],
                            beacon_number=beacon_data["beacon_number"],
                            mac_address=beacon_data["mac_address"],
                            machine_type=beacon_data["machine_type"],
                            environment_code=beacon_data["environment_code"],
                            registration_date=beacon_data["registration_date"],
                            equipment_owner=beacon_data.get("equipment_owner")
                        )
                        new_whitelist[entry.mac_address] = entry
                        valid_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to create BeaconEntry from data: {beacon_data}, error: {e}")
                        continue
                
                self.whitelist = new_whitelist
                self.last_update_time = datetime.now()
                self.last_update_success = True
                
                logger.info(f"Beacon whitelist updated: {valid_count} entries (from {len(beacons_data)} total)")
                return True
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch beacon whitelist (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to fetch beacon whitelist after {max_retries} attempts")
                    self.last_update_success = False
                    return False
            except Exception as e:
                logger.error(f"Unexpected error fetching whitelist: {e}")
                self.last_update_success = False
                return False
        
        return False
    
    def _validate_beacon_data(self, beacon_data: Dict) -> bool:
        """
        验证信标数据格式
        
        Args:
            beacon_data: 信标数据字典
        
        Returns:
            bool: 是否有效
        """
        required_fields = ["id", "beacon_number", "mac_address", "machine_type", "environment_code"]
        
        for field in required_fields:
            if field not in beacon_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # 验证MAC地址格式
        mac = beacon_data["mac_address"]
        normalized_mac = BeaconEntry._normalize_mac(mac)
        if not re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', normalized_mac):
            logger.error(f"Invalid MAC address format: {mac}")
            return False
        
        return True
    
    def should_update(self) -> bool:
        """
        检查是否需要更新白名单
        
        Returns:
            bool: 是否需要更新
        """
        if not self.last_update_time:
            return True
        
        elapsed = (datetime.now() - self.last_update_time).total_seconds()
        return elapsed >= self.update_interval
    
    def auto_update(self) -> bool:
        """
        自动更新白名单（如果需要）
        
        Returns:
            bool: 是否成功
        """
        if self.should_update():
            return self.fetch_whitelist()
        return self.last_update_success
    
    def match_beacon(self, mac_address: str) -> Optional[BeaconEntry]:
        """
        匹配信标MAC地址
        
        Args:
            mac_address: 信标MAC地址（支持多种格式）
        
        Returns:
            BeaconEntry: 匹配的信标条目，如果未匹配返回None
        """
        # 标准化MAC地址格式
        normalized_mac = BeaconEntry._normalize_mac(mac_address)
        
        # 确保白名单是最新的
        self.auto_update()
        
        return self.whitelist.get(normalized_mac)
    
    def get_all_beacons(self) -> List[BeaconEntry]:
        """
        获取所有信标条目
        
        Returns:
            List[BeaconEntry]: 所有信标条目
        """
        self.auto_update()
        return list(self.whitelist.values())
    
    def is_registered(self, mac_address: str) -> bool:
        """
        检查信标是否已注册
        
        Args:
            mac_address: 信标MAC地址
        
        Returns:
            bool: 是否已注册
        """
        return self.match_beacon(mac_address) is not None
    
    def get_whitelist_dict(self) -> Dict[str, Dict]:
        """
        获取白名单字典（兼容BeaconFilter格式）
        
        Returns:
            Dict[str, Dict]: MAC地址 -> 信标信息字典
        """
        self.auto_update()
        return {mac: entry.to_dict() for mac, entry in self.whitelist.items()}
    
    def get_stats(self) -> Dict:
        """
        获取白名单统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "total_beacons": len(self.whitelist),
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None,
            "last_update_success": self.last_update_success,
            "update_interval": self.update_interval
        }

