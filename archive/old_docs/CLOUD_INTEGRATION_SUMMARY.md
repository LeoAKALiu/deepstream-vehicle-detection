# 云边协同集成总结

## 实现概述

已成功实现Jetson边缘设备与云端服务器的协同功能，将车辆检测结果实时上传到云端仪表板。

## 实现内容

### 1. 核心模块实现

#### ✅ config.py - 配置管理模块
- 从环境变量或配置文件加载云端配置
- 支持所有配置参数的默认值
- 类型安全的配置类

#### ✅ cloud_client.py - 云端通信模块
- `send_alert()` - 发送警报JSON到云端
- `upload_image()` - 上传图片文件（支持压缩）
- `health_check()` - 检查服务器连接状态
- 自动重试机制（可配置）
- 图片自动压缩（超过大小限制时）

#### ✅ detection_result.py - 检测结果数据结构
- 完整的检测结果数据类
- 包含车辆类型、置信度、车牌号、时间戳等
- 支持边界框、距离、备案状态等扩展信息

#### ✅ main_integration.py - 主集成模块
- `SentinelIntegration` 类
- 队列机制（异步上传，不阻塞检测）
- 后台线程处理上传任务
- 健康检查和队列监控

### 2. 主程序集成

#### ✅ 配置集成
- 在 `config.yaml` 中添加了 `cloud` 配置节
- 支持通过配置文件或环境变量配置
- 在 `config_loader.py` 中添加了 `get_cloud()` 方法

#### ✅ 初始化集成
- 在主程序初始化时自动初始化云端集成（如果启用）
- 创建快照保存目录
- 执行健康检查

#### ✅ 检测结果上传
- 在检测到车辆时自动保存快照
- 自动上传警报和图片到云端
- 异步处理，不阻塞检测流程

### 3. 文件结构

```
jetson-client/
├── __init__.py              # 包初始化
├── config.py                # 配置管理
├── cloud_client.py          # 云端通信
├── detection_result.py      # 数据结构
├── main_integration.py      # 主集成模块
├── requirements.txt         # 依赖列表
├── .env.example            # 环境变量示例
├── README.md               # 使用说明
├── JETSON_DEVELOPMENT.md   # 开发指南（已有）
└── JETSON_INTEGRATION_SUMMARY.md  # 集成总结（已有）
```

## 使用方法

### 1. 启用云端上传

在 `config.yaml` 中配置：

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

### 2. 安装依赖

```bash
cd jetson-client
pip install -r requirements.txt
```

### 3. 运行主程序

正常启动主程序，如果云端配置已启用，系统会自动：
- 初始化云端集成
- 在检测到车辆时保存快照
- 异步上传警报和图片到云端

## 工作流程

```
检测到车辆
    ↓
创建alert字典
    ↓
保存快照到本地（/tmp/vehicle_snapshots/）
    ↓
创建DetectionResult对象
    ↓
添加到上传队列（异步）
    ↓
后台线程处理：
    ├─ 发送警报JSON → POST /api/alerts
    └─ 上传图片 → POST /api/images
```

## API端点

### 发送警报
- **端点**: `POST /api/alerts`
- **认证**: `X-API-Key: your-api-key`
- **数据**:
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
- **认证**: `X-API-Key: your-api-key`
- **数据**: `multipart/form-data`
  - `file`: 图片文件
  - `alert_id`: 关联的警报ID（可选）

## 特性

### ✅ 异步上传
- 使用队列机制，不阻塞检测流程
- 后台线程处理上传任务

### ✅ 自动重试
- 网络错误时自动重试（可配置次数和延迟）
- 指数退避策略

### ✅ 图片压缩
- 自动检测图片大小
- 超过限制时自动压缩（调整尺寸和质量）

### ✅ 错误处理
- 完善的异常处理
- 详细的日志记录

### ✅ 健康检查
- 启动时检查服务器连接
- 可随时调用 `health_check()` 检查状态

## 配置选项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enabled` | 是否启用云端上传 | `false` |
| `api_base_url` | 云端服务器地址 | `http://your-server-ip:8000` |
| `api_key` | API密钥 | `your-api-key-here` |
| `upload_interval` | 上传间隔（秒） | `10` |
| `max_image_size_mb` | 最大图片大小（MB） | `5` |
| `enable_image_upload` | 是否上传图片 | `true` |
| `enable_alert_upload` | 是否上传警报 | `true` |
| `retry_attempts` | 重试次数 | `3` |
| `retry_delay` | 重试延迟（秒） | `2.0` |
| `save_snapshots` | 是否保存本地快照 | `true` |

## 测试

### 1. 测试连接

```python
from jetson_client import SentinelIntegration, CloudConfig

config = CloudConfig(
    api_base_url="http://your-server:8000",
    api_key="your-api-key"
)
integration = SentinelIntegration(config)
integration.start()

if integration.health_check():
    print("✅ 云端服务器连接正常")
else:
    print("❌ 无法连接到云端服务器")
```

### 2. 测试上传

运行主程序，检测到车辆时会自动上传。

## 故障排查

### 连接失败
1. 检查服务器IP和端口
2. 检查防火墙设置
3. 确认服务器运行：`curl http://your-server:8000/health`

### 认证失败
1. 验证API密钥
2. 检查请求头设置

### 图片上传失败
1. 检查文件大小
2. 验证文件路径
3. 检查磁盘空间

## 下一步优化

- [ ] 本地缓存机制（网络断开时缓存数据）
- [ ] 批量上传（提高效率）
- [ ] 上传进度监控
- [ ] 性能指标统计

## 相关文档

- `jetson-client/README.md` - 使用说明
- `jetson-client/JETSON_DEVELOPMENT.md` - 开发指南
- `jetson-client/JETSON_INTEGRATION_SUMMARY.md` - 集成总结

---
*实现时间: 2025-01-02*
*状态: ✅ 已完成并集成到主程序*

