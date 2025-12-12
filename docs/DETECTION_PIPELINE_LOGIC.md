# 车辆检测系统逻辑文档

## 概述

本文档详细描述了从输入图像帧到最终判别结果的完整处理流程，包括各个阶段的阈值、验证逻辑和潜在问题点。旨在帮助理解系统逻辑，减少假阳性和假阴性。

---

## 一、整体流程图

```
输入帧 (RGB)
    ↓
【阶段1: 预处理与推理】
    ├─ 图像预处理 (resize, normalization)
    ├─ TensorRT推理
    └─ YOLO后处理 (NMS)
    ↓
【阶段2: 多帧验证】(可选)
    ├─ 帧间IoU匹配
    ├─ 出现频率验证
    └─ 过滤假阳性
    ↓
【阶段3: 跟踪】
    ├─ ByteTrack/Simple IoU跟踪
    └─ Track ID分配
    ↓
【阶段4: 车辆分类】
    ├─ 工程车辆 (construction_vehicle)
    └─ 社会车辆 (social_vehicle)
    ↓
【阶段5A: 工程车辆处理】
    ├─ 距离测量
    ├─ 信标匹配
    ├─ 备案状态判断
    └─ 云端上传
    ↓
【阶段5B: 社会车辆处理】
    ├─ ROI裁剪
    ├─ 车牌识别 (异步)
    └─ 云端上传
    ↓
【输出: 判别结果】
```

---

## 二、详细流程说明

### 阶段1: 预处理与推理

#### 1.1 输入
- **来源**: Orbbec深度相机的RGB帧
- **格式**: numpy array (H×W×3, uint8, RGB)

#### 1.2 预处理
```python
# 步骤：
1. Resize到模型输入尺寸 (默认640×640)
2. 归一化到 [0, 1] (除以255.0)
3. 转换为RGB (如果需要)
4. 转换为CHW格式 (Channel-Height-Width)
5. 添加batch维度
```

**配置文件**: `config.yaml` → `detection.input_resolution`

#### 1.3 TensorRT推理
- **引擎**: `custom_yolo.engine` (FP16量化)
- **输出**: 原始YOLO输出 (包含所有anchor的检测结果)

#### 1.4 后处理 (NMS)

**关键参数**:
- `conf_threshold: 0.75` - 检测置信度阈值
  - **作用**: 过滤低置信度检测框
  - **位置**: `config.yaml` → `detection.conf_threshold`
  - **影响**: 
    - 提高 → 减少假阳性，但可能增加假阴性
    - 降低 → 增加检测数量，但可能增加假阳性

- `iou_threshold: 0.5` - NMS的IoU阈值
  - **作用**: 去除重叠检测框
  - **位置**: `config.yaml` → `detection.iou_threshold`
  - **影响**:
    - 提高 → 保留更多重叠检测（可能重复）
    - 降低 → 更激进地去除重叠（可能丢失真实目标）

**输出**: 
- `boxes`: 边界框列表 (N×4, [x1, y1, x2, y2])
- `confidences`: 置信度列表 (N,)
- `class_ids`: 类别ID列表 (N,)

---

### 阶段2: 多帧验证 (Multi-Frame Validation)

**目的**: 通过连续帧验证减少假阳性检测

**配置**: `config.yaml` → `detection.multi_frame_validation`

#### 2.1 帧间IoU匹配
- **参数**: `iou_threshold: 0.4`
- **逻辑**: 使用IoU匹配当前帧检测与历史检测
- **匹配条件**: IoU >= 0.4 且类别相同

#### 2.2 出现频率验证

**关键参数**:
- `min_frames: 5` - 最小连续帧数
  - **作用**: 检测框必须在至少5帧中出现才认为是有效检测
  - **影响**:
    - 提高 → 更严格，减少假阳性，但可能增加假阴性（快速移动车辆）
    - 降低 → 更宽松，可能增加假阳性

