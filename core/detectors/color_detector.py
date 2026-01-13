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

        # ========== 改进：区分真正的色偏和纯色背景/遮挡物 ==========
        # 检测是否有大面积纯色区域（可能是背景或遮挡物）
        solid_color_ratio, dominant_color = self._detect_solid_color_regions(image)
        
        # 检查色偏是否均匀分布在整个图像中
        color_cast_uniformity = self._check_color_cast_uniformity(image, b_mean, g_mean, r_mean)
        
        # 真正的色偏应该是整个图像均匀地偏向某个颜色，而不是因为部分区域是纯色
        is_color_cast = False
        adjusted_deviation = max_deviation
        
        # 如果有大面积纯色区域（>15%）或色偏不均匀，更严格地判断
        if solid_color_ratio > 0.15 or color_cast_uniformity < 0.75:
            # 如果纯色区域占很大比例（>50%），很可能是纯色背景/遮挡物，不是色偏
            if solid_color_ratio > 0.5:
                # 纯色区域占主导，直接判定为不是色偏（除非非纯色区域也有明显色偏）
                if dominant_color != "none":
                    non_solid_mask = self._get_non_solid_color_mask(image, dominant_color)
                    if np.any(non_solid_mask) and np.sum(non_solid_mask) > (h * w * 0.2):
                        # 非纯色区域存在，检查非纯色区域是否有色偏
                        b_mean_adjusted = float(image[non_solid_mask, 0].mean())
                        g_mean_adjusted = float(image[non_solid_mask, 1].mean())
                        r_mean_adjusted = float(image[non_solid_mask, 2].mean())
                        rgb_avg_adjusted = (b_mean_adjusted + g_mean_adjusted + r_mean_adjusted) / 3
                        adjusted_deviation = max(
                            abs(b_mean_adjusted - rgb_avg_adjusted),
                            abs(g_mean_adjusted - rgb_avg_adjusted),
                            abs(r_mean_adjusted - rgb_avg_adjusted),
                        )
                        # 非常严格的阈值：非纯色区域必须明显色偏才判定
                        is_color_cast = adjusted_deviation > self.color_cast_threshold * 2.5
                    else:
                        # 非纯色区域太小，肯定是纯色背景/遮挡物，不是色偏
                        is_color_cast = False
                else:
                    # 无法确定主要颜色，但纯色区域很大，不是色偏
                    is_color_cast = False
            elif solid_color_ratio > 0.2:
                # 纯色区域占20-50%，排除后重新计算
                if dominant_color != "none":
                    non_solid_mask = self._get_non_solid_color_mask(image, dominant_color)
                    if np.any(non_solid_mask) and np.sum(non_solid_mask) > (h * w * 0.3):
                        # 非纯色区域足够大，重新计算
                        b_mean_adjusted = float(image[non_solid_mask, 0].mean())
                        g_mean_adjusted = float(image[non_solid_mask, 1].mean())
                        r_mean_adjusted = float(image[non_solid_mask, 2].mean())
                        rgb_avg_adjusted = (b_mean_adjusted + g_mean_adjusted + r_mean_adjusted) / 3
                        adjusted_deviation = max(
                            abs(b_mean_adjusted - rgb_avg_adjusted),
                            abs(g_mean_adjusted - rgb_avg_adjusted),
                            abs(r_mean_adjusted - rgb_avg_adjusted),
                        )
                        # 大幅提高阈值，减少误报
                        is_color_cast = adjusted_deviation > self.color_cast_threshold * 2.2
                    else:
                        # 非纯色区域太小，可能是纯色背景/遮挡物，不是色偏
                        is_color_cast = False
                else:
                    # 没有明确的纯色区域，但色偏不均匀，可能是局部纯色导致的
                    # 使用更严格的阈值
                    is_color_cast = max_deviation > self.color_cast_threshold * 2.0
            else:
                # 纯色区域15-20%，或色偏不均匀，使用更严格的阈值
                is_color_cast = max_deviation > self.color_cast_threshold * 1.8
        else:
            # 没有大面积纯色区域且色偏均匀，可能是真正的色偏
            # 但仍需要检查是否真的是全局色偏
            is_color_cast = max_deviation > self.color_cast_threshold

        # 检测各种颜色问题
        is_grayscale = mean_saturation < self.saturation_min
        is_blue_screen, blue_confidence = self._detect_solid_color(image, "blue")
        is_green_screen, green_confidence = self._detect_solid_color(image, "green")

        # 确定主要问题（使用调整后的偏差值）
        # 如果有纯色区域或色偏不均匀，使用调整后的偏差值
        final_deviation = adjusted_deviation if (solid_color_ratio > 0.2 or color_cast_uniformity < 0.7) else max_deviation
        issue_type, is_abnormal, severity, confidence = self._determine_issue(
            is_grayscale,
            is_color_cast,
            is_blue_screen,
            is_green_screen,
            mean_saturation,
            final_deviation,
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
            "adjusted_deviation": adjusted_deviation,
            "solid_color_ratio": solid_color_ratio,
            "color_cast_uniformity": color_cast_uniformity,
            "dominant_color": dominant_color,
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
            # 如果有纯色区域，使用调整后的偏差值
            # 如果有纯色区域或色偏不均匀，使用调整后的偏差值
            score = adjusted_deviation if (solid_color_ratio > 0.2 or color_cast_uniformity < 0.7) else max_deviation

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

    def _detect_solid_color_regions(self, image: np.ndarray) -> tuple:
        """
        检测大面积纯色区域（可能是背景或遮挡物）
        
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
        
        local_std = np.sqrt(local_std_b + local_std_g + local_std_r)
        
        # 低变化区域（可能是纯色）- 提高阈值，更容易检测到纯色区域
        low_variation_mask = local_std < 12  # 提高阈值，更容易检测
        solid_color_ratio = float(np.sum(low_variation_mask)) / (h * w)
        
        # 使用HSV空间进一步验证纯色区域（更准确）
        # 在HSV空间中，纯色区域应该有高饱和度且色调集中
        if solid_color_ratio > 0.1:
            low_var_region_hsv = hsv[low_variation_mask]
            if len(low_var_region_hsv) > 0:
                # 检查饱和度（纯色应该有较高饱和度）
                saturation_in_region = low_var_region_hsv[:, 1]
                mean_saturation_in_region = float(np.mean(saturation_in_region))
                
                # 检查色调集中度（纯色区域色调应该集中）
                hue_in_region = low_var_region_hsv[:, 0]
                # 计算色调的标准差（考虑色调的循环性）
                hue_mean = float(np.mean(hue_in_region))
                hue_diff = np.minimum(np.abs(hue_in_region - hue_mean), 180 - np.abs(hue_in_region - hue_mean))
                hue_std = float(np.std(hue_diff))
                
                # 如果饱和度足够高（>80）且色调集中（std < 20），才是真正的纯色区域
                if mean_saturation_in_region > 80 and hue_std < 20:
                    # 这是真正的纯色区域，保持比例
                    pass
                elif mean_saturation_in_region > 60 and hue_std < 30:
                    # 可能是纯色，但稍微降低比例
                    solid_color_ratio *= 0.8
                else:
                    # 不是纯色，大幅降低比例
                    solid_color_ratio *= 0.4
                
                # 进一步检查：在低变化区域内，检查RGB通道的变化
                low_var_region = image[low_variation_mask]
                if len(low_var_region) > 0:
                    # 计算该区域内RGB的标准差
                    b_std_in_region = float(np.std(low_var_region[:, 0]))
                    g_std_in_region = float(np.std(low_var_region[:, 1]))
                    r_std_in_region = float(np.std(low_var_region[:, 2]))
                    
                    # 如果区域内RGB变化很小，才是真正的纯色区域
                    if b_std_in_region > 18 or g_std_in_region > 18 or r_std_in_region > 18:
                        # 区域内颜色变化较大，不是纯色，进一步降低比例
                        solid_color_ratio *= 0.6
        
        # 确定主要颜色（使用HSV空间更准确）
        if solid_color_ratio > 0.1:
            # 在纯色区域内，使用HSV空间计算主要颜色
            low_var_region_hsv = hsv[low_variation_mask]
            if len(low_var_region_hsv) > 0:
                # 计算主要色调（考虑色调的循环性）
                hue_values = low_var_region_hsv[:, 0]
                # 使用中位数更稳健
                dominant_hue = float(np.median(hue_values))
                mean_saturation = float(np.mean(low_var_region_hsv[:, 1]))
                
                # 如果饱和度足够高，根据色调判断颜色
                if mean_saturation > 60:
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
                    # 饱和度不够，可能是灰色调，使用RGB判断
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
                dominant_color = "unknown"
        else:
            dominant_color = "none"
        
        return solid_color_ratio, dominant_color

    def _check_color_cast_uniformity(self, image: np.ndarray, b_mean: float, g_mean: float, r_mean: float) -> float:
        """
        检查色偏是否均匀分布在整个图像中
        
        Returns:
            float: 均匀度（0-1），1表示完全均匀，0表示集中在某个区域
        """
        h, w = image.shape[:2]
        
        # 将图像分成多个块
        block_size = 64
        blocks_h = h // block_size
        blocks_w = w // block_size
        
        if blocks_h < 2 or blocks_w < 2:
            return 1.0  # 图像太小，无法分块
        
        block_deviations = []
        rgb_avg = (b_mean + g_mean + r_mean) / 3
        
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = image[
                    i * block_size : (i + 1) * block_size,
                    j * block_size : (j + 1) * block_size
                ]
                b_block = float(block[:, :, 0].mean())
                g_block = float(block[:, :, 1].mean())
                r_block = float(block[:, :, 2].mean())
                block_avg = (b_block + g_block + r_block) / 3
                
                block_deviation = max(
                    abs(b_block - block_avg),
                    abs(g_block - block_avg),
                    abs(r_block - block_avg),
                )
                block_deviations.append(block_deviation)
        
        if len(block_deviations) == 0:
            return 1.0
        
        # 计算各块偏差的标准差
        # 如果标准差小，说明各块偏差接近，色偏均匀分布
        # 如果标准差大，说明某些块偏差大，某些块偏差小，色偏不均匀
        block_deviations = np.array(block_deviations)
        mean_deviation = float(block_deviations.mean())
        std_deviation = float(block_deviations.std())
        
        if mean_deviation < 1:
            return 1.0  # 几乎没有色偏
        
        # 均匀度 = 1 - (标准差 / 平均值)，归一化到0-1
        # 改进：使用变异系数（CV = std/mean）来评估均匀性
        if mean_deviation < 1:
            return 1.0  # 几乎没有色偏，认为是均匀的
        
        cv_coefficient = std_deviation / mean_deviation if mean_deviation > 0 else 0
        # 如果变异系数小（<0.3），说明各块偏差接近，色偏均匀
        # 如果变异系数大（>0.5），说明某些块偏差大，某些块偏差小，色偏不均匀
        if cv_coefficient < 0.3:
            uniformity = 1.0
        elif cv_coefficient > 0.6:
            uniformity = 0.0
        else:
            uniformity = 1.0 - (cv_coefficient - 0.3) / 0.3
        
        return max(0.0, min(1.0, uniformity))

    def _get_non_solid_color_mask(self, image: np.ndarray, dominant_color: str) -> np.ndarray:
        """
        获取非纯色区域的掩码
        
        Args:
            image: BGR图像
            dominant_color: 主要纯色（"red", "green", "blue"等）
        
        Returns:
            np.ndarray: 布尔掩码，True表示非纯色区域
        """
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 根据主要颜色创建掩码
        if dominant_color == "red":
            # 红色在HSV中跨越0度和180度
            lower1 = np.array([0, 100, 100])
            upper1 = np.array([10, 255, 255])
            lower2 = np.array([170, 100, 100])
            upper2 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            solid_mask = mask1 | mask2
        elif dominant_color == "green":
            lower = np.array([35, 100, 100])
            upper = np.array([85, 255, 255])
            solid_mask = cv2.inRange(hsv, lower, upper)
        elif dominant_color == "blue":
            lower = np.array([100, 100, 100])
            upper = np.array([130, 255, 255])
            solid_mask = cv2.inRange(hsv, lower, upper)
        else:
            # 未知颜色，返回全True（不排除任何区域）
            return np.ones((h, w), dtype=bool)
        
        # 反转掩码，得到非纯色区域
        non_solid_mask = ~(solid_mask.astype(bool))
        return non_solid_mask

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

