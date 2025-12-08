#!/usr/bin/env python3
"""
混合方案：TensorRT GPU推理 + Python后处理
- GPU: TensorRT推理（使用pycuda）
- CPU: YOLO输出解析、ByteTrack跟踪、HyperLPR车牌识别
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict

# TensorRT和CUDA
try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    import tensorrt as trt
    TRT_AVAILABLE = True
    print("✓ TensorRT和PyCUDA可用")
except ImportError as e:
    TRT_AVAILABLE = False
    print(f"✗ TensorRT/PyCUDA不可用: {e}")
    print("  请在容器中运行或使用CPU方案")
    sys.exit(1)

# ByteTrack跟踪
try:
    from byte_tracker import BYTETracker
    BYTETRACK_AVAILABLE = True
    print("✓ ByteTrack可用")
except ImportError:
    BYTETRACK_AVAILABLE = False
    print("⚠ ByteTrack不可用，将使用简单跟踪")

# HyperLPR车牌识别
try:
    from hyperlpr3 import LicensePlateCN
    HYPERLPR_AVAILABLE = True
    print("✓ HyperLPR可用")
except ImportError:
    HYPERLPR_AVAILABLE = False
    print("⚠ HyperLPR不可用，跳过车牌识别")


# 车辆类别
CONSTRUCTION_VEHICLES = {
    0: ('excavator', '挖掘机'),
    1: ('bulldozer', '推土机'),
    2: ('roller', '压路机'),
    3: ('loader', '装载机'),
    4: ('dump-truck', '自卸车'),
    5: ('concrete-mixer', '混凝土搅拌车'),
    6: ('pump-truck', '泵车'),
    7: ('crane', '起重机'),
}

CIVILIAN_VEHICLES = {
    8: ('truck', '卡车'),
    9: ('car', '轿车'),
}

ALL_CLASSES = {**CONSTRUCTION_VEHICLES, **CIVILIAN_VEHICLES}

# 每个类别的颜色（BGR格式）
CLASS_COLORS = {
    0: (0, 255, 0),      # 挖掘机 - 绿色
    1: (0, 255, 127),    # 推土机 - 春绿色
    2: (0, 255, 255),    # 压路机 - 黄色
    3: (0, 200, 0),      # 装载机 - 深绿色
    4: (0, 180, 180),    # 自卸车 - 橄榄绿
    5: (0, 220, 100),    # 混凝土搅拌车 - 黄绿色
    6: (0, 160, 200),    # 泵车 - 金黄色
    7: (100, 255, 100),  # 起重机 - 浅绿色
    8: (255, 0, 0),      # 卡车 - 蓝色
    9: (255, 100, 200),  # 轿车 - 粉蓝色
}


class TensorRTInference:
    """TensorRT推理引擎"""
    
    def __init__(self, engine_path, input_shape=(640, 640)):
        """
        Args:
            engine_path: TensorRT引擎文件路径
            input_shape: 输入图像大小 (height, width)
        """
        self.engine_path = engine_path
        self.input_shape = input_shape
        
        # 加载引擎
        print(f"\n加载TensorRT引擎: {engine_path}")
        self.logger = trt.Logger(trt.Logger.WARNING)
        
        with open(engine_path, 'rb') as f:
            engine_data = f.read()
        
        runtime = trt.Runtime(self.logger)
        self.engine = runtime.deserialize_cuda_engine(engine_data)
        self.context = self.engine.create_execution_context()
        
        # 获取输入输出信息（兼容TensorRT 10.x）
        # TensorRT 10.x使用新API
        if hasattr(self.engine, 'get_tensor_name'):
            # TensorRT 10.x
            self.input_name = self.engine.get_tensor_name(0)
            self.output_name = self.engine.get_tensor_name(1)
            self.input_shape_trt = self.engine.get_tensor_shape(self.input_name)
            self.output_shape = self.engine.get_tensor_shape(self.output_name)
        else:
            # TensorRT 8.x
            self.input_name = self.engine.get_binding_name(0)
            self.output_name = self.engine.get_binding_name(1)
            self.input_shape_trt = self.engine.get_binding_shape(0)
            self.output_shape = self.engine.get_binding_shape(1)
        
        print(f"  输入: {self.input_name} {list(self.input_shape_trt)}")
        print(f"  输出: {self.output_name} {list(self.output_shape)}")
        
        # 分配GPU内存
        self.input_size = trt.volume(self.input_shape_trt) * np.dtype(np.float32).itemsize
        self.output_size = trt.volume(self.output_shape) * np.dtype(np.float32).itemsize
        
        self.d_input = cuda.mem_alloc(self.input_size)
        self.d_output = cuda.mem_alloc(self.output_size)
        
        self.bindings = [int(self.d_input), int(self.d_output)]
        self.stream = cuda.Stream()
        
        print("✓ TensorRT引擎初始化完成")
    
    def preprocess(self, image):
        """
        预处理图像
        Args:
            image: OpenCV图像 (BGR)
        Returns:
            preprocessed: 预处理后的图像 (1, 3, 640, 640)
            ratio: 缩放比例
            (dw, dh): padding
        """
        h, w = image.shape[:2]
        target_h, target_w = self.input_shape
        
        # 计算缩放比例（保持宽高比）
        ratio = min(target_w / w, target_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        
        # 缩放
        resized = cv2.resize(image, (new_w, new_h))
        
        # 填充到目标大小
        dw = (target_w - new_w) // 2
        dh = (target_h - new_h) // 2
        
        padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        padded[dh:dh+new_h, dw:dw+new_w] = resized
        
        # BGR -> RGB, HWC -> CHW, normalize
        image_rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        image_chw = np.transpose(image_rgb, (2, 0, 1))
        image_norm = image_chw.astype(np.float32) / 255.0
        image_batch = np.expand_dims(image_norm, axis=0)
        
        return np.ascontiguousarray(image_batch), ratio, (dw, dh)
    
    def infer(self, image_batch):
        """
        执行推理
        Args:
            image_batch: 预处理后的图像 (1, 3, 640, 640)
        Returns:
            output: 推理结果 (1, 14, 8400)
        """
        # 复制输入到GPU
        cuda.memcpy_htod_async(self.d_input, image_batch, self.stream)
        
        # 执行推理（兼容TensorRT 10.x）
        if hasattr(self.context, 'execute_async_v3'):
            # TensorRT 10.x使用新API
            self.context.set_tensor_address(self.input_name, int(self.d_input))
            self.context.set_tensor_address(self.output_name, int(self.d_output))
            self.context.execute_async_v3(stream_handle=self.stream.handle)
        else:
            # TensorRT 8.x使用旧API
            self.context.execute_async_v2(
                bindings=self.bindings,
                stream_handle=self.stream.handle
            )
        
        # 复制输出到CPU
        output = np.empty(self.output_shape, dtype=np.float32)
        cuda.memcpy_dtoh_async(output, self.d_output, self.stream)
        
        self.stream.synchronize()
        
        return output
    
    def postprocess(self, output, ratio, pad, conf_threshold=0.25, iou_threshold=0.45, debug=False):
        """
        后处理YOLOv11输出
        Args:
            output: (1, 14, 8400) - [x, y, w, h, conf, class0...class9]
            ratio: 缩放比例
            pad: (dw, dh) padding
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU阈值
            debug: 是否打印调试信息
        Returns:
            detections: List of (x1, y1, x2, y2, conf, class_id)
        """
        output = output[0]  # (14, 8400)
        
        if debug:
            print(f"\n[调试] 原始输出shape: {output.shape}")
            print(f"[调试] 输出范围: [{output.min():.3f}, {output.max():.3f}]")
        
        # 转置为 (8400, 14)
        predictions = output.transpose()  # (8400, 14)
        
        # YOLOv11输出格式: [x, y, w, h, class0, class1, ..., class9]
        # 注意：YOLOv11可能已经没有单独的objectness，直接是class scores
        boxes_xywh = predictions[:, :4]  # (8400, 4) [x, y, w, h]
        class_scores = predictions[:, 4:]  # (8400, 10) 直接的类别分数
        
        if debug:
            print(f"[调试] boxes范围: [{boxes_xywh.min():.3f}, {boxes_xywh.max():.3f}]")
            print(f"[调试] class_scores范围: [{class_scores.min():.3f}, {class_scores.max():.3f}]")
            print(f"[调试] class_scores前5个最大值: {np.sort(class_scores.flatten())[-5:]}")
        
        # 直接使用class scores
        class_ids = np.argmax(class_scores, axis=1)  # (8400,)
        confidences = np.max(class_scores, axis=1)  # (8400,)
        
        if debug:
            print(f"[调试] 最大置信度: {confidences.max():.3f}")
            print(f"[调试] >0.1的数量: {(confidences > 0.1).sum()}")
            print(f"[调试] >0.25的数量: {(confidences > 0.25).sum()}")
            print(f"[调试] >0.5的数量: {(confidences > 0.5).sum()}")
        
        # 过滤低置信度
        mask = confidences > conf_threshold
        boxes_xywh = boxes_xywh[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        
        if debug:
            print(f"[调试] 过滤后剩余: {len(boxes_xywh)} 个检测")
        
        if len(boxes_xywh) == 0:
            return []
        
        # xywh -> xyxy
        boxes_xyxy = np.zeros_like(boxes_xywh)
        boxes_xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x1
        boxes_xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y1
        boxes_xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x2
        boxes_xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y2
        
        # 还原到原图坐标
        dw, dh = pad
        boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - dw) / ratio
        boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - dh) / ratio
        
        # NMS
        indices = self.nms(boxes_xyxy, confidences, iou_threshold)
        
        detections = []
        for i in indices:
            x1, y1, x2, y2 = boxes_xyxy[i]
            conf = confidences[i]
            cls = class_ids[i]
            detections.append((x1, y1, x2, y2, conf, cls))
        
        return detections
    
    @staticmethod
    def nms(boxes, scores, iou_threshold):
        """
        Non-Maximum Suppression
        Args:
            boxes: (N, 4) [x1, y1, x2, y2]
            scores: (N,)
            iou_threshold: IoU阈值
        Returns:
            indices: 保留的索引
        """
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return keep


class VehicleDetectionSystem:
    """车辆检测系统（混合方案）"""
    
    def __init__(self, engine_path, video_source, no_display=False, 
                 cassia_config=None, use_depth_camera=False):
        """
        Args:
            engine_path: TensorRT引擎路径
            video_source: 视频文件路径或'camera'
            no_display: 是否禁用显示窗口
            cassia_config: Cassia配置 {'mode': 'local', 'router_ip': x}
            use_depth_camera: 是否使用深度相机
        """
        self.engine_path = engine_path
        self.video_source = video_source
        self.no_display = no_display
        self.use_depth_camera = use_depth_camera
        
        # 初始化TensorRT
        self.trt_engine = TensorRTInference(engine_path)
        
        # 初始化Orbbec深度相机
        self.depth_camera = None
        if use_depth_camera:
            try:
                from orbbec_depth import OrbbecDepthCamera
                self.depth_camera = OrbbecDepthCamera()
                if self.depth_camera.start():
                    print("✓ Orbbec深度相机启动成功")
                else:
                    print("✗ Orbbec深度相机启动失败，使用简单估计")
                    self.depth_camera = None
            except Exception as e:
                print(f"✗ Orbbec深度相机初始化失败: {e}")
                print("  将使用简单距离估计")
                self.depth_camera = None
        
        # 初始化HyperLPR
        self.lpr = None
        if HYPERLPR_AVAILABLE:
            try:
                self.lpr = LicensePlateCN(detect_level=1, max_num=5)
                print("✓ HyperLPR初始化成功")
            except Exception as e:
                print(f"✗ HyperLPR初始化失败: {e}")
        
        # 初始化Cassia信标客户端
        self.beacon_client = None
        if cassia_config:
            try:
                if cassia_config.get('mode') == 'local':
                    # 本地路由器模式
                    from cassia_local_client import CassiaLocalClient
                    self.beacon_client = CassiaLocalClient(
                        cassia_config['router_ip'],
                        cassia_config.get('username'),
                        cassia_config.get('password')
                    )
                    self.beacon_client.start()
                    print(f"✓ Cassia本地路由器启动成功 ({cassia_config['router_ip']})")
                else:
                    # AC模式
                    from cassia_beacon_client import CassiaBeaconClient
                    self.beacon_client = CassiaBeaconClient(
                        cassia_config['ac_url'],
                        cassia_config['key'],
                        cassia_config['secret'],
                        cassia_config['router_mac']
                    )
                    self.beacon_client.start()
                    print("✓ Cassia信标客户端启动成功（AC模式）")
            except Exception as e:
                print(f"✗ Cassia信标客户端启动失败: {e}")
                print("  将使用模拟模式（所有工程车辆显示'未备案'）")
        
        # 统计
        self.stats = {
            'construction_verified': [],  # 已验证的工程车辆（信标匹配）
            'construction_unverified': [],  # 未备案的工程车辆
            'civilian_plates': [],  # 识别到的车牌
            'frame_count': 0,
            'fps': 0,
        }
        
        # 跟踪状态
        self.tracked_vehicles = {}  # {track_id: {'bbox': [x1,y1,x2,y2], 'class_id': x, 'first_frame': x, 'last_frame': x, 'processed': bool}}
        self.next_track_id = 1
        self.iou_threshold = 0.3  # IoU阈值用于匹配
        self.max_disappeared = 30  # 最大消失帧数
        self.process_distance_threshold = 50  # 距离变化超过50像素才重新处理（避免重复）
    
    def process_video(self, output_path=None):
        """处理视频"""
        
        # 打开视频
        if self.video_source == 'camera':
            cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            print(f"✗ 无法打开视频: {self.video_source}")
            return
        
        fps_cap = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"\n视频信息:")
        print(f"  分辨率: {width}x{height}")
        print(f"  帧率: {fps_cap:.2f} FPS")
        print(f"  总帧数: {total_frames}")
        print(f"\n开始处理...")
        
        # 输出视频（可选）
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps_cap, (width, height))
        
        # 性能统计
        frame_times = []
        start_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_start = time.time()
                
                # 统计
                frame_time = time.time() - frame_start
                frame_times.append(frame_time)
                self.stats['frame_count'] += 1
                
                # TensorRT推理
                input_batch, ratio, pad = self.trt_engine.preprocess(frame)
                output = self.trt_engine.infer(input_batch)
                
                # 第一帧输出调试信息
                debug = (self.stats['frame_count'] == 1)
                detections = self.trt_engine.postprocess(output, ratio, pad, debug=debug)
                
                # 前几帧显示检测数量
                if self.stats['frame_count'] <= 10:
                    print(f"  帧{self.stats['frame_count']}: {len(detections)} 个检测")
                
                # IoU跟踪 + 信标匹配 + 车牌识别（返回带track_id的检测）
                tracked_detections = self.iou_tracking(detections, frame)
                
                # 计算FPS
                if len(frame_times) > 30:
                    frame_times = frame_times[-30:]
                avg_fps = 1.0 / np.mean(frame_times)
                self.stats['fps'] = avg_fps
                
                # 绘制结果和FPS
                self.draw_results(frame, tracked_detections, avg_fps)
                
                # 写入输出
                if writer:
                    writer.write(frame)
                
                # 显示（如果启用）
                if not self.no_display:
                    cv2.imshow('TensorRT Vehicle Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # 进度
                if self.stats['frame_count'] % 100 == 0:
                    elapsed = time.time() - start_time
                    print(f"  已处理 {self.stats['frame_count']}/{total_frames} 帧, "
                          f"平均 {avg_fps:.1f} FPS, 用时 {elapsed:.1f}s")
        
        except KeyboardInterrupt:
            print("\n用户中断")
        
        finally:
            cap.release()
            if writer:
                writer.release()
            cv2.destroyAllWindows()
            
            # 停止信标客户端
            if self.beacon_client:
                self.beacon_client.stop()
            
            # 停止深度相机
            if self.depth_camera:
                self.depth_camera.stop()
            
            # 打印统计
            self.print_statistics()
    
    @staticmethod
    def compute_iou(box1, box2):
        """计算两个bbox的IoU"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 计算交集
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        inter_area = (x2_i - x1_i) * (y2_i - y1_i)
        
        # 计算并集
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def calculate_distance(self, bbox, frame_shape):
        """
        计算车辆到相机的距离
        Args:
            bbox: [x1, y1, x2, y2]
            frame_shape: 帧的shape
        Returns:
            distance: 距离（米）
            bottom_center: bbox底边中点坐标 (x, y)
        """
        x1, y1, x2, y2 = bbox
        # bbox底边中点
        bottom_center_x = int((x1 + x2) / 2)
        bottom_center_y = int(y2)
        
        # 如果有深度相机，使用真实深度
        if self.depth_camera:
            depth = self.depth_camera.get_average_depth_at_bbox_bottom(bbox, radius=5)
            if depth is not None:
                return depth, (bottom_center_x, bottom_center_y)
        
        # 否则使用简单的bbox高度反比例估计
        bbox_height = y2 - y1
        estimated_distance = 1000 / max(bbox_height, 1)  # 简单反比例
        
        return estimated_distance, (bottom_center_x, bottom_center_y)
    
    def match_beacon(self, distance, class_id):
        """
        匹配蓝牙信标
        Args:
            distance: 估计距离（米）
            class_id: 车辆类别
        Returns:
            beacon_id: 信标MAC地址（如果匹配到），否则None
        """
        if self.beacon_client is None:
            # 未启用信标客户端
            return None
        
        # 查找最接近的信标
        beacon = self.beacon_client.find_nearest_beacon(distance, tolerance=2.5)
        
        if beacon:
            return beacon['mac']
        
        return None
    
    def recognize_plate(self, frame, bbox):
        """
        识别车牌（HyperLPR）
        Args:
            frame: 原始帧
            bbox: [x1, y1, x2, y2]
        Returns:
            plate: 车牌号，None if 识别失败
        """
        if self.lpr is None:
            return None
        
        try:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            # 扩大ROI（车牌通常在车辆下部）
            h, w = frame.shape[:2]
            y1 = max(0, y1)
            y2 = min(h, y2)
            x1 = max(0, x1)
            x2 = min(w, x2)
            
            roi = frame[y1:y2, x1:x2]
            
            if roi.size == 0:
                return None
            
            # HyperLPR识别
            results = self.lpr.simple_recognize(roi)
            
            if results and len(results) > 0:
                plate, confidence = results[0]
                if confidence > 0.7:  # 置信度阈值
                    return plate
        except Exception as e:
            pass
        
        return None
    
    def iou_tracking(self, detections, frame):
        """
        基于IoU的跟踪 + 工程车辆信标匹配 + 社会车辆车牌识别
        """
        current_frame = self.stats['frame_count']
        
        # 清理消失太久的跟踪
        to_remove = []
        for track_id, track_info in self.tracked_vehicles.items():
            if current_frame - track_info['last_frame'] > self.max_disappeared:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.tracked_vehicles[track_id]
        
        # 匹配当前检测与已有跟踪
        tracked_detections = []
        matched_tracks = set()
        new_detections = []
        
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            cls = int(cls)
            det_bbox = [x1, y1, x2, y2]
            
            # 寻找最佳匹配
            best_iou = 0
            best_track_id = None
            
            for track_id, track_info in self.tracked_vehicles.items():
                if track_info['class_id'] != cls:
                    continue
                if track_id in matched_tracks:
                    continue
                
                iou = self.compute_iou(det_bbox, track_info['bbox'])
                
                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id
            
            if best_track_id is not None:
                # 匹配到已有跟踪，更新
                self.tracked_vehicles[best_track_id]['bbox'] = det_bbox
                self.tracked_vehicles[best_track_id]['last_frame'] = current_frame
                matched_tracks.add(best_track_id)
                tracked_detections.append((x1, y1, x2, y2, conf, cls, best_track_id))
            else:
                # 新检测
                new_detections.append((det_bbox, cls, conf))
        
        # 处理新检测
        for det_bbox, cls, conf in new_detections:
            track_id = self.next_track_id
            self.next_track_id += 1
            
            self.tracked_vehicles[track_id] = {
                'bbox': det_bbox,
                'class_id': cls,
                'first_frame': current_frame,
                'last_frame': current_frame,
                'processed': False,
                'beacon_id': None,
                'plate': None,
            }
            
            # 工程车辆：距离计算 + 信标匹配
            if cls in CONSTRUCTION_VEHICLES:
                distance, bottom_center = self.calculate_distance(det_bbox, frame.shape)
                beacon_id = self.match_beacon(distance, cls)
                
                vtype, cn_name = CONSTRUCTION_VEHICLES[cls]
                
                if beacon_id:
                    # 匹配到信标
                    self.tracked_vehicles[track_id]['beacon_id'] = beacon_id
                    self.stats['construction_verified'].append({
                        'track_id': track_id,
                        'type': vtype,
                        'beacon_id': beacon_id,
                        'frame': current_frame
                    })
                    print(f"  ✓ 已备案车辆 ID{track_id}: {cn_name}, 信标={beacon_id}")
                else:
                    # 未匹配到信标 - 未备案车辆
                    self.stats['construction_unverified'].append({
                        'track_id': track_id,
                        'type': vtype,
                        'frame': current_frame
                    })
                    print(f"  ⚠ 未备案车辆入场! ID{track_id}: {cn_name}, 帧{current_frame}")
                
                self.tracked_vehicles[track_id]['processed'] = True
            
            # 社会车辆：车牌识别
            elif cls in CIVILIAN_VEHICLES:
                plate = self.recognize_plate(frame, det_bbox)
                
                vtype, cn_name = CIVILIAN_VEHICLES[cls]
                
                if plate:
                    self.tracked_vehicles[track_id]['plate'] = plate
                    self.stats['civilian_plates'].append({
                        'track_id': track_id,
                        'plate': plate,
                        'type': vtype,
                        'frame': current_frame
                    })
                    print(f"  🚗 社会车辆 ID{track_id}: {cn_name}, 车牌={plate}")
                else:
                    print(f"  🚗 社会车辆 ID{track_id}: {cn_name}, 车牌识别失败")
                
                self.tracked_vehicles[track_id]['processed'] = True
            
            # 添加到结果
            x1, y1, x2, y2 = det_bbox
            tracked_detections.append((x1, y1, x2, y2, conf, cls, track_id))
        
        return tracked_detections
    
    def draw_results(self, frame, detections, fps=0):
        """绘制检测结果（纯OpenCV，快速可靠）"""
        # 绘制所有检测框和标签
        for det in detections:
            # 解包（带track_id）
            if len(det) == 7:
                x1, y1, x2, y2, conf, cls, track_id = det
            else:
                x1, y1, x2, y2, conf, cls = det
                track_id = None
            
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cls = int(cls)
            
            # 获取颜色和标签（使用英文）
            color = CLASS_COLORS.get(cls, (128, 128, 128))
            
            if cls in CONSTRUCTION_VEHICLES:
                label_en, label_cn = CONSTRUCTION_VEHICLES[cls]
            elif cls in CIVILIAN_VEHICLES:
                label_en, label_cn = CIVILIAN_VEHICLES[cls]
            else:
                label_en = f"class{cls}"
            
            # 绘制框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            
            # 绘制标签（ID + 类型 + 置信度）
            if track_id is not None:
                label_text = f"ID{track_id} {label_en} {conf:.2f}"
            else:
                label_text = f"{label_en} {conf:.2f}"
            
            # 标签背景
            (w, h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - 25), (x1 + w + 10, y1), color, -1)
            
            # 标签文字
            cv2.putText(frame, label_text, (x1 + 5, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 绘制统计信息（右上角）
        stats_text = f"Tracked: {len(self.tracked_vehicles)}"
        cv2.rectangle(frame, (frame.shape[1] - 200, 5), (frame.shape[1] - 5, 40), (0, 0, 0), -1)
        cv2.putText(frame, stats_text, (frame.shape[1] - 195, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # 绘制FPS（左上角）
        if fps > 0:
            fps_text = f"FPS: {fps:.1f}"
            cv2.rectangle(frame, (5, 5), (150, 40), (0, 0, 0), -1)
            cv2.putText(frame, fps_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    def print_statistics(self):
        """打印统计结果"""
        print("\n" + "="*70)
        print("TensorRT车辆检测统计")
        print("="*70)
        
        print(f"\n总帧数: {self.stats['frame_count']}")
        print(f"平均FPS: {self.stats['fps']:.1f}")
        
        print("\n【工程车辆 - 已备案】")
        if self.stats['construction_verified']:
            print(f"  总数: {len(self.stats['construction_verified'])} 辆\n")
            for item in self.stats['construction_verified']:
                vtype = item['type']
                beacon_id = item['beacon_id']
                track_id = item['track_id']
                print(f"  ID{track_id}: {vtype:15s} 信标={beacon_id}")
        else:
            print("  无")
        
        print("\n【工程车辆 - 未备案（警告）】")
        if self.stats['construction_unverified']:
            print(f"  总数: {len(self.stats['construction_unverified'])} 辆\n")
            for item in self.stats['construction_unverified']:
                vtype = item['type']
                track_id = item['track_id']
                frame = item['frame']
                print(f"  ⚠ ID{track_id}: {vtype:15s} 帧{frame}")
        else:
            print("  无")
        
        print("\n【社会车辆 - 车牌识别】")
        if self.stats['civilian_plates']:
            print(f"  总数: {len(self.stats['civilian_plates'])} 辆\n")
            for item in self.stats['civilian_plates']:
                track_id = item['track_id']
                plate = item['plate']
                vtype = item['type']
                print(f"  ID{track_id}: {vtype:10s} 车牌={plate}")
        else:
            print("  无")
        
        print("\n" + "="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TensorRT车辆检测（混合方案）')
    parser.add_argument('video', help='视频文件路径或camera')
    parser.add_argument('--engine', default='models/yolov11.engine',
                       help='TensorRT引擎路径')
    parser.add_argument('--output', help='输出视频路径（可选）')
    parser.add_argument('--no-display', action='store_true',
                       help='不显示窗口（SSH模式）')
    
    # Cassia信标配置
    parser.add_argument('--cassia-local', help='Cassia本地路由器IP，如 192.168.40.1')
    parser.add_argument('--cassia-user', help='Cassia路由器用户名（可选）')
    parser.add_argument('--cassia-pass', help='Cassia路由器密码（可选）')
    
    # AC模式（高级）
    parser.add_argument('--cassia-ac', help='Cassia AC地址，如 http://192.168.1.100')
    parser.add_argument('--cassia-key', help='Cassia开发者密钥')
    parser.add_argument('--cassia-secret', help='Cassia开发者密码')
    parser.add_argument('--cassia-router', help='Cassia路由器MAC地址')
    
    # 深度相机
    parser.add_argument('--use-depth', action='store_true',
                       help='使用Orbbec深度相机计算距离')
    
    args = parser.parse_args()
    
    print("="*70)
    print("工程机械实时识别系统")
    print("="*70)
    print("GPU: TensorRT推理")
    print("CPU: YOLO后处理、跟踪")
    
    # Cassia配置
    cassia_config = None
    if args.cassia_local:
        # 本地路由器模式
        cassia_config = {
            'mode': 'local',
            'router_ip': args.cassia_local,
            'username': args.cassia_user,
            'password': args.cassia_pass
        }
        print(f"信标: Cassia本地路由器 ({args.cassia_local})")
    elif args.cassia_ac and args.cassia_key and args.cassia_secret and args.cassia_router:
        # AC模式
        cassia_config = {
            'mode': 'ac',
            'ac_url': args.cassia_ac,
            'key': args.cassia_key,
            'secret': args.cassia_secret,
            'router_mac': args.cassia_router
        }
        print("信标: Cassia蓝牙信标（AC模式）")
    else:
        print("信标: 未配置（所有工程车辆将显示'未备案'）")
    
    if args.use_depth:
        print("深度: Orbbec深度相机（已启用）")
    else:
        print("深度: 简单估计（基于bbox高度）")
    
    print("车牌: HyperLPR" if HYPERLPR_AVAILABLE else "车牌: 未安装")
    print("="*70)
    
    if args.no_display:
        print("模式: 无显示（SSH模式）")
    
    system = VehicleDetectionSystem(
        args.engine, 
        args.video, 
        args.no_display,
        cassia_config=cassia_config,
        use_depth_camera=args.use_depth
    )
    system.process_video(args.output)


if __name__ == '__main__':
    main()

