# -*- coding: utf-8 -*-
"""
视频检测器测试
"""

import numpy as np
import pytest
import cv2

from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
from core.detectors.video.base import VideoDetectionResult


def create_test_frames(count: int = 30, width: int = 640, height: int = 480) -> list:
    """创建测试帧"""
    frames = []
    for i in range(count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # 添加一些变化，模拟真实视频
        cv2.rectangle(frame, (50 + i * 2, 50), (200 + i * 2, 200), (255, 255, 255), -1)
        cv2.circle(frame, (320 + i, 240), 30, (0, 0, 255), -1)
        frames.append(frame)
    return frames


def create_frozen_frames(count: int = 60) -> list:
    """创建包含冻结段的测试帧"""
    frames = []
    
    # 正常帧 (0-19)
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50 + i * 2, 50), (200 + i * 2, 200), (255, 255, 255), -1)
        frames.append(frame)
    
    # 冻结帧 (20-49) - 完全相同的帧
    frozen_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frozen_frame, (100, 100), (300, 300), (128, 128, 128), -1)
    for _ in range(30):
        frames.append(frozen_frame.copy())
    
    # 正常帧 (50-59)
    for i in range(10):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50 + i * 3, 50), (200 + i * 3, 200), (255, 255, 255), -1)
        frames.append(frame)
    
    return frames


def create_scene_change_frames(count: int = 60) -> list:
    """创建包含场景变化的测试帧"""
    frames = []
    
    # 场景1: 红色背景 (0-19)
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (0, 0, 200)  # 红色
        cv2.circle(frame, (320 + i, 240), 50, (255, 255, 255), -1)
        frames.append(frame)
    
    # 场景2: 蓝色背景 (20-39) - 场景变化
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (200, 0, 0)  # 蓝色
        cv2.rectangle(frame, (100 + i, 100), (300 + i, 300), (0, 255, 0), -1)
        frames.append(frame)
    
    # 场景3: 绿色背景 (40-59) - 另一次场景变化
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (0, 200, 0)  # 绿色
        cv2.circle(frame, (320, 240), 100 - i, (255, 0, 255), -1)
        frames.append(frame)
    
    return frames


def create_shaky_frames(count: int = 60) -> list:
    """创建包含抖动的测试帧"""
    frames = []
    base_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(base_frame, (100, 100), (540, 380), (255, 255, 255), -1)
    cv2.circle(base_frame, (320, 240), 80, (0, 0, 255), -1)
    
    np.random.seed(42)
    for i in range(count):
        # 添加随机偏移（模拟抖动）
        dx = np.random.randint(-15, 15)
        dy = np.random.randint(-15, 15)
        
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        frame = cv2.warpAffine(base_frame, M, (640, 480))
        frames.append(frame)
    
    return frames


class TestFreezeDetector:
    """画面冻结检测器测试"""
    
    def test_detect_normal_video(self):
        """测试正常视频不应检测出冻结"""
        frames = create_test_frames(30)
        detector = FreezeDetector()
        result = detector.detect(frames, fps=30)
        
        assert isinstance(result, VideoDetectionResult)
        assert result.is_abnormal is False
        assert result.detector_name == "freeze"
    
    def test_detect_frozen_video(self):
        """测试包含冻结的视频应正确检测"""
        frames = create_frozen_frames(60)
        detector = FreezeDetector(config={"min_freeze_frames": 10})
        result = detector.detect(frames, fps=30)
        
        assert result.is_abnormal is True
        assert result.issue_type == "freeze"
        assert len(result.segments) > 0
    
    def test_freeze_duration(self):
        """测试冻结时长计算"""
        frames = create_frozen_frames(60)
        detector = FreezeDetector(config={"min_freeze_frames": 10, "min_freeze_duration": 0.5})
        result = detector.detect(frames, fps=30)
        
        assert result.is_abnormal is True
        assert result.score > 0  # 冻结时长应大于0
    
    def test_ignore_short_freeze(self):
        """测试忽略短暂的相似帧"""
        # 只有5帧相同，不应被检测为冻结
        frames = []
        for i in range(20):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (i * 10, 50), (200 + i * 10, 200), (255, 255, 255), -1)
            frames.append(frame)
        
        # 添加5帧相同的
        same_frame = frames[-1].copy()
        for _ in range(5):
            frames.append(same_frame.copy())
        
        detector = FreezeDetector(config={"min_freeze_frames": 30})
        result = detector.detect(frames, fps=30)
        
        assert result.is_abnormal is False


