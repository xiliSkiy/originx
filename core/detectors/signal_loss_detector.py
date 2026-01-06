"""信号丢失检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class SignalLossDetector(BaseDetector):
    """
    信号丢失检测器

    检测视频信号是否丢失，包括：
    - 黑屏
    - 纯色屏
    - 无信号状态
    """

    name = "signal_loss"
    display_name = "信号丢失检测"
    description = "检测视频信号是否丢失，如黑屏、无信号等"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 10  # 最高优先级
    suppresses = ["too_dark", "blur", "low_contrast", "no_texture", "noise"]

    DEFAULT_BLACK_THRESHOLD = 10.0

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        self.black_threshold = self.config.get(
            "black_screen_threshold", self.DEFAULT_BLACK_THRESHOLD
        )

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行信号丢失检测"""
        start_time = time.time()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 计算亮度统计
        mean_brightness = float(gray.mean())
        std_brightness = float(gray.std())
        min_brightness = float(gray.min())
        max_brightness = float(gray.max())

        # 黑屏检测
        is_black_screen = mean_brightness < self.black_threshold

        # 纯色检测（高亮度但无变化）
        is_solid_color = std_brightness < 3 and not is_black_screen

        # 白屏检测
        is_white_screen = mean_brightness > 250 and std_brightness < 3

        # 确定问题类型
        is_abnormal = is_black_screen or is_solid_color or is_white_screen

        if is_black_screen:
            issue_type = "black_screen"
            score = mean_brightness
            threshold = self.black_threshold
        elif is_white_screen:
            issue_type = "white_screen"
            score = 255 - mean_brightness
            threshold = 5
        elif is_solid_color:
            issue_type = "solid_color"
            score = std_brightness
            threshold = 3
        else:
            issue_type = "signal_normal"
            score = mean_brightness
            threshold = self.black_threshold

        # 置信度
        if is_abnormal:
            if is_black_screen:
                confidence = min(1.0, (self.black_threshold - mean_brightness) / self.black_threshold)
            elif is_white_screen:
                confidence = min(1.0, (mean_brightness - 250) / 5)
            else:
                confidence = min(1.0, (3 - std_brightness) / 3)
        else:
            confidence = min(1.0, mean_brightness / 128)

        severity = self._calculate_severity(is_black_screen, is_white_screen, is_solid_color, mean_brightness)

        evidence = {
            "mean_brightness": mean_brightness,
            "std_brightness": std_brightness,
            "min_brightness": min_brightness,
            "max_brightness": max_brightness,
            "is_black_screen": is_black_screen,
            "is_white_screen": is_white_screen,
            "is_solid_color": is_solid_color,
            "black_threshold": self.black_threshold,
        }

        if level == DetectionLevel.DEEP:
            # 深度分析
            # 检查边缘是否有信息
            edges = cv2.Canny(gray, 50, 150)
            edge_ratio = float(np.sum(edges > 0)) / (h * w)
            evidence["edge_ratio"] = edge_ratio

            # 检查是否有周期性图案（如"无信号"图案）
            has_pattern = self._detect_no_signal_pattern(image)
            evidence["has_no_signal_pattern"] = has_pattern

            # 颜色分析
            if not is_black_screen:
                dominant_color = self._get_dominant_color(image)
                evidence["dominant_color"] = dominant_color

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type=issue_type,
            is_abnormal=is_abnormal,
            score=score,
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

    def _detect_no_signal_pattern(self, image: np.ndarray) -> bool:
        """检测是否有"无信号"图案"""
        # 简单检测：查找特定颜色条纹
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, w = image.shape[:2]

        # 检查是否有彩色条纹（常见于无信号画面）
        unique_hues = len(np.unique(hsv[:, :, 0] // 20))
        if unique_hues >= 5:
            # 检查是否呈条纹状
            row_means = image.mean(axis=1)
            row_stds = np.std(row_means, axis=0)
            if np.all(row_stds < 10):
                return True

        return False

    def _get_dominant_color(self, image: np.ndarray) -> Dict[str, int]:
        """获取主色"""
        b_mean = int(image[:, :, 0].mean())
        g_mean = int(image[:, :, 1].mean())
        r_mean = int(image[:, :, 2].mean())

        return {"r": r_mean, "g": g_mean, "b": b_mean}

    def _calculate_severity(
        self,
        is_black: bool,
        is_white: bool,
        is_solid: bool,
        brightness: float,
    ) -> Severity:
        if not (is_black or is_white or is_solid):
            return Severity.NORMAL

        if is_black and brightness < 3:
            return Severity.CRITICAL
        elif is_black:
            return Severity.WARNING
        elif is_white:
            return Severity.WARNING
        elif is_solid:
            return Severity.WARNING

        return Severity.INFO

    def get_explanation(self, result: DetectionResult) -> str:
        issue_type = result.issue_type
        brightness = result.evidence.get("mean_brightness", 0)

        if issue_type == "black_screen":
            return f"检测到黑屏，平均亮度{brightness:.1f}"
        elif issue_type == "white_screen":
            return f"检测到白屏，平均亮度{brightness:.1f}"
        elif issue_type == "solid_color":
            return "检测到纯色画面，可能信号异常"
        else:
            return "信号正常"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        issue_type = result.issue_type

        if issue_type == "black_screen":
            return [
                "摄像头电源故障",
                "视频信号线断开",
                "摄像头完全遮挡",
                "编码器故障",
                "网络连接中断",
            ]
        elif issue_type == "white_screen":
            return [
                "强光直射",
                "摄像头曝光失控",
                "传感器故障",
            ]
        elif issue_type == "solid_color":
            return [
                "信号源异常",
                "编码解码问题",
                "硬件故障",
            ]

        return []

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        issue_type = result.issue_type

        if issue_type == "black_screen":
            return [
                "检查摄像头电源",
                "检查视频线缆连接",
                "检查网络连接",
                "重启摄像头",
                "检查摄像头是否被遮挡",
            ]
        elif issue_type == "white_screen":
            return [
                "检查是否有强光源",
                "调整摄像头曝光设置",
                "检查传感器状态",
            ]
        elif issue_type == "solid_color":
            return [
                "检查信号源",
                "重启相关设备",
                "检查编码器状态",
            ]

        return []

