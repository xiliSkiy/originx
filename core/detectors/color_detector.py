"""颜色检测器"""

import time
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class ColorDetector(BaseDetector):
    """
    颜色检测器

    检测图像颜色是否正常，包括：
    - 偏色检测
    - 黑白/灰度检测
    - 蓝屏/绿屏检测
    """

    name = "color"
    display_name = "图像颜色检测"
    description = "检测图像颜色是否正常，包括偏色、黑白、蓝屏/绿屏检测"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 20  # 高优先级（蓝屏等应该抑制其他问题）
    suppresses = ["color_cast", "low_saturation"]

    # 默认阈值
    DEFAULT_SATURATION_MIN = 10.0
    DEFAULT_COLOR_CAST_THRESHOLD = 30.0

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        """从配置加载阈值"""
        self.saturation_min = self.config.get("saturation_min", self.DEFAULT_SATURATION_MIN)
        self.color_cast_threshold = self.config.get(
            "color_cast_threshold", self.DEFAULT_COLOR_CAST_THRESHOLD
        )

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行颜色检测"""
        start_time = time.time()

        # 计算颜色指标
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        mean_saturation = float(saturation.mean())

        # RGB通道分析
        b_mean = float(image[:, :, 0].mean())
        g_mean = float(image[:, :, 1].mean())
        r_mean = float(image[:, :, 2].mean())
        rgb_avg = (b_mean + g_mean + r_mean) / 3
        max_deviation = max(
            abs(b_mean - rgb_avg),
            abs(g_mean - rgb_avg),
            abs(r_mean - rgb_avg),
        )

        # 检测各种颜色问题
        is_grayscale = mean_saturation < self.saturation_min
        is_color_cast = max_deviation > self.color_cast_threshold
        is_blue_screen, blue_confidence = self._detect_solid_color(image, "blue")
        is_green_screen, green_confidence = self._detect_solid_color(image, "green")

        # 确定主要问题
        issue_type, is_abnormal, severity, confidence = self._determine_issue(
            is_grayscale,
            is_color_cast,
            is_blue_screen,
            is_green_screen,
            mean_saturation,
            max_deviation,
            blue_confidence,
            green_confidence,
        )

        # 构建证据
        evidence = {
            "mean_saturation": mean_saturation,
            "b_channel_mean": b_mean,
            "g_channel_mean": g_mean,
            "r_channel_mean": r_mean,
            "rgb_average": rgb_avg,
            "max_channel_deviation": max_deviation,
            "is_grayscale": is_grayscale,
            "is_color_cast": is_color_cast,
            "blue_screen_confidence": blue_confidence,
            "green_screen_confidence": green_confidence,
        }

        if level == DetectionLevel.DEEP:
            # 深度分析：色调分布
            hue = hsv[:, :, 0]
            hue_hist = cv2.calcHist([hue], [0], None, [180], [0, 180])
            hue_hist = hue_hist.flatten() / hue_hist.sum()

            # 主色调
            dominant_hue = int(np.argmax(hue_hist))
            evidence["dominant_hue"] = dominant_hue
            evidence["hue_concentration"] = float(hue_hist.max())

            # 色温估计
            color_temp = self._estimate_color_temperature(r_mean, g_mean, b_mean)
            evidence["estimated_color_temp"] = color_temp

        # 确定阈值（根据问题类型）
        if issue_type == "grayscale":
            threshold = self.saturation_min
            score = mean_saturation
        elif issue_type in ["blue_screen", "green_screen"]:
            threshold = 0.8
            score = blue_confidence if issue_type == "blue_screen" else green_confidence
        else:
            threshold = self.color_cast_threshold
            score = max_deviation

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

    def _detect_solid_color(
        self,
        image: np.ndarray,
        color: str,
    ) -> Tuple[bool, float]:
        """
        检测纯色屏幕（蓝屏/绿屏）

        Args:
            image: BGR图像
            color: "blue" 或 "green"

        Returns:
            Tuple[bool, float]: (是否为纯色屏幕, 置信度)
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        if color == "blue":
            # 蓝色范围 (HSV)
            lower = np.array([100, 100, 100])
            upper = np.array([130, 255, 255])
        elif color == "green":
            # 绿色范围 (HSV)
            lower = np.array([35, 100, 100])
            upper = np.array([85, 255, 255])
        else:
            return False, 0.0

        mask = cv2.inRange(hsv, lower, upper)
        ratio = np.count_nonzero(mask) / mask.size

        # 超过80%为该颜色则判定为纯色屏幕
        is_solid = ratio > 0.8
        confidence = min(1.0, ratio / 0.8) if ratio > 0.5 else 0.0

        return is_solid, confidence

    def _determine_issue(
        self,
        is_grayscale: bool,
        is_color_cast: bool,
        is_blue_screen: bool,
        is_green_screen: bool,
        saturation: float,
        deviation: float,
        blue_conf: float,
        green_conf: float,
    ) -> Tuple[str, bool, Severity, float]:
        """确定主要颜色问题"""
        # 优先级：蓝屏/绿屏 > 灰度 > 偏色

        if is_blue_screen:
            return "blue_screen", True, Severity.CRITICAL, blue_conf

        if is_green_screen:
            return "green_screen", True, Severity.CRITICAL, green_conf

        if is_grayscale:
            # 计算严重程度
            if saturation < 3:
                severity = Severity.CRITICAL
            elif saturation < self.saturation_min * 0.5:
                severity = Severity.WARNING
            else:
                severity = Severity.INFO

            confidence = min(1.0, (self.saturation_min - saturation) / self.saturation_min)
            return "grayscale", True, severity, confidence

        if is_color_cast:
            # 计算严重程度
            if deviation > self.color_cast_threshold * 2:
                severity = Severity.WARNING
            else:
                severity = Severity.INFO

            confidence = min(1.0, deviation / (self.color_cast_threshold * 2))
            return "color_cast", True, severity, confidence

        return "color_normal", False, Severity.NORMAL, 1.0

    def _estimate_color_temperature(
        self,
        r: float,
        g: float,
        b: float,
    ) -> str:
        """估计色温"""
        if r > b * 1.2:
            return "warm"  # 偏暖
        elif b > r * 1.2:
            return "cool"  # 偏冷
        else:
            return "neutral"  # 中性

    def get_explanation(self, result: DetectionResult) -> str:
        """生成解释说明"""
        issue_type = result.issue_type

        if issue_type == "blue_screen":
            return "检测到蓝屏，画面被蓝色填充"
        elif issue_type == "green_screen":
            return "检测到绿屏，画面被绿色填充"
        elif issue_type == "grayscale":
            saturation = result.evidence.get("mean_saturation", 0)
            return f"图像饱和度{saturation:.1f}，画面接近黑白/灰度"
        elif issue_type == "color_cast":
            deviation = result.evidence.get("max_channel_deviation", 0)
            r = result.evidence.get("r_channel_mean", 0)
            g = result.evidence.get("g_channel_mean", 0)
            b = result.evidence.get("b_channel_mean", 0)

            if r > g and r > b:
                cast_color = "红色"
            elif g > r and g > b:
                cast_color = "绿色"
            else:
                cast_color = "蓝色"

            return f"图像偏色（偏{cast_color}），通道偏差{deviation:.1f}"
        else:
            return "图像颜色正常"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        """获取可能原因"""
        if not result.is_abnormal:
            return []

        issue_type = result.issue_type

        if issue_type == "blue_screen":
            return [
                "摄像头信号异常",
                "视频编码器故障",
                "连接线松动",
                "摄像头固件问题",
            ]
        elif issue_type == "green_screen":
            return [
                "摄像头信号异常",
                "视频编码器故障",
                "HDMI/SDI接口问题",
            ]
        elif issue_type == "grayscale":
            return [
                "摄像头处于黑白模式",
                "夜视模式已启用",
                "色彩传感器故障",
                "ISP处理异常",
            ]
        elif issue_type == "color_cast":
            return [
                "白平衡设置不当",
                "环境光源色温影响",
                "摄像头色彩校正异常",
                "老化导致的色彩漂移",
            ]

        return []

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        """获取建议措施"""
        if not result.is_abnormal:
            return []

        issue_type = result.issue_type

        if issue_type in ["blue_screen", "green_screen"]:
            return [
                "检查摄像头连接线",
                "重启摄像头",
                "检查视频编码器",
                "更新摄像头固件",
            ]
        elif issue_type == "grayscale":
            return [
                "检查摄像头是否处于夜视模式",
                "调整摄像头彩色/黑白设置",
                "检查环境光线是否充足",
            ]
        elif issue_type == "color_cast":
            return [
                "调整白平衡设置",
                "使用自动白平衡",
                "检查环境光源",
                "执行色彩校正",
            ]

        return []

