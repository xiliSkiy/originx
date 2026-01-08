# -*- coding: utf-8 -*-
"""
视频诊断流水线

协调视频检测器执行和结果聚合
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

import numpy as np

from .detectors.video.base import BaseVideoDetector, VideoDetectionResult, VideoSegment
from .detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
from .utils.video_utils import (
    VideoLoader,
    VideoMetadata,
    FrameSampler,
    SampleStrategy,
)

logger = logging.getLogger(__name__)


@dataclass
class VideoIssue:
    """视频问题"""
    issue_type: str              # 问题类型
    severity: str                # 严重程度
    start_time: float            # 开始时间
    end_time: float              # 结束时间
    duration: float              # 持续时间
    confidence: float            # 置信度
    description: str             # 描述
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "confidence": self.confidence,
            "description": self.description,
        }


@dataclass
class VideoDiagnosisResult:
    """视频诊断结果"""
    video_path: str                      # 视频路径
    video_id: str                        # 视频ID
    
    # 视频元数据
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    frame_count: int = 0
    sampled_frames: int = 0
    
    # 诊断结果
    is_abnormal: bool = False
    overall_score: float = 100.0
    primary_issue: Optional[str] = None
    severity: str = "normal"
    
    # 问题列表
    issues: List[VideoIssue] = field(default_factory=list)
    
    # 检测器结果
    detection_results: List[VideoDetectionResult] = field(default_factory=list)
    
    # 处理信息
    process_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": self.video_path,
            "video_id": self.video_id,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration": self.duration,
            "frame_count": self.frame_count,
            "sampled_frames": self.sampled_frames,
            "is_abnormal": self.is_abnormal,
            "overall_score": self.overall_score,
            "primary_issue": self.primary_issue,
            "severity": self.severity,
            "issues": [issue.to_dict() for issue in self.issues],
            "detection_results": [r.to_dict() for r in self.detection_results],
            "process_time_ms": self.process_time_ms,
        }


class VideoDiagnosisPipeline:
    """视频诊断流水线"""
    
    # 默认检测器
    DEFAULT_DETECTORS = [
        FreezeDetector,
        SceneChangeDetector,
        ShakeDetector,
    ]
    
    def __init__(
        self,
        detectors: Optional[List[Type[BaseVideoDetector]]] = None,
        detector_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        sample_strategy: SampleStrategy = SampleStrategy.INTERVAL,
        sample_interval: float = 1.0,
        max_frames: int = 300,
    ):
        """
        初始化视频诊断流水线
        
        Args:
            detectors: 检测器类列表，None 表示使用默认检测器
            detector_configs: 检测器配置，key 为检测器名称
            sample_strategy: 采样策略
            sample_interval: 采样间隔（秒）
            max_frames: 最大采样帧数
        """
        self.detector_configs = detector_configs or {}
        self.sample_strategy = sample_strategy
        self.sample_interval = sample_interval
        self.max_frames = max_frames
        
        # 初始化检测器
        detector_classes = detectors or self.DEFAULT_DETECTORS
        self.detectors: List[BaseVideoDetector] = []
        for detector_cls in detector_classes:
            config = self.detector_configs.get(detector_cls.name, {})
            self.detectors.append(detector_cls(config))
    
    def diagnose(
        self,
        video_path: str,
        include_frame_results: bool = False
    ) -> VideoDiagnosisResult:
        """
        诊断视频
        
        Args:
            video_path: 视频文件路径
            include_frame_results: 是否包含逐帧结果
            
        Returns:
            VideoDiagnosisResult: 诊断结果
        """
        start_time = time.time()
        
        # 生成视频ID
        video_id = Path(video_path).stem
        
        # 加载视频
        try:
            loader = VideoLoader(video_path)
            metadata = loader.metadata
        except Exception as e:
            logger.error(f"加载视频失败: {video_path}, 错误: {e}")
            raise
        
        # 采样帧
        sampler = FrameSampler(
            strategy=self.sample_strategy,
            interval=self.sample_interval,
            max_frames=self.max_frames,
        )
        frames, indices, timestamps = sampler.sample(loader)
        
        if len(frames) == 0:
            logger.warning(f"视频采样结果为空: {video_path}")
            return VideoDiagnosisResult(
                video_path=video_path,
                video_id=video_id,
                width=metadata.width,
                height=metadata.height,
                fps=metadata.fps,
                duration=metadata.duration,
                frame_count=metadata.frame_count,
                sampled_frames=0,
                is_abnormal=True,
                overall_score=0.0,
                primary_issue="no_frames",
                severity="error",
                process_time_ms=(time.time() - start_time) * 1000,
            )
        
        # 执行检测
        detection_results = []
        for detector in self.detectors:
            try:
                result = detector.detect(frames, metadata.fps, timestamps)
                detection_results.append(result)
            except Exception as e:
                logger.error(f"检测器 {detector.name} 执行失败: {e}")
        
        # 聚合结果
        result = self._aggregate_results(
            video_path=video_path,
            video_id=video_id,
            metadata=metadata,
            sampled_frames=len(frames),
            detection_results=detection_results,
        )
        
        result.process_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _aggregate_results(
        self,
        video_path: str,
        video_id: str,
        metadata: VideoMetadata,
        sampled_frames: int,
        detection_results: List[VideoDetectionResult],
    ) -> VideoDiagnosisResult:
        """聚合检测结果"""
        
        # 收集所有问题
        issues: List[VideoIssue] = []
        abnormal_results = []
        
        for result in detection_results:
            if result.is_abnormal:
                abnormal_results.append(result)
                
                # 将检测结果转换为问题
                for segment in result.segments:
                    issues.append(VideoIssue(
                        issue_type=result.issue_type,
                        severity=result.severity,
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                        duration=segment.duration,
                        confidence=segment.confidence,
                        description=result.explanation,
                    ))
        
        # 按时间排序问题
        issues.sort(key=lambda x: x.start_time)
        
        # 确定主要问题
        primary_issue = None
        max_severity_order = {"normal": 0, "info": 1, "warning": 2, "error": 3}
        max_severity = "normal"
        
        for result in abnormal_results:
            if max_severity_order.get(result.severity, 0) > max_severity_order.get(max_severity, 0):
                max_severity = result.severity
                primary_issue = result.issue_type
        
        # 如果没有找到主要问题但有异常，使用第一个异常
        if primary_issue is None and abnormal_results:
            primary_issue = abnormal_results[0].issue_type
        
        # 计算整体评分
        overall_score = self._calculate_overall_score(detection_results)
        
        # 确定是否异常
        is_abnormal = len(abnormal_results) > 0
        
        return VideoDiagnosisResult(
            video_path=video_path,
            video_id=video_id,
            width=metadata.width,
            height=metadata.height,
            fps=metadata.fps,
            duration=metadata.duration,
            frame_count=metadata.frame_count,
            sampled_frames=sampled_frames,
            is_abnormal=is_abnormal,
            overall_score=overall_score,
            primary_issue=primary_issue,
            severity=max_severity,
            issues=issues,
            detection_results=detection_results,
        )
    
    def _calculate_overall_score(
        self,
        detection_results: List[VideoDetectionResult]
    ) -> float:
        """计算整体评分"""
        if not detection_results:
            return 100.0
        
        # 基于各检测器结果计算加权评分
        total_score = 100.0
        
        severity_penalties = {
            "normal": 0,
            "info": 5,
            "warning": 15,
            "error": 30,
        }
        
        for result in detection_results:
            penalty = severity_penalties.get(result.severity, 0)
            total_score -= penalty
        
        return max(0.0, total_score)
    
    def get_detector_info(self) -> List[Dict[str, Any]]:
        """获取所有检测器信息"""
        return [detector.get_info() for detector in self.detectors]

