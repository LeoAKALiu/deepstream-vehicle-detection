# Phase 2 部署指南

## ⚠️ 重要提示

本次部署包含**已测试通过的3项Phase 2优化**：
1. ✅ ByteTrack参数调优
2. ✅ 深度测量时间平滑
3. ✅ LPR最佳帧选取

**未包含**（待后续实施）：
- ⏳ 徘徊判定

---

## 部署前检查清单

### ✅ 已验证项目
- [x] 所有测试通过 (5/5)
- [x] 配置文件语法正确
- [x] 模块导入正常
- [x] 功能测试通过

### ⚠️ 待执行
- [ ] 停止当前运行中的系统
- [ ] 创建备份
- [ ] 部署验证
- [ ] 重启系统测试

---

## 安全部署步骤

### 方法1: 使用自动化部署脚本（推荐）

```bash
# 1. 运行安全部署脚本
cd /home/liubo/Download/deepstream-vehicle-detection
./scripts/deploy_phase2_safe.sh

# 脚本会自动：
# - 检查系统状态（会提示停止运行中的系统）
# - 创建完整备份
# - 验证所有文件
# - 运行测试
# - 生成部署摘要
```

### 方法2: 手动部署

#### 步骤1: 停止当前系统

```bash
# 找到运行中的进程
ps aux | grep test_system_realtime

# 停止系统
pkill -f "test_system_realtime"

# 确认已停止
ps aux | grep test_system_realtime | grep -v grep
```

#### 步骤2: 创建备份

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 创建备份目录
BACKUP_DIR="backups/phase2_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份关键文件
cp config.yaml "$BACKUP_DIR/config.yaml.backup"
cp test_system_realtime.py "$BACKUP_DIR/test_system_realtime.py.backup"
cp python_apps/depth_smoothing.py "$BACKUP_DIR/python_apps/depth_smoothing.py.backup" 2>/dev/null || true
cp python_apps/best_frame_lpr.py "$BACKUP_DIR/python_apps/best_frame_lpr.py.backup" 2>/dev/null || true

echo "备份位置: $BACKUP_DIR"
```

#### 步骤3: 运行测试验证

```bash
# 运行Phase 2测试套件
python3 tests/test_phase2_optimizations.py
```

#### 步骤4: 启动系统

```bash
# 启动系统（无头模式）
python3 test_system_realtime.py --no-display

# 或后台运行并查看日志
nohup python3 test_system_realtime.py --no-display > phase2_deployment.log 2>&1 &
tail -f phase2_deployment.log
```

---

## 部署后的验证

### 1. 检查系统启动日志

启动时应该看到以下信息：

```
✓ ByteTrack跟踪器初始化完成 (Phase 2优化)
  匹配阈值: 0.4 (Phase 2优化)
  跟踪缓冲区: 200 (Phase 2优化)
  ✓ 深度测量时间平滑: 启用 (方法=ema, alpha=0.7)
  ✓ LPR最佳帧选择器初始化成功 (质量阈值=0.6, 最大等待帧数=30)
```

### 2. 验证功能正常

#### ByteTrack参数优化
- 观察Track ID切换率是否降低
- 验证静止车辆是否不再丢失ID
- 验证遮挡后恢复跟踪是否更稳定

#### 深度测量时间平滑
- 观察深度值是否更稳定
- 查看日志中是否有"平滑后"的深度值
- 验证信标匹配准确性是否提升

#### LPR最佳帧选取
- 观察是否有"⏳ 等待最佳帧出现..."的日志
- 验证是否使用最佳帧进行识别
- 检查识别成功率是否提升

### 3. 监控系统性能

```bash
# 监控FPS
watch -n 1 'ps aux | grep test_system_realtime | grep -v grep'

# 监控内存使用
watch -n 1 'ps aux | grep test_system_realtime | grep -v grep | awk "{print \$6/1024\" MB\"}"'

# 查看实时日志
tail -f phase2_deployment.log
```

---

## 回滚方案

如果出现问题，可以快速回滚：

### 方法1: 使用回滚脚本（如果有）

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
./scripts/rollback_phase2.sh
```

### 方法2: 手动回滚

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 找到最新的备份
LATEST_BACKUP=$(ls -td backups/phase2_* | head -1)

# 恢复文件
cp "$LATEST_BACKUP/config.yaml.backup" config.yaml
cp "$LATEST_BACKUP/test_system_realtime.py.backup" test_system_realtime.py

# 可选：删除新文件（如果不再需要）
rm python_apps/depth_smoothing.py
rm python_apps/best_frame_lpr.py

# 重启系统
python3 test_system_realtime.py --no-display
```

---

## 向后兼容性

### ✅ Phase 2 完全向后兼容

1. **配置项都有默认值**
   - ByteTrack参数有默认值（但已优化）
   - 深度平滑可以禁用（`depth.smoothing.enabled: false`）
   - LPR最佳帧可以禁用（`lpr.best_frame_selection.enabled: false`）

2. **功能可选**
   - 深度平滑可以通过配置禁用
   - LPR最佳帧可以通过配置禁用
   - 如果禁用，行为与之前一致

3. **不破坏现有功能**
   - 所有原有功能保持不变
   - 只是添加了新功能和优化

---

## 风险评估

### 低风险 ✅

1. **测试充分**
   - 所有测试通过 (5/5)
   - 模块导入验证通过
   - 配置文件语法验证通过

2. **代码修改最小化**
   - 主要是配置读取和初始化逻辑
   - 核心检测逻辑未改变

3. **回滚简单**
   - 只需恢复2个文件
   - 不需要数据库迁移或其他复杂操作

### 可能的问题和解决方案

| 问题 | 可能性 | 解决方案 |
|------|--------|----------|
| 配置项缺失 | 低 | 使用默认值，系统仍可运行 |
| 模块导入失败 | 低 | 已验证模块导入正常 |
| 深度平滑延迟 | 低 | 延迟可忽略（3帧后生效） |
| LPR识别延迟 | 中 | 正常现象，最多30帧≈1.2秒@25fps |
| 性能下降 | 低 | 影响可忽略（已测试） |

---

## 部署检查清单

在部署前，请确认：

- [ ] 已阅读本文档
- [ ] 已停止运行中的系统
- [ ] 已创建备份
- [ ] 已验证所有文件存在
- [ ] 已运行测试并全部通过
- [ ] 了解回滚方法
- [ ] 准备好监控系统状态

---

## 部署后监控

部署后请监控以下指标：

1. **系统稳定性**
   - 是否有崩溃
   - 是否有异常日志

2. **功能正确性**
   - 检测是否正常
   - 信标匹配是否正常
   - LPR识别是否正常

3. **性能指标**
   - FPS是否正常
   - 内存使用是否正常
   - CPU使用率是否正常

4. **新功能验证**
   - ByteTrack参数优化效果
   - 深度平滑是否生效
   - LPR最佳帧选择是否工作

---

## 支持信息

- 测试结果: `docs/PHASE2_TEST_RESULTS.md`
- 实施进度: `docs/PHASE2_IMPLEMENTATION_PROGRESS.md`
- 测试总结: `PHASE2_TEST_SUMMARY.md`
- 备份位置: `backups/phase2_YYYYMMDD_HHMMSS/`

---

**部署时间**: 请记录实际部署时间  
**部署人员**: 请填写部署人员姓名  
**备注**: 如有特殊情况，请在此记录

