# 项目目录清理日志

**清理时间**: 2025-12-09  
**清理范围**: 项目根目录及子目录中的过时文档、代码和脚本

---

## 清理内容

### 1. 根目录文档
- `GIT_SETUP.md` - Git设置文档（已不再需要）

### 2. 开发阶段文档
- `P0_*.md` - P0阶段相关文档
- `P1_*.md` - P1阶段相关文档
- `daily_progress.md` - 日常开发日志
- `REMAINING_TASKS.md` - 剩余任务列表
- `IMPROVEMENT_TODO.md` - 改进待办事项
- `CURRENT_STATUS.md` - 当前状态文档
- `DEPLOYMENT_STATUS.md` - 部署状态文档
- `SHORT_TERM_TASKS_COMPLETE.md` - 短期任务完成文档

### 3. Bug修复文档（已修复并集成）
- `BUG_FIX_SUMMARY.md` - Bug修复总结
- `CONFIDENCE_BUG_FIX.md` - 置信度修复文档
- `DATA_QUALITY_ISSUE_CONFIRMATION.md` - 数据质量问题确认
- `DATA_ISSUES_FIX_PLAN.md` - 数据问题修复计划
- `DATA_FIX_VERIFICATION.md` - 数据修复验证
- `IMAGE_API_FIX.md` - 图像API修复
- `ALERT_FIX_IMPLEMENTATION.md` - 警报修复实现
- `ALERT_DEDUPLICATION_ANALYSIS.md` - 警报去重分析
- `ISSUE_DIAGNOSIS_AND_FIX.md` - 问题诊断和修复

### 4. 功能实现文档（已集成到主文档）
- `CLOUD_INTEGRATION_COMPLETE.md` - 云端集成完成
- `CLOUD_INTEGRATION_SUMMARY.md` - 云端集成总结
- `CLOUD_TEAM_UPDATE.md` - 云端团队更新
- `SERVICE_RESTART_GUIDE.md` - 服务重启指南
- `BEACON_WHITELIST_IMPLEMENTATION.md` - 信标白名单实现
- `MONITORING_SNAPSHOT_FEATURE.md` - 监控截图功能
- `DATA_RETENTION_IMPLEMENTATION.md` - 数据留存实现

### 5. 重复和过时的参考文档
- `readme_full.md` - 完整README（与主README重复）
- `readme_start_dev.txt` - 开发启动说明
- `api_reference.md` - API参考（已集成到主文档）
- `quick_reference.md` - 快速参考
- `development_guide.md` - 开发指南（已集成）
- `debugging_guide.md` - 调试指南（已集成）
- `manual_test_guide.md` - 手动测试指南

### 6. 现场测试文档
- `field_test_*.md` - 现场测试相关文档
- `lab_simulation_guide.md` - 实验室模拟指南
- `local_router_guide.md` - 本地路由器指南

### 7. DeepStream开发文档（已移至deepstream-dev目录）
- `deepstream_*.md` - DeepStream相关文档
- `start_deepstream_dev.md` - DeepStream开发启动
- `DEEPSTREAM_TEST_TODO.md` - DeepStream测试待办

### 8. 解决方案文档
- `final_solution_summary.md` - 最终解决方案总结
- `hybrid_solution_guide.md` - 混合解决方案指南
- `system_completion_summary.md` - 系统完成总结
- `construction_vehicle_detection_issue.md` - 工程车辆检测问题

### 9. ByteTrack相关文档
- `ByteTrack*.md` - ByteTrack相关文档
- `boxmot_ByteTrack对比分析.md` - ByteTrack对比分析

### 10. 配置和API文档
- `配置文件使用说明.md` - 配置文件使用说明
- `硬编码参数列表.md` - 硬编码参数列表
- `功能差异分析.md` - 功能差异分析
- `pyorbbecsdk_api_reference.md` - PyOrbbecSDK API参考
- `convert_custom_model.md` - 自定义模型转换
- `gpu_acceleration_guide.md` - GPU加速指南

### 11. 长期测试文档
- `LONG_TERM_TEST_TODO.md` - 长期测试待办
- `QUICK_START_LONG_TERM_TEST.md` - 长期测试快速开始
- `LONG_TERM_TEST_CHECKLIST.md` - 长期测试检查清单

