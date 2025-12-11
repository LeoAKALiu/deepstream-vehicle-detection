#!/usr/bin/env python3
"""
Cassia本地路由器客户端（Standalone模式）
用于直接连接到Cassia路由器（非AC模式）
"""

import asyncio
import aiohttp
from aiohttp_sse_client import client as sse_client_async
import json
import time
from threading import Thread, Lock
import math


class CassiaLocalClient:
    """Cassia本地路由器客户端（Standalone模式）"""
    
    def __init__(self, router_ip, username=None, password=None):
        """
        Args:
            router_ip: 路由器IP地址，如 '192.168.40.1'
            username: 可选，路由器用户名（如果需要认证）
            password: 可选，路由器密码
        """
        self.router_ip = router_ip
        self.base_url = f'http://{router_ip}'
        self.username = username
        self.password = password
        
        # 信标数据缓存 {mac: {'rssi': x, 'name': x, 'last_update': timestamp}}
        self.beacons = {}
        self.beacons_lock = Lock()
        
        # 后台扫描线程
        self.scan_thread = None
        self.running = False
        
        # RSSI转距离参数
        self.tx_power = -59  # 信标发射功率（需要根据实际信标调整）
        self.path_loss_exponent = 2.5  # 路径衰减指数（室外2-3，室内2.5-4）
    
    def start(self):
        """启动后台扫描"""
        self.running = True
        self.scan_thread = Thread(target=self._run_scan_loop, daemon=True)
        self.scan_thread.start()
        print("✓ Cassia本地扫描已启动")
    
    def stop(self):
        """停止扫描"""
        self.running = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
    
    def _run_scan_loop(self):
        """在后台线程中运行异步扫描"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._scan_loop())
    
    async def _scan_loop(self):
        """异步扫描循环"""
        while self.running:
            try:
                await self._scan_beacons()
            except Exception as e:
                print(f"⚠ 信标扫描错误: {e}")
                await asyncio.sleep(5)
    
    async def _scan_beacons(self):
        """扫描信标（SSE流）"""
        params = {
            'filter_rssi': -90,  # RSSI阈值
            'active': 1,         # 主动扫描
            'event': 1           # SSE模式
        }
        
        # 本地API端点
        url = f"{self.base_url}/gap/nodes"
        
        # 认证配置
        auth = None
        if self.username and self.password:
            auth = aiohttp.BasicAuth(self.username, self.password)
        
        timeout = aiohttp.ClientTimeout(total=None)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with sse_client_async.EventSource(
                    url, 
                    params=params, 
                    session=session,
                    auth=auth
                ) as evts:
                    async for event in evts:
                        if not self.running:
                            break
                        
                        try:
                            # 解析SSE事件
                            data = json.loads(event.data)
                            
                            # Cassia本地API格式
                            if 'bdaddrs' in data and len(data['bdaddrs']) > 0:
                                device_mac = data['bdaddrs'][0]['bdaddr']
                                rssi = data['rssi']
                                name = data.get('name', 'Unknown')
                                
                                # 更新信标数据
                                with self.beacons_lock:
                                    self.beacons[device_mac] = {
                                        'rssi': rssi,
                                        'name': name,
                                        'last_update': time.time()
                                    }
                        except Exception as e:
                            # 忽略解析错误（keep-alive等）
                            pass
        except Exception as e:
            if self.running:
                print(f"⚠ SSE连接错误: {e}")
                raise
    
    def get_beacons(self, max_age=5.0):
        """
        获取最近的信标数据
        Args:
            max_age: 最大数据年龄（秒）
        Returns:
            list of {'mac': x, 'rssi': x, 'name': x, 'distance': x}
        """
        current_time = time.time()
        beacons = []
        
        with self.beacons_lock:
            for mac, info in self.beacons.items():
                if current_time - info['last_update'] < max_age:
                    distance = self.rssi_to_distance(info['rssi'])
                    beacons.append({
                        'mac': mac,
                        'rssi': info['rssi'],
                        'name': info['name'],
                        'distance': distance
                    })
        
        return beacons
    
    def rssi_to_distance(self, rssi):
        """
        RSSI转距离（自由空间传播模型）
        
        公式: d = 10^((TxPower - RSSI) / (10 * n))
        
        Args:
            rssi: 接收信号强度
        Returns:
            distance: 距离（米）
        """
        distance = 10 ** ((self.tx_power - rssi) / (10 * self.path_loss_exponent))
        return distance
    
    def find_nearest_beacon(self, target_distance, tolerance=2.0):
        """
        查找距离最接近的信标
        Args:
            target_distance: 目标距离（米）
            tolerance: 容差（米）
        Returns:
            {'mac': x, 'rssi': x, 'distance': x} 或 None
        """
        beacons = self.get_beacons()
        
        candidates = []
        for beacon in beacons:
            distance_diff = abs(beacon['distance'] - target_distance)
            if distance_diff < tolerance:
                candidates.append({
                    'mac': beacon['mac'],
                    'rssi': beacon['rssi'],
                    'name': beacon['name'],
                    'distance': beacon['distance'],
                    'distance_diff': distance_diff
                })
        
        if candidates:
            # 返回距离差最小的
            best = min(candidates, key=lambda x: x['distance_diff'])
            return best
        
        return None


# 使用示例和测试
if __name__ == '__main__':
    import sys
    
    # 配置
    ROUTER_IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.40.1'
    USERNAME = None  # 如果需要认证，填入用户名
    PASSWORD = None  # 如果需要认证，填入密码
    
    print(f"连接到Cassia路由器: {ROUTER_IP}")
    print("按Ctrl+C停止")
    print("")
    
    # 创建客户端
    client = CassiaLocalClient(ROUTER_IP, USERNAME, PASSWORD)
    client.start()
    
    print("扫描信标中...")
    time.sleep(5)  # 等待扫描数据
    
    try:
        while True:
            # 获取信标
            beacons = client.get_beacons()
            
            print(f"\r发现 {len(beacons)} 个信标:", end='')
            for beacon in beacons[:5]:  # 只显示前5个
                print(f" [{beacon['mac'][-8:]}: {beacon['rssi']}dBm, {beacon['distance']:.1f}m]", end='')
            
            sys.stdout.flush()
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n停止扫描...")
        client.stop()
        
        # 显示最终统计
        beacons = client.get_beacons(max_age=60)
        print(f"\n共发现 {len(beacons)} 个信标:")
        for beacon in beacons:
            print(f"  MAC: {beacon['mac']}, RSSI: {beacon['rssi']}, "
                  f"距离: {beacon['distance']:.2f}m, 名称: {beacon['name']}")

