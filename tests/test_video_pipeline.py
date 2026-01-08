# -*- coding: utf-8 -*-
"""
视频处理流水线测试
"""

import tempfile
import numpy as np
import pytest
import cv2
from pathlib import Path

from core.video_pipeline import VideoDiagnosisPipeline, VideoDiagnosisResult
from core.utils.video_utils import (
    VideoLoader,
    FrameSampler,
    FrameBuffer,
    SampleStrategy,
    calculate_frame_similarity,
)


def create_test_video(duration_sec: float = 2.0, fps: int = 30) -> str:
    """创建测试视频文件"""
    frame_count = int(duration_sec * fps)
    width, height = 640, 480
    
    # 创建临时文件
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tmp_path = tmp.name
    tmp.close()
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
    
    for i in range(frame_count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # 添加动态内容
        cv2.rectangle(frame, (50 + i % 100, 50), (200 + i % 100, 200), (255, 255, 255), -1)
        cv2.circle(frame, (320, 240), 50, (0, 0, 255), -1)
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    
    out.release()
    return tmp_path


def create_frozen_test_video(duration_sec: float = 3.0, fps: int = 30) -> str:
    """创建包含冻结段的测试视频"""
    frame_count = int(duration_sec * fps)
    width, height = 640, 480
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tmp_path = tmp.name
    tmp.close()
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
    
    # 正常帧 (1秒)
    for i in range(fps):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50 + i * 2, 50), (200 + i * 2, 200), (255, 255, 255), -1)
        out.write(frame)
    
    # 冻结帧 (1秒)
    frozen_frame = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(frozen_frame, (100, 100), (300, 300), (128, 128, 128), -1)
    for _ in range(fps):
        out.write(frozen_frame)
    
    # 正常帧 (1秒)
    for i in range(fps):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50 + i * 3, 50), (200 + i * 3, 200), (255, 255, 255), -1)
        out.write(frame)
    
    out.release()
    return tmp_path


class TestVideoLoader:
    """视频加载器测试"""
    
    def test_load_video(self):
        """测试加载视频"""
        video_path = create_test_video()
        try:
            loader = VideoLoader(video_path)
            metadata = loader.metadata
            
            assert metadata.width == 640
            assert metadata.height == 480
            assert metadata.fps == 30
            assert metadata.frame_count > 0
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_read_frames(self):
        """测试读取帧"""
        video_path = create_test_video()
        try:
            loader = VideoLoader(video_path)
            frames = list(loader.read_frames())
            
            assert len(frames) > 0
            assert isinstance(frames[0][1], np.ndarray)
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_read_frames_with_step(self):
        """测试按步长读取帧"""
        video_path = create_test_video()
        try:
            loader = VideoLoader(video_path)
            frames = list(loader.read_frames(step=5))
            
            # 应该比全部帧少
            assert len(frames) < loader.metadata.frame_count
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            VideoLoader("/nonexistent/video.mp4")
    
    def test_unsupported_format(self):
        """测试不支持的格式"""
        with pytest.raises(ValueError):
            VideoLoader("/some/file.txt")


class TestFrameSampler:
    """帧采样器测试"""
    
    def test_interval_sampling(self):
        """测试间隔采样"""
        video_path = create_test_video(duration_sec=5.0)
        try:
            loader = VideoLoader(video_path)
            sampler = FrameSampler(
                strategy=SampleStrategy.INTERVAL,
                interval=1.0,
                max_frames=10
            )
            
            frames, indices, timestamps = sampler.sample(loader)
            
            assert len(frames) <= 10
            assert len(frames) == len(indices) == len(timestamps)
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_max_frames_limit(self):
        """测试最大帧数限制"""
        video_path = create_test_video(duration_sec=5.0)
        try:
            loader = VideoLoader(video_path)
            sampler = FrameSampler(
                strategy=SampleStrategy.INTERVAL,
                interval=0.1,
                max_frames=20
            )
            
            frames, _, _ = sampler.sample(loader)
            
            assert len(frames) <= 20
        finally:
            Path(video_path).unlink(missing_ok=True)


class TestFrameBuffer:
    """帧缓冲区测试"""
    
    def test_add_frames(self):
        """测试添加帧"""
        buffer = FrameBuffer(max_size=10)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for i in range(5):
            buffer.add(frame, i, i * 0.033)
        
        assert len(buffer) == 5
    
    def test_max_size(self):
        """测试最大容量"""
        buffer = FrameBuffer(max_size=10)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for i in range(15):
            buffer.add(frame, i, i * 0.033)
        
        assert len(buffer) == 10
    
    def test_clear(self):
        """测试清空"""
        buffer = FrameBuffer(max_size=10)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for i in range(5):
            buffer.add(frame, i, i * 0.033)
        
        buffer.clear()
        assert len(buffer) == 0


class TestFrameSimilarity:
    """帧相似度计算测试"""
    
    def test_identical_frames(self):
        """测试相同帧"""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        similarity = calculate_frame_similarity(frame, frame.copy())
        
        assert similarity > 0.99
    
    def test_different_frames(self):
        """测试不同帧"""
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        frame2 = np.ones((480, 640, 3), dtype=np.uint8) * 255
        
        similarity = calculate_frame_similarity(frame1, frame2)
        
        assert similarity < 0.5


class TestVideoDiagnosisPipeline:
    """视频诊断流水线测试"""
    
    def test_diagnose_normal_video(self):
        """测试正常视频诊断"""
        video_path = create_test_video()
        try:
            pipeline = VideoDiagnosisPipeline()
            result = pipeline.diagnose(video_path)
            
            assert isinstance(result, VideoDiagnosisResult)
            assert result.video_path == video_path
            assert result.width == 640
            assert result.height == 480
            assert result.sampled_frames > 0
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_diagnose_frozen_video(self):
        """测试包含冻结的视频诊断"""
        video_path = create_frozen_test_video()
        try:
            pipeline = VideoDiagnosisPipeline(
                sample_strategy=SampleStrategy.ALL,
                max_frames=100,
                detector_configs={
                    "freeze": {"min_freeze_frames": 10}
                }
            )
            result = pipeline.diagnose(video_path)
            
            # 可能检测到冻结
            assert isinstance(result, VideoDiagnosisResult)
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_result_to_dict(self):
        """测试结果序列化"""
        video_path = create_test_video()
        try:
            pipeline = VideoDiagnosisPipeline()
            result = pipeline.diagnose(video_path)
            
            result_dict = result.to_dict()
            
            assert isinstance(result_dict, dict)
            assert 'video_path' in result_dict
            assert 'is_abnormal' in result_dict
            assert 'detection_results' in result_dict
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_get_detector_info(self):
        """测试获取检测器信息"""
        pipeline = VideoDiagnosisPipeline()
        info = pipeline.get_detector_info()
        
        assert len(info) >= 3  # 至少3个检测器
        assert all('name' in d for d in info)

