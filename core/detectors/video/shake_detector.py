# -*- coding: utf-8 -*-
"""
视频抖动检测器

通过光流法或特征点跟踪检测画面整体位移
"""

import time
import cv2
import numpy as np
from typing import Any, Dict, List, Optional

from .base import BaseVideoDetector, VideoDetectionResult, VideoSegment


class ShakeDetector(BaseVideoDetector):
    """视频抖动检测器"""
    
    name = "shake"
    display_name = "视频抖动检测"
    description = "检测视频画面是否存在抖动/晃动"
    
    default_config = {
        "motion_threshold": 5.0,         # 运动向量阈值（像素）
        "variance_threshold": 10.0,      # 方差阈值
        "min_shake_duration": 0.5,       # 最小抖动持续时长（秒）
        "feature_count": 100,            # 跟踪特征点数量
        "min_feature_quality": 0.01,     # 特征点最小质量
        "min_feature_distance": 10,      # 特征点最小距离
        "use_subpixel": True,            # 是否使用亚像素精度
    }
    
    def detect(
        self,
        frames: List[np.ndarray],
        fps: float,
        timestamps: Optional[List[float]] = None
    ) -> VideoDetectionResult:
        """
        检测视频抖动
        
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
                process_time=time.time() - start_time
            )
        
        # 计算时间戳
        if timestamps is None:
            timestamps = [i / fps for i in range(len(frames))]
        
        # 计算运动向量
        motion_vectors = []
        shake_frames = []  # 记录抖动帧
        
        # 光流参数
        lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )
        
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        prev_points = cv2.goodFeaturesToTrack(
            prev_gray,
            maxCorners=self.config["feature_count"],
            qualityLevel=self.config["min_feature_quality"],
            minDistance=self.config["min_feature_distance"]
        )
        
        for i in range(1, len(frames)):
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            
            if prev_points is not None and len(prev_points) > 0:
                # 计算光流
                curr_points, status, _ = cv2.calcOpticalFlowPyrLK(
                    prev_gray, curr_gray, prev_points, None, **lk_params
                )
                
                if curr_points is not None:
                    # 获取有效点
                    valid_mask = status.flatten() == 1
                    valid_prev = prev_points[valid_mask]
                    valid_curr = curr_points[valid_mask]
                    
                    if len(valid_prev) > 0:
                        # 计算运动向量
                        motion = valid_curr - valid_prev
                        mean_motion = np.mean(motion, axis=0).flatten()
                        motion_std = np.std(motion, axis=0).flatten()
                        motion_magnitude = np.linalg.norm(mean_motion)
                        
                        motion_vectors.append({
                            "frame_index": i,
                            "timestamp": timestamps[i] if i < len(timestamps) else i / fps,
                            "motion_x": float(mean_motion[0]),
                            "motion_y": float(mean_motion[1]),
                            "magnitude": float(motion_magnitude),
                            "std_x": float(motion_std[0]),
                            "std_y": float(motion_std[1]),
                            "valid_points": len(valid_prev),
                        })
                        
                        # 检查是否为抖动帧
                        if motion_magnitude > self.config["motion_threshold"]:
                            shake_frames.append(i)
            
            # 更新特征点（每隔一定帧数重新检测）
            if i % 30 == 0 or prev_points is None or len(prev_points) < 10:
                prev_points = cv2.goodFeaturesToTrack(
                    curr_gray,
                    maxCorners=self.config["feature_count"],
                    qualityLevel=self.config["min_feature_quality"],
                    minDistance=self.config["min_feature_distance"]
                )
            else:
                prev_points = curr_points
            
            prev_gray = curr_gray
        
        # 分析抖动
        if len(motion_vectors) > 0:
            magnitudes = [mv["magnitude"] for mv in motion_vectors]
            motion_variance = float(np.var(magnitudes))
            max_motion = float(np.max(magnitudes))
            avg_motion = float(np.mean(magnitudes))
        else:
            motion_variance = 0.0
            max_motion = 0.0
            avg_motion = 0.0
        
        # 检测连续抖动段
        segments = self._detect_shake_segments(shake_frames, fps, timestamps)
        
        # 判断是否异常
        is_abnormal = motion_variance > self.config["variance_threshold"]
        
        return self._create_result(
            is_abnormal=is_abnormal,
            score=motion_variance,
            segments=segments,
            frames_count=len(frames),
            process_time=time.time() - start_time,
            extra_evidence={
                "motion_variance": motion_variance,
                "max_motion": max_motion,
                "avg_motion": avg_motion,
                "shake_frame_count": len(shake_frames),
                "shake_ratio": len(shake_frames) / len(frames) if frames else 0,
                "motion_samples": motion_vectors[:20],  # 只保存前20个采样
            }
        )
    
    def _detect_shake_segments(
        self,
        shake_frames: List[int],
        fps: float,
        timestamps: List[float]
    ) -> List[VideoSegment]:
        """检测连续抖动段"""
        if not shake_frames:
            return []
        
        segments = []
        segment_start = shake_frames[0]
        segment_end = shake_frames[0]
        
        for i in range(1, len(shake_frames)):
            if shake_frames[i] - shake_frames[i - 1] <= 5:  # 允许5帧间隔
                segment_end = shake_frames[i]
            else:
                # 保存当前段
                if segment_end > segment_start:
                    segment = self._create_segment(
                        segment_start, segment_end, fps, timestamps
                    )
                    if segment.duration >= self.config["min_shake_duration"]:
                        segments.append(segment)
                # 开始新段
                segment_start = shake_frames[i]
                segment_end = shake_frames[i]
        
        # 保存最后一段
        if segment_end > segment_start:
            segment = self._create_segment(
                segment_start, segment_end, fps, timestamps
            )
            if segment.duration >= self.config["min_shake_duration"]:
                segments.append(segment)
        
        return segments
    
    def _create_segment(
        self,
        start_frame: int,
        end_frame: int,
        fps: float,
        timestamps: List[float]
    ) -> VideoSegment:
        """创建抖动片段"""
        start_time = timestamps[start_frame] if start_frame < len(timestamps) else start_frame / fps
        end_time = timestamps[end_frame] if end_frame < len(timestamps) else end_frame / fps
        
        return VideoSegment(
            start_frame=start_frame,
            end_frame=end_frame,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            confidence=0.85,
            metadata={"shake_frames": end_frame - start_frame + 1}
        )
    
    def _create_result(
        self,
        is_abnormal: bool,
        score: float,
        segments: List[VideoSegment],
        frames_count: int,
        process_time: float,
        extra_evidence: Optional[Dict[str, Any]] = None
    ) -> VideoDetectionResult:
        """创建检测结果"""
        threshold = self.config["variance_threshold"]
        
        # 生成解释
        if is_abnormal:
            total_shake_duration = sum(seg.duration for seg in segments)
            explanation = f"检测到视频抖动，运动方差 {score:.2f}（阈值 {threshold}），共 {len(segments)} 处抖动段，总时长 {total_shake_duration:.2f} 秒"
        else:
            explanation = f"视频画面稳定，运动方差 {score:.2f}（阈值 {threshold}）"
        
        # 生成建议
        suggestions = []
        possible_causes = []
        if is_abnormal:
            suggestions = [
                "检查摄像头固定是否牢固",
                "检查安装支架是否稳定",
                "使用防抖功能或防抖支架",
                "检查是否有风或振动影响",
            ]
            possible_causes = [
                "摄像头固定不稳",
                "安装位置有振动",
                "风力影响",
                "人为干扰",
            ]
        
        evidence = {
            "config": self.config,
            "frames_analyzed": frames_count,
        }
        if extra_evidence:
            evidence.update(extra_evidence)
        
        return VideoDetectionResult(
            detector_name=self.name,
            is_abnormal=is_abnormal,
            score=score,
            threshold=threshold,
            confidence=0.85,
            issue_type="shake" if is_abnormal else "normal",
            severity=self._calculate_severity(score, threshold),
            segments=segments,
            explanation=explanation,
            suggestions=suggestions,
            possible_causes=possible_causes,
            evidence=evidence,
            process_time_ms=process_time * 1000,
            frames_analyzed=frames_count,
        )