- `min_occurrence_ratio: 0.8` - 最小出现频率
  - **作用**: 在验证窗口内，检测框必须出现的频率 >= 0.8
  - **计算**: `occurrence_ratio = recent_frames_count / actual_window_size`
  - **影响**:
    - 提高 → 更严格，减少闪烁误检
    - 降低 → 更宽松，可能允许更多不稳定检测

- `validation_window: 10` - 验证窗口大小（帧数）
  - **作用**: 计算出现频率的时间窗口
  - **实际窗口大小**: `min(frame_id + 1, validation_window)`
    - 系统启动早期: 使用实际处理的帧数
    - 正常运行: 使用10帧窗口
  - **影响**:
    - 增大 → 更稳定，但响应更慢
    - 减小 → 响应更快，但可能不稳定

**验证逻辑**:
```python
if frame_id < min_frames:
    # 系统刚启动，允许所有检测通过
    valid_indices.append(i)
else:
    if len(frame_ids) >= min_frames:
        recent_frames = [fid for fid in frame_ids 
                        if frame_id - fid < validation_window]
        actual_window_size = min(frame_id + 1, validation_window)
        occurrence_ratio = len(recent_frames) / actual_window_size
        if occurrence_ratio >= min_occurrence_ratio:
            valid_indices.append(i)
```

**潜在问题**:
- **假阴性**: 快速移动车辆可能无法通过多帧验证
- **假阳性**: 稳定的误检（如背景物体）可能通过验证

---

### 阶段3: 跟踪 (Tracking)

#### 3.1 ByteTrack跟踪器

**配置**: `config.yaml` → `tracking`

**关键参数**:
- `track_thresh: 0.5` - 跟踪阈值
  - **作用**: 高置信度检测直接进入跟踪
  - **影响**: 提高可减少低质量跟踪

- `high_thresh: 0.7` - 高置信度阈值
  - **作用**: 区分高/低置信度检测
  - **影响**: 提高可提高跟踪质量

- `match_thresh: 0.5` - IoU匹配阈值
  - **作用**: 帧间跟踪匹配的IoU阈值
  - **影响**: 降低可提高跟踪稳定性（允许更大位置变化）

- `track_buffer: 100` - 跟踪缓冲区大小
  - **作用**: 跟踪消失后的保留帧数
  - **影响**: 增大可减少ID切换

**输出**: 
- `tracks`: 字典 {track_id: track_info}
  - `bbox`: 边界框
  - `class`: 类别ID
  - `confidence/score`: 置信度
  - `processed`: 是否已处理

#### 3.2 置信度阈值检查

**代码位置**: `test_system_realtime.py:2477`

```python
if detection_confidence < 0.7:
    # 跳过低置信度检测
    continue
```

**潜在问题**:
- 硬编码阈值 0.7，未配置化
- 可能导致假阴性（真实的低置信度检测被过滤）

---

### 阶段4: 车辆分类

#### 4.1 类别映射

**类别定义**:
- **工程车辆**: excavator, bulldozer, dump_truck, loader, mixer_truck, roller, crane
- **社会车辆**: car, truck (非工程类)

**映射逻辑**:
```python
class_name = CUSTOM_CLASSES.get(track['class'], 'unknown')
vehicle_type = VEHICLE_CLASSES.get(class_name, 'construction')
```

**潜在问题**:
- 如果类别映射不正确，可能导致错误分类

---

### 阶段5A: 工程车辆处理

#### 5A.1 批量收集

**目的**: 支持多目标信标匹配

**收集条件**:
- `vehicle_type == 'construction'`
- `not track['processed']`
- `track_id not in alerts_dict`
- `detection_confidence >= 0.7`

#### 5A.2 批量处理 (多目标匹配)

**步骤**:
1. **距离测量**
   - 使用深度相机获取车辆底部中心点距离
   - **配置**: `config.yaml` → `depth`
   - **输出**: 距离值（米）

