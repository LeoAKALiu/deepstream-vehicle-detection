#!/usr/bin/env python3
"""
Cassia蓝牙信标客户端
用于获取信标RSSI数据并匹配距离
"""

import asyncio
import aiohttp
from aiohttp_sse_client import client as sse_client_async
import json
import time
from threading import Thread, Lock
import math


class CassiaBeaconClient:
    """Cassia蓝牙信标客户端"""
    
    def __init__(self, ac_url, developer_key, developer_secret, router_mac):
        """
        Args:
            ac_url: AC控制器地址，如 'http://192.168.1.100'
            developer_key: 开发者密钥
            developer_secret: 开发者密码
            router_mac: 路由器MAC地址
        """
        self.ac_url = ac_url
        self.ac_host = f'{ac_url}/api'
        self.developer_key = developer_key
        self.developer_secret = developer_secret
        self.router_mac = router_mac
        
        self.token = None
        self.token_expire_time = 0
        
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
        print("✓ Cassia信标扫描已启动")
    
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
                # 认证
                if not self.token or time.time() > self.token_expire_time:
                    await self._authenticate()
                
                # 扫描
                await self._scan_beacons()
            except Exception as e:
                print(f"⚠ 信标扫描错误: {e}")
                await asyncio.sleep(5)
    
    async def _authenticate(self):
        """认证获取token"""
        url = f"{self.ac_host}/oauth2/token"
        auth = aiohttp.BasicAuth(self.developer_key, self.developer_secret)
        data = {"grant_type": "client_credentials"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=auth, json=data) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"认证失败: {error}")
                result = await resp.json()
                self.token = result.get('access_token')
                self.token_expire_time = time.time() + 3500  # 提前100秒刷新
                print(f"✓ Cassia认证成功")
    
    async def _scan_beacons(self):
        """扫描信标（SSE流）"""
        params = {
            'filter_rssi': -90,  # RSSI阈值
            'active': 1,         # 主动扫描
            'mac': self.router_mac,
            'access_token': self.token,
            'event': 1
        }
        
        url = f"{self.ac_host}/gap/nodes"
        timeout = aiohttp.ClientTimeout(total=None)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with sse_client_async.EventSource(url, params=params, session=session) as evts:
                    async for event in evts:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(event.data)
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
                            pass
                        
            except Exception as e:
                if self.running:
                    print(f"⚠ SSE连接错误: {e}")
    
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


# 使用示例
if __name__ == '__main__':
    # 配置
    AC_URL = 'http://192.168.1.100'  # 修改为你的AC地址
    DEVELOPER_KEY = 'your_key'
    DEVELOPER_SECRET = 'your_secret'
    ROUTER_MAC = 'CC:1B:E0:E2:E9:B8'  # 修改为你的路由器MAC
    
    # 创建客户端
    client = CassiaBeaconClient(AC_URL, DEVELOPER_KEY, DEVELOPER_SECRET, ROUTER_MAC)
    client.start()
    
    print("扫描信标中...")
    time.sleep(10)  # 等待扫描数据
    
    # 获取信标
    beacons = client.get_beacons()
    print(f"\n发现 {len(beacons)} 个信标:")
    for beacon in beacons:
        print(f"  MAC: {beacon['mac']}, RSSI: {beacon['rssi']}, 距离: {beacon['distance']:.2f}m")
    
    # 查找特定距离的信标
    target = client.find_nearest_beacon(5.0, tolerance=2.0)
    if target:
        print(f"\n找到5米附近的信标: {target['mac']}, 实际距离: {target['distance']:.2f}m")
    
    client.stop()

