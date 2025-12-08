#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络故障处理和自动重连模块
"""

from __future__ import annotations

import time
import socket
import subprocess
import threading
from typing import Optional, Callable
from datetime import datetime


class NetworkRecovery:
    """网络恢复管理器"""
    
    def __init__(
        self,
        cassia_ip: str,
        cassia_recovery: Optional[Callable] = None,
        check_interval: float = 30.0,
        retry_interval: float = 5.0,
        max_retries: int = 10
    ):
        """
        初始化网络恢复管理器
        
        Args:
            cassia_ip: Cassia路由器IP地址
            cassia_recovery: Cassia恢复函数（返回True表示成功）
            check_interval: 网络检查间隔（秒）
            retry_interval: 重试间隔（秒）
            max_retries: 最大重试次数（0表示无限重试）
        """
        self.cassia_ip = cassia_ip
        self.cassia_recovery = cassia_recovery
        self.check_interval = check_interval
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        
        # 状态跟踪
        self.retry_count = 0
        self.last_failure_time = None
        self.recovering = False
        self.last_check_time = None
        
        # 锁
        self.lock = threading.Lock()
    
    def check_cassia_connectivity(self) -> bool:
        """
        检查Cassia路由器连通性
        
        Returns:
            True表示连通，False表示不通
        """
        try:
            # 使用ping检查
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', self.cassia_ip],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def check_internet_connectivity(self) -> bool:
        """
        检查互联网连通性
        
        Returns:
            True表示连通，False表示不通
        """
        try:
            # 检查DNS解析
            socket.gethostbyname('www.baidu.com')
            return True
        except Exception:
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
            if self.recovering:
                return False  # 正在恢复中
            
            # 检查重试次数
            if self.max_retries > 0 and self.retry_count >= self.max_retries:
                return False
            
            self.recovering = True
        
        try:
            print(f"[网络恢复] 尝试恢复Cassia连接 (第 {self.retry_count + 1} 次)...")
            success = self.cassia_recovery()
            
            with self.lock:
                self.recovering = False
                if success:
                    self.retry_count = 0
                    self.last_failure_time = None
                    print("[网络恢复] ✓ Cassia连接恢复成功")
                else:
                    self.retry_count += 1
                    self.last_failure_time = datetime.now()
                    print(f"[网络恢复] ✗ Cassia连接恢复失败 (已重试 {self.retry_count} 次)")
            
            return success
        except Exception as e:
            with self.lock:
                self.recovering = False
                self.retry_count += 1
                self.last_failure_time = datetime.now()
            print(f"[网络恢复] ✗ Cassia连接恢复异常: {e}")
            return False
    
    def monitor_and_recover(self, cassia_client) -> None:
        """
        监控网络状态并自动恢复（在后台线程中运行）
        
        Args:
            cassia_client: Cassia客户端对象
        """
        while True:
            try:
                # 检查Cassia连通性
                cassia_connected = self.check_cassia_connectivity()
                
                if not cassia_connected:
                    # 检查是否需要重试
                    should_retry = True
                    with self.lock:
                        if self.max_retries > 0 and self.retry_count >= self.max_retries:
                            should_retry = False
                            print("[网络恢复] ⚠ Cassia连接恢复失败次数过多，但系统将继续运行")
                    
                    if should_retry:
                        # 检查重试间隔
                        with self.lock:
                            if self.last_failure_time is None:
                                self.recover_cassia()
                            else:
                                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                                if elapsed >= self.retry_interval:
                                    self.recover_cassia()
                
                # 检查互联网连通性（仅记录，不自动恢复）
                internet_connected = self.check_internet_connectivity()
                if not internet_connected:
                    print("[网络恢复] ⚠ 互联网连接不可用（不影响本地功能）")
                
                with self.lock:
                    self.last_check_time = datetime.now()
                
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"[网络恢复] 监控异常: {e}")
                time.sleep(self.check_interval)
    
    def start_monitoring(
        self,
        cassia_client,
        daemon: bool = True
    ) -> threading.Thread:
        """
        启动网络监控线程
        
        Args:
            cassia_client: Cassia客户端对象
            daemon: 是否作为守护线程
            
        Returns:
            监控线程
        """
        thread = threading.Thread(
            target=self.monitor_and_recover,
            args=(cassia_client,),
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
                'retry_count': self.retry_count,
                'max_retries': self.max_retries,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'recovering': self.recovering,
                'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
                'cassia_connected': self.check_cassia_connectivity(),
                'internet_connected': self.check_internet_connectivity()
            }