2. **信标匹配** (多目标)
   - 获取所有活跃信标 (Cassia蓝牙路由器)
   - 对每个工程车辆，匹配最近的符合条件的信标
   - **匹配条件**:
     - 距离匹配 (车辆距离 vs 信标距离)
     - RSSI强度
     - 白名单验证
   - **匹配算法**: 最小匹配代价 (match_cost)
   
   **配置**: `config.yaml` → `beacon_filter`
   - `distance_threshold: 5.0` - 距离阈值（米）
   - `rssi_threshold: -80` - RSSI阈值 (dBm)
   - `match_cost_threshold: 10.0` - 匹配代价阈值

3. **备案状态判断**
   - **已备案**: 匹配到信标 && 信标在白名单中
     - `status = 'registered'`
     - `is_registered = True`
   - **未备案**: 未匹配到信标 || 信标不在白名单中
     - `status = 'unregistered'`
     - `is_registered = False`

4. **单目标处理** (如果批量匹配失败)
   - 回退到单目标匹配逻辑
   - 使用相同的匹配条件

#### 5A.3 创建Alert并上传

**Alert信息**:
```python
alert = {
    'track_id': track_id,
    'type': 'construction_vehicle',
    'status': 'registered' | 'unregistered',
    'detected_class': class_name,  # excavator, bulldozer等
    'confidence': detection_confidence,
    'distance': distance,
    'beacon_mac': beacon_mac,  # 如果匹配到
    'company': company,  # 从白名单获取
    'environment_code': environment_code,  # 从白名单获取
    'is_registered': is_registered,
    ...
}
```

**上传流程**:
1. 保存快照到本地
2. 上传图片到云端 (`POST /api/images`)
3. 创建警报记录 (`POST /api/alerts`)
4. 更新 `alerts_dict[track_id] = alert`
5. 添加到 `recent_alerts` (用于去重)

**潜在问题**:
- **假阳性**: 背景物体被误识别为工程车辆
- **假阴性**: 
  - 距离测量不准确导致信标匹配失败
  - 信标信号弱导致匹配失败
  - 白名单未及时更新

---

### 阶段5B: 社会车辆处理

#### 5B.1 ROI裁剪

**步骤**:
1. 从track获取bbox
2. 从原图裁剪车辆区域
3. 转换为BGR格式（HyperLPR需要）

#### 5B.2 车牌识别 (异步)

**工具**: HyperLPR3

**流程**:
1. 提交识别任务到线程池
2. 异步识别车牌
3. 识别完成后更新alert

**识别结果**:
- **成功**: `plate_number = "xxx"`, `status = 'identified'`
- **失败**: `plate_number = None`, `status = 'failed'`

#### 5B.3 创建Alert并上传

**Alert信息**:
```python
alert = {
    'track_id': track_id,
    'type': 'social_vehicle',
    'status': 'identifying' → 'identified' | 'failed',
    'detected_class': 'car',  # 社会车辆只有car类别
    'confidence': detection_confidence,
    'plate_number': plate_number,  # 识别结果
    ...
}
```

**潜在问题**:
- **假阳性**: 非车辆物体被误识别为车辆
- **假阴性**: 
  - 车牌识别失败（光照、角度、遮挡）
  - 快速移动车辆车牌模糊

---

## 三、去重逻辑

### 3.1 重复警报检查

**位置**: `test_system_realtime.py:_is_duplicate_alert()`

**检查条件**:
1. **时间窗口**: 最近30秒内
2. **位置重叠**: IoU >= 0.5
3. **类别相同**: class_name相同

**逻辑**:
```python
for prev_track_id, prev_bbox, prev_time, prev_class in recent_alerts:
    time_diff = current_time - prev_time
    if time_diff < 30.0:  # 30秒窗口
        iou = _compute_bbox_iou(bbox, prev_bbox)
        if iou >= 0.5 and class_name == prev_class:
            return True  # 重复
return False
```

**潜在问题**:
- IoU阈值 0.5 可能过高（重叠车辆可能被误判为重复）
- 时间窗口 30秒 可能过长（同一车辆多次进出可能被误判为重复）

