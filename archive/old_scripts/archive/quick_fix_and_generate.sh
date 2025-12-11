#!/bin/bash
# 快速修复视频并生成结果图的脚本

set -e

VIDEO_PATH="recordings/field_test_20251124_120342/rgb_video.mp4"
REPAIRED_PATH="recordings/field_test_20251124_120342/rgb_video_repaired.mp4"
OUTPUT_DIR="result_images"

echo "============================================================"
echo "修复视频并生成检测结果图"
echo "============================================================"
echo ""

# 检查视频文件
if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ 视频文件不存在: $VIDEO_PATH"
    exit 1
fi

# 检查ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg未安装，正在安装..."
    sudo apt update
    sudo apt install -y ffmpeg
fi

# 修复视频
echo "步骤1: 修复视频文件..."
if [ -f "$REPAIRED_PATH" ]; then
    echo "⚠️  修复后的视频已存在，跳过修复步骤"
else
    ffmpeg -i "$VIDEO_PATH" \
           -c copy \
           -movflags +faststart \
           "$REPAIRED_PATH" \
           -y
    
    if [ $? -eq 0 ]; then
        echo "✅ 视频修复成功: $REPAIRED_PATH"
    else
        echo "❌ 视频修复失败"
        exit 1
    fi
fi

echo ""
echo "步骤2: 从修复后的视频生成结果图..."
python3 process_video_file.py \
    "$REPAIRED_PATH" \
    --num-images 5 \
    --output-dir "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ 完成！结果图已保存到: $OUTPUT_DIR"
    echo "============================================================"
    ls -lh "$OUTPUT_DIR"/*.jpg 2>/dev/null | head -10
else
    echo ""
    echo "❌ 生成结果图失败"
    exit 1
fi



