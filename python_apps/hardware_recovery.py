#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件异常处理和自动重连模块
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Callable
from datetime import datetime


class HardwareRecovery:
    """硬件恢复管理器"""
    
    def __init__(
        self,
        camera_recovery: Optional[Callable] = None,
        cassia_recovery: Optional[Callable] = None,
        camera_retry_interval: float = 5.0,
        cassia_retry_interval: float = 3.0,
        camera_max_retries: int = 10,
        cassia_max_retries: int = 10,
        graceful_degradation: bool = True
    ):
        """
        初始化硬件恢复管理器
        
        Args:
            camera_recovery: 相机恢复函数（返回True表示成功）
            cassia_recovery: Cassia恢复函数（返回True表示成功）
            camera_retry_interval: 相机重试间隔（秒）
            cassia_retry_interval: Cassia重试间隔（秒）
            camera_max_retries: 相机最大重试次数（0表示无限重试）
            cassia_max_retries: Cassia最大重试次数（0表示无限重试）
            graceful_degradation: 是否启用优雅降级（部分功能失效时继续运行）
        """
        self.camera_recovery = camera_recovery
        self.cassia_recovery = cassia_recovery
        self.camera_retry_interval = camera_retry_interval
        self.cassia_retry_interval = cassia_retry_interval
        self.camera_max_retries = camera_max_retries
        self.cassia_max_retries = cassia_max_retries
        self.graceful_degradation = graceful_degradation
        
        # 状态跟踪
        self.camera_retry_count = 0
        self.cassia_retry_count = 0
        self.camera_last_failure_time = None
        self.cassia_last_failure_time = None
        self.camera_recovering = False
        self.cassia_recovering = False
        
        # 锁
        self.lock = threading.Lock()
    
    def check_camera_health(self, camera) -> bool:
        """
        检查相机健康状态
        
        Args:
            camera: 相机对象
            
        Returns:
            True表示健康，False表示异常
        """
        if camera is None:
            return False
        
        try:
            # 尝试获取一帧来检查相机是否正常
            frame = camera.get_color_frame()
            return frame is not None
        except Exception:
            return False
    
    def check_cassia_health(self, cassia_client) -> bool:
        """
        检查Cassia客户端健康状态
        
        Args:
            cassia_client: Cassia客户端对象
            
        Returns:
            True表示健康，False表示异常
        """
        if cassia_client is None:
            return False
        
        try:
            # 尝试获取信标列表来检查连接是否正常
            beacons = cassia_client.get_beacons()
            return beacons is not None
        except Exception:
            return False
    
    def recover_camera(self) -> bool:
        """
        恢复相机连接
        
        Returns:
            True表示恢复成功，False表示失败
        """
        if self.camera_recovery is None:
            return False
        
        with self.lock:
            if self.camera_recovering:
                return False  # 正在恢复中
            
            # 检查重试次数
            if self.camera_max_retries > 0 and self.camera_retry_count >= self.camera_max_retries:
                return False
            
            self.camera_recovering = True
        
        try:
            print(f"[硬件恢复] 尝试恢复相机连接 (第 {self.camera_retry_count + 1} 次)...")
            success = self.camera_recovery()
            
            with self.lock:
                self.camera_recovering = False
                if success:
                    self.camera_retry_count = 0
                    self.camera_last_failure_time = None
                    print("[硬件恢复] ✓ 相机恢复成功")
                else:
                    self.camera_retry_count += 1
                    self.camera_last_failure_time = datetime.now()
                    print(f"[硬件恢复] ✗ 相机恢复失败 (已重试 {self.camera_retry_count} 次)")
            
            return success
        except Exception as e:
            with self.lock:
                self.camera_recovering = False
                self.camera_retry_count += 1
                self.camera_last_failure_time = datetime.now()
            print(f"[硬件恢复] ✗ 相机恢复异常: {e}")
            return False
    
    def recover_cassia(self) -> bool:
        """
        恢复Cassia连接
        
        Returns:
            True表示恢复成功，False表示失败
        """
        if self.cassia_recovery is None:
            return False
        
        with self.lock:
            if self.cassia_recovering:
                return False  # 正在恢复中
            
            # 检查重试次数
            if self.cassia_max_retries > 0 and self.cassia_retry_count >= self.cassia_max_retries:
                return False
            
            self.cassia_recovering = True
        
        try:
            print(f"[硬件恢复] 尝试恢复Cassia连接 (第 {self.cassia_retry_count + 1} 次)...")
            success = self.cassia_recovery()
            
            with self.lock:
                self.cassia_recovering = False
                if success:
                    self.cassia_retry_count = 0
                    self.cassia_last_failure_time = None
                    print("[硬件恢复] ✓ Cassia恢复成功")
                else:
                    self.cassia_retry_count += 1
                    self.cassia_last_failure_time = datetime.now()
                    print(f"[硬件恢复] ✗ Cassia恢复失败 (已重试 {self.cassia_retry_count} 次)")
            
            return success
        except Exception as e:
            with self.lock:
                self.cassia_recovering = False
                self.cassia_retry_count += 1
                self.cassia_last_failure_time = datetime.now()
            print(f"[硬件恢复] ✗ Cassia恢复异常: {e}")
            return False
    
    def monitor_and_recover(
        self,
        camera,
        cassia_client,
        check_interval: float = 10.0
    ) -> None:
        """
        监控硬件状态并自动恢复（在后台线程中运行）
        
        Args:
            camera: 相机对象
            cassia_client: Cassia客户端对象
            check_interval: 检查间隔（秒）
        """
        while True:
            try:
                # 检查相机
                if camera is not None:
                    camera_healthy = self.check_camera_health(camera)
                    if not camera_healthy:
                        # 检查是否需要重试
                        should_retry = True
                        with self.lock:
                            if self.camera_max_retries > 0 and self.camera_retry_count >= self.camera_max_retries:
                                should_retry = False
                                if not self.graceful_degradation:
                                    print("[硬件恢复] ⚠ 相机恢复失败次数过多，系统将退出")
                                    return
                        
                        if should_retry:
                            # 检查重试间隔
                            with self.lock:
                                if self.camera_last_failure_time is None:
                                    self.recover_camera()
                                else:
                                    elapsed = (datetime.now() - self.camera_last_failure_time).total_seconds()
                                    if elapsed >= self.camera_retry_interval:
                                        self.recover_camera()
                
                # 检查Cassia
                if cassia_client is not None:
                    cassia_healthy = self.check_cassia_health(cassia_client)
                    if not cassia_healthy:
                        # 检查是否需要重试
                        should_retry = True
                        with self.lock:
                            if self.cassia_max_retries > 0 and self.cassia_retry_count >= self.cassia_max_retries:
                                should_retry = False
                                if not self.graceful_degradation:
                                    print("[硬件恢复] ⚠ Cassia恢复失败次数过多，但系统将继续运行（优雅降级）")
                        
                        if should_retry:
                            # 检查重试间隔
                            with self.lock:
                                if self.cassia_last_failure_time is None:
                                    self.recover_cassia()
                                else:
                                    elapsed = (datetime.now() - self.cassia_last_failure_time).total_seconds()
                                    if elapsed >= self.cassia_retry_interval:
                                        self.recover_cassia()
                
                time.sleep(check_interval)
            except Exception as e:
                print(f"[硬件恢复] 监控异常: {e}")
                time.sleep(check_interval)
    
    def start_monitoring(
        self,
        camera,
        cassia_client,
        check_interval: float = 10.0,
        daemon: bool = True
    ) -> threading.Thread:
        """
        启动硬件监控线程
        
        Args:
            camera: 相机对象
            cassia_client: Cassia客户端对象
            check_interval: 检查间隔（秒）
            daemon: 是否作为守护线程
            
        Returns:
            监控线程
        """
        thread = threading.Thread(
            target=self.monitor_and_recover,
            args=(camera, cassia_client, check_interval),
            daemon=daemon
        )
        thread.start()
        return thread
    
    def get_status(self) -> dict:
        """
        获取恢复状态
        
        Returns:
            状态字典
        """
        with self.lock:
            return {
                'camera': {
                    'retry_count': self.camera_retry_count,
                    'max_retries': self.camera_max_retries,
                    'last_failure_time': self.camera_last_failure_time.isoformat() if self.camera_last_failure_time else None,
                    'recovering': self.camera_recovering
                },
                'cassia': {
                    'retry_count': self.cassia_retry_count,
                    'max_retries': self.cassia_max_retries,
                    'last_failure_time': self.cassia_last_failure_time.isoformat() if self.cassia_last_failure_time else None,
                    'recovering': self.cassia_recovering
                }
            }

