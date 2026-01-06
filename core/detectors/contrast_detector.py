"""对比度检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class ContrastDetector(BaseDetector):
    """
    对比度检测器

    检测图像对比度是否正常，低对比度可能导致画面灰蒙蒙。
    """

    name = "contrast"
    display_name = "图像对比度检测"
    description = "检测图像对比度是否正常，低对比度会导致画面层次感差"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 60  # 中等优先级
    suppresses = []

    # 默认阈值
    DEFAULT_MIN = 30.0

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        """从配置加载阈值"""
        self.contrast_min = self.config.get("contrast_min", self.DEFAULT_MIN)

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行对比度检测"""
        start_time = time.time()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 计算对比度指标
        std_contrast = float(gray.std())
        min_val = float(gray.min())
        max_val = float(gray.max())
        dynamic_range = max_val - min_val

        # 判断异常
        is_abnormal = std_contrast < self.contrast_min

        # 计算置信度
        if is_abnormal:
            confidence = min(1.0, (self.contrast_min - std_contrast) / self.contrast_min)
        else:
            confidence = min(1.0, (std_contrast - self.contrast_min) / self.contrast_min)

        # 确定严重程度
        severity = self._calculate_severity(std_contrast)

        evidence = {
            "std_contrast": std_contrast,
            "dynamic_range": dynamic_range,
            "min_value": min_val,
            "max_value": max_val,
            "contrast_threshold": self.contrast_min,
        }

        if level in [DetectionLevel.STANDARD, DetectionLevel.DEEP]:
            # 计算局部对比度
            kernel_size = 31
            local_mean = cv2.blur(gray.astype(float), (kernel_size, kernel_size))
            local_var = cv2.blur(
                (gray.astype(float) - local_mean) ** 2, (kernel_size, kernel_size)
            )
            local_contrast = float(np.sqrt(local_var).mean())
            evidence["local_contrast"] = local_contrast

        if level == DetectionLevel.DEEP:
            # RMS对比度
            rms_contrast = float(np.sqrt(np.mean((gray.astype(float) - gray.mean()) ** 2)))
            evidence["rms_contrast"] = rms_contrast

            # Michelson对比度
            if max_val + min_val > 0:
                michelson = (max_val - min_val) / (max_val + min_val)
            else:
                michelson = 0
            evidence["michelson_contrast"] = float(michelson)

            # Weber对比度（相对于背景的对比度）
            bg_value = float(np.median(gray))
            if bg_value > 0:
                weber = (gray.astype(float) - bg_value) / bg_value
                evidence["weber_contrast_mean"] = float(np.abs(weber).mean())

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type="low_contrast" if is_abnormal else "contrast_normal",
            is_abnormal=is_abnormal,
            score=std_contrast,
            threshold=self.contrast_min,
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

    def _calculate_severity(self, contrast: float) -> Severity:
        """计算严重程度"""
        if contrast >= self.contrast_min:
            return Severity.NORMAL
        elif contrast >= self.contrast_min * 0.7:
            return Severity.INFO
        elif contrast >= self.contrast_min * 0.4:
            return Severity.WARNING
        else:
            return Severity.CRITICAL

    def get_explanation(self, result: DetectionResult) -> str:
        """生成解释说明"""
        contrast = result.score
        dynamic_range = result.evidence.get("dynamic_range", 0)

        if result.is_abnormal:
            return (
                f"图像对比度{contrast:.1f}，"
                f"低于阈值{self.contrast_min:.1f}，"
                f"动态范围{dynamic_range:.1f}，"
                f"画面层次感较差"
            )
        return f"图像对比度{contrast:.1f}，对比度正常"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        """获取可能原因"""
        if not result.is_abnormal:
            return []

        causes = [
            "光线条件较差",
            "雾气或灰尘影响",
            "摄像头参数设置不当",
            "镜头脏污",
        ]

        dynamic_range = result.evidence.get("dynamic_range", 255)
        if dynamic_range < 50:
            causes.append("场景本身缺乏层次（如纯色墙壁）")

        if result.severity == Severity.CRITICAL:
            causes.append("摄像头传感器可能老化")

        return causes

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        """获取建议措施"""
        if not result.is_abnormal:
            return []

        suggestions = [
            "检查并清洁镜头",
            "调整摄像头对比度参数",
            "改善环境光线条件",
        ]

        if result.severity in [Severity.WARNING, Severity.CRITICAL]:
            suggestions.extend([
                "检查是否有雾气或灰尘",
                "考虑启用WDR（宽动态）功能",
            ])

        return suggestions

