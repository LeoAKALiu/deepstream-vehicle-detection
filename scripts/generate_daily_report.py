#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成日报脚本
可以手动运行或通过cron定时执行
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "python_apps"))

from python_apps.performance_reporter import PerformanceReporter
from python_apps.config_loader import get_config
import json
from datetime import datetime


def main():
    """主函数"""
    # 加载配置
    config = get_config()
    paths_cfg = config.get_paths()
    db_path = paths_cfg.get('detection_db_path', 'detection_results.db')
    
    # 创建报告生成器
    reporter = PerformanceReporter(
        db_path=db_path,
        report_dir="reports"
    )
    
    # 生成日报
    print("="*70)
    print("生成日报")
    print("="*70)
    
    report = reporter.generate_daily_report()
    
    # 打印报告摘要
    print("\n【报告摘要】")
    summary = report.get('summary', {})
    print(f"  总检测数: {summary.get('total_detections', 0)}")
    print(f"  总车辆数: {summary.get('total_vehicles', 0)}")
    print(f"  已备案车辆: {summary.get('registered_vehicles', 0)}")
    print(f"  未备案车辆: {summary.get('unregistered_vehicles', 0)}")
    print(f"  社会车辆: {summary.get('civilian_vehicles', 0)}")
    print(f"  检测率: {summary.get('detection_rate', 0.0):.2f} 次/小时")
    
    # 车辆类型分布
    vehicle_types = report.get('vehicle_types', {})
    if vehicle_types:
        print("\n【车辆类型分布】")
        for v_type, count in sorted(vehicle_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {v_type}: {count}")
    
    # 保存报告路径
    report_file = f"reports/daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n✓ 报告已保存到: {report_file}")
    
    # 如果配置了云端上传，可以在这里上传报告
    # TODO: 实现报告上传功能


if __name__ == "__main__":
    main()




