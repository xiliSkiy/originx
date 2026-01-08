# -*- coding: utf-8 -*-
"""
视频检测器模块

V1.5 新增的视频质量检测器
"""

from .base import BaseVideoDetector, VideoDetectionResult
from .freeze_detector import FreezeDetector
from .scene_change_detector import SceneChangeDetector
from .shake_detector import ShakeDetector

__all__ = [
    "BaseVideoDetector",
    "VideoDetectionResult",
    "FreezeDetector",
    "SceneChangeDetector",
    "ShakeDetector",
]

