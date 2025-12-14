# Phase 1 生产环境部署指南

## ⚠️ 重要提示

**当前系统正在运行！** 在生产环境部署前，请仔细阅读本文档。

---

## 部署前检查清单

### 1. 当前系统状态
- ✅ 系统正在运行 (PID: 68583)
- ✅ 已检测到运行中的进程
- ✅ 所有Phase 1修改已完成并通过测试

### 2. 文件完整性验证
- ✅ `python_apps/beacon_match_tracker.py` - 新文件，已创建
- ✅ `config.yaml` - 已添加新配置项
- ✅ `test_system_realtime.py` - 已集成Phase 1功能
- ✅ 所有模块可以正常导入
- ✅ 配置文件语法正确

### 3. 测试验证
- ✅ 所有测试通过 (4/4)
- ✅ 配置读取测试通过
- ✅ 信标匹配跟踪器测试通过
- ✅ 默认值验证通过
- ✅ 配置集成测试通过

---

## 安全部署步骤

### 方法1: 使用自动化部署脚本（推荐）

```bash
# 1. 运行安全部署脚本
cd /home/liubo/Download/deepstream-vehicle-detection
./scripts/deploy_phase1_safe.sh

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

# 停止系统（使用进程ID）
kill <PID>

# 或使用脚本中的方法
pkill -f "test_system_realtime"

# 确认已停止
ps aux | grep test_system_realtime | grep -v grep
```

#### 步骤2: 创建备份

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 创建备份目录
BACKUP_DIR="backups/phase1_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份关键文件
cp config.yaml "$BACKUP_DIR/config.yaml.backup"
cp test_system_realtime.py "$BACKUP_DIR/test_system_realtime.py.backup"

echo "备份位置: $BACKUP_DIR"
```

#### 步骤3: 验证Phase 1文件

```bash
# 检查新文件是否存在
ls -la python_apps/beacon_match_tracker.py

# 验证模块导入
python3 -c "import sys; sys.path.insert(0, 'python_apps'); from beacon_match_tracker import BeaconMatchTracker; print('OK')"

# 验证配置文件
python3 -c "import yaml; yaml.safe_load(open('config.yaml')); print('OK')"
```

#### 步骤4: 运行测试

```bash
# 运行Phase 1测试套件
python3 tests/test_phase1_optimizations.py
```

#### 步骤5: 启动系统

```bash
# 启动系统（无头模式）
python3 test_system_realtime.py --no-display

# 或前台运行观察日志
python3 test_system_realtime.py --no-display 2>&1 | tee deployment.log
```

---

## 部署后的验证

### 1. 检查系统启动日志

启动时应该看到以下信息：

```
  跟踪最小置信度阈值: 0.7
  警报去重配置: 时间窗口=30.0s, IoU阈值=0.5
  信标匹配时空一致性: 启用 (最小连续帧=5, 距离误差阈值=1.0m)
```

### 2. 验证功能正常

- ✅ 系统正常启动
- ✅ 检测功能正常
- ✅ 信标匹配正常工作
- ✅ 观察是否有"⏳ [信标匹配] Track#X 匹配中... 等待连续5帧确认"的日志（说明时空一致性在工作）

### 3. 监控系统性能

```bash
# 监控FPS
watch -n 1 'ps aux | grep test_system_realtime | grep -v grep'

# 监控内存使用
watch -n 1 'ps aux | grep test_system_realtime | grep -v grep | awk "{print \$6/1024\" MB\"}"'
```

---

## 回滚方案

如果出现问题，可以快速回滚：

### 方法1: 使用回滚脚本

```bash
cd /home/liubo/Download/deepstream-vehicle-detection
./scripts/rollback_phase1.sh
```

### 方法2: 手动回滚

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 找到最新的备份
LATEST_BACKUP=$(ls -td backups/phase1_* | head -1)

# 恢复文件
cp "$LATEST_BACKUP/config.yaml.backup" config.yaml
cp "$LATEST_BACKUP/test_system_realtime.py.backup" test_system_realtime.py

# 重启系统
```

---

## 向后兼容性

### ✅ Phase 1 完全向后兼容

1. **配置项都有默认值**
   - 如果配置文件中没有新配置项，会使用默认值
   - `min_track_confidence` 默认: 0.7
   - `alert_dedup.*` 默认值与原硬编码值相同
   - `beacon_match.temporal_consistency.enabled` 默认: true

2. **功能可选**
   - 信标匹配时空一致性可以通过配置禁用
   - 如果禁用，行为与之前完全一致

3. **不破坏现有功能**
   - 所有原有功能保持不变
   - 只是添加了新功能和配置化

---

## 风险评估

### 低风险 ✅

1. **代码修改最小化**
   - 主要是配置读取和初始化逻辑
   - 核心检测逻辑未改变

2. **测试充分**
   - 所有测试通过
   - 模块导入验证通过
   - 配置文件语法验证通过

3. **回滚简单**
   - 只需恢复两个文件
   - 不需要数据库迁移或其他复杂操作

### 可能的问题和解决方案

| 问题 | 可能性 | 解决方案 |
|------|--------|----------|
| 配置项缺失 | 低 | 使用默认值，系统仍可运行 |
| 模块导入失败 | 低 | 已验证模块导入正常 |
| 信标匹配延迟 | 中 | 正常现象，5帧≈0.2秒（@25fps） |
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
   - 报警是否正常

3. **性能指标**
   - FPS是否正常
   - 内存使用是否正常
   - CPU使用率是否正常

4. **新功能验证**
   - 信标匹配时空一致性是否生效
   - 是否有"匹配中...等待确认"的日志
   - 匹配锁定后是否稳定

---

## 支持信息

- 测试结果: `docs/PHASE1_TEST_RESULTS.md`
- 实施总结: `docs/PHASE1_IMPLEMENTATION_SUMMARY.md`
- 备份位置: `backups/phase1_YYYYMMDD_HHMMSS/`

---

**部署时间**: 请记录实际部署时间  
**部署人员**: 请填写部署人员姓名  
**备注**: 如有特殊情况，请在此记录

