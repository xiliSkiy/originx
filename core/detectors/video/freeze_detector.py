# -*- coding: utf-8 -*-
"""
画面冻结检测器

检测视频中是否存在画面冻结（连续帧高度相似）的情况
"""

import time
import cv2
import numpy as np
from typing import Any, Dict, List, Optional

from .base import BaseVideoDetector, VideoDetectionResult, VideoSegment


class FreezeDetector(BaseVideoDetector):
    """画面冻结检测器"""
    
    name = "freeze"
    display_name = "画面冻结检测"
    description = "检测视频画面是否存在冻结/卡顿"
    
    default_config = {
        "similarity_threshold": 0.98,    # 帧相似度阈值
        "min_freeze_frames": 30,          # 最小冻结帧数
        "min_freeze_duration": 1.0,       # 最小冻结时长（秒）
        "method": "histogram",            # 相似度计算方法: histogram | mse
        "ignore_black_frames": True,      # 是否忽略黑屏帧
        "black_threshold": 10,            # 黑屏判定阈值
    }
    
    def detect(
        self,
        frames: List[np.ndarray],
        fps: float,
        timestamps: Optional[List[float]] = None
    ) -> VideoDetectionResult:
        """
        检测画面冻结
        
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
        
        # 检测冻结段
        freeze_segments = []
        current_freeze_start = None
        consecutive_similar = 0
        similarity_scores = []
        
        for i in range(1, len(frames)):
            prev_frame = frames[i - 1]
            curr_frame = frames[i]
            
            # 检查是否为黑屏
            if self.config["ignore_black_frames"]:
                if self._is_black_frame(prev_frame) or self._is_black_frame(curr_frame):
                    # 重置冻结检测
                    if consecutive_similar >= self.config["min_freeze_frames"]:
                        freeze_segments.append(self._create_segment(
                            current_freeze_start, i - 1, fps, timestamps
                        ))
                    current_freeze_start = None
                    consecutive_similar = 0
                    continue
            
            # 计算帧相似度
            similarity = self._calculate_similarity(prev_frame, curr_frame)
            similarity_scores.append(similarity)
            
            if similarity > self.config["similarity_threshold"]:
                # 帧相似，可能是冻结
                if current_freeze_start is None:
                    current_freeze_start = i - 1
                consecutive_similar += 1
            else:
                # 帧不相似，检查是否形成冻结段
                if consecutive_similar >= self.config["min_freeze_frames"]:
                    segment = self._create_segment(
                        current_freeze_start, i - 1, fps, timestamps
                    )
                    if segment.duration >= self.config["min_freeze_duration"]:
                        freeze_segments.append(segment)
                current_freeze_start = None
                consecutive_similar = 0
        
        # 处理结尾的冻结段
        if consecutive_similar >= self.config["min_freeze_frames"]:
            segment = self._create_segment(
                current_freeze_start, len(frames) - 1, fps, timestamps
            )
            if segment.duration >= self.config["min_freeze_duration"]:
                freeze_segments.append(segment)
        
        # 计算总冻结时长
        total_freeze_duration = sum(seg.duration for seg in freeze_segments)
        
        # 计算平均相似度
        avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.0
        
        return self._create_result(
            is_abnormal=len(freeze_segments) > 0,
            score=total_freeze_duration,
            segments=freeze_segments,
            frames_count=len(frames),
            process_time=time.time() - start_time,
            extra_evidence={
                "freeze_count": len(freeze_segments),
                "total_freeze_duration": total_freeze_duration,
                "avg_similarity": float(avg_similarity),
                "max_freeze_duration": max((seg.duration for seg in freeze_segments), default=0.0),
            }
        )
    
    def _calculate_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算两帧的相似度"""
        if self.config["method"] == "mse":
            return self._mse_similarity(frame1, frame2)
        else:
            return self._histogram_similarity(frame1, frame2)
    
    def _histogram_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """直方图相似度"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # 使用相关性比较
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # 归一化到 0-1
        return (correlation + 1) / 2
    
    def _mse_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """MSE 相似度"""
        # 转换为灰度并调整大小以加快计算
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 缩小图像以加快计算
        small1 = cv2.resize(gray1, (160, 120))
        small2 = cv2.resize(gray2, (160, 120))
        
        mse = np.mean((small1.astype(float) - small2.astype(float)) ** 2)
        
        # 转换为相似度
        similarity = 1 - (mse / 65025)
        return max(0, similarity)
    
    def _is_black_frame(self, frame: np.ndarray) -> bool:
        """判断是否为黑屏帧"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) < self.config["black_threshold"]
    
    def _create_segment(
        self,
        start_frame: int,
        end_frame: int,
        fps: float,
        timestamps: List[float]
    ) -> VideoSegment:
        """创建冻结片段"""
        start_time = timestamps[start_frame] if start_frame < len(timestamps) else start_frame / fps
        end_time = timestamps[end_frame] if end_frame < len(timestamps) else end_frame / fps
        
        return VideoSegment(
            start_frame=start_frame,
            end_frame=end_frame,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            confidence=0.95,
            metadata={"freeze_frames": end_frame - start_frame + 1}
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
        threshold = self.config["min_freeze_duration"]
        
        # 生成解释
        if is_abnormal:
            explanation = f"检测到 {len(segments)} 处画面冻结，总冻结时长 {score:.2f} 秒"
        else:
            explanation = "未检测到画面冻结"
        
        # 生成建议
        suggestions = []
        possible_causes = []
        if is_abnormal:
            suggestions = [
                "检查视频源设备是否正常工作",
                "检查视频传输链路是否稳定",
                "检查编码器设置是否正确",
            ]
            possible_causes = [
                "摄像头设备故障",
                "网络传输中断",
                "编码器处理延迟",
                "存储设备写入问题",
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
            confidence=0.95 if is_abnormal else 1.0,
            issue_type="freeze" if is_abnormal else "normal",
            severity=self._calculate_severity(score, threshold),
            segments=segments,
            explanation=explanation,
            suggestions=suggestions,
            possible_causes=possible_causes,
            evidence=evidence,
            process_time_ms=process_time * 1000,
            frames_analyzed=frames_count,
        )

