# 系统改进TODO列表

基于风险分析的系统改进计划，按优先级组织。

---

## P0 | 功能正确性与演示可靠性

### P0-1: RGB-Depth对齐与距离精度优化 🔴 高优先级

**当前状态**:
- ✅ 已启用SW_MODE对齐 (`config.set_align_mode(ob.OBAlignMode.SW_MODE)`)
- ⚠️ 无效值过滤范围较宽 (100-10000mm)
- ⚠️ 未记录有效像素比例用于置信度
- ⚠️ 未使用D2C硬件对齐（如果支持）

**改进任务**:

- [ ] **验证D2C硬件对齐支持**
  - 检查Orbbec SDK是否支持D2C (Depth-to-Color) 硬件对齐
  - 如果支持，优先使用D2C模式（性能更好）
  - 文件: `python_apps/orbbec_depth.py`
  - 代码位置: `OrbbecDepthCamera.start()` 方法

- [ ] **优化无效深度值过滤**
  - 使用配置文件中的 `invalid_min` 和 `invalid_max` 参数
  - 当前硬编码: `(region > 100) & (region < 10000)`
  - 改为: `(region > invalid_min) & (region < invalid_max)`
  - 文件: `python_apps/orbbec_depth.py`
  - 代码位置: `get_depth_region_stats()` 方法

- [ ] **改进bbox底边中点深度采样**
  - 当前: 单点采样或区域平均
  - 改进: 在底边中点周围取小窗口（如5×5或7×7）计算中位数
  - 过滤离群值（使用IQR方法或标准差）
  - 文件: `python_apps/orbbec_depth.py`
  - 新增方法: `get_depth_at_bbox_bottom_robust(bbox, window_size=5)`

- [ ] **记录有效像素比例**
  - 在深度测量时计算有效像素占比
  - 作为置信度指标返回
  - 如果有效像素 < 30%，标记为低置信度
  - 文件: `python_apps/orbbec_depth.py`, `test_system_realtime.py`
  - 修改: `get_depth_region_stats()` 返回 `(depth, confidence)` 元组

**预期效果**: 提高深度测量精度和可靠性，减少信标匹配错误

---

### P0-2: YOLO输出解析一致性验证 🔴 高优先级

**当前状态**:
- ⚠️ 硬编码假设输出为 `[1, 14, 8400]` (5+9类)
- ⚠️ 未验证引擎元信息与labels.txt一致性
- ⚠️ 类别数量变化会导致解析错误

**改进任务**:

- [ ] **读取引擎元信息并验证输出通道数**
  - 在 `TensorRTInference.__init__()` 中读取输出shape
  - 验证: `output_channels = 5 + num_classes` (5=xywh+conf, num_classes=类别数)
  - 如果不一致，立即抛出异常并提示
  - 文件: `test_system_realtime.py`
  - 代码位置: `TensorRTInference.__init__()` 方法

- [ ] **读取labels.txt并验证类别数量**
  - 从 `config/labels.txt` 读取类别列表
  - 验证类别数量与引擎输出通道数一致
  - 如果不一致，警告并提示
  - 文件: `test_system_realtime.py`
  - 新增方法: `_validate_model_consistency(engine_path, labels_path)`

- [ ] **动态解析输出格式**
  - 根据实际输出shape动态确定类别数量
  - 更新 `CUSTOM_CLASSES` 映射（如果labels.txt存在）
  - 文件: `test_system_realtime.py`
  - 代码位置: `TensorRTInference.__init__()` 和 `postprocess()` 方法

**预期效果**: 防止模型结构变更导致的解析错误，提高系统健壮性

---

### P0-3: Beacon匹配误关联优化 🔴 高优先级

**当前状态**:
- ⚠️ 使用简单最近距离匹配（单目标-单信标）
- ⚠️ 多目标场景下易错配
- ⚠️ 未考虑时间稳定度

**改进任务**:

- [ ] **实现多目标-多信标匈牙利算法匹配**
  - 构建代价矩阵: `cost[i][j] = |视觉距离[i] - 信标距离[j]| + 时间稳定度惩罚`
  - 使用 `scipy.optimize.linear_sum_assignment` 进行最优匹配
  - 文件: `python_apps/beacon_filter.py`
  - 新增方法: `match_multiple_targets(vehicles, scanned_beacons) -> List[Dict]`

- [ ] **添加时间稳定度惩罚**
  - 计算信标在时间窗口内的RSSI/距离稳定性
  - 不稳定信标增加代价惩罚
  - 文件: `python_apps/beacon_filter.py`
  - 修改: `_calculate_confidence()` 方法

