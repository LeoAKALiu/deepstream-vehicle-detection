# 生成检测结果图使用说明

## 用途
当视频文件损坏无法播放时，可以运行检测算法实时生成带检测框的结果图，用于客户展示。

## 使用方法

### 基本用法
```bash
python3 generate_result_images.py
```

### 参数说明
```bash
python3 generate_result_images.py \
    --output-dir result_images \    # 输出目录（默认: result_images）
    --num-images 5 \                 # 需要生成的图片数量（默认: 5）
    --interval 10 \                  # 捕获间隔（秒，默认: 10）
    --min-detections 1 \             # 最少检测目标数才保存（默认: 1）
    --max-wait 300 \                 # 最大等待时间（秒，默认: 300）
    --config config.yaml             # 配置文件路径（可选）
```

### 示例
```bash
# 生成10张图片，每5秒捕获一次
python3 generate_result_images.py -n 10 -i 5

# 指定输出目录
python3 generate_result_images.py -o /tmp/detection_results -n 3
```

## 工作原理
1. 初始化检测系统（相机、模型等）
2. 开始实时检测
3. 当检测到目标时，自动保存带检测框的结果图
4. 达到指定数量或超时后停止

## 输出文件
- 文件格式: JPG
- 文件命名: `detection_result_01_YYYYMMDD_HHMMSS.jpg`
- 包含内容: 原始帧 + 检测框 + 标签 + 跟踪ID

## 注意事项
- 确保相机已连接
- 确保场景中有车辆（工程车辆或社会车辆）
- 按 Ctrl+C 可随时停止
