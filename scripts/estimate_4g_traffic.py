#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4G流量评估工具
评估系统每月上传数据所需的4G流量
"""

import sys
from pathlib import Path
import yaml
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def estimate_traffic(
    alerts_per_day: int = 50,
    images_per_alert: float = 1.0,
    avg_image_size_kb: float = 200.0,
    alert_data_size_kb: float = 0.5,
    days_per_month: int = 30
) -> dict:
    """
    估算每月流量需求
    
    Args:
        alerts_per_day: 每天检测到的车辆数量（警报数）
        images_per_alert: 每个警报上传的图片数量（通常为1）
        avg_image_size_kb: 平均每张图片大小（KB）
        alert_data_size_kb: 每个警报的JSON数据大小（KB）
        days_per_month: 每月天数
    
    Returns:
        流量估算结果字典
    """
    # 每天流量
    daily_alert_data = alerts_per_day * alert_data_size_kb  # KB
    daily_image_data = alerts_per_day * images_per_alert * avg_image_size_kb  # KB
    daily_total_kb = daily_alert_data + daily_image_data
    daily_total_mb = daily_total_kb / 1024
    
    # 每月流量
    monthly_alert_data = daily_alert_data * days_per_month  # KB
    monthly_image_data = daily_image_data * days_per_month  # KB
    monthly_total_kb = monthly_total_kb = daily_total_kb * days_per_month
    monthly_total_mb = monthly_total_mb = daily_total_mb * days_per_month
    monthly_total_gb = monthly_total_mb / 1024
    
    # 考虑压缩和重传
    compression_ratio = 0.7  # 假设压缩后为原来的70%
    retry_overhead = 1.1  # 假设10%的重传开销
    
    monthly_actual_mb = monthly_total_mb * compression_ratio * retry_overhead
    monthly_actual_gb = monthly_actual_mb / 1024
    
    return {
        'daily': {
            'alert_data_kb': daily_alert_data,
            'image_data_kb': daily_image_data,
            'total_kb': daily_total_kb,
            'total_mb': daily_total_mb
        },
        'monthly': {
            'alert_data_kb': monthly_alert_data,
            'image_data_kb': monthly_image_data,
            'total_kb': monthly_total_kb,
            'total_mb': monthly_total_mb,
            'total_gb': monthly_total_gb,
            'actual_mb': monthly_actual_mb,
            'actual_gb': monthly_actual_gb
        },
        'parameters': {
            'alerts_per_day': alerts_per_day,
            'images_per_alert': images_per_alert,
            'avg_image_size_kb': avg_image_size_kb,
            'alert_data_size_kb': alert_data_size_kb,
            'days_per_month': days_per_month,
            'compression_ratio': compression_ratio,
            'retry_overhead': retry_overhead
        }
    }


def print_estimate(result: dict):
    """打印流量估算结果"""
    print("="*70)
    print("4G流量需求评估")
    print("="*70)
    
    params = result['parameters']
    print("\n【参数设置】")
    print(f"  每天检测车辆数: {params['alerts_per_day']} 辆")
    print(f"  每辆车上传图片数: {params['images_per_alert']} 张")
    print(f"  平均图片大小: {params['avg_image_size_kb']} KB")
    print(f"  警报数据大小: {params['alert_data_size_kb']} KB")
    print(f"  每月天数: {params['days_per_month']} 天")
    
    daily = result['daily']
    print("\n【每日流量】")
    print(f"  警报数据: {daily['alert_data_kb']:.2f} KB ({daily['alert_data_kb']/1024:.3f} MB)")
    print(f"  图片数据: {daily['image_data_kb']:.2f} KB ({daily['image_data_kb']/1024:.3f} MB)")
    print(f"  总计: {daily['total_kb']:.2f} KB ({daily['total_mb']:.3f} MB)")
    
    monthly = result['monthly']
    print("\n【每月流量（理论值）】")
    print(f"  警报数据: {monthly['alert_data_kb']/1024:.2f} MB")
    print(f"  图片数据: {monthly['image_data_kb']/1024:.2f} MB")
    print(f"  总计: {monthly['total_mb']:.2f} MB ({monthly['total_gb']:.3f} GB)")
    
    print("\n【每月流量（实际值，考虑压缩和重传）】")
    print(f"  实际需求: {monthly['actual_mb']:.2f} MB ({monthly['actual_gb']:.3f} GB)")
    
    # 推荐套餐
    print("\n【4G套餐推荐】")
    actual_gb = monthly['actual_gb']
    
    if actual_gb < 1:
        recommended = "1GB/月"
        cost_estimate = "约10-20元/月"
    elif actual_gb < 3:
        recommended = "3GB/月"
        cost_estimate = "约20-30元/月"
    elif actual_gb < 5:
        recommended = "5GB/月"
        cost_estimate = "约30-50元/月"
    elif actual_gb < 10:
        recommended = "10GB/月"
        cost_estimate = "约50-80元/月"
    elif actual_gb < 20:
        recommended = "20GB/月"
        cost_estimate = "约80-120元/月"
    else:
        recommended = "50GB/月 或 不限量套餐"
        cost_estimate = "约120-200元/月"
    
    print(f"  推荐套餐: {recommended}")
    print(f"  预估费用: {cost_estimate}")
    print(f"  流量余量: {max(0, (int(actual_gb) + 1) * 1024 - monthly['actual_mb']):.2f} MB")
    
    # 优化建议
    print("\n【优化建议】")
    if actual_gb > 10:
        print("  ⚠️  流量需求较大，建议优化：")
        print("    1. 降低图片质量（config.yaml: max_image_size_mb）")
        print("    2. 减少上传频率（仅上传未备案车辆）")
        print("    3. 启用图片压缩（已默认启用）")
        print("    4. 考虑本地存储+定期批量上传")
    elif actual_gb > 5:
        print("  ℹ️  流量需求适中，建议：")
        print("    1. 监控实际使用情况")
        print("    2. 根据实际情况调整图片大小")
    else:
        print("  ✅ 流量需求较小，当前配置合理")


def load_config() -> dict:
    """从config.yaml加载配置"""
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def estimate_from_config():
    """基于配置文件估算流量"""
    config = load_config()
    cloud_cfg = config.get('cloud', {})
    
    # 从配置读取参数
    max_image_size_mb = cloud_cfg.get('max_image_size_mb', 5)
    # 假设实际图片大小为配置最大值的40%（压缩后）
    avg_image_size_kb = max_image_size_mb * 1024 * 0.4
    
    # 默认参数
    alerts_per_day = 50  # 每天50辆车
    images_per_alert = 1.0 if cloud_cfg.get('enable_image_upload', True) else 0.0
    
    return estimate_traffic(
        alerts_per_day=alerts_per_day,
        images_per_alert=images_per_alert,
        avg_image_size_kb=avg_image_size_kb,
        alert_data_size_kb=0.5,
        days_per_month=30
    )


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='4G流量需求评估工具')
    parser.add_argument('--alerts-per-day', type=int, default=None,
                        help='每天检测到的车辆数量（默认：从配置文件读取或50）')
    parser.add_argument('--image-size-kb', type=float, default=None,
                        help='平均每张图片大小（KB，默认：从配置文件计算）')
    parser.add_argument('--no-images', action='store_true',
                        help='不上传图片（仅上传警报数据）')
    parser.add_argument('--scenarios', action='store_true',
                        help='显示多个场景的估算')
    
    args = parser.parse_args()
    
    if args.scenarios:
        # 显示多个场景
        print("="*70)
        print("不同场景下的4G流量需求")
        print("="*70)
        
        scenarios = [
            ("低流量场景", 20, 150),
            ("中等流量场景", 50, 200),
            ("高流量场景", 100, 300),
            ("极高流量场景", 200, 400),
        ]
        
        for name, alerts, image_size in scenarios:
            print(f"\n【{name}】")
            print(f"  每天检测: {alerts} 辆车")
            print(f"  平均图片: {image_size} KB")
            result = estimate_traffic(
                alerts_per_day=alerts,
                images_per_alert=1.0,
                avg_image_size_kb=image_size,
                alert_data_size_kb=0.5,
                days_per_month=30
            )
            monthly = result['monthly']
            print(f"  每月流量: {monthly['actual_mb']:.2f} MB ({monthly['actual_gb']:.3f} GB)")
        
        return
    
    # 从配置或参数获取值
    config = load_config()
    cloud_cfg = config.get('cloud', {})
    
    alerts_per_day = args.alerts_per_day or 50
    images_per_alert = 0.0 if args.no_images else (1.0 if cloud_cfg.get('enable_image_upload', True) else 0.0)
    
    if args.image_size_kb:
        avg_image_size_kb = args.image_size_kb
    else:
        max_image_size_mb = cloud_cfg.get('max_image_size_mb', 5)
        avg_image_size_kb = max_image_size_mb * 1024 * 0.4
    
    # 估算流量
    result = estimate_traffic(
        alerts_per_day=alerts_per_day,
        images_per_alert=images_per_alert,
        avg_image_size_kb=avg_image_size_kb,
        alert_data_size_kb=0.5,
        days_per_month=30
    )
    
    # 打印结果
    print_estimate(result)
    
    # 保存结果到文件
    output_file = project_root / "4g_traffic_estimate.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ 估算结果已保存到: {output_file}")


if __name__ == "__main__":
    main()




