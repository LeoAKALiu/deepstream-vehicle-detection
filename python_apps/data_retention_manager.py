#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据留存管理模块
负责自动清理旧数据，控制占用空间，实现循环写入
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DataRetentionManager:
    """数据留存管理器"""
    
    def __init__(self, config: Dict[str, Any], detection_db=None):
        """
        初始化数据留存管理器
        
        Args:
            config: 数据留存配置（从config.yaml的data_retention部分读取）
            detection_db: DetectionDatabase实例（可选）
        """
        self.config = config
        self.detection_db = detection_db
        self.running = False
        self.cleanup_thread: Optional[threading.Thread] = None
        
        # 数据库配置
        self.db_config = config.get('database', {})
        self.db_enabled = self.db_config.get('enabled', True)
        self.db_max_records = self.db_config.get('max_records', 10000)
        self.db_retention_days = self.db_config.get('retention_days', 30)
        self.db_auto_cleanup = self.db_config.get('auto_cleanup', True)
        self.db_cleanup_interval = self.db_config.get('cleanup_interval_hours', 24) * 3600
        
        # 快照配置
        self.snapshot_config = config.get('snapshots', {})
        self.snapshot_enabled = self.snapshot_config.get('enabled', True)
        self.snapshot_max_count = self.snapshot_config.get('max_count', 1000)
        self.snapshot_max_size_mb = self.snapshot_config.get('max_size_mb', 500)
        self.snapshot_retention_days = self.snapshot_config.get('retention_days', 7)
        self.snapshot_auto_cleanup = self.snapshot_config.get('auto_cleanup', True)
        self.snapshot_cleanup_interval = self.snapshot_config.get('cleanup_interval_hours', 6) * 3600
        self.snapshot_dir = None  # 将在启动时设置
        
        # 监控截图配置
        self.monitoring_config = config.get('monitoring_snapshots', {})
        self.monitoring_enabled = self.monitoring_config.get('enabled', True)
        self.monitoring_max_count = self.monitoring_config.get('max_count', 500)
        self.monitoring_max_size_mb = self.monitoring_config.get('max_size_mb', 200)
        self.monitoring_retention_days = self.monitoring_config.get('retention_days', 3)
        self.monitoring_auto_cleanup = self.monitoring_config.get('auto_cleanup', True)
        self.monitoring_cleanup_interval = self.monitoring_config.get('cleanup_interval_hours', 12) * 3600
        
        # 清理时间记录
        self.last_db_cleanup = 0
        self.last_snapshot_cleanup = 0
        self.last_monitoring_cleanup = 0
    
    def set_snapshot_dir(self, snapshot_dir: str) -> None:
        """
        设置快照目录路径
        
        Args:
            snapshot_dir: 快照目录路径
        """
        self.snapshot_dir = snapshot_dir
    
    def start(self) -> None:
        """启动自动清理线程"""
        if self.running:
            logger.warning("Data retention manager already running")
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info("Data retention manager started")
    
    def stop(self) -> None:
        """停止自动清理线程"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Data retention manager stopped")
    
    def _cleanup_worker(self) -> None:
        """自动清理工作线程"""
        while self.running:
            try:
                current_time = time.time()
                
                # 清理数据库
                if self.db_enabled and self.db_auto_cleanup and self.detection_db:
                    if current_time - self.last_db_cleanup >= self.db_cleanup_interval:
                        self.cleanup_database()
                        self.last_db_cleanup = current_time
                
                # 清理快照
                if self.snapshot_enabled and self.snapshot_auto_cleanup:
                    if current_time - self.last_snapshot_cleanup >= self.snapshot_cleanup_interval:
                        self.cleanup_snapshots()
                        self.last_snapshot_cleanup = current_time
                
                # 清理监控截图（在快照目录中查找）
                if self.monitoring_enabled and self.monitoring_auto_cleanup:
                    if current_time - self.last_monitoring_cleanup >= self.monitoring_cleanup_interval:
                        self.cleanup_monitoring_snapshots()
                        self.last_monitoring_cleanup = current_time
                
                # 等待1分钟后再次检查
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(300)  # 出错时等待5分钟
    
    def cleanup_database(self) -> int:
        """
        清理数据库（按时间和数量限制）
        
        Returns:
            删除的记录数
        """
        if not self.detection_db:
            return 0
        
        try:
            deleted_count = 0
            
            # 1. 按时间清理
            if self.db_retention_days > 0:
                deleted_by_time = self.detection_db.cleanup_old_records(self.db_retention_days)
                deleted_count += deleted_by_time
                if deleted_by_time > 0:
                    logger.info(f"Database cleanup: deleted {deleted_by_time} records older than {self.db_retention_days} days")
            
            # 2. 按数量限制清理（循环写入）
            if self.db_max_records > 0:
                deleted_by_count = self.detection_db.cleanup_excess_records(self.db_max_records)
                deleted_count += deleted_by_count
                if deleted_by_count > 0:
                    logger.info(f"Database cleanup: deleted {deleted_by_count} excess records (max: {self.db_max_records})")
            
            # 3. 执行VACUUM以回收空间
            if deleted_count > 0:
                try:
                    conn = self.detection_db._get_connection()
                    conn.execute("VACUUM")
                    conn.close()
                    logger.info(f"Database VACUUM completed, freed space")
                except Exception as e:
                    logger.warning(f"Database VACUUM failed: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
            return 0
    
    def cleanup_snapshots(self) -> int:
        """
        清理快照（按时间、数量和大小限制）
        
        Returns:
            删除的快照数
        """
        if not self.snapshot_dir or not os.path.exists(self.snapshot_dir):
            return 0
        
        try:
            deleted_count = 0
            snapshot_path = Path(self.snapshot_dir)
            
            # 获取所有快照文件（排除监控截图）
            snapshots = [
                f for f in snapshot_path.glob("snapshot_*.jpg")
                if not f.name.startswith("monitoring_snapshot_")
            ]
            
            if not snapshots:
                return 0
            
            # 按修改时间排序（最旧的在前面）
            snapshots.sort(key=lambda f: f.stat().st_mtime)
            
            # 1. 按时间清理
            if self.snapshot_retention_days > 0:
                cutoff_time = time.time() - (self.snapshot_retention_days * 86400)
                for snapshot in snapshots[:]:
                    if snapshot.stat().st_mtime < cutoff_time:
                        try:
                            snapshot.unlink()
                            snapshots.remove(snapshot)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete snapshot {snapshot}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Snapshot cleanup: deleted {deleted_count} snapshots older than {self.snapshot_retention_days} days")
            
            # 2. 按数量限制清理（循环写入）
            if self.snapshot_max_count > 0 and len(snapshots) > self.snapshot_max_count:
                excess_count = len(snapshots) - self.snapshot_max_count
                for snapshot in snapshots[:excess_count]:
                    try:
                        snapshot.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete snapshot {snapshot}: {e}")
                
                if excess_count > 0:
                    logger.info(f"Snapshot cleanup: deleted {excess_count} excess snapshots (max: {self.snapshot_max_count})")
            
            # 3. 按大小限制清理
            if self.snapshot_max_size_mb > 0:
                total_size_mb = sum(f.stat().st_size for f in snapshots) / (1024 * 1024)
                
                if total_size_mb > self.snapshot_max_size_mb:
                    # 计算需要删除的大小
                    target_size_mb = self.snapshot_max_size_mb * 0.9  # 保留90%的目标大小
                    need_delete_mb = total_size_mb - target_size_mb
                    
                    deleted_size = 0
                    for snapshot in snapshots:
                        if deleted_size >= need_delete_mb:
                            break
                        
                        try:
                            file_size_mb = snapshot.stat().st_size / (1024 * 1024)
                            snapshot.unlink()
                            deleted_size += file_size_mb
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete snapshot {snapshot}: {e}")
                    
                    if deleted_count > 0:
                        logger.info(f"Snapshot cleanup: deleted {deleted_count} snapshots to reduce size (target: {self.snapshot_max_size_mb}MB)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up snapshots: {e}")
            return 0
    
    def cleanup_monitoring_snapshots(self) -> int:
        """
        清理监控截图（按时间、数量和大小限制）
        
        Returns:
            删除的监控截图数
        """
        if not self.snapshot_dir or not os.path.exists(self.snapshot_dir):
            return 0
        
        try:
            deleted_count = 0
            snapshot_path = Path(self.snapshot_dir)
            
            # 获取所有监控截图文件
            monitoring_snapshots = list(snapshot_path.glob("monitoring_snapshot_*.jpg"))
            
            if not monitoring_snapshots:
                return 0
            
            # 按修改时间排序（最旧的在前面）
            monitoring_snapshots.sort(key=lambda f: f.stat().st_mtime)
            
            # 1. 按时间清理
            if self.monitoring_retention_days > 0:
                cutoff_time = time.time() - (self.monitoring_retention_days * 86400)
                for snapshot in monitoring_snapshots[:]:
                    if snapshot.stat().st_mtime < cutoff_time:
                        try:
                            snapshot.unlink()
                            monitoring_snapshots.remove(snapshot)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete monitoring snapshot {snapshot}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Monitoring snapshot cleanup: deleted {deleted_count} snapshots older than {self.monitoring_retention_days} days")
            
            # 2. 按数量限制清理（循环写入）
            if self.monitoring_max_count > 0 and len(monitoring_snapshots) > self.monitoring_max_count:
                excess_count = len(monitoring_snapshots) - self.monitoring_max_count
                for snapshot in monitoring_snapshots[:excess_count]:
                    try:
                        snapshot.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete monitoring snapshot {snapshot}: {e}")
                
                if excess_count > 0:
                    logger.info(f"Monitoring snapshot cleanup: deleted {excess_count} excess snapshots (max: {self.monitoring_max_count})")
            
            # 3. 按大小限制清理
            if self.monitoring_max_size_mb > 0:
                total_size_mb = sum(f.stat().st_size for f in monitoring_snapshots) / (1024 * 1024)
                
                if total_size_mb > self.monitoring_max_size_mb:
                    target_size_mb = self.monitoring_max_size_mb * 0.9
                    need_delete_mb = total_size_mb - target_size_mb
                    
                    deleted_size = 0
                    for snapshot in monitoring_snapshots:
                        if deleted_size >= need_delete_mb:
                            break
                        
                        try:
                            file_size_mb = snapshot.stat().st_size / (1024 * 1024)
                            snapshot.unlink()
                            deleted_size += file_size_mb
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete monitoring snapshot {snapshot}: {e}")
                    
                    if deleted_count > 0:
                        logger.info(f"Monitoring snapshot cleanup: deleted {deleted_count} snapshots to reduce size (target: {self.monitoring_max_size_mb}MB)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up monitoring snapshots: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据留存统计信息
        
        Returns:
            统计信息字典
        """
        stats = {}
        
        # 数据库统计
        if self.detection_db:
            stats['database'] = {
                'record_count': self.detection_db.get_record_count(),
                'size_mb': self.detection_db.get_database_size_mb(),
                'max_records': self.db_max_records,
                'retention_days': self.db_retention_days
            }
        
        # 快照统计
        if self.snapshot_dir and os.path.exists(self.snapshot_dir):
            snapshot_path = Path(self.snapshot_dir)
            snapshots = [
                f for f in snapshot_path.glob("snapshot_*.jpg")
                if not f.name.startswith("monitoring_snapshot_")
            ]
            total_size = sum(f.stat().st_size for f in snapshots) / (1024 * 1024)
            
            stats['snapshots'] = {
                'count': len(snapshots),
                'size_mb': total_size,
                'max_count': self.snapshot_max_count,
                'max_size_mb': self.snapshot_max_size_mb,
                'retention_days': self.snapshot_retention_days
            }
            
            # 监控截图统计
            monitoring_snapshots = list(snapshot_path.glob("monitoring_snapshot_*.jpg"))
            monitoring_size = sum(f.stat().st_size for f in monitoring_snapshots) / (1024 * 1024)
            
            stats['monitoring_snapshots'] = {
                'count': len(monitoring_snapshots),
                'size_mb': monitoring_size,
                'max_count': self.monitoring_max_count,
                'max_size_mb': self.monitoring_max_size_mb,
                'retention_days': self.monitoring_retention_days
            }
        
        return stats


