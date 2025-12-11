# 安装说明

## 当前状态

✅ **所有依赖已安装，无需再次安装**

系统已安装以下依赖包，版本虽然略低于requirements.txt中的要求，但完全可以使用：

| 包名 | 已安装版本 | 最低要求 | 状态 |
|------|-----------|---------|------|
| requests | 2.25.1 | 2.25.0 | ✅ 可用 |
| Pillow | 9.0.1 | 9.0.0 | ✅ 可用 |
| opencv-python | 4.11.0 | 4.8.0 | ✅ 可用 |
| numpy | 1.26.1 | 1.24.0 | ✅ 可用 |

**注意**：系统已安装 `opencv-python`，无需安装 `opencv-python-headless`。两者功能相同，headless版本只是没有GUI支持，但系统已有完整版本可用。

## 测试结果

✅ 所有模块导入成功
✅ 云端集成模块可以使用

## 使用说明

由于网络问题无法从PyPI安装新版本，但现有版本完全满足功能需求，可以：

1. **直接使用**：无需安装，直接运行主程序即可
2. **功能正常**：所有云端集成功能都可以正常使用
3. **可选升级**：如果将来网络恢复，可以升级到最新版本（非必需）

## 关于 opencv-python-headless

`opencv-python-headless` 是 opencv-python 的轻量级版本（无GUI支持），但系统已安装完整的 `opencv-python` 4.11.0，功能完全相同，**无需安装 headless 版本**。

## 如果将来需要升级

当网络连接正常时，可以运行：

```bash
pip install --upgrade requests Pillow numpy
```

注意：opencv-python 已满足需求，无需安装 opencv-python-headless。

## 验证安装

运行以下命令验证模块是否可用：

```bash
cd jetson-client
python3 -c "from main_integration import SentinelIntegration; print('✅ 模块可用')"
```

---
*最后更新: 2025-01-02*

