"""亮度检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class BrightnessDetector(BaseDetector):
    """
    亮度检测器

    检测图像亮度是否正常，包括过亮、过暗检测。
    """

    name = "brightness"
    display_name = "图像亮度检测"
    description = "检测图像亮度是否正常，包括过亮和过暗检测"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 30  # 较高优先级
    suppresses = []

    # 默认阈值
    DEFAULT_MIN = 20.0
    DEFAULT_MAX = 235.0

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        """从配置加载阈值"""
        self.brightness_min = self.config.get("brightness_min", self.DEFAULT_MIN)
        self.brightness_max = self.config.get("brightness_max", self.DEFAULT_MAX)

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行亮度检测"""
        start_time = time.time()

        # 转换为灰度计算亮度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 计算亮度指标
        mean_brightness = float(gray.mean())
        std_brightness = float(gray.std())
        p5 = float(np.percentile(gray, 5))
        p95 = float(np.percentile(gray, 95))

        # 判断异常类型
        is_too_dark = mean_brightness < self.brightness_min
        is_too_bright = mean_brightness > self.brightness_max
        is_abnormal = is_too_dark or is_too_bright

        # 确定问题类型
        if is_too_dark:
            issue_type = "too_dark"
            threshold = self.brightness_min
        elif is_too_bright:
            issue_type = "too_bright"
            threshold = self.brightness_max
        else:
            issue_type = "brightness_normal"
            threshold = self.brightness_min  # 使用下限作为参考

        # 计算置信度
        if is_too_dark:
            distance = self.brightness_min - mean_brightness
            confidence = min(1.0, distance / self.brightness_min) if self.brightness_min > 0 else 1.0
        elif is_too_bright:
            distance = mean_brightness - self.brightness_max
            confidence = min(1.0, distance / (255 - self.brightness_max)) if self.brightness_max < 255 else 1.0
        else:
            # 正常情况，计算到边界的距离
            dist_to_min = mean_brightness - self.brightness_min
            dist_to_max = self.brightness_max - mean_brightness
            min_dist = min(dist_to_min, dist_to_max)
            range_size = self.brightness_max - self.brightness_min
            confidence = min_dist / (range_size / 2) if range_size > 0 else 1.0

        # 确定严重程度
        severity = self._calculate_severity(mean_brightness, is_too_dark, is_too_bright)

        # 深度分析时的额外指标
        evidence = {
            "mean_brightness": mean_brightness,
            "std_brightness": std_brightness,
            "percentile_5": p5,
            "percentile_95": p95,
            "brightness_min_threshold": self.brightness_min,
            "brightness_max_threshold": self.brightness_max,
        }

        if level == DetectionLevel.DEEP:
            # 计算直方图分布
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = hist.flatten() / hist.sum()

            # 暗区和亮区像素占比
            dark_ratio = float(hist[:30].sum())
            bright_ratio = float(hist[225:].sum())

            evidence.update({
                "dark_pixel_ratio": dark_ratio,
                "bright_pixel_ratio": bright_ratio,
                "histogram_entropy": float(-np.sum(hist[hist > 0] * np.log2(hist[hist > 0]))),
            })

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type=issue_type,
            is_abnormal=is_abnormal,
            score=mean_brightness,
            threshold=threshold,
            confidence=confidence,
            severity=severity,
            evidence=evidence,
            process_time_ms=process_time,
            detection_level=level,
        )

        result.explanation = self.get_explanation(result)
        result.possible_causes = self.get_possible_causes(result)
        result.suggestions = self.get_suggestions(result)

        return result

    def _calculate_severity(
        self,
        brightness: float,
        is_too_dark: bool,
        is_too_bright: bool,
    ) -> Severity:
        """计算严重程度"""
        if not (is_too_dark or is_too_bright):
            return Severity.NORMAL

        if is_too_dark:
            if brightness < 5:
                return Severity.CRITICAL  # 几乎全黑
            elif brightness < self.brightness_min * 0.5:
                return Severity.WARNING
            else:
                return Severity.INFO

        if is_too_bright:
            if brightness > 250:
                return Severity.CRITICAL  # 几乎全白
            elif brightness > self.brightness_max + (255 - self.brightness_max) * 0.5:
                return Severity.WARNING
            else:
                return Severity.INFO

        return Severity.NORMAL

    def get_explanation(self, result: DetectionResult) -> str:
        """生成解释说明"""
        mean_brightness = result.evidence.get("mean_brightness", result.score)

        if result.issue_type == "too_dark":
            return (
                f"图像平均亮度{mean_brightness:.1f}，"
                f"低于最小阈值{self.brightness_min:.1f}，"
                f"画面过暗"
            )
        elif result.issue_type == "too_bright":
            return (
                f"图像平均亮度{mean_brightness:.1f}，"
                f"高于最大阈值{self.brightness_max:.1f}，"
                f"画面过亮"
            )
        else:
            return f"图像平均亮度{mean_brightness:.1f}，亮度正常"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        """获取可能原因"""
        if not result.is_abnormal:
            return []

        if result.issue_type == "too_dark":
            causes = [
                "环境光线不足",
                "摄像头曝光设置过低",
                "镜头遮挡",
                "夜间模式未正确切换",
            ]
            if result.severity == Severity.CRITICAL:
                causes.extend([
                    "摄像头故障",
                    "信号丢失",
                    "镜头盖未打开",
                ])
        else:  # too_bright
            causes = [
                "强光直射镜头",
                "摄像头曝光设置过高",
                "背光环境",
                "反光表面影响",
            ]
            if result.severity == Severity.CRITICAL:
                causes.extend([
                    "摄像头传感器故障",
                    "曝光失控",
                ])

        return causes

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        """获取建议措施"""
        if not result.is_abnormal:
            return []

        if result.issue_type == "too_dark":
            suggestions = [
                "检查环境照明",
                "调整摄像头曝光参数",
                "检查是否有遮挡物",
            ]
            if result.severity == Severity.CRITICAL:
                suggestions.extend([
                    "检查摄像头电源和连接",
                    "检查镜头盖是否已移除",
                ])
        else:  # too_bright
            suggestions = [
                "调整摄像头角度避免直射光",
                "降低曝光参数",
                "安装遮光罩",
                "检查BLC/WDR设置",
            ]

        return suggestions

