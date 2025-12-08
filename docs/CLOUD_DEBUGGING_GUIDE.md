# 云端服务器联调指南

## 概述

本文档提供云端服务器联调的详细步骤和故障排除指南。

## 快速开始

### 1. 配置云端服务器信息

编辑 `config.yaml` 文件，更新云端配置：

```yaml
cloud:
  enabled: true                              # 启用云端上传
  api_base_url: "http://your-server-ip:8000" # 替换为实际服务器地址
  api_key: "your-api-key-here"                # 替换为实际API密钥
  upload_interval: 10                         # 上传间隔（秒）
  max_image_size_mb: 5                        # 最大图片大小（MB）
  enable_image_upload: true                   # 是否上传图片
  enable_alert_upload: true                   # 是否上传警报
  retry_attempts: 3                          # 重试次数
  retry_delay: 2.0                            # 重试延迟（秒）
```

### 2. 运行联调测试

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
python3 scripts/test_cloud_connection.py
```

测试脚本会依次测试：
1. 健康检查（服务器连通性）
2. 发送警报
3. 上传图片
4. 集成模块

## 测试步骤详解

### 步骤1：健康检查

测试服务器是否可达：

```python
client = CloudClient(config)
result = client.health_check()
```

**预期结果**：返回 `True` 表示服务器可达

**常见问题**：
- ❌ 连接超时：检查服务器地址和端口是否正确
- ❌ 404错误：检查服务器是否运行，API路径是否正确
- ❌ 认证失败：检查API密钥是否正确

### 步骤2：发送警报

测试发送检测警报到服务器：

```python
alert_id = client.send_alert(
    vehicle_type="Excavator",
    timestamp=datetime.now(),
    plate_number="测试车牌",
    confidence=0.95,
    distance=5.2,
    is_registered=True,
    track_id=1
)
```

**预期结果**：返回警报ID（整数）

**API端点**：`POST /api/alerts`

**请求格式**：
```json
{
  "timestamp": "2025-12-01T10:30:00",
  "vehicle_type": "Excavator",
  "plate_number": "测试车牌",
  "confidence": 0.95,
  "distance": 5.2,
  "is_registered": true,
  "track_id": 1
}
```

**常见问题**：
- ❌ 400错误：检查请求数据格式是否正确
- ❌ 401错误：检查API密钥是否正确
- ❌ 500错误：服务器内部错误，联系服务器管理员

### 步骤3：上传图片

测试上传车辆快照到服务器：

```python
image_url = client.upload_image("/path/to/image.jpg", alert_id=123)
```

**预期结果**：返回图片URL或路径

**API端点**：`POST /api/images`

**请求格式**：`multipart/form-data`
- `file`: 图片文件
- `alert_id`: 关联的警报ID（可选）

**常见问题**：
- ❌ 文件过大：图片会被自动压缩
- ❌ 格式不支持：确保图片为JPEG格式
- ❌ 上传超时：检查网络连接和图片大小

### 步骤4：集成模块测试

测试完整的集成流程：

```python
integration = SentinelIntegration(config)
integration.start()

detection = DetectionResult(
    vehicle_type="Excavator",
    confidence=0.95,
    plate_number="测试车牌",
    timestamp=datetime.now(),
    image_path="/path/to/snapshot.jpg",
    bbox=(100, 100, 500, 400),
    track_id=1,
    distance=5.2,
    is_registered=True
)

integration.on_detection(detection)
```

**预期结果**：检测结果被添加到队列并自动上传

## 故障排除

### 问题1：无法连接到服务器

**症状**：健康检查失败，连接超时

**解决方案**：
1. 检查服务器地址和端口是否正确
2. 检查网络连接（ping服务器）
3. 检查防火墙设置
4. 检查服务器是否运行

```bash
# 测试网络连接
ping your-server-ip

# 测试端口
telnet your-server-ip 8000
# 或
nc -zv your-server-ip 8000
```

### 问题2：API密钥错误

**症状**：401 Unauthorized 错误

**解决方案**：
1. 检查 `config.yaml` 中的 `api_key` 是否正确
2. 检查服务器端的API密钥配置
3. 确认API密钥格式（是否有空格、换行等）

### 问题3：图片上传失败

**症状**：图片上传返回错误或超时

**解决方案**：
1. 检查图片文件是否存在
2. 检查图片大小（会被自动压缩到5MB以下）
3. 检查图片格式（支持JPEG）
4. 检查网络带宽

### 问题4：警报发送成功但图片未上传

**症状**：警报ID返回，但图片上传失败

**解决方案**：
1. 检查 `enable_image_upload` 配置
2. 检查图片路径是否正确
3. 检查服务器端图片上传接口
4. 查看日志文件获取详细错误信息

## 调试技巧

### 1. 启用详细日志

在主程序中，检查日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 手动测试API

使用 `curl` 命令测试API：

```bash
# 健康检查
curl -H "X-API-Key: your-api-key" http://your-server-ip:8000/health

# 发送警报
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-12-01T10:30:00",
    "vehicle_type": "Excavator",
    "confidence": 0.95
  }' \
  http://your-server-ip:8000/api/alerts

# 上传图片
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -F "file=@/path/to/image.jpg" \
  -F "alert_id=123" \
  http://your-server-ip:8000/api/images
```

### 3. 检查队列状态

在集成模块中，检查队列大小：

```python
queue_size = integration.get_queue_size()
print(f"队列大小: {queue_size}")
```

### 4. 查看网络请求

使用 `tcpdump` 或 `wireshark` 捕获网络请求：

```bash
sudo tcpdump -i any -A 'host your-server-ip and port 8000'
```

## 配置检查清单

在开始联调前，确认以下配置：

- [ ] `cloud.enabled = true`
- [ ] `api_base_url` 已更新为实际服务器地址
- [ ] `api_key` 已更新为实际API密钥
- [ ] 网络连接正常（可以ping通服务器）
- [ ] 服务器端口可访问（telnet/nc测试）
- [ ] 防火墙规则允许出站连接

## 服务器端API规范

### 健康检查端点

```
GET /health
Headers:
  X-API-Key: <api_key>
Response:
  200 OK
```

### 警报端点

```
POST /api/alerts
Headers:
  X-API-Key: <api_key>
  Content-Type: application/json
Body:
  {
    "timestamp": "ISO 8601格式时间戳",
    "vehicle_type": "车辆类型字符串",
    "plate_number": "车牌号（可选）",
    "confidence": 0.0-1.0,
    "distance": 距离（米，可选）,
    "is_registered": true/false,
    "track_id": 跟踪ID（可选）
  }
Response:
  {
    "id": 警报ID
  }
```

### 图片上传端点

```
POST /api/images
Headers:
  X-API-Key: <api_key>
Body (multipart/form-data):
  file: 图片文件
  alert_id: 关联的警报ID（可选）
Response:
  {
    "path": "图片路径或URL",
    "url": "图片URL（可选）"
  }
```

## 联系支持

如果遇到无法解决的问题，请提供以下信息：

1. 测试脚本的完整输出
2. 服务器地址和端口
3. 错误消息和堆栈跟踪
4. 网络连接测试结果
5. 服务器端日志（如果可访问）

## 下一步

联调成功后：

1. 在主程序中启用云端上传（`cloud.enabled = true`）
2. 运行主程序进行实际测试
3. 监控上传队列和错误日志
4. 根据实际情况调整配置参数




