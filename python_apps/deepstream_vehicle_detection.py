#!/usr/bin/env python3
"""
DeepStream车辆检测系统
- GPU加速检测（TensorRT）
- NvDCF目标跟踪
- HyperLPR车牌识别
"""

import sys
import time
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import pyds
import numpy as np
import cv2
from collections import defaultdict

try:
    from hyperlpr3 import LicensePlateCN
    HYPERLPR_AVAILABLE = True
    print("✓ HyperLPR可用")
except ImportError:
    HYPERLPR_AVAILABLE = False
    print("⚠ HyperLPR未安装")


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


class VehicleDetectionApp:
    """DeepStream车辆检测应用"""
    
    def __init__(self, source):
        """
        Args:
            source: 输入源（视频文件路径或'camera'）
        """
        self.source = source
        
        # 统计
        self.stats = {
            'construction': defaultdict(int),
            'civilian_plates': [],
            'frame_count': 0,
        }
        
        self.tracked_vehicles = set()  # 已跟踪的vehicle ID
        self.seen_plates = set()
        
        # HyperLPR
        self.lpr = None
        if HYPERLPR_AVAILABLE:
            try:
                self.lpr = LicensePlateCN(detect_level=1, max_num=5)
                print("✓ HyperLPR初始化成功")
            except Exception as e:
                print(f"✗ HyperLPR初始化失败: {e}")
        
        # GStreamer
        Gst.init(None)
    
    def build_pipeline(self):
        """构建GStreamer pipeline"""
        
        print("\n构建DeepStream pipeline...")
        
        # 创建pipeline
        pipeline = Gst.Pipeline()
        
        if not pipeline:
            raise RuntimeError("无法创建pipeline")
        
        # 创建elements
        print("  创建GStreamer elements...")
        
        # Source
        if self.source == 'camera':
            # V4L2相机源
            source = Gst.ElementFactory.make("v4l2src", "source")
            source.set_property('device', '/dev/video0')
        else:
            # 文件源
            source = Gst.ElementFactory.make("filesrc", "source")
            source.set_property('location', self.source)
        
        # H264解析器
        h264parser = Gst.ElementFactory.make("h264parse", "h264-parser")
        
        # 硬件解码器
        decoder = Gst.ElementFactory.make("nvv4l2decoder", "decoder")
        
        # Streammux
        streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
        streammux.set_property('width', 1920)
        streammux.set_property('height', 1080)
        streammux.set_property('batch-size', 1)
        streammux.set_property('batched-push-timeout', 4000000)
        
        # Primary GIE (YOLO推理)
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        pgie.set_property('config-file-path', "../config/config_infer_yolov11.txt")
        
        # Tracker
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        tracker.set_property('tracker-width', 640)
        tracker.set_property('tracker-height', 384)
        tracker.set_property('ll-lib-file', 
            '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so')
        tracker.set_property('ll-config-file', '../config/config_tracker_NvDCF_accuracy.yml')
        tracker.set_property('enable-batch-process', 1)
        tracker.set_property('display-tracking-id', 1)
        
        # 视频转换
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        
        # OSD (On-Screen Display)
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        
        # Sink
        if self.source == 'camera':
            # EGL sink (显示)
            sink = Gst.ElementFactory.make("nveglglessink", "sink")
        else:
            # 文件输出
            nvvidconv2 = Gst.ElementFactory.make("nvvideoconvert", "convertor2")
            capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
            caps = Gst.Caps.from_string("video/x-raw, format=I420")
            capsfilter.set_property("caps", caps)
            
            encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
            encoder.set_property('bitrate', 4000000)
            
            h264parser2 = Gst.ElementFactory.make("h264parse", "h264-parser2")
            
            muxer = Gst.ElementFactory.make("qtmux", "muxer")
            
            sink = Gst.ElementFactory.make("filesink", "filesink")
            output_file = f"output_{int(time.time())}.mp4"
            sink.set_property('location', output_file)
            sink.set_property('sync', 0)
        
        if not all([source, h264parser, decoder, streammux, pgie, tracker, 
                   nvvidconv, nvosd, sink]):
            raise RuntimeError("无法创建所有elements")
        
        print("  ✓ Elements创建成功")
        
        # 添加到pipeline
        pipeline.add(source)
        pipeline.add(h264parser)
        pipeline.add(decoder)
        pipeline.add(streammux)
        pipeline.add(pgie)
        pipeline.add(tracker)
        pipeline.add(nvvidconv)
        pipeline.add(nvosd)
        
        if self.source != 'camera':
            pipeline.add(nvvidconv2)
            pipeline.add(capsfilter)
            pipeline.add(encoder)
            pipeline.add(h264parser2)
            pipeline.add(muxer)
        
        pipeline.add(sink)
        
        # 链接elements
        print("  链接pipeline...")
        
        source.link(h264parser)
        h264parser.link(decoder)
        
        # Decoder -> Streammux需要手动链接pad
        sinkpad = streammux.get_request_pad("sink_0")
        if not sinkpad:
            raise RuntimeError("无法获取streammux sink pad")
        
        srcpad = decoder.get_static_pad("src")
        if not srcpad:
            raise RuntimeError("无法获取decoder src pad")
        
        srcpad.link(sinkpad)
        
        # 链接其余elements
        streammux.link(pgie)
        pgie.link(tracker)
        tracker.link(nvvidconv)
        nvvidconv.link(nvosd)
        
        if self.source == 'camera':
            nvosd.link(sink)
        else:
            nvosd.link(nvvidconv2)
            nvvidconv2.link(capsfilter)
            capsfilter.link(encoder)
            encoder.link(h264parser2)
            h264parser2.link(muxer)
            muxer.link(sink)
        
        print("  ✓ Pipeline构建完成")
        
        return pipeline
    
    def osd_sink_pad_buffer_probe(self, pad, info, u_data):
        """
        OSD sink pad的probe函数
        在这里处理检测结果和跟踪数据
        """
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return Gst.PadProbeReturn.OK
        
        # 获取batch metadata
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break
            
            self.stats['frame_count'] += 1
            frame_number = frame_meta.frame_num
            
            # 遍历对象
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                
                # 获取信息
                class_id = obj_meta.class_id
                object_id = obj_meta.object_id  # 跟踪ID
                confidence = obj_meta.confidence
                
                # 新车辆
                if object_id not in self.tracked_vehicles:
                    self.tracked_vehicles.add(object_id)
                    
                    if class_id in CONSTRUCTION_VEHICLES:
                        vtype, cn_name = CONSTRUCTION_VEHICLES[class_id]
                        self.stats['construction'][vtype] += 1
                        print(f"\n新车辆 ID{object_id}: {cn_name} ({vtype}), 帧{frame_number}")
                    
                    elif class_id in CIVILIAN_VEHICLES and self.lpr:
                        # 社会车辆：尝试识别车牌
                        # 这里需要访问原始图像数据进行ROI裁剪
                        # DeepStream的复杂部分
                        pass
                
                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break
            
            # Display metadata
            display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
            display_meta.num_labels = 1
            py_nvosd_text_params = display_meta.text_params[0]
            
            # 统计信息显示
            stats_text = f"跟踪: {len(self.tracked_vehicles)} | 帧: {frame_number}"
            py_nvosd_text_params.display_text = stats_text
            py_nvosd_text_params.x_offset = 10
            py_nvosd_text_params.y_offset = 12
            py_nvosd_text_params.font_params.font_name = "Serif"
            py_nvosd_text_params.font_params.font_size = 14
            py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 0.0, 1.0)
            py_nvosd_text_params.set_bg_clr = 1
            py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 0.5)
            
            pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
            
            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        
        return Gst.PadProbeReturn.OK
    
    def run(self):
        """运行DeepStream应用"""
        
        print("\n启动DeepStream应用...")
        
        # 构建pipeline
        pipeline = self.build_pipeline()
        
        # 添加probe
        print("  添加probe函数...")
        # 获取nvosd的sink pad
        nvosd = pipeline.get_by_name("onscreendisplay")
        if nvosd:
            nvosd_sink_pad = nvosd.get_static_pad("sink")
            if nvosd_sink_pad:
                nvosd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, 
                                        self.osd_sink_pad_buffer_probe, 0)
                print("  ✓ Probe添加成功")
        
        # 创建主循环
        self.loop = GLib.MainLoop()
        
        # 创建bus
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call)
        
        # 启动
        print("  启动pipeline...")
        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("  ✗ 无法启动pipeline")
            return
        
        print("  ✓ Pipeline运行中...")
        print("\n按Ctrl+C停止\n")
        
        # 主循环
        try:
            self.loop.run()
        except KeyboardInterrupt:
            print("\n用户中断")
        
        # 清理
        pipeline.set_state(Gst.State.NULL)
        
        # 打印统计
        self.print_statistics()
    
    def bus_call(self, bus, message):
        """处理GStreamer bus消息"""
        t = message.type
        if t == Gst.MessageType.EOS:
            print("\n视频结束")
            self.loop.quit()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            print(f"\n警告: {err}")
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"\n错误: {err}")
            print(f"调试信息: {debug}")
            self.loop.quit()
        return True
    
    def print_statistics(self):
        """打印统计结果"""
        print("\n" + "="*70)
        print("DeepStream检测统计")
        print("="*70)
        
        print("\n【工程车辆】")
        if self.stats['construction']:
            total = sum(self.stats['construction'].values())
            print(f"  总数: {total} 辆\n")
            for vtype, count in sorted(self.stats['construction'].items()):
                cn_name = CONSTRUCTION_VEHICLES[[k for k,v in CONSTRUCTION_VEHICLES.items() if v[0]==vtype][0]][1]
                pct = count / total * 100
                print(f"  {cn_name:12s}: {count:4d} 辆 ({pct:5.1f}%)")
        else:
            print("  未检测到")
        
        print("\n【车牌识别】")
        if self.stats['civilian_plates']:
            print(f"  总数: {len(self.stats['civilian_plates'])} 个")
        else:
            print("  未识别到")
        
        print("\n" + "="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='DeepStream车辆检测')
    parser.add_argument('source', help='输入源（视频文件或camera）')
    
    args = parser.parse_args()
    
    print("="*70)
    print("DeepStream车辆检测系统")
    print("="*70)
    print(f"输入: {args.source}")
    print("="*70)
    
    app = VehicleDetectionApp(args.source)
    app.run()


if __name__ == '__main__':
    main()


