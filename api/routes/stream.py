# -*- coding: utf-8 -*-
"""
流检测 API 路由
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.stream_service import StreamService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])

# 全局流检测服务实例
_stream_service: Optional[StreamService] = None


def get_stream_service() -> StreamService:
    """获取流检测服务实例"""
    global _stream_service
    if _stream_service is None:
        _stream_service = StreamService()
    return _stream_service


class StreamStartRequest(BaseModel):
    """启动流检测请求"""
    stream_url: str = Field(..., description="流地址")
    stream_type: str = Field(default="rtsp", description="流类型 (rtsp/rtmp)")
    sample_interval: float = Field(default=1.0, description="采样间隔（秒）")
    detection_interval: float = Field(default=5.0, description="检测间隔（秒）")
    config: Optional[Dict[str, Any]] = Field(default=None, description="检测配置")


class StreamStartResponse(BaseModel):
    """启动流检测响应"""
    stream_id: str = Field(..., description="流ID")
    status: str = Field(..., description="状态")
    stream_url: str = Field(..., description="流地址")
    started_at: str = Field(..., description="启动时间")


@router.post("/start", response_model=StreamStartResponse)
async def start_stream(request: StreamStartRequest):
    """
    启动流检测
    
    Args:
        request: 启动请求
        
    Returns:
        启动响应
    """
    try:
        service = get_stream_service()
        stream_id = service.start_stream(
            stream_url=request.stream_url,
            stream_type=request.stream_type,
            sample_interval=request.sample_interval,
            detection_interval=request.detection_interval,
            config=request.config,
        )
        
        status = service.get_stream_status(stream_id)
        
        return StreamStartResponse(
            stream_id=stream_id,
            status=status["status"] if status else "running",
            stream_url=request.stream_url,
            started_at=status.get("last_detection_time") if status else "",
        )
    except Exception as e:
        logger.error(f"Failed to start stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50001,
                "message": "Failed to start stream",
                "details": str(e),
            },
        )


@router.post("/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """
    停止流检测
    
    Args:
        stream_id: 流ID
        
    Returns:
        停止响应
    """
    try:
        service = get_stream_service()
        success = service.stop_stream(stream_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Stream not found",
                    "details": f"Stream {stream_id} not found",
                },
            )
        
        return {
            "stream_id": stream_id,
            "status": "stopped",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50002,
                "message": "Failed to stop stream",
                "details": str(e),
            },
        )


@router.get("/{stream_id}/status")
async def get_stream_status(stream_id: str):
    """
    获取流检测状态
    
    Args:
        stream_id: 流ID
        
    Returns:
        流状态
    """
    try:
        service = get_stream_service()
        status = service.get_stream_status(stream_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Stream not found",
                    "details": f"Stream {stream_id} not found",
                },
            )
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stream status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50003,
                "message": "Failed to get stream status",
                "details": str(e),
            },
        )


@router.get("/{stream_id}/results")
async def get_stream_results(
    stream_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="结果数量限制"),
    since: Optional[str] = Query(default=None, description="起始时间（ISO格式）"),
):
    """
    获取流检测结果
    
    Args:
        stream_id: 流ID
        limit: 结果数量限制
        since: 起始时间
        
    Returns:
        检测结果
    """
    try:
        service = get_stream_service()
        results = service.get_stream_results(
            stream_id=stream_id,
            limit=limit,
            since=since,
        )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Stream not found",
                    "details": f"Stream {stream_id} not found",
                },
            )
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stream results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50004,
                "message": "Failed to get stream results",
                "details": str(e),
            },
        )


@router.get("/streams")
async def list_streams():
    """
    列出所有流
    
    Returns:
        流列表
    """
    try:
        service = get_stream_service()
        streams = service.list_streams()
        
        return {
            "streams": streams,
            "total": len(streams),
        }
    except Exception as e:
        logger.error(f"Failed to list streams: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50005,
                "message": "Failed to list streams",
                "details": str(e),
            },
        )
