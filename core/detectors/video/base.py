# -*- coding: utf-8 -*-
"""
视频检测器基类

定义视频检测器的基本接口和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import numpy as np


class VideoIssueType(Enum):
    """视频问题类型"""
    NORMAL = "normal"
    FREEZE = "freeze"                    # 画面冻结
    SCENE_CHANGE = "scene_change"        # 场景变换
    SHAKE = "shake"                      # 视频抖动
    FLICKER = "flicker"                  # 频闪
    ROLLING = "rolling"                  # 滚屏


@dataclass
class VideoSegment:
    """视频片段信息"""
    start_frame: int                     # 起始帧
    end_frame: int                       # 结束帧
    start_time: float                    # 起始时间（秒）
    end_time: float                      # 结束时间（秒）
    duration: float                      # 持续时长（秒）
    confidence: float = 1.0              # 置信度
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoDetectionResult:
    """视频检测结果"""
    detector_name: str                   # 检测器名称
    is_abnormal: bool                    # 是否异常
    score: float                         # 检测得分
    threshold: float                     # 判定阈值
    confidence: float                    # 置信度
    issue_type: str                      # 问题类型
    severity: str = "normal"             # 严重程度: normal, info, warning, error
    
    # 异常片段列表
    segments: List[VideoSegment] = field(default_factory=list)
    
    # 说明信息
    explanation: str = ""                # 结果解释
    suggestions: List[str] = field(default_factory=list)      # 改进建议
    possible_causes: List[str] = field(default_factory=list)  # 可能原因
    
    # 证据数据
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # 处理信息
    process_time_ms: float = 0.0         # 处理耗时
    frames_analyzed: int = 0             # 分析帧数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "detector_name": self.detector_name,
            "is_abnormal": self.is_abnormal,
            "score": self.score,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "segments": [
                {
                    "start_frame": seg.start_frame,
                    "end_frame": seg.end_frame,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "duration": seg.duration,
                    "confidence": seg.confidence,
                    "metadata": seg.metadata,
                }
                for seg in self.segments
            ],
            "explanation": self.explanation,
            "suggestions": self.suggestions,
            "possible_causes": self.possible_causes,
            "evidence": self.evidence,
            "process_time_ms": self.process_time_ms,
            "frames_analyzed": self.frames_analyzed,
        }


class BaseVideoDetector(ABC):
    """视频检测器基类"""
    
    # 子类必须定义的属性
    name: str = "base_video"
    display_name: str = "基础视频检测器"
    description: str = "视频检测器基类"
    
    # 默认配置
    default_config: Dict[str, Any] = {}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化检测器
        
        Args:
            config: 检测器配置，会与默认配置合并
        """
        self.config = {**self.default_config}
        if config:
            self.config.update(config)
    
    @abstractmethod
    def detect(
        self,
        frames: List[np.ndarray],
        fps: float,
        timestamps: Optional[List[float]] = None
    ) -> VideoDetectionResult:
        """
        执行视频检测
        
        Args:
            frames: 帧列表（BGR格式的numpy数组）
            fps: 视频帧率
            timestamps: 每帧的时间戳（可选）
            
        Returns:
            VideoDetectionResult: 检测结果
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取检测器信息"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "config": self.config,
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(config)
    
    def _calculate_severity(self, score: float, threshold: float) -> str:
        """根据得分计算严重程度"""
        if score <= threshold:
            return "normal"
        ratio = score / threshold if threshold > 0 else float('inf')
        if ratio < 1.5:
            return "info"
        elif ratio < 2.0:
            return "warning"
        else:
            return "error"
    
    def _frame_to_time(self, frame_index: int, fps: float) -> float:
        """帧索引转换为时间"""
        return frame_index / fps if fps > 0 else 0.0

