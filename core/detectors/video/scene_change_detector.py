# -*- coding: utf-8 -*-
"""
场景变换检测器

检测视频中是否发生非预期的场景切换
"""

import time
import cv2
import numpy as np
from typing import Any, Dict, List, Optional

from .base import BaseVideoDetector, VideoDetectionResult, VideoSegment


class SceneChangeDetector(BaseVideoDetector):
    """场景变换检测器"""
    
    name = "scene_change"
    display_name = "场景变换检测"
    description = "检测视频是否发生非预期的场景切换"
    
    default_config = {
        "histogram_threshold": 0.4,      # 直方图差异阈值
        "edge_threshold": 0.3,           # 边缘变化阈值
        "min_scene_duration": 2.0,       # 最小场景持续时长（秒）
        "max_changes_per_minute": 5,     # 每分钟最大变化次数（超过视为异常）
        "use_edge_detection": True,      # 是否使用边缘检测辅助判断
        "combine_method": "or",          # 组合方法: and | or
    }
    
    def detect(
        self,
        frames: List[np.ndarray],
        fps: float,
        timestamps: Optional[List[float]] = None
    ) -> VideoDetectionResult:
        """
        检测场景变换
        
        Args:
            frames: 帧列表
            fps: 视频帧率
            timestamps: 每帧的时间戳
            
        Returns:
            VideoDetectionResult: 检测结果
        """
        start_time = time.time()
        
        if len(frames) < 2:
            return self._create_result(
                is_abnormal=False,
                score=0.0,
                segments=[],
                frames_count=len(frames),
                video_duration=0.0,
                process_time=time.time() - start_time
            )
        
        # 计算时间戳
        if timestamps is None:
            timestamps = [i / fps for i in range(len(frames))]
        
        video_duration = timestamps[-1] - timestamps[0] if timestamps else len(frames) / fps
        
        # 检测场景变化
        scene_changes = []
        hist_diffs = []
        edge_diffs = []
        
        for i in range(1, len(frames)):
            prev_frame = frames[i - 1]
            curr_frame = frames[i]
            
            # 计算直方图差异
            hist_diff = self._histogram_difference(prev_frame, curr_frame)
            hist_diffs.append(hist_diff)
            
            # 计算边缘差异（可选）
            edge_diff = 0.0
            if self.config["use_edge_detection"]:
                edge_diff = self._edge_difference(prev_frame, curr_frame)
                edge_diffs.append(edge_diff)
            
            # 判断是否为场景变化
            is_scene_change = False
            if self.config["combine_method"] == "and":
                is_scene_change = (
                    hist_diff > self.config["histogram_threshold"] and
                    edge_diff > self.config["edge_threshold"]
                )
            else:  # or
                is_scene_change = (
                    hist_diff > self.config["histogram_threshold"] or
                    (self.config["use_edge_detection"] and edge_diff > self.config["edge_threshold"])
                )
            
            if is_scene_change:
                timestamp = timestamps[i] if i < len(timestamps) else i / fps
                scene_changes.append({
                    "frame_index": i,
                    "timestamp": timestamp,
                    "histogram_diff": hist_diff,
                    "edge_diff": edge_diff,
                })
        
        # 将场景变化点转换为片段
        segments = self._changes_to_segments(scene_changes, fps, timestamps)
        
        # 计算每分钟变化次数
        changes_per_minute = (len(scene_changes) / video_duration * 60) if video_duration > 0 else 0
        
        # 判断是否异常（变化过于频繁）
        is_abnormal = changes_per_minute > self.config["max_changes_per_minute"]
        
        return self._create_result(
            is_abnormal=is_abnormal,
            score=changes_per_minute,
            segments=segments,
            frames_count=len(frames),
            video_duration=video_duration,
            process_time=time.time() - start_time,
            extra_evidence={
                "scene_change_count": len(scene_changes),
                "changes_per_minute": changes_per_minute,
                "avg_histogram_diff": float(np.mean(hist_diffs)) if hist_diffs else 0.0,
                "max_histogram_diff": float(np.max(hist_diffs)) if hist_diffs else 0.0,
                "change_points": scene_changes[:20],  # 只保存前20个变化点
            }
        )
    
    def _histogram_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算直方图差异"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # 使用 Bhattacharyya 距离
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
    
    def _edge_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算边缘差异"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 使用 Canny 边缘检测
        edges1 = cv2.Canny(gray1, 50, 150)
        edges2 = cv2.Canny(gray2, 50, 150)
        
        # 计算边缘图的差异
        diff = cv2.absdiff(edges1, edges2)
        
        # 计算差异比例
        return np.mean(diff) / 255.0
    
    def _changes_to_segments(
        self,
        changes: List[Dict],
        fps: float,
        timestamps: List[float]
    ) -> List[VideoSegment]:
        """将变化点转换为片段"""
        segments = []
        
        for change in changes:
            frame_idx = change["frame_index"]
            timestamp = change["timestamp"]
            
            segments.append(VideoSegment(
                start_frame=frame_idx,
                end_frame=frame_idx,
                start_time=timestamp,
                end_time=timestamp,
                duration=0.0,  # 场景变化是瞬时的
                confidence=min(change["histogram_diff"] / self.config["histogram_threshold"], 1.0),
                metadata={
                    "histogram_diff": change["histogram_diff"],
                    "edge_diff": change["edge_diff"],
                }
            ))
        
        return segments
    
    def _create_result(
        self,
        is_abnormal: bool,
        score: float,
        segments: List[VideoSegment],
        frames_count: int,
        video_duration: float,
        process_time: float,
        extra_evidence: Optional[Dict[str, Any]] = None
    ) -> VideoDetectionResult:
        """创建检测结果"""
        threshold = self.config["max_changes_per_minute"]
        
        # 生成解释
        change_count = len(segments)
        if is_abnormal:
            explanation = f"检测到场景变换过于频繁，每分钟 {score:.1f} 次变化，共 {change_count} 处"
        else:
            if change_count > 0:
                explanation = f"检测到 {change_count} 处场景变换，频率正常（每分钟 {score:.1f} 次）"
            else:
                explanation = "未检测到明显的场景变换"
        
        # 生成建议
        suggestions = []
        possible_causes = []
        if is_abnormal:
            suggestions = [
                "检查视频源是否稳定",
                "确认摄像头是否被移动或干扰",
                "检查视频信号是否受到干扰",
            ]
            possible_causes = [
                "摄像头被频繁移动",
                "视频信号切换器故障",
                "视频源不稳定",
                "光线变化剧烈",
            ]
        
        evidence = {
            "config": self.config,
            "frames_analyzed": frames_count,
            "video_duration": video_duration,
        }
        if extra_evidence:
            evidence.update(extra_evidence)
        
        return VideoDetectionResult(
            detector_name=self.name,
            is_abnormal=is_abnormal,
            score=score,
            threshold=threshold,
            confidence=0.9,
            issue_type="scene_change" if is_abnormal else "normal",
            severity=self._calculate_severity(score, threshold),
            segments=segments,
            explanation=explanation,
            suggestions=suggestions,
            possible_causes=possible_causes,
            evidence=evidence,
            process_time_ms=process_time * 1000,
            frames_analyzed=frames_count,
        )

