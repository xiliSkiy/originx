"""条纹检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class StripeDetector(BaseDetector):
    """
    条纹检测器

    检测图像中的条纹干扰，包括水平条纹和垂直条纹。
    使用FFT频域分析检测周期性条纹模式。
    """

    name = "stripe"
    display_name = "条纹干扰检测"
    description = "检测图像中的条纹干扰，包括水平和垂直条纹"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 65
    suppresses = []

    DEFAULT_THRESHOLD = 0.3

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        self.stripe_threshold = self.config.get("stripe_threshold", self.DEFAULT_THRESHOLD)

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行条纹检测"""
        start_time = time.time()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # FFT分析
        f = np.fft.fft2(gray.astype(float))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        magnitude = magnitude / magnitude.max()

        h, w = magnitude.shape
        cy, cx = h // 2, w // 2

        # 分析水平和垂直方向的能量（排除中心）
        margin = min(h, w) // 10
        center_margin = min(h, w) // 20

        # 水平条纹（在频域表现为垂直线）
        vertical_line = magnitude[:, cx - 2 : cx + 2].copy()
        vertical_line[cy - center_margin : cy + center_margin, :] = 0
        horizontal_stripe_energy = float(vertical_line[margin:-margin, :].mean())

        # 垂直条纹（在频域表现为水平线）
        horizontal_line = magnitude[cy - 2 : cy + 2, :].copy()
        horizontal_line[:, cx - center_margin : cx + center_margin] = 0
        vertical_stripe_energy = float(horizontal_line[:, margin:-margin].mean())

        # 综合条纹强度
        stripe_strength = max(horizontal_stripe_energy, vertical_stripe_energy)

        # 判断条纹方向
        if horizontal_stripe_energy > vertical_stripe_energy * 1.5:
            stripe_direction = "horizontal"
        elif vertical_stripe_energy > horizontal_stripe_energy * 1.5:
            stripe_direction = "vertical"
        else:
            stripe_direction = "both" if stripe_strength > self.stripe_threshold else "none"

        # 判断是否异常
        is_abnormal = stripe_strength > self.stripe_threshold

        # 计算置信度
        if is_abnormal:
            confidence = min(1.0, (stripe_strength - self.stripe_threshold) / self.stripe_threshold)
        else:
            confidence = min(1.0, (self.stripe_threshold - stripe_strength) / self.stripe_threshold)

        severity = self._calculate_severity(stripe_strength)

        evidence = {
            "horizontal_stripe_energy": horizontal_stripe_energy,
            "vertical_stripe_energy": vertical_stripe_energy,
            "stripe_strength": stripe_strength,
            "stripe_direction": stripe_direction,
            "stripe_threshold": self.stripe_threshold,
        }

        if level == DetectionLevel.DEEP:
            # 深度分析：检测条纹周期
            period = self._estimate_stripe_period(gray, stripe_direction)
            evidence["estimated_period_pixels"] = period

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type="stripe" if is_abnormal else "stripe_normal",
            is_abnormal=is_abnormal,
            score=stripe_strength,
            threshold=self.stripe_threshold,
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

    def _estimate_stripe_period(self, gray: np.ndarray, direction: str) -> float:
        """估计条纹周期"""
        if direction == "horizontal":
            # 水平条纹，分析垂直方向的变化
            profile = gray.mean(axis=1)
        elif direction == "vertical":
            # 垂直条纹，分析水平方向的变化
            profile = gray.mean(axis=0)
        else:
            return 0.0

        # 使用自相关估计周期
        profile = profile - profile.mean()
        autocorr = np.correlate(profile, profile, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        # 找第一个峰值（排除起点）
        peaks = []
        for i in range(1, len(autocorr) - 1):
            if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1]:
                peaks.append(i)
                if len(peaks) >= 1:
                    break

        return float(peaks[0]) if peaks else 0.0

    def _calculate_severity(self, strength: float) -> Severity:
        if strength <= self.stripe_threshold:
            return Severity.NORMAL
        elif strength <= self.stripe_threshold * 1.5:
            return Severity.INFO
        elif strength <= self.stripe_threshold * 2.5:
            return Severity.WARNING
        else:
            return Severity.CRITICAL

    def get_explanation(self, result: DetectionResult) -> str:
        if not result.is_abnormal:
            return "未检测到明显条纹干扰"

        direction = result.evidence.get("stripe_direction", "unknown")
        direction_text = {
            "horizontal": "水平",
            "vertical": "垂直",
            "both": "水平和垂直",
        }.get(direction, "")

        return f"检测到{direction_text}条纹干扰，强度{result.score:.3f}"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        return [
            "电源干扰（50Hz/60Hz）",
            "摄像头传感器故障",
            "视频信号干扰",
            "编码器问题",
            "接地不良",
        ]

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        return [
            "检查电源稳定性",
            "检查视频线缆屏蔽",
            "检查接地连接",
            "尝试更换摄像头",
            "调整摄像头曝光设置",
        ]

