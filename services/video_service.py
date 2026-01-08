# -*- coding: utf-8 -*-
"""
视频诊断服务

提供视频诊断的业务逻辑封装
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from core.video_pipeline import VideoDiagnosisPipeline, VideoDiagnosisResult
from core.detectors.video.base import BaseVideoDetector
from core.utils.video_utils import SampleStrategy

logger = logging.getLogger(__name__)


class VideoService:
    """视频诊断服务"""
    
    def __init__(
        self,
        sample_strategy: str = "interval",
        sample_interval: float = 1.0,
        max_frames: int = 300,
        detector_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        初始化视频服务
        
        Args:
            sample_strategy: 采样策略 (interval, scene, hybrid, all)
            sample_interval: 采样间隔（秒）
            max_frames: 最大采样帧数
            detector_configs: 检测器配置
        """
        self.sample_strategy = self._parse_strategy(sample_strategy)
        self.sample_interval = sample_interval
        self.max_frames = max_frames
        self.detector_configs = detector_configs or {}
    
    def _parse_strategy(self, strategy: str) -> SampleStrategy:
        """解析采样策略"""
        strategy_map = {
            "interval": SampleStrategy.INTERVAL,
            "scene": SampleStrategy.SCENE,
            "hybrid": SampleStrategy.HYBRID,
            "all": SampleStrategy.ALL,
        }
        return strategy_map.get(strategy.lower(), SampleStrategy.INTERVAL)
    
    def diagnose_video(
        self,
        video_path: str,
        detectors: Optional[List[str]] = None,
        profile: str = "normal",
    ) -> VideoDiagnosisResult:
        """
        诊断单个视频
        
        Args:
            video_path: 视频文件路径
            detectors: 要使用的检测器名称列表，None 表示使用全部
            profile: 配置模板 (strict, normal, loose)
            
        Returns:
            VideoDiagnosisResult: 诊断结果
        """
        # 验证文件存在
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 创建流水线
        pipeline = self._create_pipeline(detectors, profile)
        
        # 执行诊断
        result = pipeline.diagnose(video_path)
        
        return result
    
    def diagnose_batch(
        self,
        video_paths: List[str],
        detectors: Optional[List[str]] = None,
        profile: str = "normal",
    ) -> List[VideoDiagnosisResult]:
        """
        批量诊断视频
        
        Args:
            video_paths: 视频文件路径列表
            detectors: 要使用的检测器名称列表
            profile: 配置模板
            
        Returns:
            诊断结果列表
        """
        results = []
        
        # 创建流水线（复用同一个流水线）
        pipeline = self._create_pipeline(detectors, profile)
        
        for video_path in video_paths:
            try:
                result = pipeline.diagnose(video_path)
                results.append(result)
            except Exception as e:
                logger.error(f"视频诊断失败: {video_path}, 错误: {e}")
                # 创建错误结果
                results.append(VideoDiagnosisResult(
                    video_path=video_path,
                    video_id=Path(video_path).stem,
                    is_abnormal=True,
                    overall_score=0.0,
                    primary_issue="error",
                    severity="error",
                ))
        
        return results
    
    def _create_pipeline(
        self,
        detector_names: Optional[List[str]],
        profile: str,
    ) -> VideoDiagnosisPipeline:
        """创建诊断流水线"""
        from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
        
        # 检测器映射
        detector_map = {
            "freeze": FreezeDetector,
            "scene_change": SceneChangeDetector,
            "shake": ShakeDetector,
        }
        
        # 选择检测器
        if detector_names:
            detector_classes = [
                detector_map[name] for name in detector_names
                if name in detector_map
            ]
        else:
            detector_classes = list(detector_map.values())
        
        # 应用配置模板
        configs = self._apply_profile(profile)
        
        # 创建流水线
        return VideoDiagnosisPipeline(
            detectors=detector_classes,
            detector_configs=configs,
            sample_strategy=self.sample_strategy,
            sample_interval=self.sample_interval,
            max_frames=self.max_frames,
        )
    
    def _apply_profile(self, profile: str) -> Dict[str, Dict[str, Any]]:
        """应用配置模板"""
        configs = {}
        
        if profile == "strict":
            configs = {
                "freeze": {
                    "similarity_threshold": 0.95,
                    "min_freeze_duration": 0.5,
                },
                "scene_change": {
                    "histogram_threshold": 0.3,
                    "max_changes_per_minute": 3,
                },
                "shake": {
                    "variance_threshold": 5.0,
                },
            }
        elif profile == "loose":
            configs = {
                "freeze": {
                    "similarity_threshold": 0.99,
                    "min_freeze_duration": 2.0,
                },
                "scene_change": {
                    "histogram_threshold": 0.5,
                    "max_changes_per_minute": 10,
                },
                "shake": {
                    "variance_threshold": 20.0,
                },
            }
        # normal 使用默认配置
        
        # 合并用户自定义配置
        for name, user_config in self.detector_configs.items():
            if name in configs:
                configs[name].update(user_config)
            else:
                configs[name] = user_config
        
        return configs
    
    def get_available_detectors(self) -> List[Dict[str, Any]]:
        """获取可用的视频检测器列表"""
        from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
        
        detectors = [FreezeDetector(), SceneChangeDetector(), ShakeDetector()]
        return [d.get_info() for d in detectors]

