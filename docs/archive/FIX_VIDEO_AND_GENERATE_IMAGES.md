# 从损坏的视频文件生成结果图

## 问题
11月24日的RGB视频（48MB）损坏，缺少 `moov atom`（元数据），无法正常播放。

## 解决方案

### 方案1: 安装ffmpeg并修复视频（推荐）

```bash
# 1. 安装ffmpeg
sudo apt update
sudo apt install -y ffmpeg

# 2. 修复视频
ffmpeg -i recordings/field_test_20251124_120342/rgb_video.mp4 \
       -c copy \
       -movflags +faststart \
       recordings/field_test_20251124_120342/rgb_video_repaired.mp4

# 3. 从修复后的视频生成结果图
python3 process_video_file.py \
    recordings/field_test_20251124_120342/rgb_video_repaired.mp4 \
    --num-images 5 \
    --output-dir result_images
```

### 方案2: 直接从损坏的视频提取帧（需要ffmpeg）

```bash
# 安装ffmpeg（如果未安装）
sudo apt install -y ffmpeg

# 使用修复脚本
python3 fix_video_and_extract.py \
    recordings/field_test_20251124_120342/rgb_video.mp4 \
    extracted_frames

# 然后从提取的帧生成结果图
# （需要手动处理提取的帧）
```

### 方案3: 使用实时检测生成新结果图（无需视频）

如果无法修复视频，可以在有相机和车辆的场景下运行：

```bash
python3 generate_result_images.py \
    --num-images 5 \
    --output-dir result_images \
    --interval 10
```

## 快速修复命令（一键执行）

```bash
# 安装ffmpeg并修复视频
sudo apt install -y ffmpeg && \
ffmpeg -i recordings/field_test_20251124_120342/rgb_video.mp4 \
       -c copy \
       -movflags +faststart \
       recordings/field_test_20251124_120342/rgb_video_repaired.mp4 && \
python3 process_video_file.py \
    recordings/field_test_20251124_120342/rgb_video_repaired.mp4 \
    --num-images 5 \
    --output-dir result_images
```

## 文件说明

- `process_video_file.py` - 从视频文件生成检测结果图
- `fix_video_and_extract.py` - 修复损坏的视频并提取帧
- `generate_result_images.py` - 实时检测生成结果图（需要相机）

## 注意事项

1. **ffmpeg安装**: 如果系统无法联网，可能需要手动安装ffmpeg
2. **视频修复**: 如果视频数据本身损坏，修复可能无效
3. **替代方案**: 如果所有方法都失败，建议重新录制或使用实时检测
