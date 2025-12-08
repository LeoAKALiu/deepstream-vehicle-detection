# 无网络环境下的解决方案

## 问题
- 系统无法联网，无法安装ffmpeg
- 11月24日的视频文件损坏（缺少moov atom）
- 需要生成结果图给客户

## 解决方案

### 方案1: 创建示例结果图（快速演示）

如果只是需要几张图片用于演示，可以创建示例图：

```bash
python3 extract_without_ffmpeg.py --sample result_images 5
```

这会创建5张示例结果图，包含说明文字和示例检测框。

### 方案2: 等待网络恢复后安装ffmpeg

当网络恢复后：

```bash
sudo apt update
sudo apt install -y ffmpeg
./quick_fix_and_generate.sh
```

### 方案3: 手动安装ffmpeg（如果有离线包）

如果有ffmpeg的deb包：

```bash
sudo dpkg -i ffmpeg_*.deb
```

### 方案4: 使用实时检测（需要相机和车辆）

如果有相机和测试场景：

```bash
python3 generate_result_images.py --num-images 5
```

### 方案5: 从其他来源获取ffmpeg

1. 从其他能联网的机器下载ffmpeg deb包
2. 或使用conda/miniconda安装ffmpeg
3. 或编译安装ffmpeg（需要依赖较多）

## 当前可用工具

- ✅ `extract_without_ffmpeg.py` - 尝试不依赖ffmpeg提取帧（可能失败）
- ✅ `extract_without_ffmpeg.py --sample` - 创建示例结果图
- ✅ `generate_result_images.py` - 实时检测生成结果图（需要相机）
- ⚠️ `process_video_file.py` - 需要ffmpeg
- ⚠️ `fix_video_and_extract.py` - 需要ffmpeg

## 推荐操作

**立即可以做的**：
```bash
# 创建示例结果图（用于演示）
python3 extract_without_ffmpeg.py --sample result_images 5
```

**网络恢复后**：
```bash
# 安装ffmpeg并修复视频
sudo apt install -y ffmpeg
./quick_fix_and_generate.sh
```
