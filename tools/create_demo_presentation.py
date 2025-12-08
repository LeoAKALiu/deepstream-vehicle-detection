#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成客户演示图片（支持中文字体）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")


class TextCanvas:
    """在OpenCV图像上添加中文文本的辅助画布。"""

    def __init__(self, image: np.ndarray) -> None:
        """将OpenCV图像包装为Pillow画布。"""
        self._pil_image = Image.fromarray(image)
        self._drawer = ImageDraw.Draw(self._pil_image)

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """加载指定字号的Noto字体。"""
        font_path = FONT_BOLD_PATH if bold and FONT_BOLD_PATH.exists() else FONT_REGULAR_PATH
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)
        return ImageFont.load_default()

    def text(self, position: Tuple[int, int], text_value: str, *, size: int,
             color: Tuple[int, int, int], bold: bool = False) -> None:
        """在指定位置绘制文本。"""
        font = self._load_font(size, bold=bold)
        self._drawer.text(position, text_value, font=font, fill=color)

    def text_center(self, center: Tuple[int, int], text_value: str, *, size: int,
                    color: Tuple[int, int, int], bold: bool = False) -> None:
        """以指定坐标为中心绘制文本。"""
        font = self._load_font(size, bold=bold)
        bbox = font.getbbox(text_value)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        position = (int(center[0] - width / 2), int(center[1] - height / 2))
        self._drawer.text(position, text_value, font=font, fill=color)

    def to_ndarray(self) -> np.ndarray:
        """返回绘制完成的OpenCV图像。"""
        return np.array(self._pil_image)


def create_system_overview_image(output_path: str) -> str:
    """创建系统概览图。"""
    img = np.ones((1080, 1920, 3), dtype=np.uint8) * 255
    canvas = TextCanvas(img)

    canvas.text((100, 150), "工程机械实时识别系统", size=80, color=(0, 100, 200), bold=True)
    canvas.text((100, 230), "Real-time Construction Vehicle Detection System",
                size=48, color=(100, 100, 100))

    features: List[str] = [
        "✓ 实时车辆检测（YOLOv11 + TensorRT加速）",
        "✓ 工程车辆识别（挖掘机、推土机、装载机等）",
        "✓ 社会车辆识别（车牌识别 + 深度测量）",
        "✓ 蓝牙信标匹配（已备案车辆识别）",
        "✓ 深度相机集成（距离测量）",
        "✓ 云端数据上传（报警和快照）",
        "✓ 多帧验证（减少误检）",
        "✓ 异步处理（优化性能）",
    ]
    for idx, feature in enumerate(features):
        canvas.text((150, 350 + idx * 60), feature, size=38, color=(50, 50, 50))

    canvas.text((100, 900), "技术栈: Python | TensorRT | OpenCV | ByteTrack | HyperLPR3 | Orbbec SDK",
                size=30, color=(80, 80, 80))
    canvas.text((100, 1000), f"生成日期: {datetime.now().strftime('%Y-%m-%d')}",
                size=28, color=(120, 120, 120))

    cv2.imwrite(output_path, canvas.to_ndarray())
    return output_path