- [ ] **设置最小代价阈值**
  - 如果所有匹配的代价都超过阈值，判定为"不确定"
  - 阈值可配置: `beacon_whitelist.yaml` 中的 `match_cost_threshold`
  - 文件: `python_apps/beacon_filter.py`, `beacon_whitelist.yaml`

- [ ] **修改主程序调用逻辑**
  - 从单目标匹配改为批量匹配
  - 文件: `test_system_realtime.py`
  - 代码位置: `check_construction_vehicle()` 方法

**预期效果**: 减少多目标场景下的信标错配，提高匹配准确率

---

### P0-4: LPR准确率与实时性优化 🔴 高优先级

**当前状态**:
- ⚠️ 同步处理，阻塞主循环
- ⚠️ CPU推理，可能成为瓶颈
- ⚠️ 未限制识别频率

**改进任务**:

- [ ] **实现异步LPR处理**
  - 使用线程池 (`concurrent.futures.ThreadPoolExecutor`)
  - 创建LPR任务队列
  - 文件: `test_system_realtime.py`
  - 新增类: `AsyncLPRProcessor`

- [ ] **添加ROI质量检查**
  - 计算ROI清晰度（拉普拉斯方差）
  - 只有清晰度 > 阈值才触发识别
  - 文件: `test_system_realtime.py`
  - 新增方法: `_check_roi_quality(roi) -> bool`

- [ ] **限制识别频率**
  - 每个track_id每秒最多识别1次
  - 使用时间戳记录上次识别时间
  - 文件: `test_system_realtime.py`
  - 修改: `check_civilian_vehicle()` 方法

- [ ] **添加重试和回退逻辑**
  - 识别失败时，等待下一帧再试
  - 最多重试3次
  - 文件: `test_system_realtime.py`
  - 修改: `AsyncLPRProcessor` 类

- [ ] **仅对特定车型触发**
  - 只对 `car` 和 `truck` 类型触发LPR
  - 其他类型跳过（节省资源）
  - 文件: `test_system_realtime.py`
  - 代码位置: `process_new_vehicle()` 方法

**预期效果**: 提高系统实时性，减少LPR阻塞，提高识别准确率

---

### P0-5: 性能目标与指标统一 🔴 高优先级

**当前状态**:
- ⚠️ 文档中混用 "15-25 FPS" 和 "50-100 FPS"
- ⚠️ 未提供多档性能配置

**改进任务**:

- [ ] **统一性能指标口径**
  - 更新 `PROJECT_DOCUMENTATION.md`
  - 明确标注: 当前实测 15-25 FPS (1080p), 目标 50+ FPS (720p)
  - 文件: `PROJECT_DOCUMENTATION.md`

- [ ] **实现多档性能配置**
  - 添加 `performance_mode` 配置项: `"quality"` / `"balanced"` / `"speed"`
  - `quality`: 1080p, 全功能, 目标 25-30 FPS
  - `balanced`: 720p, 全功能, 目标 40-50 FPS
  - `speed`: 720p, 简化绘制, 目标 50+ FPS
  - 文件: `config.yaml`, `test_system_realtime.py`

- [ ] **添加分辨率配置**
  - 支持动态调整输入分辨率
  - 文件: `config.yaml`
  - 新增配置项: `detection.input_resolution: [640, 480]` 或 `[1920, 1080]`

- [ ] **添加跳帧配置**
  - 性能模式下可跳帧处理
  - 文件: `config.yaml`
  - 新增配置项: `performance.frame_skip: 0` (0=不跳帧, 1=跳1帧)

- [ ] **添加绘制开关**
  - 性能模式下可禁用部分绘制
  - 文件: `config.yaml`
  - 新增配置项: `display.enable_detailed_drawing: true`

**预期效果**: 明确性能目标，支持不同场景的性能需求

---

## P1 | 稳定性与可恢复性

### P1-1: 设备断连与重连机制 🔵 中优先级

**当前状态**:
- ⚠️ 配置中有重连参数，但未实现
- ⚠️ 断连后需手动重启

**改进任务**:

- [ ] **实现相机自动重连**
  - 检测相机断连（获取帧失败）
  - 指数退避重试（1s, 2s, 4s, 8s, ...）
  - 最大重试次数可配置
  - 文件: `python_apps/orbbec_depth.py`, `test_system_realtime.py`
  - 修改: `OrbbecDepthCamera._capture_loop()` 方法

- [ ] **实现Cassia自动重连**
  - 检测SSE连接断开
  - 自动重建连接
  - 指数退避重试
  - 文件: `python_apps/cassia_local_client.py`
  - 修改: `_scan_loop()` 方法

