#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测结果数据库模块
使用 SQLite 存储检测结果
"""

from __future__ import annotations

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading


class DetectionDatabase:
    """检测结果数据库"""
    
    def __init__(self, db_path: str = "detection_results.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库表结构"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检测结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    track_id INTEGER,
                    vehicle_type TEXT,
                    detected_class TEXT,
                    status TEXT,
                    beacon_mac TEXT,
                    plate_number TEXT,
                    company TEXT,
                    distance REAL,
                    confidence REAL,
                    bbox_x1 REAL,
                    bbox_y1 REAL,
                    bbox_x2 REAL,
                    bbox_y2 REAL,
                    snapshot_path TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_track_id ON detections(track_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vehicle_type ON detections(vehicle_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON detections(status)
            """)
            
            conn.commit()
            conn.close()
    
    def insert_detection(self, detection: Dict[str, Any]) -> int:
        """
        插入检测结果
        
        Args:
            detection: 检测结果字典
            
        Returns:
            插入记录的ID
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = detection.get('timestamp', datetime.now().isoformat())
            track_id = detection.get('track_id')
            vehicle_type = detection.get('type', detection.get('vehicle_type'))
            detected_class = detection.get('detected_class', detection.get('detected_type'))
            status = detection.get('status')
            beacon_mac = detection.get('beacon_mac')
            plate_number = detection.get('plate_number', detection.get('plate'))
            company = detection.get('company')
            distance = detection.get('distance')
            confidence = detection.get('confidence')
            
            # 边界框
            bbox = detection.get('bbox')
            if bbox and isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                bbox_x1, bbox_y1, bbox_x2, bbox_y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            else:
                bbox_x1 = bbox_y1 = bbox_x2 = bbox_y2 = None
            
            snapshot_path = detection.get('snapshot_path')
            metadata = json.dumps(detection.get('metadata', {}))
            
            cursor.execute("""
                INSERT INTO detections (
                    timestamp, track_id, vehicle_type, detected_class, status,
                    beacon_mac, plate_number, company, distance, confidence,
                    bbox_x1, bbox_y1, bbox_x2, bbox_y2, snapshot_path, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, track_id, vehicle_type, detected_class, status,
                beacon_mac, plate_number, company, distance, confidence,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2, snapshot_path, metadata
            ))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return record_id
    
    def query_detections(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        查询检测结果
        
        Args:
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            vehicle_type: 车辆类型
            status: 状态（registered/unregistered）
            limit: 返回记录数限制
            
        Returns:
            检测结果列表
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM detections WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            if vehicle_type:
                query += " AND vehicle_type = ?"
                params.append(vehicle_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                # 解析metadata
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                results.append(result)
            
            conn.close()
            return results
    
    def get_statistics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计信息字典
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM detections WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            # 总检测数
            cursor.execute(query, params)
            total_count = cursor.fetchone()[0]
            
            # 按类型统计
            type_query = query.replace("COUNT(*)", "vehicle_type, COUNT(*) as count")
            type_query += " GROUP BY vehicle_type"
            cursor.execute(type_query, params)
            type_stats = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
            
            # 按状态统计
            status_query = query.replace("COUNT(*)", "status, COUNT(*) as count")
            status_query += " GROUP BY status"
            cursor.execute(status_query, params)
            status_stats = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
            
            conn.close()
            
            return {
                'total_count': total_count,
                'by_type': type_stats,
                'by_status': status_stats,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def export_to_csv(self, output_path: str, **kwargs) -> None:
        """
        导出为CSV格式
        
        Args:
            output_path: 输出文件路径
            **kwargs: 查询参数（同query_detections）
        """
        import csv
        
        detections = self.query_detections(**kwargs)
        
        if not detections:
            return
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=detections[0].keys())
            writer.writeheader()
            writer.writerows(detections)
    
    def export_to_json(self, output_path: str, **kwargs) -> None:
        """
        导出为JSON格式
        
        Args:
            output_path: 输出文件路径
            **kwargs: 查询参数（同query_detections）
        """
        detections = self.query_detections(**kwargs)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(detections, f, ensure_ascii=False, indent=2)
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """
        清理旧记录
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            cutoff_date = cutoff_date - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            cursor.execute("DELETE FROM detections WHERE timestamp < ?", (cutoff_str,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return deleted_count
    
    def cleanup_excess_records(self, max_records: int) -> int:
        """
        清理超出最大记录数的旧记录（循环写入）
        
        Args:
            max_records: 最大记录数
            
        Returns:
            删除的记录数
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前记录数
            cursor.execute("SELECT COUNT(*) FROM detections")
            current_count = cursor.fetchone()[0]
            
            if current_count <= max_records:
                conn.close()
                return 0
            
            # 计算需要删除的记录数
            excess_count = current_count - max_records
            
            # 删除最旧的记录
            cursor.execute("""
                DELETE FROM detections 
                WHERE id IN (
                    SELECT id FROM detections 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
            """, (excess_count,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count
    
    def get_record_count(self) -> int:
        """
        获取当前记录数
        
        Returns:
            记录数
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM detections")
            count = cursor.fetchone()[0]
            conn.close()
            return count
    
    def get_database_size_mb(self) -> float:
        """
        获取数据库文件大小（MB）
        
        Returns:
            文件大小（MB）
        """
        if not os.path.exists(self.db_path):
            return 0.0
        return os.path.getsize(self.db_path) / (1024 * 1024)


if __name__ == '__main__':
    # 测试代码
    db = DetectionDatabase("test_detection.db")
    
    # 插入测试数据
    test_detection = {
        'timestamp': datetime.now().isoformat(),
        'track_id': 1,
        'type': 'construction',
        'detected_class': 'excavator',
        'status': 'registered',
        'beacon_mac': 'AA:BB:CC:DD:EE:FF',
        'plate_number': '',
        'company': '测试公司',
        'distance': 5.2,
        'confidence': 0.95,
        'bbox': [100, 200, 300, 400],
        'snapshot_path': '/tmp/test.jpg',
        'metadata': {'test': 'data'}
    }
    
    record_id = db.insert_detection(test_detection)
    print(f"插入记录 ID: {record_id}")
    
    # 查询
    results = db.query_detections(limit=10)
    print(f"查询结果数: {len(results)}")
    
    # 统计
    stats = db.get_statistics()
    print(f"统计信息: {stats}")
    
    # 清理测试数据库
    os.remove("test_detection.db")