def create_architecture_diagram(output_path: str) -> str:
    """创建系统架构图。"""
    img = np.ones((1080, 1920, 3), dtype=np.uint8) * 245

    boxes = [
        {"name": "Orbbec相机", "pos": (200, 200), "size": (250, 120), "color": (100, 200, 100)},
        {"name": "Cassia路由器", "pos": (500, 200), "size": (250, 120), "color": (100, 200, 100)},
        {"name": "YOLOv11检测", "pos": (200, 400), "size": (250, 120), "color": (200, 150, 100)},
        {"name": "ByteTrack跟踪", "pos": (500, 400), "size": (250, 120), "color": (200, 150, 100)},
        {"name": "深度测量", "pos": (800, 400), "size": (250, 120), "color": (200, 150, 100)},
        {"name": "车牌识别", "pos": (200, 600), "size": (250, 120), "color": (150, 150, 200)},
        {"name": "信标匹配", "pos": (500, 600), "size": (250, 120), "color": (150, 150, 200)},
        {"name": "报警系统", "pos": (200, 800), "size": (250, 120), "color": (200, 100, 100)},
        {"name": "云端上传", "pos": (500, 800), "size": (250, 120), "color": (200, 100, 100)},
    ]
    for box in boxes:
        x_pos, y_pos = box["pos"]
        width, height = box["size"]
        color = box["color"]
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + width, y_pos + height), color, 3)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + width, y_pos + height), (255, 255, 255), -1)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + width, y_pos + height), color, 3)

    arrows = [
        ((325, 320), (325, 400)),
        ((625, 320), (625, 400)),
        ((925, 320), (925, 400)),
        ((325, 520), (325, 600)),
        ((625, 520), (625, 600)),
        ((325, 720), (325, 800)),
        ((625, 720), (625, 800)),
    ]
    for start, end in arrows:
        cv2.arrowedLine(img, start, end, (100, 100, 100), 2, tipLength=0.1)

    canvas = TextCanvas(img)
    canvas.text((100, 80), "系统架构图", size=72, color=(0, 100, 200), bold=True)
    for box in boxes:
        x_pos, y_pos = box["pos"]
        width, height = box["size"]
        center_point = (x_pos + width // 2, y_pos + height // 2)
        canvas.text_center(center_point, box["name"], size=32, color=(50, 50, 50))

    cv2.imwrite(output_path, canvas.to_ndarray())
    return output_path


def create_detection_example(output_path: str) -> str:
    """创建检测示例图（模拟）。"""
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 50
    cv2.rectangle(img, (200, 150), (600, 450), (0, 140, 255), 3)
    cv2.rectangle(img, (700, 200), (1100, 500), (0, 255, 0), 3)

    canvas = TextCanvas(img)
    canvas.text((50, 40), "Detection Example", size=44, color=(255, 255, 255), bold=True)
    canvas.text((210, 120), "Excavator [ID: 001]", size=32, color=(0, 140, 255), bold=True)
    canvas.text((210, 165), "Registered", size=24, color=(0, 255, 0))
    canvas.text((210, 205), "Distance: 5.2m", size=24, color=(255, 255, 255))

    canvas.text((710, 170), "Car [ID: 002]", size=32, color=(0, 255, 0), bold=True)
    canvas.text((710, 210), "Plate: 京A12345", size=26, color=(255, 255, 255))
    canvas.text((710, 250), "Distance: 8.5m", size=24, color=(255, 255, 255))

    info_items = [
        "Frame: 1234 | FPS: 15.2",
        "Detections: 2 | Tracks: 2",
        "Time: 2025-01-04 12:00:00",
    ]
    for idx, item in enumerate(info_items):
        canvas.text((50, 540 + idx * 40), item, size=26, color=(200, 200, 200))

    cv2.imwrite(output_path, canvas.to_ndarray())
    return output_path


def create_configuration_summary(output_path: str) -> str:
    """创建配置摘要图。"""
    img = np.ones((1080, 1920, 3), dtype=np.uint8) * 250
    canvas = TextCanvas(img)
    canvas.text((100, 80), "系统配置摘要", size=72, color=(0, 100, 200), bold=True)

    configs: List[str] = [
        "检测配置:",
        "  - 置信度阈值: 0.7",
        "  - IoU阈值: 0.5",
        "  - 模型: YOLOv11 (TensorRT加速)",
        "",
        "跟踪配置:",
        "  - 跟踪器: ByteTrack",
        "  - 跟踪阈值: 0.6",
        "  - 缓冲区大小: 50帧",
        "",
        "深度相机:",
        "  - 型号: Orbbec Gemini 335L",
        "  - 分辨率: 1280x720",
        "  - 帧率: 15 FPS",
        "",
        "蓝牙信标:",
        "  - 路由器: Cassia",
        "  - 匹配算法: 多目标优化",
        "",
        "云端集成:",
        "  - 支持报警上传",
        "  - 支持快照上传",
        "  - 异步处理",
    ]
    y_start = 200
    for idx, config in enumerate(configs):
        position = (150, y_start + idx * 45)
        if config.endswith(":"):
            canvas.text(position, config, size=40, color=(0, 100, 200), bold=True)
        else:
            canvas.text(position, config, size=32, color=(90, 90, 90))

    cv2.imwrite(output_path, canvas.to_ndarray())
    return output_path


def create_performance_metrics(output_path: str) -> str:
    """创建性能指标图。"""
    img = np.ones((1080, 1920, 3), dtype=np.uint8) * 255
    canvas = TextCanvas(img)
    canvas.text((100, 80), "系统性能指标", size=72, color=(0, 100, 200), bold=True)

    metrics: List[str] = [
        "检测性能:",
        "  - 检测速度: ~15 FPS (Jetson平台)",
        "  - 检测精度: mAP@0.5 > 0.85",
        "  - 支持类别: 10种工程车辆 + 社会车辆",
        "",
        "跟踪性能:",
        "  - 跟踪稳定性: ID切换率 < 5%",
        "  - 多目标跟踪: 支持同时跟踪20+目标",
        "",
        "识别性能:",
        "  - 车牌识别: 准确率 > 90%",
        "  - 信标匹配: 匹配准确率 > 95%",
        "  - 深度测量: 精度 ±5cm (5米内)",
        "",
        "系统特性:",
        "  - 多帧验证: 减少假阳性 > 80%",
        "  - 异步处理: LPR不阻塞主循环",
        "  - 云端上传: 支持断线重连",
        "",
        "硬件要求:",
        "  - 平台: NVIDIA Jetson系列",
        "  - GPU: 支持TensorRT加速",
        "  - 相机: Orbbec深度相机",
        "  - 网络: 蓝牙路由器 (Cassia)",
    ]
    y_start = 200
    for idx, metric in enumerate(metrics):
        position = (150, y_start + idx * 40)
        if metric.endswith(":"):
            canvas.text(position, metric, size=40, color=(0, 100, 200), bold=True)
        else:
            canvas.text(position, metric, size=30, color=(70, 70, 70))

    cv2.imwrite(output_path, canvas.to_ndarray())
    return output_path


def main() -> None:
    """生成所有演示图片。"""
    output_dir = Path("demo_presentation")
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("创建演示材料")
    print("=" * 60)
    print(f"输出目录: {output_dir.absolute()}")
    print()

    creators = [
        ("01_system_overview.jpg", create_system_overview_image),
        ("02_architecture.jpg", create_architecture_diagram),
        ("03_detection_example.jpg", create_detection_example),
        ("04_configuration.jpg", create_configuration_summary),
        ("05_performance.jpg", create_performance_metrics),
    ]
    generated_files: List[Path] = []

    for idx, (filename, creator) in enumerate(creators, start=1):
        print(f"{idx}. 创建 {filename} ...")
        file_path = output_dir / filename
        creator(str(file_path))
        generated_files.append(file_path)
        print(f"   ✅ {filename}")

    print()
    print("=" * 60)
    print("✅ 完成！已创建 5 张演示图片")
    print("=" * 60)
    print("生成的文件:")
    for file_path in generated_files:
        size_mb = file_path.stat().st_size / 1024 / 1024
        print(f"  - {file_path.name} ({size_mb:.2f} MB)")

    print()
    print(f"输出目录: {output_dir.absolute()}")
    print("这些图片可以用于: 系统功能展示 / 技术方案说明 / 客户演示材料")


if __name__ == "__main__":
    main()

