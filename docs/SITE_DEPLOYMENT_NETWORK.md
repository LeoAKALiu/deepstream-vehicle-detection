# 工地部署网络配置

## 网络拓扑

```
4G路由器 (网关: 192.168.3.1)
    │
    ├─ POE交换机
    │   ├─ Jetson (IP: 192.168.3.243, DHCP)
    │   └─ Cassia路由器 (IP: 192.168.3.26, 静态)
    │
    └─ 互联网 (4G)
```

## 网络配置详情

### Jetson设备
- **IP地址**: 192.168.3.243 (DHCP自动获取)
- **网关**: 192.168.3.1
- **网络接口**: enP8p1s0 (有线网口)
- **网络状态**: ✓ 可访问外网

### Cassia路由器
- **IP地址**: 192.168.3.26 (静态IP)
- **连接方式**: 通过POE交换机连接到4G路由器
- **连通性**: ✓ 正常
- **Web接口**: ✓ 可访问 (HTTP 200)
- **SSE扫描接口**: ✓ 正常响应

## 配置文件更新

### config.yaml
```yaml
network:
  cassia_ip: "192.168.3.26"  # 已更新（原: 192.168.1.2）
  camera_id: "camera_01"
```

## 连通性测试结果

### 测试时间
2025-12-01

### 测试结果
✅ **所有测试通过**

1. **Ping测试**: ✓ 成功 (延迟: 0.584ms)
2. **Web接口测试**: ✓ HTTP 200
3. **SSE扫描接口**: ✓ 正常响应，已检测到信标
4. **网络路由**: ✓ 正常

### 检测到的信标示例
```
MAC: 94:24:B8:71:47:EB
RSSI: -56 dBm
```

## 测试脚本

使用以下脚本测试Cassia连通性：

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
bash scripts/test_cassia_connectivity.sh
```

## 注意事项

1. **网络稳定性**
   - 4G网络可能不稳定，建议监控网络状态
   - 已实现网络恢复机制，会自动重连

2. **IP地址变化**
   - Jetson使用DHCP，IP可能变化
   - Cassia使用静态IP，不会变化
   - 如果Jetson IP变化，不影响Cassia连接

3. **防火墙设置**
   - 确保4G路由器允许内网设备互相访问
   - 确保Cassia的SSE接口（端口80）可访问

## 下一步

1. ✅ 配置文件已更新
2. ✅ 连通性测试通过
3. ⏭️ 运行完整系统测试
4. ⏭️ 监控长期运行稳定性

## 相关文件

- `config.yaml` - 主配置文件
- `scripts/test_cassia_connectivity.sh` - 连通性测试脚本
- `python_apps/network_recovery.py` - 网络恢复模块


