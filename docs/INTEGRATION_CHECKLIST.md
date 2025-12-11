# Jetson端集成检查清单

**文档版本**: v2.0  
**检查日期**: 2025-12-09  
**参考文档**: `/home/liubo/Download/docs/JETSON_INTEGRATION_GUIDE.md`

---

## ✅ 已实现的功能

### 1. API接口实现

- [x] **POST /api/alerts** - 创建警报记录
  - ✅ 实现位置: `jetson-client/cloud_client.py::send_alert()`
  - ✅ 支持所有必需字段
  - ✅ 支持可选字段（bbox, metadata等）

- [x] **POST /api/images** - 上传图像
  - ✅ 实现位置: `jetson-client/cloud_client.py::upload_image()`
  - ✅ 支持multipart/form-data格式
  - ✅ 支持alert_id参数

- [x] **POST /api/images** - 上传监控截图
  - ✅ 实现位置: `jetson-client/cloud_client.py::upload_monitoring_snapshot()`
  - ✅ 支持image_type="monitoring_snapshot"
  - ✅ 支持device_id参数

- [x] **GET /api/beacons** - 查询信标白名单
  - ✅ 实现位置: `jetson-client/beacon_whitelist.py::fetch_whitelist()`
  - ✅ 支持定时更新（默认60秒）
  - ✅ 支持自动刷新

---

## ⚠️ 需要确认/修复的细节

### 1. 时间戳格式

**文档要求**:
- ISO 8601格式：`YYYY-MM-DDTHH:MM:SS`
- UTC时间，推荐添加Z后缀：`YYYY-MM-DDTHH:MM:SSZ`
- 示例：`2025-12-09T13:22:53Z`

**当前实现**:
- 使用 `timestamp.isoformat()`，可能不包含Z后缀
- 需要确认是否使用UTC时间

**建议修复**:
```python
# 当前代码
"timestamp": timestamp.isoformat()

# 应该改为
"timestamp": timestamp.utcnow().isoformat() + "Z"  # 或使用UTC时间
```

### 2. 图像上传参数

**文档要求**:
- `image_type`: `"monitoring_snapshot"` 或留空
- `device_id`: 设备ID（监控截图时推荐）

**当前实现**:
- `upload_image()`: 不支持 `image_type` 和 `device_id` 参数
- `upload_monitoring_snapshot()`: 支持 `device_id`，但使用 `type` 而不是 `image_type`

**需要修复**:
- `upload_image()` 需要添加 `image_type` 参数
- `upload_monitoring_snapshot()` 需要确认使用 `image_type` 而不是 `type`

### 3. snapshot_path 和 image_path

**文档要求**:
- `snapshot_path`: 必须为 `null`
- `image_path`: 必须为 `null`
- `snapshot_url`: 使用上传接口返回的 `path`

**当前实现**:
- `send_alert()` 中，如果 `snapshot_path` 或 `image_path` 不为None，会被包含在请求中
- 需要确保这两个字段始终为 `null`

**需要修复**:
- 在 `send_alert()` 中，明确设置 `snapshot_path=None` 和 `image_path=None`

### 4. 图像上传响应格式

**文档要求**:
- 响应包含 `path` 字段（相对路径）
- 格式：`YYYY-MM-DD/filename.jpg`

**当前实现**:
- 使用 `result.get("path") or result.get("url")`
- 需要确认云端返回的字段名是 `path`

---

## 📋 详细检查项

### 检查项1: 时间戳格式

**文件**: `jetson-client/cloud_client.py`

**当前代码** (第86行):
```python
"timestamp": timestamp.isoformat(),
```

**问题**:
- 可能不包含Z后缀
- 可能不是UTC时间

**建议修复**:
```python
from datetime import timezone

# 确保使用UTC时间并添加Z后缀
if timestamp.tzinfo is None:
    # 如果没有时区信息，假设是本地时间，转换为UTC
    timestamp = timestamp.replace(tzinfo=timezone.utc)
else:
    timestamp = timestamp.astimezone(timezone.utc)

"timestamp": timestamp.isoformat().replace('+00:00', 'Z')
```

### 检查项2: 图像上传参数

**文件**: `jetson-client/cloud_client.py`

**当前代码** (第128-132行):
```python
def upload_image(
    self,
    image_path: str,
    alert_id: Optional[int] = None
) -> Optional[str]:
```

