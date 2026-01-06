"""模糊检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class BlurDetector(BaseDetector):
    """
    模糊检测器

    检测图像是否存在模糊问题，支持运动模糊和对焦模糊检测。
    使用Laplacian方差、Sobel梯度、Brenner梯度等多种算法。
    """

    name = "blur"
    display_name = "图像模糊检测"
    description = "检测图像是否存在模糊问题，支持运动模糊和对焦模糊"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 50  # 中等优先级
    suppresses = []  # 不抑制其他检测器

    # 默认阈值
    DEFAULT_THRESHOLD = 100.0

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        """从配置加载阈值"""
        self.threshold = self.config.get("blur_threshold", self.DEFAULT_THRESHOLD)

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行模糊检测"""
        start_time = time.time()

        # 根据检测级别选择算法
        if level == DetectionLevel.FAST:
            score, evidence = self._fast_detect(image)
        elif level == DetectionLevel.STANDARD:
            score, evidence = self._standard_detect(image)
        else:
            score, evidence = self._deep_detect(image)

        # 判断是否异常（分数越低越模糊）
        is_abnormal = score < self.threshold

        # 计算置信度
        confidence = self._calculate_confidence(score, self.threshold, is_higher_better=True)

        # 确定严重程度
        severity = self._calculate_severity(score)

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type="blur",
            is_abnormal=is_abnormal,
            score=score,
            threshold=self.threshold,
            confidence=confidence,
            severity=severity,
            evidence=evidence,
            process_time_ms=process_time,
            detection_level=level,
        )

        # 填充可解释性字段
        result.explanation = self.get_explanation(result)
        result.possible_causes = self.get_possible_causes(result)
        result.suggestions = self.get_suggestions(result)

        return result

    def _fast_detect(self, image: np.ndarray) -> tuple:
        """快速检测 - 仅使用Laplacian方差"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        return float(laplacian_var), {
            "laplacian_variance": float(laplacian_var),
            "method": "fast",
        }

    def _standard_detect(self, image: np.ndarray) -> tuple:
        """标准检测 - Laplacian + Sobel"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Laplacian方差
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Sobel梯度
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        gradient_mean = gradient_magnitude.mean()

        # 综合得分（加权平均）
        score = laplacian_var * 0.6 + gradient_mean * 0.4

        evidence = {
            "laplacian_variance": float(laplacian_var),
            "gradient_mean": float(gradient_mean),
            "combined_score": float(score),
            "method": "standard",
        }

        return float(score), evidence

    def _deep_detect(self, image: np.ndarray) -> tuple:
        """深度检测 - 多尺度分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        scores = []
        evidence = {}

        # 多尺度分析
        for scale in [1.0, 0.5, 0.25]:
            if scale != 1.0:
                h, w = gray.shape
                resized = cv2.resize(gray, (int(w * scale), int(h * scale)))
            else:
                resized = gray

            lap_var = cv2.Laplacian(resized, cv2.CV_64F).var()
            scores.append(lap_var)
            evidence[f"laplacian_scale_{scale}"] = float(lap_var)

        # 边缘密度
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        evidence["edge_density"] = float(edge_density)

        # Brenner梯度
        brenner = self._brenner_gradient(gray)
        evidence["brenner_gradient"] = float(brenner)

        # Tenengrad梯度
        tenengrad = self._tenengrad(gray)
        evidence["tenengrad"] = float(tenengrad)

        # 综合得分
        score = (
            np.mean(scores) * 0.4
            + brenner * 0.2
            + tenengrad * 0.2
            + edge_density * 1000 * 0.2
        )
        evidence["final_score"] = float(score)
        evidence["method"] = "deep"

        return float(score), evidence

    def _brenner_gradient(self, gray: np.ndarray) -> float:
        """Brenner梯度计算"""
        diff = gray[:, 2:].astype(float) - gray[:, :-2].astype(float)
        return float(np.mean(diff**2))

    def _tenengrad(self, gray: np.ndarray) -> float:
        """Tenengrad梯度计算"""
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        return float(np.mean(gx**2 + gy**2))

    def _calculate_severity(self, score: float) -> Severity:
        """计算严重程度"""
        if score >= self.threshold:
            return Severity.NORMAL
        elif score >= self.threshold * 0.7:
            return Severity.INFO
        elif score >= self.threshold * 0.4:
            return Severity.WARNING
        else:
            return Severity.CRITICAL

    def get_explanation(self, result: DetectionResult) -> str:
        """生成解释说明"""
        if result.is_abnormal:
            severity_text = {
                Severity.INFO: "轻微",
                Severity.WARNING: "中度",
                Severity.CRITICAL: "严重",
            }.get(result.severity, "")
            return (
                f"图像清晰度评分{result.score:.1f}，"
                f"低于阈值{result.threshold:.1f}，"
                f"判定为{severity_text}模糊"
            )
        return f"图像清晰度评分{result.score:.1f}，画面清晰度正常"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        """获取可能原因"""
        if not result.is_abnormal:
            return []

        causes = ["镜头脏污或有水渍", "摄像头对焦不准确"]

        # 根据证据推断更具体的原因
        edge_density = result.evidence.get("edge_density", 1)
        if edge_density < 0.05:
            causes.append("可能存在大面积平滑区域或遮挡")

        if result.severity == Severity.CRITICAL:
            causes.append("镜头可能损坏")
            causes.append("运动模糊（摄像头晃动）")
            causes.append("严重散焦")

        return causes

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        """获取建议措施"""
        if not result.is_abnormal:
            return []

        suggestions = ["检查并清洁摄像头镜头"]

        if result.severity in [Severity.WARNING, Severity.CRITICAL]:
            suggestions.extend(
                [
                    "调整摄像头对焦设置",
                    "检查摄像头固定是否稳固",
                    "检查摄像头是否需要更换",
                ]
            )

        return suggestions

