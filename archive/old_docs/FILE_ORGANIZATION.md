# 文件组织结构说明

本文档说明项目的文件组织结构，帮助快速定位所需文件。

## 目录结构

```
deepstream-vehicle-detection/
├── README.md                      # 项目主README
├── test_system_realtime.py        # 主程序文件
├── config.yaml                    # 主配置文件
├── beacon_whitelist.yaml          # 信标白名单配置
├── start_field_test_display.sh    # 主启动脚本（带显示）
├── start_field_test_with_recording.sh  # 主启动脚本（带录制）
│
├── python_apps/                   # Python应用模块
│   ├── tensorrt_yolo_inference.py
│   ├── byte_tracker.py
│   ├── orbbec_depth.py
│   ├── cassia_local_client.py
│   ├── beacon_filter.py
│   ├── config_loader.py
│   └── ...
│
├── docs/                          # 文档目录（42个文档）
│   ├── PROJECT_DOCUMENTATION.md   # 项目完整文档
│   ├── MULTI_FRAME_VALIDATION_GUIDE.md
│   ├── P0_IMPROVEMENTS_TEST_REPORT.md
│   ├── field_test_optimization_summary.md
│   └── ...（其他技术文档）
│
├── tests/                         # 测试脚本目录（12个文件）
│   ├── test_system_realtime.py    # （已移至根目录）
│   ├── test_p0_improvements.py
│   ├── test_realtime_system.sh
│   ├── test_custom_model.sh
│   └── ...
│
├── tools/                         # 工具脚本目录（20个文件）
│   ├── check_cassia.sh
│   ├── fix_cassia_connection.sh
│   ├── setup_cassia_network.sh
│   ├── diagnose_deepstream.sh
│   └── ...
│
├── scripts/                       # 系统安装脚本
│   ├── install_deepstream.sh
│   ├── prepare_tensorrt.sh
│   └── ...
│
├── config/                        # DeepStream配置文件
│   ├── labels.txt
│   └── ...
│
├── models/                        # 模型文件
│   └── custom_yolo.engine
│
└── recordings/                    # 录制文件
    └── field_test_*/
```

## 主要文件说明

### 根目录文件（核心文件）

| 文件 | 说明 |
|------|------|
| `test_system_realtime.py` | 主程序：实时车辆检测系统 |
| `config.yaml` | 系统主配置文件 |
| `beacon_whitelist.yaml` | BLE信标白名单配置 |
| `start_field_test_display.sh` | 启动脚本（带显示，用于现场测试） |
| `start_field_test_with_recording.sh` | 启动脚本（带录制功能） |
| `README.md` | 项目主README |

### docs/ 目录

包含所有技术文档，包括：
- **项目文档**: `PROJECT_DOCUMENTATION.md` - 完整的项目文档
- **功能指南**: 各种功能的使用说明（ByteTrack、Cassia、Orbbec等）
- **测试报告**: P0改进测试报告、现场测试优化总结
- **开发指南**: 开发指南、调试指南、安装指南等

**重要文档**:
- `PROJECT_DOCUMENTATION.md` - 项目完整文档（必读）
- `MULTI_FRAME_VALIDATION_GUIDE.md` - 多帧验证功能说明
- `field_test_optimization_summary.md` - 现场测试优化总结

### tests/ 目录

包含所有测试脚本：
- `test_p0_improvements.py` - P0改进测试
- `test_realtime_system.sh` - 实时系统测试
- `test_custom_model.sh` - 自定义模型测试
- 其他功能测试脚本

### tools/ 目录

包含工具脚本：
- **Cassia相关**: `check_cassia.sh`, `fix_cassia_connection.sh`, `setup_cassia_network.sh`
- **诊断工具**: `diagnose_deepstream.sh`, `diagnose_cassia_connection.sh`
- **配置工具**: `verify_config.sh`, `update_cassia_ip.sh`
- **其他工具**: `quick_test.sh`, `run_full_system.sh`

### scripts/ 目录

系统安装和准备脚本：
- `install_deepstream.sh` - DeepStream安装脚本
- `prepare_tensorrt.sh` - TensorRT准备脚本
- `check_deepstream.sh` - DeepStream检查脚本

## 快速查找

### 我需要...

| 需求 | 位置 |
|------|------|
| 运行主程序 | 根目录 `./start_field_test_display.sh` |
| 查看配置 | 根目录 `config.yaml` |
| 阅读项目文档 | `docs/PROJECT_DOCUMENTATION.md` |
| 运行测试 | `tests/` 目录 |
| 诊断问题 | `tools/` 目录 |
| 安装系统 | `scripts/` 目录 |
| 查看模块代码 | `python_apps/` 目录 |

## 文件整理历史

**整理时间**: 2025-01-02

**整理内容**:
1. 创建 `docs/` 目录，移动所有 `.md` 文档（42个）
2. 创建 `tests/` 目录，移动测试脚本（12个）
3. 创建 `tools/` 目录，移动工具脚本（20个）
4. 保留主程序文件在根目录
5. 保持 `scripts/` 目录不变（系统安装脚本）

**整理原则**:
- 根目录只保留核心文件（主程序、配置文件、启动脚本）
- 文档统一放在 `docs/` 目录
- 测试脚本统一放在 `tests/` 目录
- 工具脚本统一放在 `tools/` 目录

---
*最后更新: 2025-01-02*

