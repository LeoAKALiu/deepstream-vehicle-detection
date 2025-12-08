# Jetson 客户端 - 云边协同模块

## 概述

Jetson客户端模块用于将边缘设备（Jetson）上的车辆检测结果上传到云端服务器，实现云边协同。

## 功能特性

- ✅ 异步上传：使用后台线程队列，不阻塞检测流程
- ✅ 自动重试：网络错误时自动重试（可配置次数和延迟）
- ✅ 图片压缩：自动压缩大图片以减少上传时间
- ✅ 健康检查：定期检查云端服务器连接状态
- ✅ 错误处理：完善的错误处理和日志记录

## 快速开始

### 1. 安装依赖

```bash
cd jetson-client
pip install -r requirements.txt
```

### 2. 配置云端服务器

编辑 `config.yaml` 中的 `cloud` 配置：

```yaml
cloud:
  enabled: true                              # 启用云端上传
  api_base_url: "http://your-server-ip:8000" # 云端服务器地址
  api_key: "your-api-key-here"                # API密钥
  upload_interval: 10                         # 上传间隔（秒）
  max_image_size_mb: 5                        # 最大图片大小（MB）
  enable_image_upload: true                   # 是否上传图片
  enable_alert_upload: true                   # 是否上传警报
  retry_attempts: 3                          # 重试次数
  retry_delay: 2.0                            # 重试延迟（秒）
  save_snapshots: true                        # 是否保存本地快照
```

或者使用环境变量（推荐）：

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 3. 使用

在主程序 `test_system_realtime.py` 中，云端集成已自动集成。只需在配置文件中启用即可。

## 模块说明

### config.py
配置管理模块，从环境变量或配置文件加载云端配置。

### cloud_client.py
云端API客户端，负责与云端服务器通信：
- `send_alert()` - 发送警报JSON
- `upload_image()` - 上传图片文件
- `health_check()` - 检查服务器连接

### detection_result.py
检测结果数据结构，包含：
- 车辆类型
- 置信度
- 车牌号
- 时间戳
- 图片路径
- 边界框
- 距离
- 是否已备案

### main_integration.py
主集成模块，提供：
- `SentinelIntegration` 类
- 队列机制（异步上传）
- 后台线程处理

## API端点

### 发送警报
- **端点**: `POST /api/alerts`
- **认证**: Header `X-API-Key: your-api-key`
- **数据格式**:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "vehicle_type": "Excavator",
  "plate_number": "ABC-1234",
  "confidence": 0.95,
  "distance": 5.2,
  "is_registered": true,
  "track_id": 123
}
```

### 上传图片
- **端点**: `POST /api/images`
- **认证**: Header `X-API-Key: your-api-key`
- **数据格式**: `multipart/form-data`
  - `file`: 图片文件
  - `alert_id`: 可选的关联警报ID

## 集成到主程序

云端集成已集成到 `test_system_realtime.py` 主程序中：

1. **自动初始化**：如果配置中 `cloud.enabled=true`，系统会自动初始化云端集成
2. **自动上传**：检测到车辆时，自动保存快照并上传到云端
3. **异步处理**：上传过程在后台线程中进行，不阻塞检测流程

## 故障排查

### 连接失败
1. 检查服务器IP和端口是否正确
2. 检查防火墙设置
3. 确认服务器服务正在运行：`curl http://your-server:8000/health`

### 认证失败
1. 验证API密钥是否正确
2. 检查请求头是否正确设置

### 图片上传失败
1. 检查文件大小是否超过限制
2. 验证文件路径是否正确
3. 检查磁盘空间是否充足

## 详细文档

更多详细信息请参考：
- `JETSON_DEVELOPMENT.md` - 完整开发指南
- `JETSON_INTEGRATION_SUMMARY.md` - 集成总结

---
*最后更新: 2025-01-02*
