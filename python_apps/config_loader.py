#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加载模块
支持YAML格式配置文件，提供默认值和配置验证
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径（相对于项目根目录）
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(script_dir, 'config.yaml')
        
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            print(f"⚠ 配置文件不存在: {self.config_path}")
            print("   使用默认配置")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 合并默认配置（确保所有字段都存在）
            default_config = self._get_default_config()
            config = self._merge_config(default_config, config)
            
            print(f"✓ 配置文件加载成功: {self.config_path}")
            return config
            
        except Exception as e:
            print(f"✗ 配置文件加载失败: {e}")
            print("   使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'network': {
                'cassia_ip': '192.168.1.2',
                'camera_id': 'camera_01'
            },
            'detection': {
                'conf_threshold': 0.5,
                'iou_threshold': 0.4,
                'model_path': 'models/custom_yolo.engine'
            },
            'tracking': {
                'iou_threshold': 0.3,
                'max_age': 30
            },
            'paths': {
                'beacon_whitelist': 'beacon_whitelist.yaml',
                'log_file': '/tmp/vehicle_detection.log',
                'alert_log_file': '/tmp/vehicle_alerts.json',
                'shared_frame_file': '/tmp/orbbec_shared_frame.npy',
                'shared_depth_file': '/tmp/orbbec_shared_depth.npy'
            },
            'depth': {
                'min_range': 0.1,
                'max_range': 10.0,
                'method': 'median',
                'invalid_min': 0,
                'invalid_max': 65535
            },
            'logging': {
                'level': 'INFO',
                'file_enabled': True,
                'console_enabled': True,
                'max_file_size_mb': 10,
                'backup_count': 5
            },
            'performance': {
                'monitor_enabled': True,
                'fps_update_interval': 10,
                'gpu_monitor_enabled': True,
                'memory_monitor_enabled': True
            },
            'recovery': {
                'camera_retry_enabled': True,
                'camera_retry_interval': 5.0,
                'camera_max_retries': 10,
                'cassia_retry_enabled': True,
                'cassia_retry_interval': 3.0,
                'cassia_max_retries': 10,
                'graceful_degradation': True
            },
            'display': {
                'window_name': 'Vehicle Detection',
                'font_size_large': 24,
                'font_size_small': 18,
                'label_offset_y': 30,
                'wait_key_ms': 1
            }
        }
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """合并默认配置和用户配置"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self):
        """验证配置有效性"""
        errors = []
        
        # 验证网络配置
        if not isinstance(self.config['network']['cassia_ip'], str):
            errors.append("network.cassia_ip 必须是字符串")
        
        # 验证检测阈值
        conf_thresh = self.config['detection']['conf_threshold']
        if not (0.0 <= conf_thresh <= 1.0):
            errors.append("detection.conf_threshold 必须在 0.0-1.0 之间")
        
        iou_thresh = self.config['detection']['iou_threshold']
        if not (0.0 <= iou_thresh <= 1.0):
            errors.append("detection.iou_threshold 必须在 0.0-1.0 之间")
        
        # 验证跟踪参数
        track_iou = self.config['tracking']['iou_threshold']
        if not (0.0 <= track_iou <= 1.0):
            errors.append("tracking.iou_threshold 必须在 0.0-1.0 之间")
        
        if self.config['tracking']['max_age'] < 0:
            errors.append("tracking.max_age 必须 >= 0")
        
        # 验证深度参数
        depth_min = self.config['depth']['min_range']
        depth_max = self.config['depth']['max_range']
        if depth_min >= depth_max:
            errors.append("depth.min_range 必须 < depth.max_range")
        
        if self.config['depth']['method'] not in ['median', 'mean', 'min']:
            errors.append("depth.method 必须是 median/mean/min 之一")
        
        # 验证日志级别
        log_level = self.config['logging']['level']
        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            errors.append("logging.level 必须是 DEBUG/INFO/WARNING/ERROR 之一")
        
        if errors:
            print("⚠ 配置验证警告:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✓ 配置验证通过")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Args:
            key_path: 配置路径，如 'network.cassia_ip'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_network(self) -> Dict[str, Any]:
        """获取网络配置"""
        return self.config['network']
    
    def get_detection(self) -> Dict[str, Any]:
        """获取检测配置"""
        return self.config['detection']
    
    def get_tracking(self) -> Dict[str, Any]:
        """获取跟踪配置"""
        return self.config['tracking']
    
    def get_paths(self) -> Dict[str, Any]:
        """获取路径配置"""
        return self.config['paths']
    
    def get_depth(self) -> Dict[str, Any]:
        """获取深度测量配置"""
        return self.config['depth']
    
    def get_logging(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config['logging']
    
    def get_performance(self) -> Dict[str, Any]:
        """获取性能监控配置"""
        return self.config['performance']
    
    def get_recovery(self) -> Dict[str, Any]:
        """获取错误恢复配置"""
        return self.config['recovery']
    
    def get_display(self) -> Dict[str, Any]:
        """获取显示配置"""
        return self.config['display']
    
    def get_cloud(self) -> Dict[str, Any]:
        """获取云端配置"""
        return self.config.get('cloud', {})
    
    def resolve_path(self, path_key: str, base_dir: Optional[str] = None) -> str:
        """
        解析文件路径（支持相对路径和绝对路径）
        
        Args:
            path_key: 路径配置键，如 'paths.model_path'
            base_dir: 基础目录（用于相对路径），如果为None则使用项目根目录
        
        Returns:
            解析后的绝对路径
        """
        path = self.get(path_key)
        if not path:
            return ""
        
        if os.path.isabs(path):
            return path
        
        # 相对路径，需要解析基础目录
        if base_dir is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = script_dir
        
        return os.path.join(base_dir, path)


# 全局配置实例（单例模式）
_global_config: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    获取全局配置实例（单例模式）
    
    Args:
        config_path: 配置文件路径，仅在第一次调用时有效
    
    Returns:
        配置加载器实例
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader(config_path)
    return _global_config


def reload_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    重新加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置加载器实例
    """
    global _global_config
    _global_config = ConfigLoader(config_path)
    return _global_config

