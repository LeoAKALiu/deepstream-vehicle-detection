# DeepStream应用测试开发工作清单

## 📊 当前状态

### ✅ 已完成
- DeepStream Python应用框架已创建（`python_apps/deepstream_vehicle_detection.py`）
- GStreamer pipeline构建完成
- TensorRT引擎集成完成
- NvDCF跟踪器配置完成
- 基础检测结果处理完成
- 工程车辆统计功能完成

### ⚠️ 未完成/待完善

---

## 🔴 高优先级任务

### 1. 车牌识别ROI裁剪实现

**问题**：
- 当前代码中车牌识别部分只有注释（第266行）
- 需要从DeepStream的buffer中提取原始图像数据
- 需要根据检测框裁剪ROI区域

**任务**：
- [ ] **实现图像数据提取**
  - 从GstBuffer中提取NvBufSurface
  - 转换为numpy数组或OpenCV格式
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 位置：`osd_sink_pad_buffer_probe()` 方法

- [ ] **实现ROI裁剪**
  - 根据obj_meta的bbox坐标裁剪车辆区域
  - 处理坐标转换（DeepStream坐标系 → OpenCV坐标系）
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 新增方法：`_extract_roi_from_buffer(buffer, bbox) -> np.ndarray`

- [ ] **集成HyperLPR**
  - 对裁剪的ROI调用HyperLPR识别
  - 处理识别结果（车牌号、置信度）
  - 去重（避免重复识别同一车辆）
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`osd_sink_pad_buffer_probe()` 方法中社会车辆处理部分

**参考代码**：
```python
# 从buffer提取图像（需要实现）
def _extract_frame_from_buffer(self, gst_buffer):
    """从GstBuffer提取numpy图像"""
    # 需要访问NvBufSurface
    # 转换为numpy数组
    pass

# ROI裁剪
def _crop_roi(self, frame, bbox):
    """裁剪车辆ROI"""
    x1, y1, x2, y2 = bbox
    roi = frame[int(y1):int(y2), int(x1):int(x2)]
    return roi
```

**预期效果**：社会车辆能够正确识别车牌号

---

### 2. 深度相机集成

**问题**：
- DeepStream应用未集成Orbbec深度相机
- 无法进行距离测量和信标匹配

**任务**：
- [ ] **集成Orbbec深度相机**
  - 在DeepStream应用启动时初始化深度相机
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`__init__()` 方法

- [ ] **同步深度数据和检测结果**
  - 在probe函数中获取对应帧的深度数据
  - 计算车辆距离
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`osd_sink_pad_buffer_probe()` 方法

- [ ] **实现距离测量**
  - 在bbox底边中点测量深度
  - 返回距离和置信度
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 新增方法：`_get_vehicle_distance(bbox) -> (distance, confidence)`

**预期效果**：能够测量车辆距离，支持信标匹配

---

### 3. 蓝牙信标集成

**问题**：
- DeepStream应用未集成Cassia蓝牙信标扫描
- 无法进行信标匹配和备案判断

**任务**：
- [ ] **集成Cassia客户端**
  - 在应用启动时初始化CassiaLocalClient
  - 启动SSE扫描线程
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`__init__()` 方法

- [ ] **集成信标过滤器**
  - 初始化BeaconFilter
  - 在检测到工程车辆时进行信标匹配
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`osd_sink_pad_buffer_probe()` 方法

- [ ] **实现备案判断**
  - 根据信标匹配结果判断是否已备案
  - 记录备案状态
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 新增方法：`_check_vehicle_registration(vehicle_id, bbox, distance) -> dict`

**预期效果**：能够识别已备案/未备案工程车辆

---

### 4. 云端集成

**问题**：
- DeepStream应用未集成云端上传功能
- 检测结果无法上传到云端

**任务**：
- [ ] **集成云端客户端**
  - 初始化SentinelIntegration
  - 配置API地址和密钥
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 修改：`__init__()` 方法

- [ ] **实现检测结果上传**
  - 创建DetectionResult对象
  - 上传到云端
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 新增方法：`_upload_detection_result(vehicle_info) -> None`

- [ ] **实现图像上传**
  - 保存检测快照
  - 上传图像到云端
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 新增方法：`_save_and_upload_snapshot(frame, bbox, vehicle_info) -> None`

**预期效果**：检测结果能够实时上传到云端

---

## 🟡 中优先级任务

### 5. 数据持久化

