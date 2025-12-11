# 图像接口修复报告

## 修复时间
2024年12月9日

---

## 🔍 问题描述

根据云端团队反馈（`JETSON_IMAGE_API_REQUIREMENTS.md`），当前代码存在以下问题：

### 问题1：使用Jetson端绝对路径
- **错误**：`snapshot_path` 和 `image_path` 字段包含Jetson端绝对路径（如 `/tmp/vehicle_snapshots/...`）
- **影响**：前端无法访问Jetson端的本地文件系统路径，导致图像无法显示

### 问题2：路径格式不符合要求
- **要求**：`snapshot_url` 应该使用图像上传接口返回的 `path` 值（相对路径，格式：`YYYY-MM-DD/filename`）
- **当前状态**：`snapshot_url` 已正确使用上传接口返回的 `path` ✅

---

## ✅ 修复方案

### 修复内容

**文件**：`jetson-client/main_integration.py`

**修改位置**：`_upload_worker` 方法中的 `send_alert` 调用

**修复前**：
```python
snapshot_path=detection.image_path,  # 本地路径（可能是绝对路径）
snapshot_url=snapshot_url,  # 云端URL
image_path=detection.image_path  # 备用字段（可能是绝对路径）
```

**修复后**：
```python
snapshot_path=None,  # 不使用Jetson端绝对路径，设为None
snapshot_url=snapshot_url,  # 使用上传接口返回的相对路径（格式：YYYY-MM-DD/filename）
image_path=None  # 不使用Jetson端绝对路径，设为None
```

---

## 📋 修复说明

### 1. 符合云端接口规范

根据 `JETSON_IMAGE_API_REQUIREMENTS.md` 的要求：

- ✅ **snapshot_url**（推荐使用）：
  - 必须使用图像上传接口返回的 `path` 值
  - 格式：`YYYY-MM-DD/filename`（相对路径）
  - 前端会自动拼接为完整的图像URL

- ✅ **snapshot_path**（不推荐）：
  - 如果使用，必须是相对路径
  - ❌ 不要使用Jetson端的绝对路径
  - 修复后设为 `None`

- ✅ **image_path**（不推荐）：
  - 仅用于向后兼容
  - ❌ 不要使用Jetson端的绝对路径
  - 修复后设为 `None`

### 2. 数据流验证

修复后的数据流：

1. **步骤1**：上传图像到云端
   ```python
   snapshot_url = self.cloud_client.upload_image(
       image_path=detection.image_path,
       alert_id=None
   )
   # 返回: "2025-12-09/012630_snapshot_1284_20251209_092629_448.jpg.jpg"
   ```

2. **步骤2**：创建警报记录，使用上传返回的path
   ```python
   alert_data = {
       "snapshot_url": snapshot_url,  # ✅ 使用上传接口返回的相对路径
       "snapshot_path": None,  # ✅ 不使用绝对路径
       "image_path": None  # ✅ 不使用绝对路径
   }
   ```

---

## 🔍 验证方法

### 1. 检查数据库记录

修复后，数据库中的记录应该如下：

**正确的记录格式**：
```json
{
    "id": 7941,
    "timestamp": "2025-12-09T01:57:47",
    "snapshot_url": "2025-12-09/012630_snapshot_1284_20251209_092629_448.jpg.jpg",  // ✅ 相对路径
    "snapshot_path": null,  // ✅ null
    "image_path": null  // ✅ null
}
```

**错误的记录格式**（修复前）：
```json
{
    "snapshot_path": "/tmp/vehicle_snapshots/snapshot_2369_20251208_165202_613.jpg",  // ❌ 绝对路径
    "snapshot_url": "2025-12-08/085324_snapshot_2369_20251208_165202_613.jpg.jpg",  // ✅ 这个是对的
    "image_path": "/tmp/vehicle_snapshots/snapshot_2369_20251208_165202_613.jpg"    // ❌ 绝对路径
}
```

### 2. 检查前端显示

- ✅ 前端应该能够正常显示图像
- ✅ 图像URL应该可以访问：`http://<云端服务器IP>:8000/api/images/{snapshot_url}`

### 3. 检查日志

修复后，日志中应该显示：
```
Image uploaded successfully: 2025-12-09/012630_snapshot_1284_20251209_092629_448.jpg.jpg
Alert sent successfully, ID: 7941
```

---

## 📝 相关文档

- `docs/JETSON_IMAGE_API_REQUIREMENTS.md` - 云端图像接口要求文档
- `jetson-client/cloud_client.py` - 云端API客户端
- `jetson-client/main_integration.py` - 主集成模块

---

## 🚀 部署步骤

1. **确认修复已应用**：
   ```bash
   cd /home/liubo/Download/deepstream-vehicle-detection
   grep -A 3 "snapshot_path=None" jetson-client/main_integration.py
   ```

2. **重启服务**：
   ```bash
   sudo systemctl restart vehicle-detection
   ```

3. **验证新数据**：
   - 等待15-30分钟
   - 检查新创建的警报记录
   - 确认 `snapshot_path` 和 `image_path` 为 `null`
   - 确认 `snapshot_url` 为相对路径格式

---

**修复状态**：✅ 已完成  
**测试状态**：⏳ 待验证  
**文档版本**：v1.0