- [ ] **实现状态机管理**
  - 定义设备状态: `CONNECTED`, `DISCONNECTED`, `RECONNECTING`
  - 状态转换逻辑
  - 文件: `test_system_realtime.py`
  - 新增类: `DeviceStateManager`

- [ ] **主循环不崩溃**
  - 设备断连时，主循环继续运行（优雅降级）
  - 显示设备状态提示
  - 文件: `test_system_realtime.py`
  - 修改: `run()` 方法

**预期效果**: 提高系统稳定性，减少现场演示中断

---

### P1-2: 资源泄漏与清理风险 🔵 中优先级

**当前状态**:
- ⚠️ 部分资源未使用上下文管理器
- ⚠️ CTRL+C退出可能不完整清理

**改进任务**:

- [ ] **统一资源管理**
  - 为所有资源类实现 `__enter__` 和 `__exit__`
  - 文件: `python_apps/orbbec_depth.py`, `python_apps/cassia_local_client.py`
  - 修改: 所有资源类

- [ ] **实现优雅退出**
  - 捕获 `KeyboardInterrupt` 和 `SystemExit`
  - 按顺序清理: VideoWriter → 相机 → Cassia → TensorRT
  - 文件: `test_system_realtime.py`
  - 修改: `run()` 方法

- [ ] **添加资源健康检查**
  - 定期检查GPU内存使用
  - 检查文件句柄数量
  - 记录到日志
  - 文件: `test_system_realtime.py`
  - 新增方法: `_check_resource_health()`

- [ ] **确保VideoWriter正确关闭**
  - 使用 `try-finally` 确保关闭
  - 文件: `python_apps/record_field_test.py`
  - 修改: `start_recording()` 方法

**预期效果**: 防止资源泄漏，提高长时间运行稳定性

---

### P1-3: 时间同步问题 🔵 中优先级

**当前状态**:
- ⚠️ BLE扫描（秒级）与视觉帧（毫秒级）时间不同步
- ⚠️ 未维护时间窗口缓存

**改进任务**:

- [ ] **为BLE数据打时间戳**
  - 每次扫描到信标时记录 `timestamp`
  - 文件: `python_apps/cassia_local_client.py`
  - 修改: `_update_beacon()` 方法

- [ ] **维护滑窗缓存**
  - 保留最近N秒的信标数据（可配置，默认3秒）
  - 文件: `python_apps/cassia_local_client.py`
  - 修改: `beacons` 字典结构: `{mac: {'rssi': x, 'timestamp': t, ...}}`

- [ ] **时间窗口匹配**
  - 匹配时要求信标在时间窗口T内（如2-3秒）
  - 文件: `python_apps/beacon_filter.py`
  - 修改: `filter_beacons()` 方法

- [ ] **距离代价计算考虑时间**
  - 时间越近的信标，权重越高
  - 文件: `python_apps/beacon_filter.py`
  - 修改: `_calculate_confidence()` 方法

**预期效果**: 提高信标匹配的时间一致性，减少时间偏差导致的错配

---

## 实施优先级建议

### 第一阶段（立即实施 - P0关键项）
1. **P0-2**: YOLO输出解析验证（防止崩溃）
2. **P0-1**: 深度精度优化（影响信标匹配）
3. **P0-5**: 性能指标统一（文档准确性）

### 第二阶段（短期 - P0其他项）
4. **P0-3**: Beacon匹配优化（多目标场景）
5. **P0-4**: LPR异步处理（性能优化）

### 第三阶段（中期 - P1稳定性）
6. **P1-1**: 设备自动重连
7. **P1-2**: 资源管理优化
8. **P1-3**: 时间同步优化

---

## 测试验证

每个改进项完成后，需要：

1. **单元测试**: 验证功能正确性
2. **集成测试**: 验证与系统其他模块的兼容性
3. **性能测试**: 验证性能影响（FPS、延迟）
4. **现场测试**: 验证实际场景下的表现

---

## 进度跟踪

- [ ] P0-1: RGB-Depth对齐与距离精度优化
- [ ] P0-2: YOLO输出解析一致性验证
- [ ] P0-3: Beacon匹配误关联优化
- [ ] P0-4: LPR准确率与实时性优化
- [ ] P0-5: 性能目标与指标统一
- [ ] P1-1: 设备断连与重连机制
- [ ] P1-2: 资源泄漏与清理风险
- [ ] P1-3: 时间同步问题

---

**文档创建时间**: 2025-11-21  
**最后更新**: 2025-11-21  
**维护者**: SolidRusT Networks


