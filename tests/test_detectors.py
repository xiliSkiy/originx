"""检测器单元测试"""

import pytest
import numpy as np

# 导入检测器
import core.detectors  # noqa
from core import DetectorRegistry, DetectionLevel
from core.detectors import (
    BlurDetector,
    BrightnessDetector,
    ContrastDetector,
    ColorDetector,
    NoiseDetector,
)


class TestBlurDetector:
    """模糊检测器测试"""

    def test_detect_clear_image(self, sample_image):
        """测试清晰图像"""
        detector = BlurDetector({"blur_threshold": 50})
        result = detector.detect(sample_image, DetectionLevel.STANDARD)
        
        # 随机图像应该有较高的laplacian方差
        assert result.score > 0
        assert result.detector_name == "blur"

    def test_detect_blur_image(self, blur_image):
        """测试模糊图像"""
        detector = BlurDetector({"blur_threshold": 100})
        result = detector.detect(blur_image, DetectionLevel.STANDARD)
        
        # 模糊图像得分应该较低
        assert result.is_abnormal
        assert result.issue_type == "blur"
        assert len(result.possible_causes) > 0
        assert len(result.suggestions) > 0

    def test_detection_levels(self, sample_image):
        """测试不同检测级别"""
        detector = BlurDetector()
        
        result_fast = detector.detect(sample_image, DetectionLevel.FAST)
        result_standard = detector.detect(sample_image, DetectionLevel.STANDARD)
        result_deep = detector.detect(sample_image, DetectionLevel.DEEP)
        
        # 深度检测应该有更多证据
        assert len(result_deep.evidence) >= len(result_fast.evidence)


class TestBrightnessDetector:
    """亮度检测器测试"""

    def test_detect_normal_brightness(self, sample_image):
        """测试正常亮度图像"""
        detector = BrightnessDetector()
        result = detector.detect(sample_image, DetectionLevel.STANDARD)
        
        assert not result.is_abnormal
        assert result.issue_type == "brightness_normal"

    def test_detect_dark_image(self, dark_image):
        """测试过暗图像"""
        detector = BrightnessDetector({"brightness_min": 20})
        result = detector.detect(dark_image, DetectionLevel.STANDARD)
        
        assert result.is_abnormal
        assert result.issue_type == "too_dark"

    def test_detect_bright_image(self, bright_image):
        """测试过亮图像"""
        detector = BrightnessDetector({"brightness_max": 235})
        result = detector.detect(bright_image, DetectionLevel.STANDARD)
        
        assert result.is_abnormal
        assert result.issue_type == "too_bright"


class TestColorDetector:
    """颜色检测器测试"""

    def test_detect_normal_color(self, sample_image):
        """测试正常颜色图像"""
        detector = ColorDetector()
        result = detector.detect(sample_image, DetectionLevel.STANDARD)
        
        assert result.detector_name == "color"

    def test_detect_blue_screen(self, blue_screen_image):
        """测试蓝屏检测"""
        detector = ColorDetector()
        result = detector.detect(blue_screen_image, DetectionLevel.STANDARD)
        
        assert result.is_abnormal
        assert result.issue_type == "blue_screen"

    def test_detect_grayscale(self, grayscale_image):
        """测试灰度图像检测"""
        detector = ColorDetector({"saturation_min": 10})
        result = detector.detect(grayscale_image, DetectionLevel.STANDARD)
        
        # 灰度图像饱和度应该很低
        assert result.evidence.get("mean_saturation", 100) < 10


class TestNoiseDetector:
    """噪声检测器测试"""

    def test_detect_clean_image(self, sample_image):
        """测试干净图像"""
        detector = NoiseDetector({"noise_threshold": 50})
        result = detector.detect(sample_image, DetectionLevel.STANDARD)
        
        assert result.detector_name == "noise"

    def test_detect_noisy_image(self, noisy_image):
        """测试噪声图像"""
        detector = NoiseDetector({"noise_threshold": 10})
        result = detector.detect(noisy_image, DetectionLevel.STANDARD)
        
        # 噪声图像得分应该较高
        assert result.score > 10


class TestDetectorRegistry:
    """检测器注册表测试"""

    def test_list_detectors(self):
        """测试列出检测器"""
        detectors = DetectorRegistry.list_detectors()
        
        assert len(detectors) >= 5
        
        names = [d["name"] for d in detectors]
        assert "blur" in names
        assert "brightness" in names
        assert "color" in names

    def test_get_detector(self):
        """测试获取检测器"""
        detector = DetectorRegistry.get("blur")
        
        assert detector is not None
        assert detector.name == "blur"

    def test_get_by_level(self):
        """测试按级别获取检测器"""
        fast_detectors = DetectorRegistry.get_by_level(DetectionLevel.FAST)
        
        assert len(fast_detectors) > 0

