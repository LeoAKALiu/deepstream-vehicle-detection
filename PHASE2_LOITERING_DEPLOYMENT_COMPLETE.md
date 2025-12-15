# Phase 2 徘徊检测模块部署完成

## 部署时间
2025-12-15

---

## 部署状态
✅ **已完成**

---

## 部署内容

### 新增文件
- ✅ `python_apps/loitering_detector.py` - 徘徊检测器模块
- ✅ `tests/test_phase2_loitering.py` - 集成测试脚本
- ✅ `scripts/deploy_phase2_loitering.sh` - 部署脚本

### 修改文件
- ✅ `config.yaml` - 添加 `alert.loitering` 配置段
- ✅ `test_system_realtime.py` - 集成徘徊检测功能

### 备份
- ✅ `backups/phase2_loitering_20251215_144008/` - 自动备份

---

## 测试结果

```
✅ 配置集成测试通过
✅ 徘徊判定逻辑测试全部通过
  - 车辆停留（几乎不动）- 检测到徘徊 ✅
  - 停留时间不足 - 不检测到徘徊 ✅
  - 画面占比太小 - 不检测到徘徊 ✅
✅ 清理功能测试通过
```

---

## 配置参数

**文件**: `config.yaml`

```yaml
alert:
  loitering:
    enabled: true                 # 启用
    min_duration: 10.0            # 最少停留时间：10.0秒
    min_area_ratio: 0.05          # 最小画面占比：0.05
    min_movement_ratio: 0.1       # 最小移动比例：0.1（归一化）
    apply_to_unregistered_only: true  # 只对未备案车辆应用
```

---

## 功能说明

### 徘徊检测器 (LoiteringDetector)

**功能**: 减少路过车辆的误报

**策略**:
- ✅ **只对未备案车辆应用徘徊判定**
- ✅ **已备案车辆立即报警**（不应用徘徊判定）
- ✅ **未备案车辆必须满足徘徊条件才报警**

### 判定条件

车辆必须同时满足以下条件才被认为是"徘徊"：

1. **停留时间** >= 10.0秒
2. **画面占比** >= 0.05（过滤边缘路过车辆）
3. **移动距离** < 0.1（归一化，识别真正停留的车辆）

---

## 预期效果

1. **减少误报**: 路过车辆不会触发报警
2. **提高准确性**: 只对真正停留的未备案车辆报警
3. **延迟报警**: 未备案车辆需要等待至少10秒才会报警

---

## 验证部署

系统重启后，查看启动日志，应该看到：

```
✓ 徘徊检测器初始化成功 (最少停留时间=10.0s, 最小画面占比=0.05, 只对未备案车辆应用=True)
```

---

## 注意事项

1. **延迟报警**: 未备案车辆需要等待至少10秒才会报警
2. **配置调优**: 根据实际场景可以调整参数
3. **性能影响**: 徘徊检测计算开销很小，对系统性能影响可忽略

---

## 回滚方案

如果出现问题，可以使用备份恢复：

```bash
# 查看备份目录
ls -la backups/phase2_loitering_20251215_144008/

# 恢复文件
cp backups/phase2_loitering_20251215_144008/config.yaml .
cp backups/phase2_loitering_20251215_144008/test_system_realtime.py .
cp backups/phase2_loitering_20251215_144008/python_apps/loitering_detector.py python_apps/
```

---

## 下一步

1. ✅ 停止系统 - 已完成
2. ⏳ **重启系统** - 待执行
3. ⏳ **验证日志** - 待执行
4. ⏳ **观察运行效果** - 待执行

---

**部署完成时间**: 2025-12-15  
**部署脚本**: `scripts/deploy_phase2_loitering.sh`  
**测试脚本**: `tests/test_phase2_loitering.py`  
**备份位置**: `backups/phase2_loitering_20251215_144008/`