### 12. Cassia相关文档（已集成到主文档）
- `cassia_beacon_integration.md` - Cassia信标集成
- `cassia_troubleshooting.md` - Cassia故障排除
- `beacon_filter_upgrade.md` - 信标过滤器升级
- `beacon_whitelist_guide.md` - 信标白名单指南

### 13. 系统设置文档（已集成到主文档）
- `system_logic_guide.md` - 系统逻辑指南
- `run_on_jetson.md` - Jetson运行指南
- `startup_guide.md` - 启动指南
- `AUTO_START_SETUP.md` - 自动启动设置
- `SSH_SETUP.md` - SSH设置
- `SITE_DEPLOYMENT_NETWORK.md` - 现场部署网络

### 14. 项目文档（已过时）
- `PROJECT_DOCUMENTATION.md` - 项目文档（已过时）
- `FILE_ORGANIZATION.md` - 文件组织（已过时）
- `MULTI_FRAME_VALIDATION_GUIDE.md` - 多帧验证指南
- `P0_IMPROVEMENTS_TEST_REPORT.md` - P0改进测试报告
- `P0_3_4_IMPLEMENTATION_SUMMARY.md` - P0实现总结
- `field_test_optimization_summary.md` - 现场测试优化总结

### 15. 脚本清理
- `scripts/test_p0_features.sh` - P0功能测试脚本
- `scripts/install_deepstream.sh` - DeepStream安装脚本
- `scripts/install_deepstream_fixed.sh` - DeepStream安装脚本（修复版）
- `scripts/prepare_tensorrt.sh` - TensorRT准备脚本
- `scripts/check_deepstream.sh` - DeepStream检查脚本

### 16. 工具脚本清理
- `tools/quick_test.sh` - 快速测试脚本
- `tools/run_full_system.sh` - 完整系统运行脚本
- `tools/rename_files.sh` - 文件重命名脚本
- `tools/diagnose_deepstream.sh` - DeepStream诊断脚本
- `tools/setup_pyds.sh` - PyDS设置脚本
- `tools/prepare_engine_tsinghua.sh` - 引擎准备脚本
- `tools/prepare_tensorrt_engine.sh` - TensorRT引擎准备脚本
- `tools/start_deepstream_container.sh` - DeepStream容器启动脚本

### 17. 测试脚本清理
- `tests/test_hybrid_solution.sh` - 混合解决方案测试
- `tests/test_pipeline_*.sh` - 管道测试脚本
- `tests/test_deepstream_app.sh` - DeepStream应用测试

### 18. 临时文件
- `4g_traffic_estimate.json` - 4G流量估算JSON文件

---

## 保留的核心文档

### docs/ 目录保留的文档
- `API_DOCUMENTATION.md` - API文档（当前使用）
- `DATA_RETENTION.md` - 数据留存文档（当前使用）
- `orbbec_camera_guide.md` - Orbbec相机指南（当前使用）
- `CLOUD_DEBUGGING_GUIDE.md` - 云端调试指南（当前使用）

### 根目录保留的文件
- `README.md` - 项目主README
- `config.yaml` - 主配置文件
- `beacon_whitelist.yaml` - 信标白名单配置
- `test_system_realtime.py` - 主程序文件
- `detection_results.db` - 检测结果数据库

---

## 清理统计

- **文档文件**: 约60+ 个
- **脚本文件**: 约15+ 个
- **临时文件**: 1 个

所有清理的文件已移至 `archive/` 目录，按类型分类：
- `archive/old_docs/` - 过时文档
- `archive/old_scripts/` - 过时脚本
- `archive/old_tools/` - 过时工具
- `archive/old_tests/` - 过时测试

---

## 注意事项

1. 所有清理的文件都保留在 `archive/` 目录中，可以随时查看
2. 如果需要恢复某个文件，可以从 `archive/` 目录中复制回来
3. 核心功能和当前使用的文档都已保留
4. 建议定期清理 `archive/` 目录，删除不再需要的文件

---

**清理完成时间**: 2025-12-09


