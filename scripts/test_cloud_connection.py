#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端服务器联调测试脚本
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "jetson-client"))

try:
    from config import CloudConfig
    from cloud_client import CloudClient
    from detection_result import DetectionResult
    from main_integration import SentinelIntegration
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装 jetson-client 模块")
    sys.exit(1)


def test_health_check(client: CloudClient) -> bool:
    """测试健康检查"""
    print("\n" + "="*70)
    print("【测试1】健康检查")
    print("="*70)
    
    try:
        result = client.health_check()
        if result:
            print("✅ 健康检查成功：服务器可达")
        else:
            print("❌ 健康检查失败：服务器不可达或返回错误")
        return result
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False


def test_send_alert(client: CloudClient) -> bool:
    """测试发送警报"""
    print("\n" + "="*70)
    print("【测试2】发送警报")
    print("="*70)
    
    try:
        alert_id = client.send_alert(
            vehicle_type="Excavator",
            timestamp=datetime.now(),
            plate_number="测试车牌",
            confidence=0.95,
            distance=5.2,
            is_registered=True,
            track_id=1
        )
        
        if alert_id:
            print(f"✅ 警报发送成功，ID: {alert_id}")
            return True
        else:
            print("❌ 警报发送失败")
            return False
    except Exception as e:
        print(f"❌ 发送警报异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_upload_image(client: CloudClient, alert_id: int = None) -> bool:
    """测试上传图片"""
    print("\n" + "="*70)
    print("【测试3】上传图片")
    print("="*70)
    
    # 创建一个测试图片
    try:
        from PIL import Image
        import numpy as np
        
        # 创建一个简单的测试图片
        test_image_path = "/tmp/test_cloud_image.jpg"
        img = Image.new('RGB', (640, 480), color='red')
        img.save(test_image_path, 'JPEG')
        print(f"✓ 创建测试图片: {test_image_path}")
        
        # 上传图片
        image_url = client.upload_image(test_image_path, alert_id=alert_id)
        
        if image_url:
            print(f"✅ 图片上传成功: {image_url}")
            # 清理测试图片
            os.remove(test_image_path)
            return True
        else:
            print("❌ 图片上传失败")
            # 清理测试图片
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
            return False
    except Exception as e:
        print(f"❌ 上传图片异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration(config: CloudConfig) -> bool:
    """测试集成模块"""
    print("\n" + "="*70)
    print("【测试4】集成模块测试")
    print("="*70)
    
    try:
        integration = SentinelIntegration(config)
        integration.start()
        print("✓ 集成模块启动成功")
        
        # 创建测试检测结果
        detection = DetectionResult(
            vehicle_type="Excavator",
            confidence=0.95,
            plate_number="测试车牌",
            timestamp=datetime.now(),
            image_path=None,  # 暂时不上传图片
            bbox=(100, 100, 500, 400),
            track_id=1,
            distance=5.2,
            is_registered=True
        )
        
        # 提交检测结果
        integration.on_detection(detection)
        print("✓ 检测结果已提交到队列")
        
        # 等待一段时间让上传线程处理
        import time
        print("  等待上传线程处理（5秒）...")
        time.sleep(5)
        
        queue_size = integration.get_queue_size()
        print(f"✓ 当前队列大小: {queue_size}")
        
        integration.stop()
        print("✓ 集成模块停止成功")
        
        return True
    except Exception as e:
        print(f"❌ 集成模块测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("="*70)
    print("云端服务器联调测试")
    print("="*70)
    
    # 从配置文件或环境变量加载配置
    import yaml
    
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            cloud_cfg = config_data.get('cloud', {})
            
            if not cloud_cfg.get('enabled', False):
                print("⚠️  警告：config.yaml 中 cloud.enabled=false")
                print("   将使用默认配置进行测试")
                config = CloudConfig()
            else:
                config = CloudConfig(
                    api_base_url=cloud_cfg.get('api_base_url', 'http://your-server-ip:8000'),
                    api_key=cloud_cfg.get('api_key', 'your-api-key-here'),
                    upload_interval=cloud_cfg.get('upload_interval', 10),
                    max_image_size_mb=cloud_cfg.get('max_image_size_mb', 5),
                    enable_image_upload=cloud_cfg.get('enable_image_upload', True),
                    enable_alert_upload=cloud_cfg.get('enable_alert_upload', True),
                    retry_attempts=cloud_cfg.get('retry_attempts', 3),
                    retry_delay=cloud_cfg.get('retry_delay', 2.0)
                )
    else:
        print("⚠️  未找到 config.yaml，使用默认配置")
        config = CloudConfig()
    
    # 显示配置信息
    print("\n配置信息:")
    print(f"  服务器地址: {config.api_base_url}")
    print(f"  API密钥: {config.api_key[:10]}..." if len(config.api_key) > 10 else f"  API密钥: {config.api_key}")
    print(f"  上传图片: {'是' if config.enable_image_upload else '否'}")
    print(f"  上传警报: {'是' if config.enable_alert_upload else '否'}")
    print(f"  最大图片大小: {config.max_image_size_mb} MB")
    print(f"  重试次数: {config.retry_attempts}")
    print(f"  重试延迟: {config.retry_delay} 秒")
    
    # 检查配置
    if config.api_base_url == "http://your-server-ip:8000" or config.api_key == "your-api-key-here":
        print("\n⚠️  警告：检测到默认配置值，请更新 config.yaml 中的配置")
        response = input("是否继续测试？(y/n): ")
        if response.lower() != 'y':
            print("测试已取消")
            return
    
    # 创建客户端
    client = CloudClient(config)
    
    # 运行测试
    results = []
    
    # 测试1：健康检查
    results.append(("健康检查", test_health_check(client)))
    
    # 测试2：发送警报
    if config.enable_alert_upload:
        results.append(("发送警报", test_send_alert(client)))
    else:
        print("\n⚠️  警报上传已禁用，跳过测试")
        results.append(("发送警报", None))
    
    # 测试3：上传图片
    if config.enable_image_upload:
        alert_id = None
        if results[1] and results[1][1]:
            # 如果有警报ID，使用它
            pass  # 这里需要从测试2获取alert_id，简化处理
        results.append(("上传图片", test_upload_image(client, alert_id)))
    else:
        print("\n⚠️  图片上传已禁用，跳过测试")
        results.append(("上传图片", None))
    
    # 测试4：集成模块
    results.append(("集成模块", test_integration(config)))
    
    # 显示测试结果
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    for name, result in results:
        if result is None:
            status = "跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"  {name}: {status}")
    
    # 统计
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    total = len(results)
    
    print(f"\n总计: {total} 项测试")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    
    if failed == 0:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 项测试失败，请检查配置和网络连接")


if __name__ == "__main__":
    main()




