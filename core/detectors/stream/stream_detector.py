# -*- coding: utf-8 -*-
"""
RTSP/RTMP 流检测器

支持实时视频流的检测，包括画面冻结、场景变换、抖动等
"""

import cv2
import threading
import time
import uuid
from queue import Queue
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import numpy as np

from core.pipeline import DiagnosisPipeline
from core.video_pipeline import VideoDiagnosisPipeline


class StreamDetector:
    """实时流检测器"""
    
    def __init__(
        self,
        stream_url: str,
        stream_id: Optional[str] = None,
        stream_type: str = "rtsp",  # rtsp | rtmp
        sample_interval: float = 1.0,  # 采样间隔（秒）
        detection_interval: float = 5.0,  # 检测间隔（秒）
        buffer_size: int = 30,  # 帧缓冲区大小
        detection_callback: Optional[Callable] = None,  # 检测结果回调
        reconnect_interval: int = 5,  # 重连间隔（秒）
        max_reconnect_attempts: int = 10,  # 最大重连次数
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化流检测器
        
        Args:
            stream_url: 流地址
            stream_id: 流ID（可选，自动生成）
            stream_type: 流类型（rtsp/rtmp）
            sample_interval: 采样间隔（秒）
            detection_interval: 检测间隔（秒）
            buffer_size: 帧缓冲区大小
            detection_callback: 检测结果回调函数
            reconnect_interval: 重连间隔（秒）
            max_reconnect_attempts: 最大重连次数
            config: 检测配置
        """
        self.stream_id = stream_id or str(uuid.uuid4())
        self.stream_url = stream_url
        self.stream_type = stream_type
        self.sample_interval = sample_interval
        self.detection_interval = detection_interval
        self.buffer_size = buffer_size
        self.detection_callback = detection_callback
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.config = config or {}
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_buffer: Queue = Queue(maxsize=buffer_size)
        self.is_running = False
        self.is_connected = False
        self.reconnect_count = 0
        
        # 线程
        self.capture_thread: Optional[threading.Thread] = None
        self.detection_thread: Optional[threading.Thread] = None
        
        # 锁
        self._lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            "frames_received": 0,
            "frames_detected": 0,
            "connection_errors": 0,
            "last_frame_time": None,
            "start_time": None,
            "fps": 0.0,
        }
        
        # 初始化检测流水线
        self.image_pipeline = DiagnosisPipeline(self.config)
        # 视频检测器在检测时动态创建
        
        # 检测结果历史
        self.detection_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
    
    def start(self) -> bool:
        """
        启动流检测
        
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self.is_running:
                return False
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            
            if not self._connect():
                self.is_running = False
                return False
            
            # 启动帧捕获线程
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name=f"StreamCapture-{self.stream_id}"
            )
            self.capture_thread.start()
            
            # 启动检测线程
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True,
                name=f"StreamDetection-{self.stream_id}"
            )
            self.detection_thread.start()
            
            return True
    
    def stop(self) -> None:
        """停止流检测"""
        with self._lock:
            self.is_running = False
            
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.is_connected = False
        
        # 等待线程结束
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2.0)
    
    def _connect(self) -> bool:
        """连接流"""
        try:
            # RTSP 配置
            if self.stream_type == "rtsp":
                # 使用 TCP 传输（更稳定）
                rtsp_url = self.stream_url
                if "?tcp" not in rtsp_url and "tcp=" not in rtsp_url:
                    separator = "&" if "?" in rtsp_url else "?"
                    rtsp_url = f"{self.stream_url}{separator}tcp=1"
                
                self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                # 设置缓冲区大小（减少延迟）
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # RTMP
                self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if self.cap.isOpened():
                self.is_connected = True
                self.reconnect_count = 0
                return True
            else:
                raise Exception("Failed to open stream")
        except Exception as e:
            self.is_connected = False
            self.stats["connection_errors"] += 1
            return False
    
    def _capture_loop(self) -> None:
        """帧捕获循环"""
        last_sample_time = 0
        
        while self.is_running:
            try:
                if not self.is_connected:
                    # 尝试重连
                    if self.reconnect_count < self.max_reconnect_attempts:
                        time.sleep(self.reconnect_interval)
                        if self._connect():
                            continue
                        else:
                            self.reconnect_count += 1
                            continue
                    else:
                        # 超过最大重连次数，停止
                        self.is_running = False
                        break
                
                ret, frame = self.cap.read()
                if not ret:
                    # 读取失败，标记为断开
                    self.is_connected = False
                    self.reconnect_count += 1
                    continue
                
                # 采样控制
                current_time = time.time()
                if current_time - last_sample_time >= self.sample_interval:
                    # 添加到缓冲区（如果已满，移除最旧的）
                    if self.frame_buffer.full():
                        try:
                            self.frame_buffer.get_nowait()
                        except:
                            pass
                    
                    self.frame_buffer.put({
                        "frame": frame.copy(),
                        "timestamp": current_time,
                        "frame_index": self.stats["frames_received"]
                    })
                    
                    self.stats["frames_received"] += 1
                    self.stats["last_frame_time"] = current_time
                    last_sample_time = current_time
                    
                    # 计算 FPS
                    if self.stats["start_time"]:
                        elapsed = current_time - self.stats["start_time"]
                        if elapsed > 0:
                            self.stats["fps"] = self.stats["frames_received"] / elapsed
                
            except Exception as e:
                self.is_connected = False
                self.stats["connection_errors"] += 1
                time.sleep(1)
    
    def _detection_loop(self) -> None:
        """检测循环"""
        last_detection_time = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # 检测间隔控制
                if current_time - last_detection_time < self.detection_interval:
                    time.sleep(0.1)
                    continue
                
                # 从缓冲区获取帧
                buffer_copy = list(self.frame_buffer.queue)
                
                if len(buffer_copy) == 0:
                    time.sleep(0.1)
                    continue
                
                # 获取最近N帧用于视频检测
                recent_frames = buffer_copy[-min(30, len(buffer_copy)):]
                frames = [item["frame"] for item in recent_frames]
                
                if len(frames) == 0:
                    continue
                
                # 执行检测
                # 单帧检测（图像检测器）
                latest_frame = frames[-1]
                image_result = self.image_pipeline.detect(
                    latest_frame,
                    level="standard"
                )
                
                # 多帧检测（视频检测器）
                # 注意：VideoDiagnosisPipeline 需要视频文件路径，这里我们直接使用检测器
                from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
                fps = self.stats["fps"] if self.stats["fps"] > 0 else 25.0
                
                # 使用视频检测器直接检测帧
                video_results = []
                for detector_cls in [FreezeDetector, SceneChangeDetector, ShakeDetector]:
                    detector = detector_cls()
                    result = detector.detect(frames, fps=fps)
                    video_results.append(result)
                
                # 聚合视频检测结果
                video_result = {
                    "is_abnormal": any(r.is_abnormal for r in video_results),
                    "results": [r.to_dict() for r in video_results],
                }
                
                # 聚合结果
                video_is_abnormal = video_result.get("is_abnormal", False) if isinstance(video_result, dict) else False
                is_abnormal = image_result.is_abnormal or video_is_abnormal
                
                result = {
                    "stream_id": self.stream_id,
                    "stream_url": self.stream_url,
                    "timestamp": datetime.now().isoformat(),
                    "is_connected": self.is_connected,
                    "fps": self.stats["fps"],
                    "is_abnormal": is_abnormal,
                    "image_detection": image_result.to_dict() if hasattr(image_result, 'to_dict') else {},
                    "video_detection": video_result if isinstance(video_result, dict) else {},
                    "primary_issue": image_result.primary_issue if hasattr(image_result, 'primary_issue') else None,
                    "severity": str(image_result.severity) if hasattr(image_result, 'severity') else "normal",
                }
                
                self.stats["frames_detected"] += 1
                last_detection_time = current_time
                
                # 保存到历史记录
                self.detection_history.append(result)
                if len(self.detection_history) > self.max_history_size:
                    self.detection_history.pop(0)
                
                # 回调通知
                if self.detection_callback:
                    try:
                        self.detection_callback(result)
                    except Exception as e:
                        pass  # 忽略回调错误
                
            except Exception as e:
                time.sleep(1)
    
    def get_status(self) -> Dict[str, Any]:
        """获取流状态"""
        with self._lock:
            return {
                "stream_id": self.stream_id,
                "stream_url": self.stream_url,
                "stream_type": self.stream_type,
                "status": "running" if self.is_running else "stopped",
                "is_connected": self.is_connected,
                "fps": self.stats["fps"],
                "frames_received": self.stats["frames_received"],
                "frames_detected": self.stats["frames_detected"],
                "last_detection_time": self.detection_history[-1]["timestamp"] if self.detection_history else None,
                "connection_errors": self.stats["connection_errors"],
                "reconnect_count": self.reconnect_count,
            }
    
    def get_results(self, limit: int = 100, since: Optional[str] = None) -> Dict[str, Any]:
        """
        获取检测结果
        
        Args:
            limit: 返回结果数量限制
            since: 起始时间（ISO格式）
            
        Returns:
            检测结果字典
        """
        results = self.detection_history.copy()
        
        # 时间过滤
        if since:
            try:
                since_time = datetime.fromisoformat(since)
                results = [
                    r for r in results
                    if datetime.fromisoformat(r["timestamp"]) >= since_time
                ]
            except:
                pass
        
        # 限制数量
        results = results[-limit:]
        
        return {
            "stream_id": self.stream_id,
            "results": results,
            "total": len(self.detection_history),
        }