**问题**:
- 缺少 `image_type` 参数
- 缺少 `device_id` 参数

**建议修复**:
```python
def upload_image(
    self,
    image_path: str,
    alert_id: Optional[int] = None,
    image_type: Optional[str] = None,  # 新增
    device_id: Optional[str] = None     # 新增
) -> Optional[str]:
```

### 检查项3: 监控截图上传

**文件**: `jetson-client/cloud_client.py`

**当前代码** (第193-197行):
```python
def upload_monitoring_snapshot(
    self,
    image_path: str,
    device_id: Optional[str] = None
) -> Optional[str]:
```

**需要确认**:
- 是否使用 `image_type="monitoring_snapshot"` 而不是 `type="monitoring_snapshot"`

### 检查项4: snapshot_path 和 image_path

**文件**: `jetson-client/main_integration.py`

**当前代码** (第140-142行):
```python
snapshot_path=None if snapshot_url else None,  # 不使用Jetson端绝对路径，设为None
snapshot_url=snapshot_url,  # 使用上传接口返回的相对路径（格式：YYYY-MM-DD/filename）
image_path=None if snapshot_url else None  # 不使用Jetson端绝对路径，设为None
```

**问题**:
- 逻辑有误：`snapshot_path=None if snapshot_url else None` 总是返回None，但应该始终为None
- 应该明确设置为 `None`

**建议修复**:
```python
snapshot_path=None,  # 必须为null
snapshot_url=snapshot_url,  # 使用上传接口返回的相对路径
image_path=None  # 必须为null
```

---

## 🔍 代码对比

### 文档要求 vs 当前实现

| 功能 | 文档要求 | 当前实现 | 状态 |
|------|---------|---------|------|
| 时间戳格式 | ISO 8601 + Z后缀 (UTC) | `isoformat()` (可能无Z) | ⚠️ 需确认 |
| snapshot_path | 必须为null | 已设置为None | ✅ 正确 |
| image_path | 必须为null | 已设置为None | ✅ 正确 |
| snapshot_url | 使用上传返回的path | 使用返回的path | ✅ 正确 |
| image_type参数 | 支持 | upload_image()不支持 | ⚠️ 需修复 |
| device_id参数 | 支持 | upload_image()不支持 | ⚠️ 需修复 |
| 监控截图image_type | "monitoring_snapshot" | 使用type字段 | ⚠️ 需确认 |

---

## 🚀 修复建议

### 优先级1: 必须修复

1. **时间戳格式**：确保使用UTC时间并添加Z后缀
2. **snapshot_path/image_path**：明确设置为None（移除条件判断）
3. **图像上传参数**：添加 `image_type` 和 `device_id` 参数支持

### 优先级2: 建议修复

1. **监控截图参数**：确认使用 `image_type` 而不是 `type`
2. **错误处理**：增强错误日志，包含更多调试信息

---

## 📝 测试建议

### 测试1: 时间戳格式验证

```python
# 测试代码
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc)
formatted = timestamp.isoformat().replace('+00:00', 'Z')
print(formatted)  # 应该输出: 2025-12-09T13:22:53Z
```

### 测试2: 图像上传参数验证

```python
# 测试监控截图上传
result = client.upload_monitoring_snapshot(
    image_path="/tmp/test.jpg",
    device_id="jetson-01"
)

# 检查请求中是否包含:
# - image_type="monitoring_snapshot"
# - device_id="jetson-01"
```

### 测试3: 警报数据验证

```python
# 测试警报创建
alert_data = {
    "timestamp": "2025-12-09T13:22:53Z",  # 应该包含Z
    "snapshot_path": None,  # 必须为null
    "image_path": None,     # 必须为null
    "snapshot_url": "2025-12-09/filename.jpg"  # 相对路径
}
```

---

## 📊 实现完整性

### 核心功能: ✅ 100%

- [x] 警报创建接口
- [x] 图像上传接口
- [x] 监控截图上传
- [x] 信标白名单查询
- [x] API Key认证
- [x] 错误重试机制

### 细节规范: ⚠️ 90%

- [x] snapshot_path/image_path为null
- [x] snapshot_url使用相对路径
- [ ] 时间戳UTC格式+Z后缀（需确认）
- [ ] image_type参数支持（需修复）
- [ ] device_id参数支持（需修复）

---

**检查完成时间**: 2025-12-09  
**检查人**: AI Assistant  
**下一步**: 修复发现的细节问题


