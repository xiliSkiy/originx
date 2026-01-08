# -*- coding: utf-8 -*-
"""
任务执行器模块
"""

from .batch_detect import batch_detect_job
from .sample_detect import sample_detect_job
from .video_detect import video_detect_job

__all__ = [
    "batch_detect_job",
    "sample_detect_job",
    "video_detect_job",
]

