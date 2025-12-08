# Jetson 端集成总结

## 📋 开发任务清单

### ✅ 必须实现的功能

1. **配置管理模块** (`config.py`)
   - [ ] 从环境变量加载云端服务器配置
   - [ ] 存储 API 密钥和服务器地址
   - [ ] 配置上传参数（间隔、文件大小限制等）

2. **云端通信模块** (`cloud_client.py`)
   - [ ] 实现 `send_alert()` - 发送警报 JSON
   - [ ] 实现 `upload_image()` - 上传图片文件
   - [ ] 实现重试机制和错误处理
   - [ ] 实现图片压缩功能

3. **检测结果数据结构** (`detection_result.py`)
   - [ ] 定义检测结果数据类
   - [ ] 包含车辆类型、置信度、车牌号等字段
   - [ ] 时间戳自动生成

4. **主集成模块** (`main_integration.py`)
   - [ ] 实现队列机制（异步上传）
   - [ ] 后台线程处理上传
   - [ ] 提供 `on_detection()` 回调接口

5. **与现有 AI 检测代码集成**
   - [ ] 在检测循环中调用 `integration.on_detection()`
   - [ ] 保存检测快照到本地文件
   - [ ] 传递检测结果（车辆类型、置信度等）

### 🔧 可选优化功能

6. **车牌识别 (OCR)**
   - [ ] 集成车牌识别模块
   - [ ] 将识别结果添加到 `plate_number` 字段

7. **本地缓存机制**
   - [ ] 网络断开时缓存数据
   - [ ] 网络恢复后批量上传

8. **性能监控**
   - [ ] 记录上传成功率
   - [ ] 监控队列大小
   - [ ] 性能指标统计

## 📁 文件结构

```
jetson-sentinel-client/
├── config.py              # ✅ 配置管理（需实现）
├── cloud_client.py        # ✅ 云端通信（需实现）
├── detection_result.py    # ✅ 数据结构（需实现）
├── main_integration.py    # ✅ 集成模块（需实现）
├── requirements.txt       # ✅ 已提供
├── .env.example          # ✅ 已提供
└── README.md             # ✅ 已提供
```

## 🔗 API 端点

### 发送警报
- **端点**: `POST /api/alerts`
- **认证**: Header `X-API-Key: your-api-key`
- **数据格式**:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "vehicle_type": "Excavator",
  "plate_number": "ABC-1234",
  "confidence": 0.95
}
```

### 上传图片
- **端点**: `POST /api/images`
- **认证**: Header `X-API-Key: your-api-key`
- **数据格式**: `multipart/form-data`
  - `file`: 图片文件
  - `alert_id`: 可选的关联警报 ID

## 🚀 快速开始步骤

1. **复制代码文件**
   ```bash
   # 从 JETSON_DEVELOPMENT.md 复制代码到对应文件
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env，设置服务器 IP 和 API 密钥
   ```

4. **集成到检测代码**
   ```python
   from main_integration import SentinelIntegration
   from detection_result import DetectionResult
   
   # 初始化
   integration = SentinelIntegration()
   integration.start()
   
   # 在检测循环中
   detection = DetectionResult(
       vehicle_type="Excavator",
       confidence=0.95
   )
   integration.on_detection(detection)
   ```

5. **测试连接**
   ```python
   if integration.health_check():
       print("✅ Connected to cloud server")
   ```

## 📝 关键代码片段

### 最小集成示例

```python
# 在你的检测主循环中
from main_integration import SentinelIntegration
from detection_result import DetectionResult
import cv2

integration = SentinelIntegration()
integration.start()

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    
    # 运行你的 AI 检测
    # results = your_model.detect(frame)
    
    # 对于每个检测结果
    for result in results:
        if result.confidence > 0.5:  # 置信度阈值
            # 保存快照
            snapshot_path = f"/tmp/snapshot_{timestamp}.jpg"
            cv2.imwrite(snapshot_path, frame)
            
            # 创建检测结果
            detection = DetectionResult(
                vehicle_type=result.class_name,
                confidence=result.confidence,
                image_path=snapshot_path
            )
            
            # 发送到云端
            integration.on_detection(detection)
```

## ⚠️ 注意事项

1. **网络稳定性**
   - 实现重试机制（代码中已包含）
   - 考虑本地缓存机制

2. **资源管理**
   - 及时清理本地快照文件
   - 监控磁盘空间

3. **性能优化**
   - 控制上传频率（避免过于频繁）
   - 压缩大图片（代码中已包含）

4. **错误处理**
   - 网络错误不应影响检测流程
   - 记录日志便于调试

## 📚 详细文档

完整的开发指南请参考: **JETSON_DEVELOPMENT.md**

该文档包含：
- 完整的代码实现
- 详细的 API 说明
- 最佳实践
- 故障排查指南
- 集成示例

## 🆘 获取帮助

如果遇到问题：
1. 检查云端服务器是否运行: `curl http://your-server:8000/health`
2. 验证 API 密钥是否正确
3. 查看 Jetson 端日志
4. 查看云端服务器日志: `docker-compose logs backend`

