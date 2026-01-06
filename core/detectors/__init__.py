"""检测器模块 - 自动注册所有检测器"""

# 导入所有检测器以触发注册
from .blur_detector import BlurDetector
from .brightness_detector import BrightnessDetector
from .contrast_detector import ContrastDetector
from .color_detector import ColorDetector
from .noise_detector import NoiseDetector
from .stripe_detector import StripeDetector
from .occlusion_detector import OcclusionDetector
from .signal_loss_detector import SignalLossDetector

__all__ = [
    "BlurDetector",
    "BrightnessDetector",
    "ContrastDetector",
    "ColorDetector",
    "NoiseDetector",
    "StripeDetector",
    "OcclusionDetector",
    "SignalLossDetector",
]

