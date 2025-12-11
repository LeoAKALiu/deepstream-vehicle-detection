#!/bin/bash
# 重命名中文文件名为英文（保留中文内容）

cd /home/liubo/Download/deepstream-vehicle-detection

# 创建重命名映射
declare -A rename_map=(
    # Shell脚本
    ["测试实时系统.sh"]="test_realtime_system.sh"
    ["测试BLE信标.sh"]="test_ble_beacon.sh"
    ["测试信标过滤器.sh"]="test_beacon_filter.sh"
    ["测试自定义模型.sh"]="test_custom_model.sh"
    ["测试DeepStream应用.sh"]="test_deepstream_app.sh"
    ["测试Pipeline-修复版.sh"]="test_pipeline_fixed.sh"
    ["测试基础Pipeline.sh"]="test_pipeline_basic.sh"
    ["测试混合方案.sh"]="test_hybrid_solution.sh"
    ["快速测试.sh"]="quick_test.sh"
    ["调试检测.sh"]="debug_detection.sh"
    ["运行完整系统.sh"]="run_full_system.sh"
    ["配置Orbbec权限.sh"]="setup_orbbec_permissions.sh"
    ["配置Cassia网络.sh"]="setup_cassia_network.sh"
    ["配置Cassia网络-完整版.sh"]="setup_cassia_network_full.sh"
    ["配置Cassia-两个网口.sh"]="setup_cassia_dual_interface.sh"
    ["查找Cassia路由器.sh"]="find_cassia_router.sh"
    ["诊断Cassia连接.sh"]="diagnose_cassia_connection.sh"
    ["诊断DeepStream环境.sh"]="diagnose_deepstream.sh"
    ["验证配置.sh"]="verify_config.sh"
    ["准备TensorRT引擎.sh"]="prepare_tensorrt_engine.sh"
    ["准备引擎-清华源.sh"]="prepare_engine_tsinghua.sh"
    ["启动DeepStream容器.sh"]="start_deepstream_container.sh"
    ["启动现场测试-带录制.sh"]="start_field_test_with_recording.sh"
    ["更新CassiaIP地址.sh"]="update_cassia_ip.sh"
    
    # Markdown文档
    ["现场测试检查清单.md"]="field_test_checklist.md"
    ["现场测试前必做事项.md"]="field_test_prerequisites.md"
    ["现场测试录制说明.md"]="field_test_recording_guide.md"
    ["实验室模拟测试指南.md"]="lab_simulation_guide.md"
    ["信标白名单配置指南.md"]="beacon_whitelist_guide.md"
    ["信标过滤升级说明.md"]="beacon_filter_upgrade.md"
    ["快速参考.md"]="quick_reference.md"
    ["调试指南.md"]="debugging_guide.md"
    ["转换自定义模型.md"]="convert_custom_model.md"
    ["工程机械识别问题说明.md"]="construction_vehicle_detection_issue.md"
    ["GPU加速方案说明.md"]="gpu_acceleration_guide.md"
    ["混合方案说明.md"]="hybrid_solution_guide.md"
    ["系统完成总结.md"]="system_completion_summary.md"
    ["系统逻辑说明.md"]="system_logic_guide.md"
    ["最终方案总结.md"]="final_solution_summary.md"
    ["今日成果与明日计划.md"]="daily_progress.md"
    ["启动说明.md"]="startup_guide.md"
    ["在Jetson上运行.md"]="run_on_jetson.md"
    ["手动测试指南.md"]="manual_test_guide.md"
    ["开发指南.md"]="development_guide.md"
    ["开始DeepStream开发.md"]="start_deepstream_dev.md"
    ["DeepStream快速入门.md"]="deepstream_quickstart.md"
    ["Cassia信标集成指南.md"]="cassia_beacon_integration.md"
    ["Cassia连接故障排除.md"]="cassia_troubleshooting.md"
    ["本地路由器使用指南.md"]="local_router_guide.md"
    ["Orbbec深度相机使用指南.md"]="orbbec_camera_guide.md"
    ["API参考文档.md"]="api_reference.md"
    ["pyorbbecsdk_API参考.md"]="pyorbbecsdk_api_reference.md"
    ["DEEPSTREAM_INSTALL_GUIDE.md"]="deepstream_install_guide.md"
    ["README-完整版.md"]="readme_full.md"
    ["README-开始开发.txt"]="readme_start_dev.txt"
)

# 执行重命名
for old_name in "${!rename_map[@]}"; do
    new_name="${rename_map[$old_name]}"
    if [ -f "$old_name" ]; then
        echo "重命名: $old_name -> $new_name"
        mv "$old_name" "$new_name"
    fi
done

echo ""
echo "✓ 文件重命名完成！"