---

## 四、配置参数总结

### 4.1 检测阶段

| 参数 | 默认值 | 位置 | 作用 | 调整建议 |
|------|--------|------|------|----------|
| `conf_threshold` | 0.75 | detection.conf_threshold | 检测置信度阈值 | 提高→减少假阳性<br>降低→减少假阴性 |
| `iou_threshold` | 0.5 | detection.iou_threshold | NMS IoU阈值 | 提高→保留更多检测<br>降低→去除更多重叠 |

### 4.2 多帧验证

| 参数 | 默认值 | 位置 | 作用 | 调整建议 |
|------|--------|------|------|----------|
| `min_frames` | 5 | multi_frame_validation.min_frames | 最小连续帧数 | 提高→减少假阳性<br>降低→减少假阴性 |
| `min_occurrence_ratio` | 0.8 | multi_frame_validation.min_occurrence_ratio | 最小出现频率 | 提高→更严格<br>降低→更宽松 |
| `validation_window` | 10 | multi_frame_validation.validation_window | 验证窗口大小 | 增大→更稳定<br>减小→响应更快 |
| `iou_threshold` | 0.4 | multi_frame_validation.iou_threshold | 帧间匹配IoU阈值 | 降低→允许更大位置变化 |

### 4.3 跟踪阶段

| 参数 | 默认值 | 位置 | 作用 | 调整建议 |
|------|--------|------|------|----------|
| `track_thresh` | 0.5 | tracking.track_thresh | 跟踪阈值 | 提高→减少低质量跟踪 |
| `high_thresh` | 0.7 | tracking.high_thresh | 高置信度阈值 | 提高→提高跟踪质量 |
| `match_thresh` | 0.5 | tracking.match_thresh | IoU匹配阈值 | 降低→提高跟踪稳定性 |
| `track_buffer` | 100 | tracking.track_buffer | 跟踪缓冲区大小 | 增大→减少ID切换 |

### 4.4 工程车辆匹配

| 参数 | 默认值 | 位置 | 作用 | 调整建议 |
|------|--------|------|------|----------|
| `distance_threshold` | 5.0 | beacon_filter.distance_threshold | 距离阈值（米） | 根据场景调整 |
| `rssi_threshold` | -80 | beacon_filter.rssi_threshold | RSSI阈值 (dBm) | 根据信号强度调整 |
| `match_cost_threshold` | 10.0 | beacon_filter.match_cost_threshold | 匹配代价阈值 | 降低→更宽松匹配 |

### 4.5 去重逻辑（硬编码）

| 参数 | 当前值 | 位置 | 作用 | 调整建议 |
|------|--------|------|------|----------|
| 时间窗口 | 30秒 | `_is_duplicate_alert()` | 去重时间窗口 | 可配置化 |
| IoU阈值 | 0.5 | `_is_duplicate_alert()` | 位置重叠阈值 | 可配置化 |
| 置信度阈值 | 0.7 | `run()` | 跟踪置信度阈值 | 可配置化 |

---

## 五、假阳性和假阴性分析

### 5.1 假阳性 (False Positive) 来源

#### 1. 检测阶段
- **原因**: 背景物体被误识别为车辆
- **缓解措施**: 
  - 提高 `conf_threshold` (0.75 → 0.8)
  - 启用多帧验证（已启用）
  - 调整 `min_occurrence_ratio` (0.8 → 0.85)

#### 2. 多帧验证阶段
- **原因**: 稳定的误检（如固定背景物体）通过多帧验证
- **缓解措施**:
  - 提高 `min_frames` (5 → 7)
  - 提高 `min_occurrence_ratio` (0.8 → 0.85)
  - 增大 `validation_window` (10 → 15)

#### 3. 工程车辆匹配
- **原因**: 误匹配到信标（距离/RSSI匹配错误）
- **缓解措施**:
  - 提高 `match_cost_threshold` (10.0 → 15.0)
  - 调整 `distance_threshold` 和 `rssi_threshold`

