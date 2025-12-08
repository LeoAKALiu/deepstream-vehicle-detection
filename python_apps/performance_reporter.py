#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能报告生成模块
生成日报、周报、月报
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3


class PerformanceReporter:
    """性能报告生成器"""
    
    def __init__(self, db_path: str = "detection_results.db", report_dir: str = "reports"):
        """
        初始化报告生成器
        
        Args:
            db_path: 数据库文件路径
            report_dir: 报告保存目录
        """
        self.db_path = db_path
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成日报
        
        Args:
            date: 日期，如果为None则使用今天
            
        Returns:
            报告字典
        """
        if date is None:
            date = datetime.now()
        
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        return self._generate_report(start_time, end_time, "daily")
    
    def generate_weekly_report(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成周报
        
        Args:
            week_start: 周开始日期，如果为None则使用本周一
            
        Returns:
            报告字典
        """
        if week_start is None:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
        
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        
        return self._generate_report(week_start, week_end, "weekly")
    
    def generate_monthly_report(self, month: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成月报
        
        Args:
            month: 月份，如果为None则使用本月
            
        Returns:
            报告字典
        """
        if month is None:
            month = datetime.now()
        
        month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month.month == 12:
            month_end = month_start.replace(year=month.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month.month + 1)
        
        return self._generate_report(month_start, month_end, "monthly")
    
    def _generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        report_type: str
    ) -> Dict[str, Any]:
        """
        生成报告
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            report_type: 报告类型（daily/weekly/monthly）
            
        Returns:
            报告字典
        """
        # 从数据库获取数据
        stats = self._get_statistics(start_time, end_time)
        
        # 生成报告
        report = {
            "report_type": report_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_detections": stats.get("total_detections", 0),
                "total_vehicles": stats.get("total_vehicles", 0),
                "registered_vehicles": stats.get("registered_vehicles", 0),
                "unregistered_vehicles": stats.get("unregistered_vehicles", 0),
                "civilian_vehicles": stats.get("civilian_vehicles", 0),
                "detection_rate": stats.get("detection_rate", 0.0)
            },
            "vehicle_types": stats.get("vehicle_types", {}),
            "time_distribution": stats.get("time_distribution", {}),
            "system_stats": stats.get("system_stats", {}),
            "anomalies": stats.get("anomalies", [])
        }
        
        # 保存报告
        self._save_report(report, report_type, start_time)
        
        return report
    
    def _get_statistics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        从数据库获取统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计信息字典
        """
        if not os.path.exists(self.db_path):
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()
        
        stats = {}
        
        # 总检测数
        cursor.execute("""
            SELECT COUNT(*) FROM detections
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_str, end_str))
        stats["total_detections"] = cursor.fetchone()[0]
        
        # 总车辆数（去重track_id）
        cursor.execute("""
            SELECT COUNT(DISTINCT track_id) FROM detections
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_str, end_str))
        stats["total_vehicles"] = cursor.fetchone()[0]
        
        # 已备案车辆数
        cursor.execute("""
            SELECT COUNT(DISTINCT track_id) FROM detections
            WHERE timestamp >= ? AND timestamp < ?
            AND status = 'registered'
        """, (start_str, end_str))
        stats["registered_vehicles"] = cursor.fetchone()[0]
        
        # 未备案车辆数
        cursor.execute("""
            SELECT COUNT(DISTINCT track_id) FROM detections
            WHERE timestamp >= ? AND timestamp < ?
            AND status = 'unregistered'
        """, (start_str, end_str))
        stats["unregistered_vehicles"] = cursor.fetchone()[0]
        
        # 社会车辆数
        cursor.execute("""
            SELECT COUNT(DISTINCT track_id) FROM detections
            WHERE timestamp >= ? AND timestamp < ?
            AND type = 'civilian'
        """, (start_str, end_str))
        stats["civilian_vehicles"] = cursor.fetchone()[0]
        
        # 检测率（每小时检测数）
        hours = (end_time - start_time).total_seconds() / 3600
        if hours > 0:
            stats["detection_rate"] = stats["total_detections"] / hours
        else:
            stats["detection_rate"] = 0.0
        
        # 车辆类型分布
        cursor.execute("""
            SELECT detected_class, COUNT(*) as count
            FROM detections
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY detected_class
            ORDER BY count DESC
        """, (start_str, end_str))
        stats["vehicle_types"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 时间分布（按小时）
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM detections
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY hour
            ORDER BY hour
        """, (start_str, end_str))
        stats["time_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return stats
    
    def _save_report(
        self,
        report: Dict[str, Any],
        report_type: str,
        start_time: datetime
    ) -> str:
        """
        保存报告到文件
        
        Args:
            report: 报告字典
            report_type: 报告类型
            start_time: 开始时间
            
        Returns:
            报告文件路径
        """
        if report_type == "daily":
            filename = f"daily_report_{start_time.strftime('%Y%m%d')}.json"
        elif report_type == "weekly":
            filename = f"weekly_report_{start_time.strftime('%Y%m%d')}.json"
        elif report_type == "monthly":
            filename = f"monthly_report_{start_time.strftime('%Y%m')}.json"
        else:
            filename = f"report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def get_latest_report(self, report_type: str = "daily") -> Optional[Dict[str, Any]]:
        """
        获取最新报告
        
        Args:
            report_type: 报告类型
            
        Returns:
            报告字典，如果不存在则返回None
        """
        pattern = f"{report_type}_report_*.json"
        reports = list(self.report_dir.glob(pattern))
        
        if not reports:
            return None
        
        latest = max(reports, key=lambda p: p.stat().st_mtime)
        
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)




