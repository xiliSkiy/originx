# -*- coding: utf-8 -*-
"""
视频处理工具模块

提供视频加载、帧采样、帧缓冲等功能
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SampleStrategy(Enum):
    """帧采样策略"""
    INTERVAL = "interval"      # 固定间隔采样
    SCENE = "scene"            # 场景变化采样
    HYBRID = "hybrid"          # 混合模式
    ALL = "all"                # 全部帧


@dataclass
class VideoMetadata:
    """视频元数据"""
    path: str                  # 文件路径
    width: int                 # 宽度
    height: int                # 高度
    fps: float                 # 帧率
    frame_count: int           # 总帧数
    duration: float            # 时长（秒）
    codec: str = ""            # 编解码器
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "duration": self.duration,
            "codec": self.codec,
        }


class VideoLoader:
    """视频加载器"""
    
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    
    def __init__(self, video_path: str):
        """
        初始化视频加载器
        
        Args:
            video_path: 视频文件路径
        """
        self.video_path = video_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None
        
        # 验证文件
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的视频格式: {path.suffix}")
    
    @property
    def metadata(self) -> VideoMetadata:
        """获取视频元数据"""
        if self._metadata is None:
            self._load_metadata()
        return self._metadata
    
    def _load_metadata(self) -> None:
        """加载视频元数据"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {self.video_path}")
        
        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            
            # 计算时长
            duration = frame_count / fps if fps > 0 else 0.0
            
            self._metadata = VideoMetadata(
                path=self.video_path,
                width=width,
                height=height,
                fps=fps,
                frame_count=frame_count,
                duration=duration,
                codec=codec,
            )
        finally:
            cap.release()
    
    def read_frames(
        self,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        step: int = 1
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        读取视频帧
        
        Args:
            start_frame: 起始帧
            end_frame: 结束帧（不包含）
            step: 步长
            
        Yields:
            (帧索引, 帧图像) 元组
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {self.video_path}")
        
        try:
            metadata = self.metadata
            if end_frame is None:
                end_frame = metadata.frame_count
            
            # 设置起始位置
            if start_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            frame_idx = start_frame
            while frame_idx < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if (frame_idx - start_frame) % step == 0:
                    yield frame_idx, frame
                
                frame_idx += 1
        finally:
            cap.release()
    
    def read_all_frames(self) -> List[np.ndarray]:
        """读取所有帧"""
        frames = []
        for _, frame in self.read_frames():
            frames.append(frame)
        return frames
    
    def read_frame_at(self, frame_index: int) -> Optional[np.ndarray]:
        """读取指定位置的帧"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return None
        
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            return frame if ret else None
        finally:
            cap.release()


class FrameSampler:
    """帧采样器"""
    
    def __init__(
        self,
        strategy: SampleStrategy = SampleStrategy.INTERVAL,
        interval: float = 1.0,
        scene_threshold: float = 0.3,
        max_frames: int = 300,
        min_frames: int = 10
    ):
        """
        初始化帧采样器
        
        Args:
            strategy: 采样策略
            interval: 采样间隔（秒），用于 INTERVAL 和 HYBRID 策略
            scene_threshold: 场景变化阈值，用于 SCENE 和 HYBRID 策略
            max_frames: 最大采样帧数
            min_frames: 最小采样帧数
        """
        self.strategy = strategy
        self.interval = interval
        self.scene_threshold = scene_threshold
        self.max_frames = max_frames
        self.min_frames = min_frames
    
    def sample(
        self,
        video_loader: VideoLoader
    ) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """
        采样视频帧
        
        Args:
            video_loader: 视频加载器
            
        Returns:
            (帧列表, 帧索引列表, 时间戳列表) 元组
        """
        metadata = video_loader.metadata
        
        if self.strategy == SampleStrategy.ALL:
            return self._sample_all(video_loader)
        elif self.strategy == SampleStrategy.INTERVAL:
            return self._sample_interval(video_loader, metadata)
        elif self.strategy == SampleStrategy.SCENE:
            return self._sample_scene(video_loader, metadata)
        else:  # HYBRID
            return self._sample_hybrid(video_loader, metadata)
    
    def _sample_all(
        self,
        video_loader: VideoLoader
    ) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """采样所有帧"""
        frames = []
        indices = []
        timestamps = []
        fps = video_loader.metadata.fps
        
        for idx, frame in video_loader.read_frames():
            if len(frames) >= self.max_frames:
                break
            frames.append(frame)
            indices.append(idx)
            timestamps.append(idx / fps if fps > 0 else 0.0)
        
        return frames, indices, timestamps
    
    def _sample_interval(
        self,
        video_loader: VideoLoader,
        metadata: VideoMetadata
    ) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """固定间隔采样"""
        frames = []
        indices = []
        timestamps = []
        
        # 计算采样步长
        step = max(1, int(metadata.fps * self.interval))
        
        for idx, frame in video_loader.read_frames(step=step):
            if len(frames) >= self.max_frames:
                break
            frames.append(frame)
            indices.append(idx)
            timestamps.append(idx / metadata.fps if metadata.fps > 0 else 0.0)
        
        return frames, indices, timestamps
    
    def _sample_scene(
        self,
        video_loader: VideoLoader,
        metadata: VideoMetadata
    ) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """场景变化采样"""
        frames = []
        indices = []
        timestamps = []
        
        prev_hist = None
        
        for idx, frame in video_loader.read_frames():
            if len(frames) >= self.max_frames:
                break
            
            # 计算直方图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            # 第一帧或场景变化时采样
            if prev_hist is None:
                should_sample = True
            else:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                should_sample = diff > self.scene_threshold
            
            if should_sample:
                frames.append(frame)
                indices.append(idx)
                timestamps.append(idx / metadata.fps if metadata.fps > 0 else 0.0)
                prev_hist = hist
        
        # 确保至少有最小帧数
        if len(frames) < self.min_frames:
            return self._sample_interval(video_loader, metadata)
        
        return frames, indices, timestamps
    
    def _sample_hybrid(
        self,
        video_loader: VideoLoader,
        metadata: VideoMetadata
    ) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """混合采样：固定间隔 + 场景变化"""
        frames = []
        indices = []
        timestamps = []
        
        # 计算采样步长
        step = max(1, int(metadata.fps * self.interval))
        
        prev_hist = None
        last_sampled_idx = -step  # 确保第一帧被采样
        
        for idx, frame in video_loader.read_frames():
            if len(frames) >= self.max_frames:
                break
            
            # 计算直方图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            should_sample = False
            
            # 固定间隔采样
            if idx - last_sampled_idx >= step:
                should_sample = True
            
            # 场景变化采样
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if diff > self.scene_threshold:
                    should_sample = True
            
            if should_sample or prev_hist is None:
                frames.append(frame)
                indices.append(idx)
                timestamps.append(idx / metadata.fps if metadata.fps > 0 else 0.0)
                last_sampled_idx = idx
            
            prev_hist = hist
        
        return frames, indices, timestamps


class FrameBuffer:
    """帧缓冲区"""
    
    def __init__(self, max_size: int = 30):
        """
        初始化帧缓冲区
        
        Args:
            max_size: 最大缓冲帧数
        """
        self.max_size = max_size
        self._frames: List[np.ndarray] = []
        self._indices: List[int] = []
        self._timestamps: List[float] = []
    
    def add(self, frame: np.ndarray, index: int, timestamp: float) -> None:
        """添加帧到缓冲区"""
        self._frames.append(frame)
        self._indices.append(index)
        self._timestamps.append(timestamp)
        
        # 超出最大容量时移除最旧的帧
        while len(self._frames) > self.max_size:
            self._frames.pop(0)
            self._indices.pop(0)
            self._timestamps.pop(0)
    
    def get_frames(self) -> List[np.ndarray]:
        """获取所有帧"""
        return self._frames.copy()
    
    def get_indices(self) -> List[int]:
        """获取所有帧索引"""
        return self._indices.copy()
    
    def get_timestamps(self) -> List[float]:
        """获取所有时间戳"""
        return self._timestamps.copy()
    
    def clear(self) -> None:
        """清空缓冲区"""
        self._frames.clear()
        self._indices.clear()
        self._timestamps.clear()
    
    def __len__(self) -> int:
        return len(self._frames)
    
    def __getitem__(self, index: int) -> Tuple[np.ndarray, int, float]:
        return self._frames[index], self._indices[index], self._timestamps[index]


def calculate_frame_similarity(
    frame1: np.ndarray,
    frame2: np.ndarray,
    method: str = "histogram"
) -> float:
    """
    计算两帧的相似度
    
    Args:
        frame1: 第一帧
        frame2: 第二帧
        method: 计算方法 (histogram, mse, ssim)
        
    Returns:
        相似度 (0-1, 越大越相似)
    """
    if method == "histogram":
        return _histogram_similarity(frame1, frame2)
    elif method == "mse":
        return _mse_similarity(frame1, frame2)
    else:
        # 默认使用直方图
        return _histogram_similarity(frame1, frame2)


def _histogram_similarity(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """直方图相似度"""
    # 转换为灰度图
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # 计算直方图
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
    
    # 归一化
    hist1 = cv2.normalize(hist1, hist1).flatten()
    hist2 = cv2.normalize(hist2, hist2).flatten()
    
    # 计算相关性（值越大越相似）
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    
    # 归一化到 0-1
    return (similarity + 1) / 2


def _mse_similarity(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """MSE 相似度"""
    # 确保尺寸一致
    if frame1.shape != frame2.shape:
        frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))
    
    # 计算 MSE
    mse = np.mean((frame1.astype(float) - frame2.astype(float)) ** 2)
    
    # 转换为相似度（MSE越小越相似）
    # 最大MSE约为 255^2 = 65025
    similarity = 1 - (mse / 65025)
    return max(0, similarity)


def calculate_histogram_difference(
    frame1: np.ndarray,
    frame2: np.ndarray
) -> float:
    """
    计算两帧的直方图差异
    
    Args:
        frame1: 第一帧
        frame2: 第二帧
        
    Returns:
        差异值 (0-1, 越大差异越大)
    """
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
    
    hist1 = cv2.normalize(hist1, hist1).flatten()
    hist2 = cv2.normalize(hist2, hist2).flatten()
    
    # 使用 Bhattacharyya 距离
    return cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)

