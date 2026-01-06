#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OriginX 快速入门示例

演示如何使用 OriginX 进行图像质量诊断
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

# 导入检测器（触发注册）
import core.detectors  # noqa

from core import DiagnosisPipeline, DetectorRegistry, DetectionLevel
from config import AppConfig


def create_test_images():
    """创建测试图像"""
    images = {}
    
    # 正常图像
    normal = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    cv2.rectangle(normal, (100, 100), (300, 300), (255, 255, 255), 2)
    cv2.circle(normal, (400, 200), 50, (0, 0, 255), -1)
    images['normal'] = normal
    
    # 模糊图像
    blur = cv2.GaussianBlur(normal.copy(), (31, 31), 10)
    images['blur'] = blur
    
    # 过暗图像
    dark = np.random.randint(0, 15, (480, 640, 3), dtype=np.uint8)
    images['dark'] = dark
    
    # 噪声图像
    noisy = normal.copy().astype(np.int16)
    noise = np.random.normal(0, 30, noisy.shape).astype(np.int16)
    noisy = np.clip(noisy + noise, 0, 255).astype(np.uint8)
    images['noisy'] = noisy
    
    # 蓝屏图像
    blue = np.zeros((480, 640, 3), dtype=np.uint8)
    blue[:, :, 0] = 200
    blue[:, :, 1] = 50
    blue[:, :, 2] = 50
    images['blue_screen'] = blue
    
    return images


def print_result(result, image_name):
    """打印诊断结果"""
    print(f"\n{'='*60}")
    print(f"图像: {image_name}")
    print(f"{'='*60}")
    print(f"是否异常: {'是' if result.is_abnormal else '否'}")
    print(f"主要问题: {result.primary_issue or '无'}")
    print(f"严重程度: {result.severity.value}")
    print(f"处理耗时: {result.total_process_time_ms:.2f}ms")
    
    print("\n检测详情:")
    for det in result.detection_results:
        status = "❌ 异常" if det.is_abnormal else "✓ 正常"
        print(f"  {det.detector_name}: {status} (得分: {det.score:.2f}, 阈值: {det.threshold:.2f})")
    
    if result.is_abnormal:
        print("\n问题分析:")
        for det in result.detection_results:
            if det.is_abnormal:
                print(f"\n  [{det.detector_name}]")
                print(f"    说明: {det.explanation}")
                if det.possible_causes:
                    print(f"    原因: {', '.join(det.possible_causes[:2])}")
                if det.suggestions:
                    print(f"    建议: {', '.join(det.suggestions[:2])}")


def main():
    """主函数"""
    print("=" * 60)
    print("OriginX 图像质量诊断系统 - 快速入门示例")
    print("=" * 60)
    
    # 1. 查看已注册的检测器
    print("\n已注册的检测器:")
    for detector in DetectorRegistry.list_detectors():
        print(f"  - {detector['display_name']} ({detector['name']})")
    
    # 2. 创建测试图像
    print("\n创建测试图像...")
    images = create_test_images()
    
    # 3. 创建诊断流水线
    config = AppConfig()
    threshold_config = config.get_threshold_dict()
    threshold_config["profile"] = "normal"
    threshold_config["parallel_detection"] = True
    threshold_config["max_workers"] = 4
    
    pipeline = DiagnosisPipeline(threshold_config)
    
    # 4. 对各种图像进行诊断
    print("\n开始诊断...")
    
    for name, image in images.items():
        result = pipeline.diagnose(
            image=image,
            level=DetectionLevel.STANDARD,
            image_id=name,
        )
        print_result(result, name)
    
    # 5. 演示不同检测级别
    print("\n" + "=" * 60)
    print("不同检测级别对比")
    print("=" * 60)
    
    test_image = images['normal']
    
    for level_name in ['fast', 'standard', 'deep']:
        level = DetectionLevel.from_string(level_name)
        result = pipeline.diagnose(test_image, level=level)
        print(f"  {level_name}: {result.total_process_time_ms:.2f}ms")
    
    # 6. 演示指定检测器
    print("\n" + "=" * 60)
    print("指定检测器诊断")
    print("=" * 60)
    
    result = pipeline.diagnose(
        image=images['blur'],
        level=DetectionLevel.STANDARD,
        detectors=['blur', 'brightness'],
    )
    
    print(f"只使用 blur 和 brightness 检测器:")
    for det in result.detection_results:
        print(f"  - {det.detector_name}: 得分 {det.score:.2f}")
    
    print("\n示例完成!")


if __name__ == "__main__":
    main()

