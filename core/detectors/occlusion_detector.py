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
    - 镜头被遮挡（全黑/全白/单色覆盖）
    - 镜头脏污模糊
    - 物理遮挡

    优化说明：
    - 区分"正常场景的低纹理区域"（如道路）和"真正的遮挡"
    - 真正的遮挡通常表现为：极低的颜色多样性 + 极低的边缘密度 + 极低的对比度
    - 正常监控场景即使有大面积道路，仍会有清晰的边缘和颜色变化
    """

    name = "occlusion"
    display_name = "画面遮挡检测"
    description = "检测画面是否被遮挡，如镜头被挡住"
    version = "1.1.0"

    supported_levels = [
        DetectionLevel.FAST,
        DetectionLevel.STANDARD,
        DetectionLevel.DEEP,
    ]

    priority = 25  # 较高优先级
    suppresses = ["partial_blur", "blur"]

    DEFAULT_THRESHOLD = 0.6  # 提高阈值，减少误报

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

        # ========== 特征提取 ==========

        # 1. 边缘密度分析 - 真正被遮挡的图像几乎没有边缘
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / (h * w)
        # 正常场景边缘密度通常 > 0.02，遮挡场景 < 0.01

        # 2. 全局对比度 - 真正被遮挡的图像对比度极低
        global_contrast = float(gray.std())
        # 正常场景对比度通常 > 30，遮挡场景 < 10

        # 3. 颜色多样性分析 - 真正被遮挡的图像颜色单一
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hue_std = float(hsv[:, :, 0].std())  # 色调标准差
        saturation_mean = float(hsv[:, :, 1].mean())  # 平均饱和度
        # 正常场景色调std > 20，遮挡场景 < 5

        # 4. 亮度分布分析 - 真正被遮挡的图像亮度分布极窄
        brightness_range = float(gray.max() - gray.min())
        brightness_std = float(gray.std())
        # 正常场景亮度范围 > 100，遮挡场景 < 30

        # 5. 局部纹理复杂度（仅用于极端情况判断）
        kernel_size = 31
        local_mean = cv2.blur(gray.astype(float), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (kernel_size, kernel_size)
        )
        local_var = local_sq_mean - local_mean ** 2
        local_std = np.sqrt(np.maximum(local_var, 0))

        # 极低纹理区域比例（阈值更严格）
        very_low_texture_mask = local_std < 2  # 更严格的阈值
        very_low_texture_ratio = float(np.sum(very_low_texture_mask)) / (h * w)

        # 6. 分块均匀性（更严格的标准）
        block_size = 32  # 更大的块
        blocks_h = h // block_size
        blocks_w = w // block_size

        very_uniform_blocks = 0
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = gray[
                    i * block_size : (i + 1) * block_size,
                    j * block_size : (j + 1) * block_size,
                ]
                # 更严格的均匀性判断
                if block.std() < 2 and (block.max() - block.min()) < 10:
                    very_uniform_blocks += 1

        very_uniform_ratio = very_uniform_blocks / max(blocks_h * blocks_w, 1)

        # ========== 综合判断 ==========

        # 判断是否是真正的遮挡，需要多个强特征同时满足
        occlusion_indicators = []

        # 指标1: 边缘极度稀疏（权重0.25）
        edge_score = max(0, 1 - edge_density * 50)  # 边缘密度 < 0.02 才开始计分
        occlusion_indicators.append(edge_score * 0.25)

        # 指标2: 对比度极低（权重0.25）
        contrast_score = max(0, 1 - global_contrast / 40)  # 对比度 < 40 才开始计分
        occlusion_indicators.append(contrast_score * 0.25)

        # 指标3: 颜色极度单一（权重0.2）
        color_score = max(0, 1 - hue_std / 30)  # 色调std < 30 才开始计分
        occlusion_indicators.append(color_score * 0.2)

        # 指标4: 亮度范围极窄（权重0.15）
        brightness_score = max(0, 1 - brightness_range / 100)  # 亮度范围 < 100 才开始计分
        occlusion_indicators.append(brightness_score * 0.15)

        # 指标5: 大面积极度均匀区域（权重0.15）
        uniform_score = very_uniform_ratio  # 直接使用比例
        occlusion_indicators.append(uniform_score * 0.15)

        # 综合得分
        occlusion_score = sum(occlusion_indicators)
        occlusion_score = max(0, min(1, occlusion_score))

        # 额外检查：如果图像有足够的边缘和对比度，即使有低纹理区域也不是遮挡
        if edge_density > 0.03 and global_contrast > 35:
            # 有清晰的场景结构，大幅降低遮挡评分
            occlusion_score *= 0.3

        # 额外检查：如果颜色多样性足够，不太可能是遮挡
        if hue_std > 25 and saturation_mean > 20:
            # 有丰富的颜色，不太可能是遮挡
            occlusion_score *= 0.5

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
            "edge_density": edge_density,
            "global_contrast": global_contrast,
            "hue_std": hue_std,
            "saturation_mean": saturation_mean,
            "brightness_range": brightness_range,
            "very_low_texture_ratio": very_low_texture_ratio,
            "very_uniform_ratio": very_uniform_ratio,
            "occlusion_threshold": self.occlusion_threshold,
            "sub_scores": {
                "edge_score": edge_score,
                "contrast_score": contrast_score,
                "color_score": color_score,
                "brightness_score": brightness_score,
                "uniform_score": uniform_score,
            },
        }

        if level == DetectionLevel.DEEP:
            # 深度分析：定位遮挡区域
            occlusion_map = self._create_occlusion_map(gray)
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

    def _create_occlusion_map(self, gray: np.ndarray) -> np.ndarray:
        """创建遮挡热力图"""
        # 计算局部标准差
        kernel_size = 31
        local_mean = cv2.blur(gray.astype(float), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (kernel_size, kernel_size)
        )
        local_var = local_sq_mean - local_mean ** 2
        local_std = np.sqrt(np.maximum(local_var, 0))

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
        elif score <= 0.7:
            return Severity.INFO
        elif score <= 0.85:
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