**任务**：
- [ ] **实现检测结果保存**
  - 保存到SQLite数据库
  - 记录车辆信息、检测时间、置信度等
  - 文件：`python_apps/deepstream_vehicle_detection.py`
  - 使用：`python_apps/detection_database.py`

- [ ] **实现报警记录**
  - 保存未备案车辆报警
  - 保存车牌识别结果
  - 文件：`python_apps/deepstream_vehicle_detection.py`

**预期效果**：检测数据持久化，支持历史查询

---

### 6. 日志系统

**任务**：
- [ ] **集成日志系统**
  - 使用Python logging模块
  - 配置日志级别和输出格式
  - 文件：`python_apps/deepstream_vehicle_detection.py`

- [ ] **关键事件记录**
  - 检测事件
  - 报警事件
  - 错误事件
  - 文件：`python_apps/deepstream_vehicle_detection.py`

**预期效果**：完整的日志记录，便于调试和问题追踪

---

### 7. 性能监控

**任务**：
- [ ] **实现FPS监控**
  - 计算实际处理帧率
  - 显示在OSD上
  - 文件：`python_apps/deepstream_vehicle_detection.py`

- [ ] **实现资源监控**
  - CPU/GPU使用率
  - 内存使用
  - 文件：`python_apps/deepstream_vehicle_detection.py`

**预期效果**：实时性能监控和显示

---

### 8. 配置管理

**任务**：
- [ ] **读取配置文件**
  - 从config.yaml读取配置
  - 支持DeepStream特定配置
  - 文件：`python_apps/deepstream_vehicle_detection.py`

- [ ] **配置验证**
  - 验证必需配置项
  - 提供默认值
  - 文件：`python_apps/deepstream_vehicle_detection.py`

**预期效果**：灵活的配置管理

---

## 🟢 低优先级任务

### 9. 测试脚本完善

**任务**：
- [ ] **完善测试脚本**
  - 更新`tests/test_deepstream_app.sh`
  - 添加更多测试场景
  - 文件：`tests/test_deepstream_app.sh`

- [ ] **添加单元测试**
  - 测试各个功能模块
  - 文件：`tests/test_deepstream_*.py`

**预期效果**：完整的测试覆盖

---

### 10. 文档完善

**任务**：
- [ ] **更新开发文档**
  - 记录DeepStream应用开发过程
  - 更新API文档
  - 文件：`docs/start_deepstream_dev.md`

- [ ] **添加使用说明**
  - 如何运行DeepStream应用
  - 配置说明
  - 文件：`docs/deepstream_usage.md`

**预期效果**：完整的文档支持

---

## 📋 实施优先级建议

### 第一阶段（核心功能）
1. **车牌识别ROI裁剪** - 完成社会车辆识别功能
2. **深度相机集成** - 支持距离测量
3. **蓝牙信标集成** - 支持备案判断

### 第二阶段（系统集成）
4. **云端集成** - 数据上传
5. **数据持久化** - 数据保存
6. **日志系统** - 调试支持

### 第三阶段（优化完善）
7. **性能监控** - 性能优化
8. **配置管理** - 灵活性提升
9. **测试和文档** - 质量保证

---

## 🔍 与TensorRT方案对比

| 功能 | TensorRT方案 | DeepStream方案 | 状态 |
|------|-------------|---------------|------|
| 车辆检测 | ✅ | ✅ | 完成 |
| 目标跟踪 | ✅ (ByteTrack) | ✅ (NvDCF) | 完成 |
| 车牌识别 | ✅ | ⚠️ 待实现 | 未完成 |
| 深度测量 | ✅ | ⚠️ 待集成 | 未完成 |
| 信标匹配 | ✅ | ⚠️ 待集成 | 未完成 |
| 云端上传 | ✅ | ⚠️ 待集成 | 未完成 |
| 数据持久化 | ✅ | ⚠️ 待实现 | 未完成 |
| 日志系统 | ✅ | ⚠️ 待实现 | 未完成 |

---

## 📝 注意事项

1. **性能考虑**
   - DeepStream方案预期性能更高（50-100 FPS）
   - 但需要完成所有功能集成才能达到完整功能

2. **开发复杂度**
   - DeepStream方案开发复杂度较高
   - 需要处理GStreamer buffer和NvBufSurface

3. **兼容性**
   - 需要确保与现有TensorRT方案的功能对等
   - 保持API接口一致性

---

**创建时间**: 2024年12月8日  
**状态**: ⏳ 待开发  
**优先级**: 🔴 高（核心功能缺失）


