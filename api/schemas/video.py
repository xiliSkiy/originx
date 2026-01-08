# -*- coding: utf-8 -*-
"""
视频相关的请求/响应模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VideoSegmentResponse(BaseModel):
    """视频片段响应"""
    start_frame: int = Field(description="起始帧")
    end_frame: int = Field(description="结束帧")
    start_time: float = Field(description="起始时间（秒）")
    end_time: float = Field(description="结束时间（秒）")
    duration: float = Field(description="持续时长（秒）")
    confidence: float = Field(description="置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class VideoDetectionResultResponse(BaseModel):
    """视频检测结果响应"""
    detector_name: str = Field(description="检测器名称")
    is_abnormal: bool = Field(description="是否异常")
    score: float = Field(description="检测得分")
    threshold: float = Field(description="判定阈值")
    confidence: float = Field(description="置信度")
    issue_type: str = Field(description="问题类型")
    severity: str = Field(description="严重程度")
    segments: List[VideoSegmentResponse] = Field(default_factory=list, description="异常片段")
    explanation: str = Field(description="结果解释")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    possible_causes: List[str] = Field(default_factory=list, description="可能原因")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="证据数据")
    process_time_ms: float = Field(description="处理耗时（毫秒）")
    frames_analyzed: int = Field(description="分析帧数")


class VideoIssueResponse(BaseModel):
    """视频问题响应"""
    issue_type: str = Field(description="问题类型")
    severity: str = Field(description="严重程度")
    start_time: float = Field(description="开始时间（秒）")
    end_time: float = Field(description="结束时间（秒）")
    duration: float = Field(description="持续时间（秒）")
    confidence: float = Field(description="置信度")
    description: str = Field(description="描述")


class VideoDiagnoseRequest(BaseModel):
    """视频诊断请求"""
    profile: str = Field(default="normal", description="配置模板: strict, normal, loose")
    detectors: Optional[List[str]] = Field(default=None, description="要使用的检测器")
    sample_strategy: str = Field(default="interval", description="采样策略: interval, scene, hybrid")
    sample_interval: float = Field(default=1.0, description="采样间隔（秒）")
    max_frames: int = Field(default=300, description="最大采样帧数")


class VideoDiagnoseResponse(BaseModel):
    """视频诊断响应"""
    video_path: str = Field(description="视频路径")
    video_id: str = Field(description="视频ID")
    width: int = Field(description="视频宽度")
    height: int = Field(description="视频高度")
    fps: float = Field(description="帧率")
    duration: float = Field(description="时长（秒）")
    frame_count: int = Field(description="总帧数")
    sampled_frames: int = Field(description="采样帧数")
    is_abnormal: bool = Field(description="是否异常")
    overall_score: float = Field(description="整体评分")
    primary_issue: Optional[str] = Field(default=None, description="主要问题")
    severity: str = Field(description="严重程度")
    issues: List[VideoIssueResponse] = Field(default_factory=list, description="问题列表")
    detection_results: List[VideoDetectionResultResponse] = Field(
        default_factory=list, description="检测器结果"
    )
    process_time_ms: float = Field(description="处理耗时（毫秒）")


class VideoBatchDiagnoseRequest(BaseModel):
    """批量视频诊断请求"""
    video_paths: List[str] = Field(description="视频文件路径列表")
    profile: str = Field(default="normal", description="配置模板")
    detectors: Optional[List[str]] = Field(default=None, description="要使用的检测器")


class VideoBatchDiagnoseResponse(BaseModel):
    """批量视频诊断响应"""
    total: int = Field(description="总数")
    success: int = Field(description="成功数")
    failed: int = Field(description="失败数")
    normal_count: int = Field(description="正常数")
    abnormal_count: int = Field(description="异常数")
    results: List[VideoDiagnoseResponse] = Field(description="诊断结果列表")
    process_time_ms: float = Field(description="总处理耗时（毫秒）")


class VideoDetectorInfo(BaseModel):
    """视频检测器信息"""
    name: str = Field(description="检测器名称")
    display_name: str = Field(description="显示名称")
    description: str = Field(description="描述")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")

