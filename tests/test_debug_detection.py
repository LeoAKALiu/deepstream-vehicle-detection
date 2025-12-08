#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本：显示所有检测到的物体
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_apps'))

import cv2
import numpy as np
import time
from collections import defaultdict
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

from orbbec_depth import OrbbecDepthCamera

# 自定义模型类别（工程车辆检测）
CUSTOM_CLASSES = {
    0: 'excavator',       # 挖掘机
    1: 'bulldozer',       # 推土机
    2: 'roller',          # 压路机
    3: 'loader',          # 装载机
    4: 'dump-truck',      # 自卸车
    5: 'concrete-mixer',  # 混凝土搅拌车
    6: 'pump-truck',      # 泵车
    7: 'truck',           # 卡车
    8: 'crane',           # 起重机
    9: 'car',             # 小汽车
}

class TensorRTInference:
    def __init__(self, engine_path):
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        
        # 获取输入输出
        self.input_shape = None
        self.output_shape = None
        
        if hasattr(self.engine, 'get_binding_name'):
            for i in range(self.engine.num_bindings):
                shape = self.engine.get_binding_shape(i)
                if self.engine.binding_is_input(i):
                    self.input_shape = shape
                else:
                    self.output_shape = shape
        else:
            for i in range(self.engine.num_io_tensors):
                name = self.engine.get_tensor_name(i)
                shape = self.engine.get_tensor_shape(name)
                if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                    self.input_shape = shape
                else:
                    self.output_shape = shape
        
        self.input_buffer = cuda.mem_alloc(trt.volume(self.input_shape) * np.dtype(np.float32).itemsize)
        self.output_buffer = cuda.mem_alloc(trt.volume(self.output_shape) * np.dtype(np.float32).itemsize)
        self.stream = cuda.Stream()
    
    def preprocess(self, image):
        input_h, input_w = self.input_shape[2], self.input_shape[3]
        resized = cv2.resize(image, (input_w, input_h))
        input_data = resized.astype(np.float32) / 255.0
        input_data = np.transpose(input_data, (2, 0, 1))
        input_data = np.expand_dims(input_data, axis=0)
        return np.ascontiguousarray(input_data)
    
    def infer(self, input_data):
        cuda.memcpy_htod_async(self.input_buffer, input_data, self.stream)
        
        if hasattr(self.context, 'execute_async_v2'):
            self.context.execute_async_v2(
                bindings=[int(self.input_buffer), int(self.output_buffer)],
                stream_handle=self.stream.handle
            )
        else:
            self.context.set_tensor_address(self.engine.get_tensor_name(0), int(self.input_buffer))
            self.context.set_tensor_address(self.engine.get_tensor_name(1), int(self.output_buffer))
            self.context.execute_async_v3(stream_handle=self.stream.handle)
        
        output = np.empty(self.output_shape, dtype=np.float32)
        cuda.memcpy_dtoh_async(output, self.output_buffer, self.stream)
        self.stream.synchronize()
        return output
    
    def postprocess(self, output, conf_threshold=0.3, iou_threshold=0.4):
        """降低置信度阈值到0.3"""
        predictions = output[0].T
        boxes = predictions[:, :4]
        scores = predictions[:, 4:]
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)
        
        mask = confidences > conf_threshold
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        
        x_center, y_center, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        x1 = x_center - w / 2
        y1 = y_center - h / 2
        x2 = x_center + w / 2
        y2 = y_center + h / 2
        boxes = np.stack([x1, y1, x2, y2], axis=1)
        
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            confidences.tolist(),
            conf_threshold,
            iou_threshold
        )
        
        if len(indices) > 0:
            indices = indices.flatten()
            return boxes[indices], confidences[indices], class_ids[indices]
        
        return np.array([]), np.array([]), np.array([])


def main():
    print("="*70)
    print("调试模式：显示所有检测结果")
    print("="*70)
    
    # 加载模型
    print("\n加载TensorRT引擎...")
    inference = TensorRTInference('models/custom_yolo.engine')
    print(f"✓ 引擎加载成功")
    print(f"  输入: {inference.input_shape}")
    print(f"  输出: {inference.output_shape}")
    
    # 启动相机
    print("\n启动Orbbec相机...")
    camera = OrbbecDepthCamera()
    camera.start()
    time.sleep(2)
    print("✓ 相机启动成功")
    
    print("\n按 'q' 退出")
    print("="*70)
    
    detection_stats = defaultdict(int)
    frame_count = 0
    fps_start = time.time()
    
    try:
        while True:
            frame = camera.get_color_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # 转换RGB->BGR for display
            display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # 推理
            input_data = inference.preprocess(frame)
            output = inference.infer(input_data)
            boxes, confidences, class_ids = inference.postprocess(output, conf_threshold=0.3)
            
            # 绘制所有检测
            h, w = frame.shape[:2]
            input_h, input_w = inference.input_shape[2], inference.input_shape[3]
            
            detected_classes = set()
            for box, conf, class_id in zip(boxes, confidences, class_ids):
                x1 = int(box[0] * w / input_w)
                y1 = int(box[1] * h / input_h)
                x2 = int(box[2] * w / input_w)
                y2 = int(box[3] * h / input_h)
                
                class_name = CUSTOM_CLASSES.get(class_id, f"unknown_{class_id}")
                detected_classes.add(class_name)
                detection_stats[class_name] += 1
                
                # 不同颜色
                if class_name in ['truck', 'bus']:
                    color = (0, 140, 255)  # 橙色 - 可能的工程车
                elif class_name == 'car':
                    color = (0, 255, 0)    # 绿色 - 社会车辆
                else:
                    color = (255, 0, 0)    # 蓝色 - 其他
                
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name} {conf:.2f}"
                cv2.putText(display_frame, label, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # FPS
            frame_count += 1
            if frame_count % 10 == 0:
                elapsed = time.time() - fps_start
                fps = 10 / elapsed
                fps_start = time.time()
            else:
                fps = 0
            
            if fps > 0:
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示当前帧检测到的类别
            if detected_classes:
                y_pos = 60
                for cls in detected_classes:
                    cv2.putText(display_frame, cls, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    y_pos += 25
            
            cv2.imshow('Detection Debug', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        
        # 统计
        print("\n" + "="*70)
        print("检测统计")
        print("="*70)
        if detection_stats:
            for cls, count in sorted(detection_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cls}: {count}次")
        else:
            print("  未检测到任何物体")
        
        print("\n" + "="*70)
        print("COCO数据集说明")
        print("="*70)
        print("""
COCO数据集包含的车辆类别:
  ✓ car      - 小汽车
  ✓ truck    - 卡车 (可能识别为工程车)
  ✓ bus      - 公交车 (可能识别为工程车)
  ✓ motorcycle - 摩托车
  ✓ bicycle  - 自行车

不包含的类别:
  ✗ excavator   - 挖掘机
  ✗ bulldozer   - 推土机
  ✗ crane       - 起重机
  ✗ concrete mixer - 混凝土搅拌车

建议:
  1. 使用truck图片测试（更可能被识别）
  2. 如需准确识别工程机械，需要用专门数据集重新训练
        """)


if __name__ == '__main__':
    main()

