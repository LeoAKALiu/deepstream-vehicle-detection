# Phase 2 徘徊检测模块部署就绪

## 部署状态
✅ **测试通过** - 所有测试用例已通过  
✅ **文件就绪** - 所有文件已就绪  
✅ **配置验证** - 配置文件验证通过  
✅ **代码验证** - Python语法和模块导入验证通过  

---

## 部署内容

### 新增文件
- `python_apps/loitering_detector.py` - 徘徊检测器模块
- `tests/test_phase2_loitering.py` - 集成测试脚本

### 修改文件
- `config.yaml` - 添加 `alert.loitering` 配置段
- `test_system_realtime.py` - 集成徘徊检测功能

### 备份位置
- `backups/phase2_loitering_YYYYMMDD_HHMMSS/` - 自动备份

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

1. **停留时间** >= 10.0秒（`min_duration`）
2. **画面占比** >= 0.05（`min_area_ratio`）- 过滤边缘路过车辆
3. **移动距离** < 0.1（归一化，`min_movement_ratio`）- 识别真正停留的车辆

---

## 配置参数

**文件**: `config.yaml`

```yaml
alert:
  loitering:
    enabled: true                 # 是否启用徘徊判定
    min_duration: 10.0            # 最少停留时间（秒）
    min_area_ratio: 0.05          # 最小画面占比（0-1）
    min_movement_ratio: 0.1       # 最小移动比例（归一化）
    apply_to_unregistered_only: true  # 只对未备案车辆应用
```

---

## 部署步骤

### 1. 停止当前系统

```bash
# 查找运行中的进程
ps aux | grep test_system_realtime | grep -v grep

# 停止进程（根据实际PID）
kill <PID>
# 或者使用
pkill -f test_system_realtime
```

### 2. 验证部署文件

所有文件已经通过部署脚本验证：
- ✅ Python语法检查
- ✅ 模块导入测试
- ✅ 配置文件验证
- ✅ 集成测试通过

### 3. 重启系统

```bash
# 启动系统（根据实际启动命令）
python3 test_system_realtime.py
# 或
./run.sh
```

### 4. 验证部署

查看启动日志，确认以下信息：

```
✓ 徘徊检测器初始化成功 (最少停留时间=10.0s, 最小画面占比=0.05, 只对未备案车辆应用=True)
```

---

## 预期效果

1. **减少误报**: 路过车辆不会触发报警
2. **提高准确性**: 只对真正停留的未备案车辆报警
3. **延迟报警**: 未备案车辆需要等待至少10秒才会报警

---

## 注意事项

1. **延迟报警**: 未备案车辆需要等待至少10秒（`min_duration`）才会报警
2. **配置调优**: 根据实际场景可以调整参数：
   - 如果误报多，可以增大 `min_duration`
   - 如果漏报多，可以减小 `min_duration`
   - 根据画面大小调整 `min_area_ratio`
3. **性能影响**: 徘徊检测计算开销很小，对系统性能影响可忽略

---

## 回滚方案

如果出现问题，可以使用备份恢复：

```bash
# 查看备份目录
ls -la backups/phase2_loitering_*/

# 恢复文件
cp backups/phase2_loitering_YYYYMMDD_HHMMSS/config.yaml .
cp backups/phase2_loitering_YYYYMMDD_HHMMSS/test_system_realtime.py .
cp backups/phase2_loitering_YYYYMMDD_HHMMSS/python_apps/loitering_detector.py python_apps/
```

---

## 测试结果

```
✅ 配置集成测试通过
✅ 徘徊判定逻辑测试全部通过
✅ 清理功能测试通过
```

**测试覆盖**:
- ✅ 配置参数读取
- ✅ 车辆停留判定
- ✅ 停留时间不足判定
- ✅ 画面占比太小判定
- ✅ 清理功能

---

**部署就绪时间**: 2025-12-15  
**部署脚本**: `scripts/deploy_phase2_loitering.sh`  
**测试脚本**: `tests/test_phase2_loitering.py`


