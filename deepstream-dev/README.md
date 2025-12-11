# DeepStream车辆检测方案 - 开发分支

## 📋 项目说明

这是DeepStream方案的独立开发分支，与主TensorRT方案并行开发。

**开发策略**：
- ✅ 保持TensorRT方案正常运行
- 🔄 并行开发DeepStream方案
- ✅ 开发完成并测试通过后，再考虑迁移

## 📁 目录结构

```
deepstream-dev/
├── python_apps/          # Python应用代码
│   ├── deepstream_vehicle_detection.py  # 主应用
│   ├── orbbec_depth.py                  # 深度相机模块
│   ├── cassia_local_client.py           # 蓝牙信标模块
│   ├── beacon_filter.py                 # 信标过滤器
│   └── config_loader.py                 # 配置加载器
├── jetson-client/        # 云端集成模块
├── config/              # 配置文件
│   ├── config_infer_yolov11.txt
│   └── labels.txt
├── models/              # 模型文件（链接到主目录）
├── docs/                # 开发文档
├── tests/               # 测试脚本
└── scripts/             # 工具脚本
```

## 🚀 快速开始

### 1. 准备环境

```bash
cd /home/liubo/Download/deepstream-vehicle-detection/deepstream-dev

# 检查DeepStream容器
sudo docker images | grep deepstream

# 运行测试
bash tests/test_basic.sh
```

### 2. 开发进度

查看 `docs/DEVELOPMENT_TODO.md` 了解当前开发任务。

## 📝 开发原则

1. **不破坏主方案**：所有修改仅在此目录进行
2. **功能对等**：确保与TensorRT方案功能一致
3. **独立测试**：所有测试在此目录进行
4. **文档同步**：重要变更记录在docs目录

---

**创建时间**: 2024年12月8日  
**状态**: 🚧 开发中