class TestSceneChangeDetector:
    """场景变换检测器测试"""
    
    def test_detect_stable_video(self):
        """测试稳定场景不应检测出频繁变化"""
        frames = create_test_frames(60)
        detector = SceneChangeDetector(config={"max_changes_per_minute": 10})
        result = detector.detect(frames, fps=30)
        
        assert isinstance(result, VideoDetectionResult)
        assert result.detector_name == "scene_change"
    
    def test_detect_scene_changes(self):
        """测试场景变换应正确检测"""
        frames = create_scene_change_frames(60)
        detector = SceneChangeDetector(config={
            "histogram_threshold": 0.3,
            "max_changes_per_minute": 1
        })
        result = detector.detect(frames, fps=30)
        
        # 应检测到场景变化
        assert len(result.segments) >= 2  # 至少2次场景变化
    
    def test_result_structure(self):
        """测试结果结构完整性"""
        frames = create_test_frames(30)
        detector = SceneChangeDetector()
        result = detector.detect(frames, fps=30)
        
        assert hasattr(result, 'detector_name')
        assert hasattr(result, 'is_abnormal')
        assert hasattr(result, 'score')
        assert hasattr(result, 'threshold')
        assert hasattr(result, 'explanation')
        assert hasattr(result, 'evidence')


class TestShakeDetector:
    """视频抖动检测器测试"""
    
    def test_detect_stable_video(self):
        """测试稳定视频不应检测出抖动"""
        frames = create_test_frames(30)
        detector = ShakeDetector(config={"variance_threshold": 50.0})
        result = detector.detect(frames, fps=30)
        
        assert isinstance(result, VideoDetectionResult)
        assert result.detector_name == "shake"
        assert result.is_abnormal is False
    
    def test_detect_shaky_video(self):
        """测试抖动视频应正确检测"""
        frames = create_shaky_frames(60)
        detector = ShakeDetector(config={"variance_threshold": 5.0})
        result = detector.detect(frames, fps=30)
        
        # 应检测到抖动
        assert result.score > 0
    
    def test_motion_evidence(self):
        """测试运动证据数据"""
        frames = create_test_frames(30)
        detector = ShakeDetector()
        result = detector.detect(frames, fps=30)
        
        assert 'motion_variance' in result.evidence
        assert 'max_motion' in result.evidence
        assert 'avg_motion' in result.evidence


class TestVideoDetectorBase:
    """视频检测器基类测试"""
    
    def test_empty_frames(self):
        """测试空帧列表"""
        detector = FreezeDetector()
        result = detector.detect([], fps=30)
        
        assert result.is_abnormal is False
        assert result.frames_analyzed == 0
    
    def test_single_frame(self):
        """测试单帧"""
        frames = create_test_frames(1)
        detector = FreezeDetector()
        result = detector.detect(frames, fps=30)
        
        assert result.is_abnormal is False
    
    def test_custom_timestamps(self):
        """测试自定义时间戳"""
        frames = create_test_frames(30)
        timestamps = [i * 0.5 for i in range(30)]  # 自定义时间戳
        
        detector = FreezeDetector()
        result = detector.detect(frames, fps=30, timestamps=timestamps)
        
        assert result.is_abnormal is False
    
    def test_result_to_dict(self):
        """测试结果序列化"""
        frames = create_test_frames(30)
        detector = FreezeDetector()
        result = detector.detect(frames, fps=30)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'detector_name' in result_dict
        assert 'is_abnormal' in result_dict
        assert 'score' in result_dict
        assert 'segments' in result_dict

