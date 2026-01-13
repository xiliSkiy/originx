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

    DEFAULT_THRESHOLD = 0.25  # 降低阈值，提高对遮挡的敏感度

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

        # ========== 局部遮挡检测（改进版）==========
        # 检测图像中是否有大面积的低纹理区域（可能是前景物体遮挡）
        # 关键改进：区分"自然前景元素"（植被、树木）和"真正的遮挡"（容器、墙壁、帐篷等）
        local_occlusion_score = 0.0
        
        # 使用更大的核来检测大面积均匀区域
        large_kernel_size = 51
        large_local_mean = cv2.blur(gray.astype(float), (large_kernel_size, large_kernel_size))
        large_local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (large_kernel_size, large_kernel_size)
        )
        large_local_var = large_local_sq_mean - large_local_mean ** 2
        large_local_std = np.sqrt(np.maximum(large_local_var, 0))
        
        # 检测大面积低纹理区域（可能是遮挡物）
        # 放宽阈值，更容易检测到遮挡
        low_texture_mask = large_local_std < 6  # 稍微放宽低纹理阈值
        low_texture_ratio = float(np.sum(low_texture_mask)) / (h * w)
        
        # 检测大面积低边缘区域
        large_edge_kernel = 51
        edge_density_map = cv2.filter2D(
            (edges > 0).astype(np.float32), 
            -1, 
            np.ones((large_edge_kernel, large_edge_kernel)) / (large_edge_kernel * large_edge_kernel)
        )
        low_edge_mask = edge_density_map < 0.015  # 稍微放宽边缘密度阈值
        low_edge_ratio = float(np.sum(low_edge_mask)) / (h * w)
        
        # 检测大面积单一颜色区域
        hue_std_map = cv2.filter2D(
            (hsv[:, :, 0].astype(np.float32) - hsv[:, :, 0].mean()) ** 2,
            -1,
            np.ones((large_kernel_size, large_kernel_size)) / (large_kernel_size * large_kernel_size)
        )
        hue_std_map = np.sqrt(hue_std_map)
        low_color_mask = hue_std_map < 12  # 稍微放宽颜色变化阈值
        low_color_ratio = float(np.sum(low_color_mask)) / (h * w)
        
        # ========== 新增：检测纯色遮挡物（如红色帐篷、金属表面等）==========
        # 纯色遮挡物的特征：大面积区域颜色高度一致，且饱和度较高
        # 使用与color_detector类似的方法检测纯色区域
        solid_color_ratio, dominant_color = self._detect_solid_color_regions(image)
        # 进一步降低阈值：如果纯色区域占比较大（>8%），很可能是遮挡物
        solid_color_occlusion_score = 0.0
        if solid_color_ratio > 0.08:
            # 纯色区域越大，遮挡可能性越高
            solid_color_occlusion_score = min(1.0, (solid_color_ratio - 0.08) * 2.5)  # 更激进的计分
            # 如果纯色区域占主导（>25%），直接认为是遮挡
            if solid_color_ratio > 0.25:
                solid_color_occlusion_score = min(1.0, solid_color_ratio * 1.8)  # 更激进的计分
            # 如果纯色区域非常大（>40%），直接给高分
            if solid_color_ratio > 0.4:
                solid_color_occlusion_score = 0.95
        
        # ========== 新增：检测前景大面积遮挡（如树叶、帐篷等占据画面很大比例）==========
        # 即使有纹理，如果前景物体占据画面很大比例，也应该算遮挡
        foreground_occlusion_score = 0.0
        
        # 方法1：检测大面积单一色调区域（如绿色树叶、红色帐篷）
        # 即使有纹理，如果颜色相对单一且占据很大比例，可能是前景遮挡
        dominant_hue_ratio = self._detect_dominant_hue_region(hsv, threshold=0.4)  # 检测占40%以上的主色调区域
        if dominant_hue_ratio > 0.4:
            # 如果主色调区域占据很大比例，很可能是前景遮挡
            foreground_occlusion_score = min(1.0, (dominant_hue_ratio - 0.4) * 2.0)
            if dominant_hue_ratio > 0.5:
                foreground_occlusion_score = min(1.0, dominant_hue_ratio * 1.5)
        
        # 方法2：检测大面积低对比度区域（前景遮挡物通常对比度较低）
        # 使用更大的核检测大面积低对比度区域
        very_large_kernel = 71
        very_large_local_mean = cv2.blur(gray.astype(float), (very_large_kernel, very_large_kernel))
        very_large_local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (very_large_kernel, very_large_kernel)
        )
        very_large_local_var = very_large_local_sq_mean - very_large_local_mean ** 2
        very_large_local_std = np.sqrt(np.maximum(very_large_local_var, 0))
        
        # 检测大面积低对比度区域（可能是前景遮挡）
        low_contrast_mask = very_large_local_std < 8  # 放宽阈值
        low_contrast_ratio = float(np.sum(low_contrast_mask)) / (h * w)
        
        if low_contrast_ratio > 0.35:  # 如果低对比度区域占35%以上
            foreground_occlusion_score = max(foreground_occlusion_score, min(0.8, (low_contrast_ratio - 0.35) * 2.0))
        
        # ========== 新增：检测结构性遮挡（如柱子、横梁等）==========
        structural_occlusion_score = 0.0
        
        # 检测长条形/线性的均匀区域（可能是柱子、横梁等）
        # 使用方向性检测
        # 水平方向检测
        horizontal_kernel = np.ones((1, 71), np.float32) / 71
        horizontal_uniform = cv2.filter2D(gray.astype(np.float32), -1, horizontal_kernel)
        horizontal_std = cv2.filter2D((gray.astype(np.float32) - horizontal_uniform) ** 2, -1, horizontal_kernel)
        horizontal_std = np.sqrt(horizontal_std)
        horizontal_uniform_mask = horizontal_std < 5  # 水平方向均匀的区域
        
        # 垂直方向检测
        vertical_kernel = np.ones((71, 1), np.float32) / 71
        vertical_uniform = cv2.filter2D(gray.astype(np.float32), -1, vertical_kernel)
        vertical_std = cv2.filter2D((gray.astype(np.float32) - vertical_uniform) ** 2, -1, vertical_kernel)
        vertical_std = np.sqrt(vertical_std)
        vertical_uniform_mask = vertical_std < 5  # 垂直方向均匀的区域
        
        # 对角线方向检测（用于检测斜向的柱子）
        diagonal_kernel1 = np.eye(71, dtype=np.float32) / 71
        diagonal_uniform1 = cv2.filter2D(gray.astype(np.float32), -1, diagonal_kernel1)
        diagonal_var1 = cv2.filter2D((gray.astype(np.float32) - diagonal_uniform1) ** 2, -1, diagonal_kernel1)
        # 避免负数，防止 sqrt 警告
        diagonal_std1 = np.sqrt(np.maximum(diagonal_var1, 0))
        diagonal_uniform_mask1 = diagonal_std1 < 5
        
        # 计算结构性遮挡区域
        structural_mask = horizontal_uniform_mask | vertical_uniform_mask | diagonal_uniform_mask1
        structural_ratio = float(np.sum(structural_mask)) / (h * w)
        
        if structural_ratio > 0.1:  # 如果结构性遮挡区域占10%以上
            structural_occlusion_score = min(1.0, (structural_ratio - 0.1) * 3.0)
            if structural_ratio > 0.15:
                structural_occlusion_score = min(1.0, structural_ratio * 2.5)
        
        # ========== 关键改进：区分自然前景和真正遮挡 ==========
        # 自然前景元素（植被、树木）的特征：
        # 1. 即使在大面积区域内，局部纹理变化仍然丰富
        # 2. 有较高的局部边缘密度
        # 3. 有颜色变化（虽然可能主要是绿色调）
        # 4. 纹理模式不规则，有细节
        
        # 在低纹理区域内，检查局部特征变化
        # 使用较小的核来检测局部纹理变化
        small_kernel_size = 15
        small_local_mean = cv2.blur(gray.astype(float), (small_kernel_size, small_kernel_size))
        small_local_sq_mean = cv2.blur(
            (gray.astype(float) ** 2), (small_kernel_size, small_kernel_size)
        )
        small_local_var = small_local_sq_mean - small_local_mean ** 2
        small_local_std = np.sqrt(np.maximum(small_local_var, 0))
        
        # 在低纹理区域内，检查是否有局部纹理变化
        # 如果低纹理区域内部仍有局部纹理变化，可能是自然元素而非遮挡
        low_texture_region = low_texture_mask.astype(bool)
        natural_element_factor = 1.0  # 自然元素因子，用于降低遮挡评分
        
        if np.any(low_texture_region):
            # 在低纹理区域内，计算局部纹理的标准差
            local_texture_in_low_region = small_local_std[low_texture_region]
            # 如果低纹理区域内的局部纹理变化较大，说明是自然元素
            if len(local_texture_in_low_region) > 0:
                local_texture_variation = float(np.std(local_texture_in_low_region))
                local_texture_mean = float(np.mean(local_texture_in_low_region))
                # 更严格的判断：需要同时满足纹理变化大且平均纹理值较高
                if local_texture_variation > 4 and local_texture_mean > 2:
                    # 这是自然元素（如植被），降低遮挡评分
                    natural_element_factor = 0.3
                elif local_texture_variation > 3:
                    # 可能是自然元素，适度降低
                    natural_element_factor = 0.6
        
        # 在低边缘区域内，检查是否有局部边缘
        if np.any(low_edge_mask):
            # 使用较小的核检测局部边缘密度
            small_edge_kernel = 15
            small_edge_density = cv2.filter2D(
                (edges > 0).astype(np.float32),
                -1,
                np.ones((small_edge_kernel, small_edge_kernel)) / (small_edge_kernel * small_edge_kernel)
            )
            local_edge_in_low_region = small_edge_density[low_edge_mask]
            if len(local_edge_in_low_region) > 0:
                local_edge_mean = float(np.mean(local_edge_in_low_region))
                local_edge_std = float(np.std(local_edge_in_low_region))
                # 更严格的判断：需要边缘密度较高且变化较大
                if local_edge_mean > 0.008 and local_edge_std > 0.003:
                    # 这是自然元素，进一步降低
                    natural_element_factor = min(natural_element_factor, 0.4)
                elif local_edge_mean > 0.005:
                    natural_element_factor = min(natural_element_factor, 0.7)
        
        # 在低颜色变化区域内，检查是否有局部颜色变化
        if np.any(low_color_mask):
            # 使用较小的核检测局部颜色变化
            small_color_kernel = 15
            small_hue_std = cv2.filter2D(
                (hsv[:, :, 0].astype(np.float32) - hsv[:, :, 0].mean()) ** 2,
                -1,
                np.ones((small_color_kernel, small_color_kernel)) / (small_color_kernel * small_color_kernel)
            )
            small_hue_std = np.sqrt(small_hue_std)
            local_color_in_low_region = small_hue_std[low_color_mask]
            if len(local_color_in_low_region) > 0:
                local_color_mean = float(np.mean(local_color_in_low_region))
                local_color_std = float(np.std(local_color_in_low_region))
                # 更严格的判断：需要颜色变化较大且变化有波动
                if local_color_mean > 8 and local_color_std > 3:
                    # 这是自然元素，进一步降低
                    natural_element_factor = min(natural_element_factor, 0.5)
                elif local_color_mean > 5:
                    natural_element_factor = min(natural_element_factor, 0.8)
        
        # 应用自然元素因子（但纯色遮挡物不受此影响）
        # 提高纯色判断阈值，避免误判
        if solid_color_ratio < 0.15:  # 如果不是明显的纯色遮挡物，才应用自然元素因子
            # 但不要过度降低，保留一定的遮挡可能性
            reduction_factor = max(0.5, natural_element_factor)  # 最多降低50%
            low_texture_ratio *= reduction_factor
            low_edge_ratio *= reduction_factor
            low_color_ratio *= reduction_factor
        
        # 综合局部遮挡指标：如果同时满足低纹理、低边缘、低颜色变化，很可能是遮挡
        # 使用平均值而不是最小值，更宽松的判断
        local_occlusion_ratio = (low_texture_ratio + low_edge_ratio + low_color_ratio) / 3.0
        
        # 进一步降低阈值：从15%降低到12%，以检测更多遮挡情况
        if local_occlusion_ratio > 0.12:
            # 局部遮挡得分：基于遮挡区域的比例，更激进的计分
            local_occlusion_score = min(1.0, (local_occlusion_ratio - 0.12) * 2.5)  # 50%区域遮挡 = 0.95分
        
        # 如果检测到明显的纯色遮挡物，直接使用纯色遮挡评分（降低阈值）
        if solid_color_occlusion_score > 0.15:
            local_occlusion_score = max(local_occlusion_score, solid_color_occlusion_score)
        
        # 如果纯色区域很大，即使其他指标不高，也要提高评分
        if solid_color_ratio > 0.2:
            local_occlusion_score = max(local_occlusion_score, min(0.8, solid_color_ratio * 2.5))
        
        # 合并前景遮挡评分
        if foreground_occlusion_score > 0.2:
            local_occlusion_score = max(local_occlusion_score, foreground_occlusion_score)
        
        # 合并结构性遮挡评分
        if structural_occlusion_score > 0.15:
            local_occlusion_score = max(local_occlusion_score, structural_occlusion_score)
        
        # ========== 综合判断 ==========

        # 判断是否是真正的遮挡，需要多个强特征同时满足
        occlusion_indicators = []

        # 指标1: 边缘极度稀疏（权重0.2）
        edge_score = max(0, 1 - edge_density * 50)  # 边缘密度 < 0.02 才开始计分
        occlusion_indicators.append(edge_score * 0.2)

        # 指标2: 对比度极低（权重0.2）
        contrast_score = max(0, 1 - global_contrast / 40)  # 对比度 < 40 才开始计分
        occlusion_indicators.append(contrast_score * 0.2)

        # 指标3: 颜色极度单一（权重0.15）
        color_score = max(0, 1 - hue_std / 30)  # 色调std < 30 才开始计分
        occlusion_indicators.append(color_score * 0.15)

        # 指标4: 亮度范围极窄（权重0.1）
        brightness_score = max(0, 1 - brightness_range / 100)  # 亮度范围 < 100 才开始计分
        occlusion_indicators.append(brightness_score * 0.1)

        # 指标5: 大面积极度均匀区域（权重0.1）
        uniform_score = very_uniform_ratio  # 直接使用比例
        occlusion_indicators.append(uniform_score * 0.1)

        # 指标6: 局部遮挡（权重0.25）
        occlusion_indicators.append(local_occlusion_score * 0.25)
        
        # 指标7: 纯色遮挡（权重0.15）
        occlusion_indicators.append(solid_color_occlusion_score * 0.15)
        
        # 指标8: 前景遮挡（权重0.15，新增）
        occlusion_indicators.append(foreground_occlusion_score * 0.15)
        
        # 指标9: 结构性遮挡（权重0.1，新增）
        occlusion_indicators.append(structural_occlusion_score * 0.1)

        # 综合得分
        occlusion_score = sum(occlusion_indicators)
        occlusion_score = max(0, min(1, occlusion_score))

        # ========== 优化：调整全局特征检查逻辑 ==========
        # 如果有明显的局部遮挡（包括纯色、前景、结构性遮挡），优先考虑局部遮挡评分
        # 进一步降低判断阈值，更容易触发
        max_local_score = max(local_occlusion_score, solid_color_occlusion_score, foreground_occlusion_score, structural_occlusion_score)
        
        if max_local_score > 0.15:  # 进一步降低阈值
            # 有明显的局部遮挡，即使整体特征丰富，也要考虑遮挡
            # 局部遮挡权重更高
            occlusion_score = max(occlusion_score, max_local_score * 0.98)
            # 如果多个遮挡指标都很高，进一步提高评分
            if local_occlusion_score > 0.3 or solid_color_occlusion_score > 0.3 or foreground_occlusion_score > 0.3:
                occlusion_score = max(occlusion_score, max_local_score * 1.0)  # 直接使用最高分
        elif edge_density > 0.03 and global_contrast > 35 and max_local_score < 0.12:
            # 只有在没有明显局部遮挡的情况下，才降低全局遮挡评分
            # 有清晰的场景结构且没有局部遮挡，降低全局遮挡评分
            occlusion_score = occlusion_score * 0.5 + max_local_score * 0.5

        # 额外检查：如果颜色多样性足够，且没有局部遮挡，才降低遮挡评分
        # 更严格的条件，避免误降低
        if hue_std > 35 and saturation_mean > 30 and max_local_score < 0.12:
            # 有丰富的颜色且没有局部遮挡，适度降低遮挡评分
            occlusion_score *= 0.7

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
            "brightness_std": brightness_std,
            "very_low_texture_ratio": very_low_texture_ratio,
            "very_uniform_ratio": very_uniform_ratio,
            "local_occlusion_score": local_occlusion_score,
            "local_occlusion_ratio": local_occlusion_ratio,
            "low_texture_ratio": low_texture_ratio,
            "low_edge_ratio": low_edge_ratio,
            "low_color_ratio": low_color_ratio,
            "solid_color_ratio": solid_color_ratio,
            "solid_color_occlusion_score": solid_color_occlusion_score,
            "foreground_occlusion_score": foreground_occlusion_score,
            "structural_occlusion_score": structural_occlusion_score,
            "dominant_color": dominant_color,
            "natural_element_factor": natural_element_factor,
            "low_contrast_ratio": low_contrast_ratio,
            "structural_ratio": structural_ratio,
            "occlusion_threshold": self.occlusion_threshold,
            "sub_scores": {
                "edge_score": edge_score,
                "contrast_score": contrast_score,
                "color_score": color_score,
                "brightness_score": brightness_score,
                "uniform_score": uniform_score,
                "local_occlusion_score": local_occlusion_score,
                "solid_color_occlusion_score": solid_color_occlusion_score,
                "foreground_occlusion_score": foreground_occlusion_score,
                "structural_occlusion_score": structural_occlusion_score,
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

    def _detect_solid_color_regions(self, image: np.ndarray) -> tuple:
        """
        检测大面积纯色区域（可能是遮挡物，如红色帐篷、金属表面等）
        
        Returns:
            Tuple[float, str]: (纯色区域比例, 主要颜色)
        """
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 检测大面积单一颜色区域
        # 使用较大的核来检测大面积均匀区域
        kernel_size = 51
        local_mean_b = cv2.blur(image[:, :, 0].astype(float), (kernel_size, kernel_size))
        local_mean_g = cv2.blur(image[:, :, 1].astype(float), (kernel_size, kernel_size))
        local_mean_r = cv2.blur(image[:, :, 2].astype(float), (kernel_size, kernel_size))
        
        local_std_b = cv2.blur((image[:, :, 0].astype(float) - local_mean_b) ** 2, (kernel_size, kernel_size))
        local_std_g = cv2.blur((image[:, :, 1].astype(float) - local_mean_g) ** 2, (kernel_size, kernel_size))
        local_std_r = cv2.blur((image[:, :, 2].astype(float) - local_mean_r) ** 2, (kernel_size, kernel_size))
        
        # 避免负数，防止 sqrt 警告
        local_std_sum = np.maximum(local_std_b + local_std_g + local_std_r, 0)
        local_std = np.sqrt(local_std_sum)
        
        # 低变化区域（可能是纯色）- 进一步放宽阈值，更容易检测到纯色遮挡物
        low_variation_mask = local_std < 18  # 进一步放宽阈值
        solid_color_ratio = float(np.sum(low_variation_mask)) / (h * w)
        
        # 使用HSV空间进一步验证纯色区域
        if solid_color_ratio > 0.08:  # 降低验证阈值
            low_var_region_hsv = hsv[low_variation_mask]
            if len(low_var_region_hsv) > 0:
                # 检查饱和度（纯色应该有较高饱和度）
                saturation_in_region = low_var_region_hsv[:, 1]
                mean_saturation_in_region = float(np.mean(saturation_in_region))
                
                # 检查色调集中度
                hue_in_region = low_var_region_hsv[:, 0]
                hue_mean = float(np.mean(hue_in_region))
                hue_diff = np.minimum(np.abs(hue_in_region - hue_mean), 180 - np.abs(hue_in_region - hue_mean))
                hue_std = float(np.std(hue_diff))
                
                # 放宽判断条件，更容易识别纯色区域
                if mean_saturation_in_region > 60 and hue_std < 30:
                    # 这是真正的纯色区域，保持比例
                    pass
                elif mean_saturation_in_region > 40 and hue_std < 40:
                    # 可能是纯色，稍微降低比例
                    solid_color_ratio *= 0.9  # 减少降低幅度
                else:
                    # 不是纯色，降低比例（但不要降太多）
                    solid_color_ratio *= 0.7  # 减少降低幅度
                
                # 进一步检查RGB通道的变化（放宽条件）
                low_var_region = image[low_variation_mask]
                if len(low_var_region) > 0:
                    b_std_in_region = float(np.std(low_var_region[:, 0]))
                    g_std_in_region = float(np.std(low_var_region[:, 1]))
                    r_std_in_region = float(np.std(low_var_region[:, 2]))
                    
                    # 如果区域内RGB变化较大，不是纯色（放宽阈值）
                    if b_std_in_region > 25 or g_std_in_region > 25 or r_std_in_region > 25:
                        solid_color_ratio *= 0.8  # 减少降低幅度
        
        # 确定主要颜色
        dominant_color = "none"
        if solid_color_ratio > 0.1:
            low_var_region_hsv = hsv[low_variation_mask]
            if len(low_var_region_hsv) > 0:
                hue_values = low_var_region_hsv[:, 0]
                dominant_hue = float(np.median(hue_values))
                mean_saturation = float(np.mean(low_var_region_hsv[:, 1]))
                
                # 根据色调判断颜色
                if mean_saturation > 50:
                    if (dominant_hue < 10 or dominant_hue > 170):
                        dominant_color = "red"
                    elif 35 < dominant_hue < 85:
                        dominant_color = "green"
                    elif 100 < dominant_hue < 130:
                        dominant_color = "blue"
                    else:
                        # 使用RGB作为备选
                        solid_region = image[low_variation_mask]
                        b_dominant = float(np.median(solid_region[:, 0]))
                        g_dominant = float(np.median(solid_region[:, 1]))
                        r_dominant = float(np.median(solid_region[:, 2]))
                        
                        if r_dominant > g_dominant * 1.2 and r_dominant > b_dominant * 1.2:
                            dominant_color = "red"
                        elif g_dominant > r_dominant * 1.2 and g_dominant > b_dominant * 1.2:
                            dominant_color = "green"
                        elif b_dominant > r_dominant * 1.2 and b_dominant > g_dominant * 1.2:
                            dominant_color = "blue"
                        else:
                            dominant_color = "unknown"
                else:
                    # 饱和度不够，可能是灰色调
                    solid_region = image[low_variation_mask]
                    b_dominant = float(np.median(solid_region[:, 0]))
                    g_dominant = float(np.median(solid_region[:, 1]))
                    r_dominant = float(np.median(solid_region[:, 2]))
                    
                    if r_dominant > g_dominant * 1.2 and r_dominant > b_dominant * 1.2:
                        dominant_color = "red"
                    elif g_dominant > r_dominant * 1.2 and g_dominant > b_dominant * 1.2:
                        dominant_color = "green"
                    elif b_dominant > r_dominant * 1.2 and b_dominant > g_dominant * 1.2:
                        dominant_color = "blue"
                    else:
                        dominant_color = "unknown"
        
        return solid_color_ratio, dominant_color

    def _detect_dominant_hue_region(self, hsv: np.ndarray, threshold: float = 0.4) -> float:
        """
        检测大面积单一色调区域（如绿色树叶、红色帐篷等）
        
        Args:
            hsv: HSV图像
            threshold: 色调集中度阈值（标准差）
        
        Returns:
            float: 主色调区域占图像的比例
        """
        h, w = hsv.shape[:2]
        
        # 计算色调直方图
        hue = hsv[:, :, 0]
        saturation = hsv[:, :, 1]
        
        # 只考虑饱和度较高的区域（排除灰色区域）
        high_sat_mask = saturation > 50
        if np.sum(high_sat_mask) < h * w * 0.1:
            return 0.0  # 如果高饱和度区域太少，返回0
        
        # 计算主色调
        hue_values = hue[high_sat_mask]
        if len(hue_values) == 0:
            return 0.0
        
        # 使用中位数作为主色调（更稳健）
        dominant_hue = float(np.median(hue_values))
        
        # 检测接近主色调的区域
        # 考虑色调的循环性（0度和180度接近）
        hue_diff = np.minimum(
            np.abs(hue - dominant_hue),
            180 - np.abs(hue - dominant_hue)
        )
        
        # 在局部区域内检测色调集中度
        kernel_size = 51
        local_hue_var = cv2.filter2D(
            (hue_diff.astype(np.float32)) ** 2,
            -1,
            np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        )
        # 避免负数，防止 sqrt 警告
        local_hue_std = np.sqrt(np.maximum(local_hue_var, 0))
        
        # 检测色调集中的区域（接近主色调）
        dominant_hue_mask = (local_hue_std < threshold) & (saturation > 40)
        dominant_hue_ratio = float(np.sum(dominant_hue_mask)) / (h * w)
        
        return dominant_hue_ratio

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