#### 4. 去重逻辑
- **原因**: 重叠车辆被误判为同一车辆
- **缓解措施**:
  - 降低IoU阈值 (0.5 → 0.3)
  - 缩短时间窗口 (30秒 → 15秒)

### 5.2 假阴性 (False Negative) 来源

#### 1. 检测阶段
- **原因**: 低置信度真实车辆被过滤
- **缓解措施**:
  - 降低 `conf_threshold` (0.75 → 0.7)
  - 移除或降低跟踪阶段的硬编码置信度阈值 (0.7 → 0.6)

#### 2. 多帧验证阶段
- **原因**: 快速移动车辆无法通过多帧验证
- **缓解措施**:
  - 降低 `min_frames` (5 → 3)
  - 降低 `min_occurrence_ratio` (0.8 → 0.6)
  - 降低帧间匹配IoU阈值 (0.4 → 0.3)

#### 3. 工程车辆匹配
- **原因**: 
  - 距离测量不准确
  - 信标信号弱
  - 白名单未及时更新
- **缓解措施**:
  - 改善深度相机标定
  - 调整信标匹配阈值
  - 缩短白名单更新间隔

#### 4. 社会车辆识别
- **原因**: 车牌识别失败
- **缓解措施**:
  - 改善ROI裁剪（扩大边界）
  - 改善图像预处理（增强对比度）
  - 使用更先进的车牌识别模型

---

## 六、优化建议

### 6.1 配置参数化
- 将硬编码的阈值（如跟踪置信度0.7、去重时间窗口30秒）移到配置文件
- 便于根据不同场景调整

### 6.2 自适应阈值
- 根据历史检测统计动态调整阈值
- 例如：如果假阳性率高，自动提高 `conf_threshold`

### 6.3 多尺度检测
- 针对不同距离的车辆使用不同的检测阈值
- 远距离车辆：降低阈值（减少假阴性）
- 近距离车辆：提高阈值（减少假阳性）

### 6.4 类别细化
- 区分不同类型的工程车辆，使用不同的处理逻辑
- 例如：大型车辆（挖掘机）vs 小型车辆（装载机）

### 6.5 时空上下文
- 利用车辆运动轨迹判断合理性
- 例如：车辆不应该突然出现或消失

### 6.6 集成学习
- 结合多个检测结果（多个模型或多个时间点）
- 投票机制决定最终结果

---

## 七、调试和监控

### 7.1 关键指标
- **检测数量**: 每帧检测到的车辆数
- **过滤率**: 多帧验证过滤的检测数
- **跟踪ID切换率**: 同一车辆ID切换的频率
- **匹配成功率**: 工程车辆信标匹配成功率
- **识别成功率**: 社会车辆车牌识别成功率

### 7.2 日志记录
- 记录每个阶段的检测数量
- 记录过滤原因（低置信度、多帧验证失败等）
- 记录匹配/识别失败原因

### 7.3 可视化
- 绘制检测框和置信度
- 显示跟踪轨迹
- 显示匹配/识别结果

---

## 八、总结

### 8.1 关键决策点
1. **检测置信度阈值** (0.75): 平衡假阳性/假阴性
2. **多帧验证** (min_frames=5, ratio=0.8): 过滤不稳定检测
3. **信标匹配阈值**: 影响工程车辆备案判断
4. **去重逻辑**: 影响重复警报检测

### 8.2 权衡考虑
- **假阳性 vs 假阴性**: 通常需要权衡
- **响应速度 vs 稳定性**: 多帧验证增加延迟但提高稳定性
- **精确度 vs 召回率**: 提高阈值减少假阳性但可能增加假阴性

### 8.3 下一步优化方向
1. 参数配置化（移除硬编码）
2. 自适应阈值调整
3. 多尺度检测策略
4. 时空上下文利用
5. 集成学习方法

---

**文档版本**: 1.0  
**最后更新**: 2024年12月  
**维护者**: DeepStream Vehicle Detection Team


