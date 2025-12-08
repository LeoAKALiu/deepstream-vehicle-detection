#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的 HTTP API 服务器
提供系统状态查询、日志查看等功能
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import threading
import subprocess


class APIHandler(BaseHTTPRequestHandler):
    """API 请求处理器"""
    
    def __init__(self, *args, project_root: str = None, **kwargs):
        self.project_root = project_root or os.getcwd()
        super().__init__(*args, **kwargs)
    
    def log_message(self, format: str, *args: Any) -> None:
        """重写日志方法，使用自定义格式"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")
    
    def do_GET(self) -> None:
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/api/status':
                self.handle_status()
            elif path == '/api/status/json':
                self.handle_status_json()
            elif path == '/api/logs':
                self.handle_logs(query_params)
            elif path == '/api/stats':
                self.handle_stats(query_params)
            elif path == '/':
                self.handle_index()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_index(self) -> None:
        """处理首页请求"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>车辆检测系统 API</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .endpoint { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
                code { background: #e8e8e8; padding: 2px 6px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>车辆检测系统 API</h1>
            <p>可用的 API 端点：</p>
            <div class="endpoint">
                <h3>GET /api/status</h3>
                <p>获取系统状态（文本格式）</p>
                <code>curl http://localhost:8080/api/status</code>
            </div>
            <div class="endpoint">
                <h3>GET /api/status/json</h3>
                <p>获取系统状态（JSON格式）</p>
                <code>curl http://localhost:8080/api/status/json</code>
            </div>
            <div class="endpoint">
                <h3>GET /api/logs?lines=100</h3>
                <p>获取最近日志</p>
                <code>curl http://localhost:8080/api/logs?lines=100</code>
            </div>
            <div class="endpoint">
                <h3>GET /api/stats</h3>
                <p>获取统计信息</p>
                <code>curl http://localhost:8080/api/stats</code>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def handle_status(self) -> None:
        """处理状态查询（文本格式）"""
        status_script = os.path.join(self.project_root, 'scripts', 'system_status.sh')
        if os.path.exists(status_script):
            result = subprocess.run(
                [status_script],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            output = result.stdout
        else:
            output = "状态脚本不存在"
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(output.encode('utf-8'))
    
    def handle_status_json(self) -> None:
        """处理状态查询（JSON格式）"""
        status_script = os.path.join(self.project_root, 'scripts', 'system_status.sh')
        if os.path.exists(status_script):
            result = subprocess.run(
                [status_script, 'json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            try:
                status_data = json.loads(result.stdout)
            except:
                status_data = {"error": "Failed to parse status"}
        else:
            status_data = {"error": "Status script not found"}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(status_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def handle_logs(self, query_params: Dict[str, list]) -> None:
        """处理日志查询"""
        lines = int(query_params.get('lines', ['100'])[0])
        
        log_files = [
            os.path.join(self.project_root, 'logs', 'startup.log'),
            os.path.join(self.project_root, 'logs', 'resource_monitor.log'),
            '/tmp/vehicle_detection.log'
        ]
        
        log_content = []
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        file_lines = f.readlines()
                        log_content.append(f"=== {log_file} ===\n")
                        log_content.extend(file_lines[-lines:])
                        log_content.append("\n")
                except Exception as e:
                    log_content.append(f"Error reading {log_file}: {e}\n")
        
        output = ''.join(log_content) if log_content else "No logs found"
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(output.encode('utf-8'))
    
    def handle_stats(self, query_params: Dict[str, list]) -> None:
        """处理统计信息查询"""
        # 尝试从数据库获取统计信息
        db_path = os.path.join(self.project_root, 'detection_results.db')
        stats = {}
        
        if os.path.exists(db_path):
            try:
                from detection_database import DetectionDatabase
                db = DetectionDatabase(db_path)
                stats = db.get_statistics()
            except Exception as e:
                stats = {"error": f"Failed to get database stats: {e}"}
        else:
            stats = {"message": "Database not found", "database_path": db_path}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(stats, ensure_ascii=False, indent=2).encode('utf-8'))


def create_handler(project_root: str):
    """创建带项目根目录的处理器类"""
    class Handler(APIHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, project_root=project_root, **kwargs)
    return Handler


class APIServer:
    """API 服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080, project_root: str = None):
        """
        初始化 API 服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            project_root: 项目根目录
        """
        self.host = host
        self.port = port
        self.project_root = project_root or os.getcwd()
        self.server = None
        self.thread = None
    
    def start(self, daemon: bool = True) -> None:
        """启动服务器"""
        Handler = create_handler(self.project_root)
        self.server = HTTPServer((self.host, self.port), Handler)
        
        if daemon:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"API 服务器已启动: http://{self.host}:{self.port}")
        else:
            print(f"API 服务器已启动: http://{self.host}:{self.port}")
            print("按 Ctrl+C 停止服务器")
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self) -> None:
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            print("API 服务器已停止")
    
    def is_running(self) -> bool:
        """检查服务器是否运行"""
        return self.server is not None and self.thread is not None and self.thread.is_alive()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='车辆检测系统 API 服务器')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8080, help='监听端口')
    parser.add_argument('--project-root', type=str, default=None, help='项目根目录')
    
    args = parser.parse_args()
    
    project_root = args.project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    server = APIServer(host=args.host, port=args.port, project_root=project_root)
    server.start(daemon=False)

