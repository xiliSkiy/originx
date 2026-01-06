"""遮挡检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class OcclusionDetector(BaseDetector):
    """
    遮挡检测器

    检测图像是否被遮挡，包括：
    - 镜头被遮挡
    - 大面积单色区域
    - 异常纹理区域
    """

    name = "occlusion"
    display_name = "画面遮挡检测"
    description = "检测画面是否被遮挡，如镜头被挡住"
    version = "1.0.0"

    supported_levels = [
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 25  # 较高优先级
    suppresses = ["partial_blur", "blur"]

    DEFAULT_THRESHOLD = 0.3  # 遮挡面积比例阈值

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    def _load_thresholds(self) -> None:
        self.occlusion_threshold = self.config.get(
            "occlusion_threshold", self.DEFAULT_THRESHOLD
        )

    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """执行遮挡检测"""
        start_time = time.time()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 方法1：低纹理区域检测
        # 计算局部标准差
        kernel_size = 31
        local_mean = cv2.blur(gray.astype(float), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (kernel_size, kernel_size)
        )
        local_var = local_sq_mean - local_mean ** 2
        local_std = np.sqrt(np.maximum(local_var, 0))

        # 低纹理区域（可能被遮挡）
        low_texture_mask = local_std < 5
        low_texture_ratio = float(np.sum(low_texture_mask)) / (h * w)

        # 方法2：边缘密度分析
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / (h * w)

        # 方法3：颜色单一性分析
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        color_std = float(hsv[:, :, 0].std())  # 色调标准差

        # 方法4：区域分析（分块检测）
        block_size = 8
        blocks_h = h // block_size
        blocks_w = w // block_size

        uniform_blocks = 0
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = gray[
                    i * block_size : (i + 1) * block_size,
                    j * block_size : (j + 1) * block_size,
                ]
                if block.std() < 3:
                    uniform_blocks += 1

        uniform_ratio = uniform_blocks / (blocks_h * blocks_w)

        # 综合判断遮挡程度
        occlusion_score = (
            low_texture_ratio * 0.4
            + (1 - edge_density * 10) * 0.3  # 边缘少说明可能遮挡
            + uniform_ratio * 0.3
        )
        occlusion_score = max(0, min(1, occlusion_score))

        # 判断是否异常
        is_abnormal = occlusion_score > self.occlusion_threshold

        # 置信度
        if is_abnormal:
            confidence = min(
                1.0,
                (occlusion_score - self.occlusion_threshold)
                / (1 - self.occlusion_threshold),
            )
        else:
            confidence = min(
                1.0,
                (self.occlusion_threshold - occlusion_score) / self.occlusion_threshold,
            )

        severity = self._calculate_severity(occlusion_score)

        evidence = {
            "occlusion_score": occlusion_score,
            "low_texture_ratio": low_texture_ratio,
            "edge_density": edge_density,
            "color_std": color_std,
            "uniform_block_ratio": uniform_ratio,
            "occlusion_threshold": self.occlusion_threshold,
        }

        if level == DetectionLevel.DEEP:
            # 深度分析：定位遮挡区域
            occlusion_map = self._create_occlusion_map(gray, local_std)
            evidence["has_occlusion_map"] = True

            # 计算遮挡区域位置
            occlusion_regions = self._find_occlusion_regions(occlusion_map)
            evidence["occlusion_regions"] = len(occlusion_regions)

        process_time = (time.time() - start_time) * 1000

        result = DetectionResult(
            detector_name=self.name,
            issue_type="occlusion" if is_abnormal else "occlusion_normal",
            is_abnormal=is_abnormal,
            score=occlusion_score,
            threshold=self.occlusion_threshold,
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

    def _create_occlusion_map(
        self, gray: np.ndarray, local_std: np.ndarray
    ) -> np.ndarray:
        """创建遮挡热力图"""
        # 标准化
        occlusion_map = 1 - (local_std / max(local_std.max(), 1))
        occlusion_map = (occlusion_map * 255).astype(np.uint8)
        return occlusion_map

    def _find_occlusion_regions(self, occlusion_map: np.ndarray) -> List[Dict]:
        """找出遮挡区域"""
        # 二值化
        _, binary = cv2.threshold(occlusion_map, 200, 255, cv2.THRESH_BINARY)

        # 形态学操作去噪
        kernel = np.ones((15, 15), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 查找轮廓
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        regions = []
        h, w = occlusion_map.shape
        min_area = h * w * 0.01  # 至少1%的面积

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, rw, rh = cv2.boundingRect(contour)
                regions.append(
                    {
                        "x": int(x),
                        "y": int(y),
                        "width": int(rw),
                        "height": int(rh),
                        "area_ratio": float(area / (h * w)),
                    }
                )

        return regions

    def _calculate_severity(self, score: float) -> Severity:
        if score <= self.occlusion_threshold:
            return Severity.NORMAL
        elif score <= 0.5:
            return Severity.INFO
        elif score <= 0.7:
            return Severity.WARNING
        else:
            return Severity.CRITICAL

    def get_explanation(self, result: DetectionResult) -> str:
        if not result.is_abnormal:
            return "画面未检测到明显遮挡"

        score = result.score
        if score > 0.7:
            return f"画面严重遮挡，遮挡程度{score:.1%}"
        elif score > 0.5:
            return f"画面部分遮挡，遮挡程度{score:.1%}"
        else:
            return f"画面轻微遮挡，遮挡程度{score:.1%}"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        causes = [
            "镜头被物体遮挡",
            "镜头脏污严重",
            "摄像头位置被调整",
        ]

        if result.severity == Severity.CRITICAL:
            causes.extend([
                "镜头盖未打开",
                "摄像头完全被覆盖",
            ])

        return causes

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        if not result.is_abnormal:
            return []

        return [
            "检查摄像头前方是否有遮挡物",
            "清洁摄像头镜头",
            "检查摄像头安装位置",
            "确认镜头盖已移除",
        ]

