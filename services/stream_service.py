# -*- coding: utf-8 -*-
"""
流检测服务

管理多个流检测器的生命周期
"""

import threading
from typing import Dict, Optional, List, Any
from core.detectors.stream import StreamDetector
from config import get_config


class StreamService:
    """流检测服务"""
    
    def __init__(self):
        """初始化流检测服务"""
        self._streams: Dict[str, StreamDetector] = {}
        self._lock = threading.Lock()
        self.config = get_config()
    
    def start_stream(
        self,
        stream_url: str,
        stream_id: Optional[str] = None,
        stream_type: str = "rtsp",
        sample_interval: float = 1.0,
        detection_interval: float = 5.0,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        启动流检测
        
        Args:
            stream_url: 流地址
            stream_id: 流ID（可选）
            stream_type: 流类型
            sample_interval: 采样间隔
            detection_interval: 检测间隔
            config: 检测配置
            
        Returns:
            str: 流ID
        """
        with self._lock:
            # 检查是否已存在
            if stream_id and stream_id in self._streams:
                existing = self._streams[stream_id]
                if existing.is_running:
                    return stream_id
            
            # 创建新的流检测器
            detector = StreamDetector(
                stream_url=stream_url,
                stream_id=stream_id,
                stream_type=stream_type,
                sample_interval=sample_interval,
                detection_interval=detection_interval,
                config=config or {},
            )
            
            # 启动检测
            if detector.start():
                self._streams[detector.stream_id] = detector
                return detector.stream_id
            else:
                raise Exception("Failed to start stream detection")
    
    def stop_stream(self, stream_id: str) -> bool:
        """
        停止流检测
        
        Args:
            stream_id: 流ID
            
        Returns:
            bool: 是否成功停止
        """
        with self._lock:
            if stream_id in self._streams:
                detector = self._streams[stream_id]
                detector.stop()
                del self._streams[stream_id]
                return True
            return False
    
    def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        获取流状态
        
        Args:
            stream_id: 流ID
            
        Returns:
            流状态字典，如果不存在返回None
        """
        with self._lock:
            if stream_id in self._streams:
                return self._streams[stream_id].get_status()
            return None
    
    def get_stream_results(
        self,
        stream_id: str,
        limit: int = 100,
        since: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取流检测结果
        
        Args:
            stream_id: 流ID
            limit: 结果数量限制
            since: 起始时间
            
        Returns:
            检测结果字典，如果不存在返回None
        """
        with self._lock:
            if stream_id in self._streams:
                return self._streams[stream_id].get_results(limit=limit, since=since)
            return None
    
    def list_streams(self) -> List[Dict[str, Any]]:
        """
        列出所有流
        
        Returns:
            流列表
        """
        with self._lock:
            return [
                detector.get_status()
                for detector in self._streams.values()
            ]
    
    def stop_all(self) -> None:
        """停止所有流检测"""
        with self._lock:
            for detector in list(self._streams.values()):
                detector.stop()
            self._streams.clear()
